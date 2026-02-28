"""
Hierarchical document tree indexing, inspired by PageIndex
(https://github.com/VectifyAI/PageIndex).

PageIndex's core insight: "similarity ≠ relevance — what we truly need in
retrieval is relevance, and that requires reasoning."  It replaces flat
vector-chunk retrieval with a hierarchical tree that mirrors how an expert
navigates a document (TOC → section → sub-section).

This implementation ports the concept to the existing Gemini stack:

  1. **TOC extraction** — PyMuPDF's native `get_toc()` first; if that is
     empty, Gemini analyses the first few pages to reconstruct the outline.
  2. **Tree construction** — Sections are assigned page ranges from adjacent
     TOC entries.  Depth ≤ 3 by default (mirrors PageIndex defaults).
  3. **Section summaries** — Each node with more than `SUMMARY_CHAR_THRESHOLD`
     chars gets a 1-sentence Gemini summary (parallel async calls).
  4. **Document description** — A single top-level description from Gemini.

Output tree shape (matches PageIndex JSON format):

    {
        "title":       "Full document title",
        "description": "One-paragraph document overview",
        "total_pages": 42,
        "children": [
            {
                "id":      "1",
                "title":   "1. Introduction",
                "page_start": 1,
                "page_end":   5,
                "summary": "This section introduces …",
                "children": [ … ]
            },
            …
        ]
    }

The tree is stored in DocumentMetadata.metadata_json["page_index"].
It is also used by /ai/chat to supply structured, section-level context
when a specific document is targeted.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Characters of section text required before we bother summarising
SUMMARY_CHAR_THRESHOLD = 300
# Maximum depth of TOC levels to include (PageIndex default is 3)
MAX_DEPTH = 3
# Pages of text sent to Gemini for "infer TOC" fallback
INFER_TOC_PAGES = 10
# Characters per page sent to Gemini for the summary pass
SUMMARY_CHARS_PER_SECTION = 2_000


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_native_toc(pdf_path: str) -> list[tuple[int, str, int]]:
    """
    Use PyMuPDF to read the PDF's embedded TOC.

    Returns a list of (level, title, page_1indexed) tuples — the same format
    PyMuPDF's `get_toc()` produces.  An empty list means no native TOC.
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        toc = doc.get_toc(simple=True)  # [(level, title, page), …]
        doc.close()
        return [(lvl, title, page) for lvl, title, page in toc if lvl <= MAX_DEPTH]
    except Exception as exc:
        logger.debug("PyMuPDF TOC extraction failed: %s", exc)
        return []


def _extract_page_texts(pdf_path: str, max_pages: int | None = None) -> list[str]:
    """
    Return a list of text strings, one per page (up to *max_pages*).
    Uses pdfplumber (already in requirements) as the primary extractor.
    Falls back to PyMuPDF if pdfplumber is not available.
    """
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            pages = pdf.pages[:max_pages] if max_pages else pdf.pages
            return [p.extract_text() or "" for p in pages]
    except Exception:
        pass

    try:
        import fitz

        doc = fitz.open(pdf_path)
        pages = list(doc)[:max_pages] if max_pages else list(doc)
        texts = [p.get_text() for p in pages]
        doc.close()
        return texts
    except Exception as exc:
        logger.debug("Page text extraction failed: %s", exc)
        return []


