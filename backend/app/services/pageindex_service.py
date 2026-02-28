"""
Hierarchical document tree indexing, inspired by PageIndex
(https://github.com/VectifyAI/PageIndex).

PageIndex's core insight: "similarity ≠ relevance — what we truly need in
retrieval is relevance, and that requires reasoning."  It replaces flat
vector-chunk retrieval with a hierarchical tree that mirrors how an expert
navigates a document (TOC → section → sub-section).

This implementation ports the concept to the existing Gemini stack:

  1. **TOC extraction** — PyMuPDF's native `get_toc()` first; if that is
     empty, Gemini analyses the PDF natively via File API (or first pages
     text as fallback) to reconstruct the outline.
  2. **Tree construction** — Sections are assigned page ranges from adjacent
     TOC entries.  Depth ≤ 3 by default (mirrors PageIndex defaults).
  3. **Section summaries** — All nodes are summarised in a SINGLE batched
     Gemini call (vs. N individual calls in v1) — major cost/latency saving.
  4. **Document description** — A single top-level description from Gemini,
     folded into the same batch call when possible.

Gemini usage
------------
  • Section summaries + description: gemini-1.5-flash-8b — cheap, fast
  • TOC inference: gemini-1.5-flash-8b with response_mime_type="application/json"
  • generate_content_async: truly async, no thread-pool executor for LLM calls
  • File API: used for TOC inference when no native TOC available (optional,
    falls back to text-based approach if upload fails)

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
import time
from typing import Any

logger = logging.getLogger(__name__)

# Characters of section text required before we bother summarising
SUMMARY_CHAR_THRESHOLD = 300
# Maximum depth of TOC levels to include (PageIndex default is 3)
MAX_DEPTH = 3
# Pages of text sent to Gemini for text-based "infer TOC" fallback
INFER_TOC_PAGES = 10
# Characters per page sent to Gemini for the summary pass
SUMMARY_CHARS_PER_SECTION = 2_000

_MODEL_FAST = "gemini-1.5-flash-8b"


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


def _get_total_pages(pdf_path: str) -> int:
    """Return page count via PyMuPDF (fast, no text needed)."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        n = doc.page_count
        doc.close()
        return n
    except Exception:
        return 0


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


# ── File API helper ────────────────────────────────────────────────────────────

