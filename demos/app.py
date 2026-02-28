"""
Documentale — Gradio Demo
=========================
Interactive demo for the AI features of the Documentale DMS.

Built with the huggingface-gradio skill (https://github.com/huggingface/skills).

Tabs
----
1. Ricerca AI           — RAG chat over all documents
2. Entità (LangExtract) — on-demand structured entity extraction
3. Indice Gerarchico    — hierarchical TOC tree for a PDF (PageIndex)
4. Analisi Approfondita — deep classification, risk, timeline, relationships
5. Documenti Simili     — pgvector cosine similarity search
6. Ricerca Testuale     — full-text keyword search

Usage
-----
    pip install gradio requests
    python demos/app.py

Environment variables (optional, override defaults):
    DOCUMENTALE_URL   base URL of the backend  (default: http://localhost:8000)
    DOCUMENTALE_USER  login email              (default: admin@example.com)
    DOCUMENTALE_PASS  login password           (default: changeme)
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests
import gradio as gr

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL = os.getenv("DOCUMENTALE_URL", "http://localhost:8000")
DEFAULT_USER = os.getenv("DOCUMENTALE_USER", "admin@example.com")
DEFAULT_PASS = os.getenv("DOCUMENTALE_PASS", "changeme")

# ── Auth helpers ──────────────────────────────────────────────────────────────

_token_cache: dict[str, str] = {}


def _login(email: str, password: str) -> str:
    """Return a JWT access token, cached per (email, password) pair."""
    key = f"{email}:{password}"
    if key in _token_cache:
        return _token_cache[key]
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    _token_cache[key] = token
    return token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Tab 1: Ricerca AI (RAG Chat) ──────────────────────────────────────────────

def ai_chat(
    query: str,
    doc_id: str,
    email: str,
    password: str,
    history: list[list[str]],
) -> tuple[list[list[str]], str]:
    """Call POST /ai/chat and append to the Chatbot history."""
    if not query.strip():
        return history, ""
    try:
        token = _login(email, password)
        payload: dict[str, Any] = {"query": query}
        if doc_id.strip():
            payload["document_id"] = doc_id.strip()

        resp = requests.post(
            f"{BASE_URL}/ai/chat",
            json=payload,
            headers=_headers(token),
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data["answer"]
        sources = data.get("sources", [])
        if sources:
            src_lines = "\n".join(
                f"  • {s['title']} (ID: {s['document_id']})" for s in sources
            )
            answer += f"\n\n**Fonti:**\n{src_lines}"
        history = history + [[query, answer]]
    except Exception as exc:
        history = history + [[query, f"❌ Errore: {exc}"]]
    return history, ""


# ── Tab 2: LangExtract entity extraction ─────────────────────────────────────

def run_extract(doc_id: str, email: str, password: str) -> str:
    """Call POST /ai/extract/{doc_id} and return formatted entities."""
    doc_id = doc_id.strip()
    if not doc_id:
        return "Inserisci un Document ID."
    try:
        token = _login(email, password)
        resp = requests.post(
            f"{BASE_URL}/ai/extract/{doc_id}",
            headers=_headers(token),
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        lines = [
            f"**Documento:** `{data['document_id']}`",
            f"**Tipo documento:** {data.get('doc_type') or '—'}",
            f"**Entità estratte:** {data['entity_count']}",
            "",
        ]
        if data.get("parties"):
            lines.append("### Parti")
            for p in data["parties"]:
                lines.append(f"- {p['name']} *(ruolo: {p.get('role', '?')})*")
        if data.get("dates"):
            lines.append("### Date")
            for d in data["dates"]:
                lines.append(f"- {d['text']} *(ruolo: {d.get('role', '?')})*")
        if data.get("amounts"):
            lines.append("### Importi")
            for a in data["amounts"]:
                lines.append(f"- {a['text']} ({a.get('currency', 'EUR')})")
        if data.get("references"):
            lines.append("### Riferimenti")
            for r in data["references"]:
                lines.append(f"- `{r}`")

        return "\n".join(lines)
    except Exception as exc:
        return f"❌ Errore: {exc}"


# ── Tab 3: PageIndex hierarchical tree ────────────────────────────────────────

def run_pageindex(doc_id: str, email: str, password: str) -> str:
    """Call POST /ai/pageindex/{doc_id} and render the tree as Markdown."""
    doc_id = doc_id.strip()
    if not doc_id:
        return "Inserisci un Document ID (PDF)."
    try:
        token = _login(email, password)
        resp = requests.post(
            f"{BASE_URL}/ai/pageindex/{doc_id}",
            headers=_headers(token),
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        tree = data.get("page_index", {})

        lines = [
            f"**Documento:** `{data['document_id']}`",
            f"**Pagine totali:** {data['total_pages']}",
            f"**Sezioni indicizzate:** {data['section_count']}",
            "",
            f"### {tree.get('title', '—')}",
        ]
        if tree.get("description"):
            lines.append(f"*{tree['description']}*")
        lines.append("")

        def _render(nodes: list[dict], depth: int = 0) -> None:
            indent = "  " * depth
            for node in nodes:
                sec_id = node.get("id", "")
                title = node.get("title", "")
                p_start = node.get("page_start", "?")
                p_end = node.get("page_end", "?")
                summary = node.get("summary", "")
                line = f"{indent}- **[{sec_id}]** {title} *(pp. {p_start}–{p_end})*"
                if summary:
                    line += f"\n{indent}  > {summary}"
                lines.append(line)
                _render(node.get("children", []), depth + 1)

        _render(tree.get("children", []))
        return "\n".join(lines)
    except Exception as exc:
        return f"❌ Errore: {exc}"


# ── Tab 4: Deep analysis ─────────────────────────────────────────────────────

_SEVERITY_EMOJI = {"critica": "🔴", "alta": "🟠", "media": "🟡", "bassa": "🟢"}
_SIGNIFICANCE_EMOJI = {"alta": "⭐⭐⭐", "media": "⭐⭐", "bassa": "⭐"}


def run_analysis(doc_id: str, email: str, password: str, rerun: bool) -> str:
    """Call POST or GET /ai/analyze/{doc_id} and render results."""
    doc_id = doc_id.strip()
    if not doc_id:
        return "Inserisci un Document ID."
    try:
        token = _login(email, password)
        method = requests.post if rerun else requests.get
        resp = method(
            f"{BASE_URL}/ai/analyze/{doc_id}",
            headers=_headers(token),
            timeout=180,
        )
        if resp.status_code == 404 and not rerun:
            return "Nessuna analisi disponibile. Attiva **Riesegui analisi** e riprova."
        resp.raise_for_status()
        d = resp.json()
        cls = d["classification"]
        risk = d.get("risk_summary", {})

        lines = [
            f"## 🗂 Classificazione",
            f"| Campo | Valore |",
            f"|---|---|",
            f"| Categoria | **{cls['primary_category']}** |",
            f"| Sottocategoria | {cls['subcategory']} |",
            f"| Tipo documento | {cls['doc_type']} |",
            f"| Intento | {cls['intent']} |",
            f"| Lingua | {cls['language']} |",
            f"| Confidenza | {cls['confidence']:.0%} |",
        ]
        if cls.get("keywords"):
            lines.append(f"| Parole chiave | {', '.join(cls['keywords'])} |")

        lines += ["", "## 📋 Sommario"]
        lines.append(f"> {d['executive_summary']}")
        lines += ["", "**Punti chiave:**"]
        for pt in d.get("key_points", []):
            lines.append(f"- {pt}")
        lines += ["", d.get("detailed_summary", "")]

        if d.get("risk_indicators"):
            lines += ["", "## ⚠️ Indicatori di Rischio"]
            if risk.get("has_risks"):
                max_sev = risk.get("max_severity", "")
                lines.append(
                    f"**Rischio massimo:** {_SEVERITY_EMOJI.get(max_sev, '')} {max_sev.upper()}  "
                    f"({risk.get('count', 0)} indicatori, {risk.get('critical_count', 0)} critici)"
                )
                lines.append("")
            for ri in d["risk_indicators"]:
                sev = ri["severity"]
                lines.append(
                    f"- {_SEVERITY_EMOJI.get(sev, '')} **{ri['risk_type']}** [{sev}]  \n"
                    f"  {ri['description']}"
                    + (f"  \n  *Valore:* `{ri['value']}`" if ri.get("value") else "")
                )

        if d.get("timeline"):
            lines += ["", "## 📅 Cronologia"]
            for ev in d["timeline"]:
                sig = _SIGNIFICANCE_EMOJI.get(ev["significance"], "⭐")
                nd = f" → `{ev['normalized_date']}`" if ev.get("normalized_date") else ""
                lines.append(f"- {sig} **{ev['date']}**{nd}: {ev['event']}")

        if d.get("relationships"):
            lines += ["", "## 🔗 Relazioni tra entità"]
            for r in d["relationships"][:10]:
                conf = f"{r['confidence']:.0%}"
                lines.append(f"- **{r['subject']}** → *{r['predicate']}* → **{r['object']}** ({conf})")

        lines += ["", f"---", f"*Analisi v{d['analysis_version']} · {d['analyzed_at'][:19]}*"]
        return "\n".join(lines)
    except Exception as exc:
        return f"❌ Errore: {exc}"


def run_similar(doc_id: str, limit: int, email: str, password: str) -> str:
    """Call GET /ai/similar/{doc_id} and render results."""
    doc_id = doc_id.strip()
    if not doc_id:
        return "Inserisci un Document ID."
    try:
        token = _login(email, password)
        resp = requests.get(
            f"{BASE_URL}/ai/similar/{doc_id}",
            params={"limit": int(limit)},
            headers=_headers(token),
            timeout=30,
        )
        resp.raise_for_status()
        d = resp.json()
        if not d["similar"]:
            return "Nessun documento simile trovato."
        lines = [f"**Documenti simili a** `{d['document_id']}`\n"]
        for s in d["similar"]:
            bar = "█" * int(s["similarity"] * 10) + "░" * (10 - int(s["similarity"] * 10))
            lines.append(
                f"- **{s['title']}** `{s['document_id']}`  \n"
                f"  Similarità: `{bar}` {s['similarity']:.1%}  "
                + (f"· {s['primary_category']} / {s['doc_type']}" if s.get("primary_category") else "")
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"❌ Errore: {exc}"


# ── Tab 5: Full-text search ───────────────────────────────────────────────────

def fts_search(query: str, email: str, password: str) -> str:
    """Call GET /documents/search and render results."""
    if not query.strip():
        return "Inserisci un termine di ricerca."
    try:
        token = _login(email, password)
        resp = requests.get(
            f"{BASE_URL}/documents/search",
            params={"q": query, "limit": 10},
            headers=_headers(token),
            timeout=30,
        )
        resp.raise_for_status()
        docs = resp.json()
        if not docs:
            return "Nessun risultato trovato."
        lines = [f"**{len(docs)} risultati per:** *{query}*\n"]
        for d in docs:
            lines.append(
                f"- **{d['title']}** `{d['id']}`  "
                f"(tipo: {d.get('file_type', '?')}, "
                f"versione: {d.get('current_version', 1)})"
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"❌ Errore: {exc}"


# ── Gradio layout ─────────────────────────────────────────────────────────────

def _auth_row() -> tuple[gr.Textbox, gr.Textbox]:
    email = gr.Textbox(value=DEFAULT_USER, label="Email", scale=2)
    pwd = gr.Textbox(value=DEFAULT_PASS, label="Password", type="password", scale=2)
    return email, pwd


with gr.Blocks(title="Documentale AI Demo", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# Documentale — AI Demo\n"
        "Interfaccia Gradio per esplorare le funzionalità AI del DMS.\n\n"
        "> Powered by LangExtract · PageIndex · pgvector RAG · Gemini"
    )

    with gr.Tab("💬 Ricerca AI (RAG)"):
        gr.Markdown(
            "Poni una domanda in linguaggio naturale. Il sistema recupera i documenti "
            "più rilevanti via pgvector e risponde con Gemini (RAG).\n\n"
            "Se specifichi un **Document ID**, la risposta è arricchita con "
            "la struttura gerarchica PageIndex del documento."
        )
        with gr.Row():
            chat_email, chat_pwd = _auth_row()
        chat_doc_id = gr.Textbox(label="Document ID (opzionale)", placeholder="uuid...")
        chatbot = gr.Chatbot(label="Chat con i documenti", height=420)
        with gr.Row():
            chat_input = gr.Textbox(
                label="Domanda", placeholder="Es. Qual è la scadenza del contratto?",
                scale=8,
            )
            send_btn = gr.Button("Invia", variant="primary", scale=1)
        clear_btn = gr.Button("Pulisci chat", size="sm")

        send_btn.click(
            fn=ai_chat,
            inputs=[chat_input, chat_doc_id, chat_email, chat_pwd, chatbot],
            outputs=[chatbot, chat_input],
        )
        chat_input.submit(
            fn=ai_chat,
            inputs=[chat_input, chat_doc_id, chat_email, chat_pwd, chatbot],
            outputs=[chatbot, chat_input],
        )
        clear_btn.click(lambda: [], outputs=chatbot)

    with gr.Tab("🔍 Entità (LangExtract)"):
        gr.Markdown(
            "Estrae entità strutturate (parti, date, importi, riferimenti) "
            "dal testo OCR di un documento usando **LangExtract + Gemini**."
        )
        with gr.Row():
            ex_email, ex_pwd = _auth_row()
        ex_doc_id = gr.Textbox(label="Document ID", placeholder="uuid...")
        ex_btn = gr.Button("Estrai entità", variant="primary")
        ex_output = gr.Markdown()
        ex_btn.click(
            fn=run_extract,
            inputs=[ex_doc_id, ex_email, ex_pwd],
            outputs=ex_output,
        )

    with gr.Tab("🌲 Indice Gerarchico (PageIndex)"):
        gr.Markdown(
            "Costruisce (o ricostruisce) l'albero TOC gerarchico di un **PDF** "
            "ispirandosi a **PageIndex** (VectifyAI). "
            "Ogni sezione riceve un riepilogo AI e un range di pagine."
        )
        with gr.Row():
            pi_email, pi_pwd = _auth_row()
        pi_doc_id = gr.Textbox(label="Document ID (PDF)", placeholder="uuid...")
        pi_btn = gr.Button("Costruisci indice", variant="primary")
        pi_output = gr.Markdown()
        pi_btn.click(
            fn=run_pageindex,
            inputs=[pi_doc_id, pi_email, pi_pwd],
            outputs=pi_output,
        )

    with gr.Tab("🔬 Analisi Approfondita"):
        gr.Markdown(
            "Esegue un'analisi profonda del documento: **classificazione tassonomica**, "
            "**indicatori di rischio**, **cronologia eventi**, **relazioni tra entità**, "
            "e **sommario esecutivo** — tutto in una singola chiamata Gemini strutturata.\n\n"
            "Attiva *Riesegui analisi* per forzare un nuovo run (altrimenti recupera il risultato salvato)."
        )
        with gr.Row():
            an_email, an_pwd = _auth_row()
        with gr.Row():
            an_doc_id = gr.Textbox(label="Document ID", placeholder="uuid...", scale=8)
            an_rerun = gr.Checkbox(label="Riesegui analisi", value=False, scale=1)
        an_btn = gr.Button("Analizza", variant="primary")
        an_output = gr.Markdown()
        an_btn.click(
            fn=run_analysis,
            inputs=[an_doc_id, an_email, an_pwd, an_rerun],
            outputs=an_output,
        )

    with gr.Tab("🔗 Documenti Simili"):
        gr.Markdown(
            "Trova i documenti più simili a quello indicato usando la **ricerca vettoriale pgvector** "
            "(cosine similarity sugli embedding Gemini a 768 dimensioni)."
        )
        with gr.Row():
            sim_email, sim_pwd = _auth_row()
        with gr.Row():
            sim_doc_id = gr.Textbox(label="Document ID", placeholder="uuid...", scale=7)
            sim_limit = gr.Slider(
                minimum=1, maximum=20, value=5, step=1,
                label="Numero risultati", scale=2,
            )
        sim_btn = gr.Button("Trova simili", variant="primary")
        sim_output = gr.Markdown()
        sim_btn.click(
            fn=run_similar,
            inputs=[sim_doc_id, sim_limit, sim_email, sim_pwd],
            outputs=sim_output,
        )

    with gr.Tab("🔎 Ricerca Testuale (FTS)"):
        gr.Markdown(
            "Ricerca full-text PostgreSQL con dizionario italiano. "
            "Restituisce i documenti che contengono il termine cercato."
        )
        with gr.Row():
            fts_email, fts_pwd = _auth_row()
        with gr.Row():
            fts_input = gr.Textbox(
                label="Termine di ricerca", placeholder="Es. contratto fornitura",
                scale=8,
            )
            fts_btn = gr.Button("Cerca", variant="primary", scale=1)
        fts_output = gr.Markdown()
        fts_btn.click(
            fn=fts_search,
            inputs=[fts_input, fts_email, fts_pwd],
            outputs=fts_output,
        )
        fts_input.submit(
            fn=fts_search,
            inputs=[fts_input, fts_email, fts_pwd],
            outputs=fts_output,
        )

    gr.Markdown(
        "---\n"
        "Powered by **LangExtract** · **PageIndex** · **pgvector RAG** · **Gemini 1.5 Flash** · "
        "[huggingface/skills](https://github.com/huggingface/skills)  \n"
        "Backend: Documentale FastAPI @ `" + BASE_URL + "`"
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, show_api=False)