async def _infer_toc_from_gemini(
    first_pages_text: str, api_key: str
) -> list[tuple[int, str, int]]:
    """
    Ask Gemini to reconstruct a table of contents from the opening pages.
    Returns the same (level, title, page) list format as PyMuPDF.
    """
    prompt = (
        "Sei un assistente per l'analisi di documenti aziendali italiani.\n"
        "Leggi il seguente testo estratto dalle prime pagine di un documento PDF "
        "e restituisci SOLO un JSON valido (nessun markdown) con questa struttura:\n"
        '{"toc": [{"level": 1, "title": "Nome sezione", "page": 1}, ...]}\n\n'
        "Regole:\n"
        "- Includi solo sezioni reali presenti nel testo.\n"
        "- level 1 = sezione principale, level 2 = sottosezione, level 3 = sotto-sottosezione.\n"
        "- page è il numero di pagina (1-based) dove la sezione inizia.\n"
        "- Se non trovi una struttura chiara restituisci {\"toc\": []}.\n\n"
        f"TESTO:\n{first_pages_text[:8000]}"
    )

    def _call() -> list[tuple[int, str, int]]:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        response = model.generate_content(prompt)
        content = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(content)
        return [
            (item["level"], item["title"], item["page"])
            for item in data.get("toc", [])
            if item.get("level", 0) <= MAX_DEPTH
        ]

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)
    except Exception as exc:
        logger.warning("Gemini TOC inference failed: %s", exc)
        return []


def _assign_page_ranges(
    toc: list[tuple[int, str, int]], total_pages: int
) -> list[dict[str, Any]]:
    """
    Convert a flat TOC list into a nested tree with page_start / page_end.
    Each node's page_end = (next sibling or parent's next sibling start) - 1.
    """
    if not toc:
        return []

    nodes: list[dict[str, Any]] = []
    for i, (level, title, page_start) in enumerate(toc):
        # Find where this section ends: the start of the next entry at the
        # same or higher level (lower number = higher in hierarchy)
        page_end = total_pages
        for j in range(i + 1, len(toc)):
            next_level, _, next_page = toc[j]
            if next_level <= level:
                page_end = next_page - 1
                break

        nodes.append(
            {
                "_level": level,
                "title": title,
                "page_start": max(1, page_start),
                "page_end": max(page_start, page_end),
                "summary": "",
                "children": [],
            }
        )

    # Build tree by nesting children
    root_nodes: list[dict] = []
    stack: list[dict] = []  # ancestors from root to current

    for node in nodes:
        lvl = node.pop("_level")
        # Pop stack until parent level < current level
        while stack and stack[-1]["_lvl"] >= lvl:
            stack.pop()
        if stack:
            stack[-1]["node"]["children"].append(node)
        else:
            root_nodes.append(node)
        stack.append({"_lvl": lvl, "node": node})

    return root_nodes


def _flatten_tree(tree: list[dict], result: list | None = None) -> list[dict]:
    """Flatten the nested tree into a list for batch processing."""
    if result is None:
        result = []
    for node in tree:
        result.append(node)
        _flatten_tree(node.get("children", []), result)
    return result


def _add_ids(tree: list[dict], prefix: str = "") -> None:
    """Assign hierarchical IDs (1, 1.1, 1.1.2, …) in-place."""
    for i, node in enumerate(tree, start=1):
        node["id"] = f"{prefix}{i}" if not prefix else f"{prefix}.{i}"
        _add_ids(node.get("children", []), node["id"])


async def _add_summaries(
    nodes: list[dict],
    page_texts: list[str],
    api_key: str,
) -> None:
    """
    For each node whose text span exceeds SUMMARY_CHAR_THRESHOLD generate a
    1-sentence summary using Gemini.  All nodes are processed concurrently.
    """

    async def _summarise_node(node: dict) -> None:
        start = node["page_start"] - 1  # 0-based index
        end = node["page_end"]  # exclusive
        section_text = " ".join(page_texts[start:end])[:SUMMARY_CHARS_PER_SECTION]

        if len(section_text.strip()) < SUMMARY_CHAR_THRESHOLD:
            return

        prompt = (
            f"Riassumi in una sola frase in italiano il contenuto di questa sezione "
            f"di documento aziendale intitolata \"{node['title']}\":\n\n{section_text}"
        )

        def _call() -> str:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("models/gemini-1.5-flash")
            return model.generate_content(prompt).text.strip()

        try:
            loop = asyncio.get_event_loop()
            node["summary"] = await loop.run_in_executor(None, _call)
        except Exception as exc:
            logger.debug("Summary generation failed for '%s': %s", node["title"], exc)

    await asyncio.gather(*[_summarise_node(n) for n in nodes])