async def _upload_pdf_async(pdf_path: str, api_key: str) -> Any:
    """Upload a PDF to Gemini File API and wait until it is active."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    def _sync_upload() -> Any:
        f = genai.upload_file(pdf_path, mime_type="application/pdf")
        for _ in range(30):
            if f.state.name != "PROCESSING":
                break
            time.sleep(1)
            f = genai.get_file(f.name)
        if f.state.name == "FAILED":
            raise RuntimeError("File API processing failed")
        return f

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_upload)


# ── TOC inference ──────────────────────────────────────────────────────────────

async def _infer_toc_from_gemini_file(
    uploaded_file: Any, api_key: str
) -> list[tuple[int, str, int]]:
    """
    Ask Gemini to reconstruct TOC from the uploaded PDF (File API).
    Falls back to [] on any error.
    """
    prompt = (
        "Leggi questo documento PDF e restituisci la struttura dell'indice (TOC).\n"
        'Formato: {"toc": [{"level": 1, "title": "Nome sezione", "page": 1}, ...]}\n'
        "Regole: level 1=sezione principale, 2=sottosezione, 3=sotto-sottosezione. "
        "Se non trovi struttura chiara restituisci {\"toc\": []}."
    )
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            _MODEL_FAST,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        response = await model.generate_content_async([uploaded_file, prompt])
        data = json.loads(response.text)
        return [
            (item["level"], item["title"], item["page"])
            for item in data.get("toc", [])
            if item.get("level", 0) <= MAX_DEPTH
        ]
    except Exception as exc:
        logger.warning("File API TOC inference failed: %s", exc)
        return []


async def _infer_toc_from_text(
    first_pages_text: str, api_key: str
) -> list[tuple[int, str, int]]:
    """
    Ask Gemini to reconstruct TOC from extracted text (text fallback).
    """
    prompt = (
        "Sei un assistente per l'analisi di documenti aziendali italiani.\n"
        "Leggi il seguente testo estratto dalle prime pagine di un documento PDF "
        "e restituisci la struttura TOC.\n"
        'Formato: {"toc": [{"level": 1, "title": "Nome sezione", "page": 1}, ...]}\n'
        "Regole:\n"
        "- Includi solo sezioni reali presenti nel testo.\n"
        "- level 1=sezione principale, 2=sottosezione, 3=sotto-sottosezione.\n"
        "- page è il numero di pagina (1-based) dove la sezione inizia.\n"
        "- Se non trovi struttura chiara restituisci {\"toc\": []}.\n\n"
        f"TESTO:\n{first_pages_text[:8000]}"
    )
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            _MODEL_FAST,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        response = await model.generate_content_async(prompt)
        data = json.loads(response.text)
        return [
            (item["level"], item["title"], item["page"])
            for item in data.get("toc", [])
            if item.get("level", 0) <= MAX_DEPTH
        ]
    except Exception as exc:
        logger.warning("Text-based TOC inference failed: %s", exc)
        return []


# ── Tree construction ──────────────────────────────────────────────────────────

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

    root_nodes: list[dict] = []
    stack: list[dict] = []

    for node in nodes:
        lvl = node.pop("_level")
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


# ── Batched summaries + description (1 Gemini call) ───────────────────────────

async def _add_summaries_and_description(
    nodes: list[dict],
    page_texts: list[str],
    doc_title: str,
    api_key: str,
) -> str:
    """
    Generate all section summaries AND the document description in a SINGLE
    Gemini call, replacing the previous N-call approach.

    Returns the document description string.
    """
    # Build per-section text snippets
    sections_to_summarize: list[tuple[int, dict]] = []  # (original_index, node)
    for i, node in enumerate(nodes):
        start = node["page_start"] - 1
        end = node["page_end"]
        section_text = " ".join(page_texts[start:end])[:SUMMARY_CHARS_PER_SECTION]
        if len(section_text.strip()) >= SUMMARY_CHAR_THRESHOLD:
            sections_to_summarize.append((i, node, section_text))

    first_page_text = page_texts[0][:3000] if page_texts else ""

    # Build a single batched prompt
    sections_block = "\n\n".join(
        f'[{idx + 1}] Sezione "{node["title"]}" (pp. {node["page_start"]}–{node["page_end"]}):\n{text}'
        for idx, (_, node, text) in enumerate(sections_to_summarize)
    )

    n = len(sections_to_summarize)
    prompt = (
        f"Documento aziendale: \"{doc_title}\"\n\n"
        "COMPITO 1 — Descrizione documento:\n"
        "Scrivi una descrizione di 2-3 frasi in italiano del documento basandoti "
        "sul seguente testo della prima pagina:\n"
        f"{first_page_text}\n\n"
    )
    if sections_to_summarize:
        prompt += (
            f"COMPITO 2 — Riassunti sezioni (esattamente {n} elementi):\n"
            "Per ciascuna sezione numerata sotto, scrivi UN SOLO riassunto di una frase in italiano.\n\n"
            f"{sections_block}\n\n"
        )
        schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "summaries": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["description", "summaries"],
        }
    else:
        prompt += "Restituisci solo la descrizione.\n"
        schema = {
            "type": "object",
            "properties": {"description": {"type": "string"}},
            "required": ["description"],
        }

    description = ""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            _MODEL_FAST,
            system_instruction=(
                "Sei un assistente di analisi documentale italiano. "
                "Rispondi solo con JSON valido."
            ),
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        response = await model.generate_content_async(prompt)
        data = json.loads(response.text)

        description = data.get("description", "")
        summaries = data.get("summaries", [])

        for idx, (_, node, _text) in enumerate(sections_to_summarize):
            if idx < len(summaries):
                node["summary"] = summaries[idx]

    except Exception as exc:
        logger.warning("Batch summary generation failed: %s", exc)

    return description


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
        loop = asyncio.get_running_loop()

        # 1. Extract per-page texts (needed for summaries)
        page_texts = await loop.run_in_executor(
            None, _extract_page_texts, pdf_path, None
        )
        total_pages = len(page_texts) or await loop.run_in_executor(
            None, _get_total_pages, pdf_path
        )

        if total_pages == 0:
            logger.warning("No pages extracted from '%s'", pdf_path)
            return {}

        # 2. Try native TOC first (fast, local, no API cost)
        toc = await loop.run_in_executor(None, _extract_native_toc, pdf_path)

        # 3. If no native TOC, infer with Gemini
        if not toc and api_key:
            logger.info("No native TOC in '%s', inferring with Gemini.", pdf_path)

            # Try File API first (native PDF reading — better quality)
            uploaded_file = None
            try:
                uploaded_file = await _upload_pdf_async(pdf_path, api_key)
                toc = await _infer_toc_from_gemini_file(uploaded_file, api_key)
            except Exception as exc:
                logger.warning("File API unavailable, falling back to text: %s", exc)
                toc = []
            finally:
                if uploaded_file is not None:
                    try:
                        import google.generativeai as genai
                        genai.delete_file(uploaded_file.name)
                    except Exception:
                        pass

            # Text fallback if File API failed or returned empty
            if not toc and page_texts:
                first_pages_text = "\n".join(page_texts[:INFER_TOC_PAGES])
                toc = await _infer_toc_from_text(first_pages_text, api_key)

        # 4. Build tree with page ranges and hierarchical IDs
        tree = _assign_page_ranges(toc, total_pages)
        _add_ids(tree)

        # 5. Generate all summaries + document description in ONE Gemini call
        all_nodes = _flatten_tree(tree)
        description = ""
        if api_key:
            description = await _add_summaries_and_description(
                all_nodes, page_texts, doc_title, api_key
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