async def _build_doc_description(
    title: str, first_text: str, api_key: str
) -> str:
    """Generate a brief overall document description with Gemini."""
    prompt = (
        f"Scrivi una descrizione di 2-3 frasi in italiano del seguente documento "
        f"aziendale intitolato \"{title}\":\n\n{first_text[:3000]}"
    )

    def _call() -> str:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        return model.generate_content(prompt).text.strip()

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)
    except Exception as exc:
        logger.warning("Document description generation failed: %s", exc)
        return ""


# ── Public API ────────────────────────────────────────────────────────────────

async def build_page_index(
    pdf_path: str,
    doc_title: str,
    api_key: str,
) -> dict[str, Any]:
    """
    Build a PageIndex-style hierarchical tree for a PDF document.

    Args:
        pdf_path:  Absolute path to the PDF file on disk.
        doc_title: Document title (from the Document model).
        api_key:   Gemini API key.

    Returns:
        A dict tree ready to be stored in metadata_json["page_index"].
        Returns an empty dict on complete failure so callers never raise.
    """
    try:
        # 1. Extract per-page texts (needed for summaries and TOC fallback)
        page_texts = await asyncio.get_event_loop().run_in_executor(
            None, _extract_page_texts, pdf_path, None
        )
        total_pages = len(page_texts)

        if total_pages == 0:
            logger.warning("No pages extracted from '%s'", pdf_path)
            return {}

        # 2. Try native TOC first; fall back to Gemini inference
        toc = await asyncio.get_event_loop().run_in_executor(
            None, _extract_native_toc, pdf_path
        )

        if not toc:
            logger.info("No native TOC in '%s', inferring with Gemini.", pdf_path)
            first_pages_text = "\n".join(page_texts[:INFER_TOC_PAGES])
            toc = await _infer_toc_from_gemini(first_pages_text, api_key)

        # 3. Build tree with page ranges
        tree = _assign_page_ranges(toc, total_pages)

        # 4. Assign hierarchical IDs
        _add_ids(tree)

        # 5. Add summaries to all nodes concurrently
        all_nodes = _flatten_tree(tree)
        if all_nodes and api_key:
            await _add_summaries(all_nodes, page_texts, api_key)

        # 6. Top-level document description
        description = ""
        if api_key:
            description = await _build_doc_description(
                doc_title, page_texts[0] if page_texts else "", api_key
            )

        return {
            "title": doc_title,
            "description": description,
            "total_pages": total_pages,
            "children": tree,
        }

    except Exception as exc:
        logger.warning("build_page_index failed for '%s': %s", pdf_path, exc)
        return {}


def tree_to_rag_context(page_index: dict[str, Any], max_chars: int = 3000) -> str:
    """
    Serialise a page_index tree into a compact text block suitable for
    injection into a RAG prompt.

    Each section is rendered as:
        [1.2] "Title" (pp. 3-7): <summary>

    This lets the LLM reason about document structure, not just flat chunks.
    """
    if not page_index or not page_index.get("children"):
        return ""

    lines: list[str] = []
    if page_index.get("description"):
        lines.append(f"Descrizione: {page_index['description']}")

    def _render(nodes: list[dict], depth: int = 0) -> None:
        for node in nodes:
            indent = "  " * depth
            sec_id = node.get("id", "")
            title = node.get("title", "")
            p_start = node.get("page_start", "?")
            p_end = node.get("page_end", "?")
            summary = node.get("summary", "")
            line = f"{indent}[{sec_id}] \"{title}\" (pp. {p_start}-{p_end})"
            if summary:
                line += f": {summary}"
            lines.append(line)
            _render(node.get("children", []), depth + 1)

    _render(page_index["children"])

    result = "\n".join(lines)
    return result[:max_chars] + ("…" if len(result) > max_chars else "")
