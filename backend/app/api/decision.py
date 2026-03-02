"""
Strumento di analisi decisionale comparativa.

  POST /ai/compare                    — confronto documenti selezionati
  GET  /ai/compare-anchor/{doc_id}    — confronto con auto-discovery semantica
"""
import asyncio
import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import google.generativeai as genai

from ..db import get_db
from ..models.user import User, UserRole
from ..models.document import Document, DocumentContent, DocumentMetadata, DocumentShare
from ..api.auth import get_current_user
from ..core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    document_ids: List[UUID]
    question: str = ""


class TimelineItem(BaseModel):
    doc_id: str
    title: str
    date: Optional[str] = None
    key_point: str
    stance: str  # favorevole | contrario | neutro | incerto


class DecisionResponse(BaseModel):
    topic_summary: str
    timeline: List[TimelineItem]
    evolution: str
    contradictions: List[str]
    agreements: List[str]
    decision_recommendation: str
    confidence: float
    reasoning: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_best_date(metadata_json: dict, fallback: Optional[str]) -> Optional[str]:
    """Return the most relevant date from LangExtract metadata, falling back to created_at."""
    dates = metadata_json.get("dates", [])
    for role in ("emissione", "decorrenza", "riferimento"):
        for d in dates:
            if isinstance(d, dict) and d.get("role") == role:
                return d.get("text")
    if dates and isinstance(dates[0], dict):
        return dates[0].get("text")
    return fallback


async def _fetch_docs_data(
    doc_ids: List[UUID], current_user: User, db: AsyncSession
) -> list:
    """
    Fetch document text + metadata for each ID.
    Applies RBAC filtering and returns list sorted chronologically.
    """
    docs_data = []
    for doc_id in doc_ids:
        doc = (
            await db.execute(select(Document).where(Document.id == doc_id, Document.is_deleted == False))
        ).scalar_one_or_none()
        if not doc:
            continue

        # RBAC: skip restricted docs the user cannot access
        if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
            if doc.is_restricted:
                share = (
                    await db.execute(
                        select(DocumentShare).where(
                            DocumentShare.document_id == doc_id,
                            DocumentShare.shared_with_id == current_user.id,
                        )
                    )
                ).scalar_one_or_none()
                if not share:
                    continue

        content = (
            await db.execute(select(DocumentContent).where(DocumentContent.document_id == doc_id))
        ).scalar_one_or_none()
        ocr_text = (content.fulltext_content or "") if content else ""

        meta = (
            await db.execute(select(DocumentMetadata).where(DocumentMetadata.document_id == doc_id))
        ).scalar_one_or_none()
        metadata_json = dict(meta.metadata_json or {}) if meta else {}

        fallback = doc.created_at.strftime("%Y-%m-%d") if doc.created_at else None
        best_date = _extract_best_date(metadata_json, fallback)

        docs_data.append({
            "doc_id": str(doc.id),
            "title": doc.title,
            "date": best_date,
            "created_at": doc.created_at,
            "ocr_text": ocr_text,
        })

    # Chronological sort
    docs_data.sort(key=lambda d: d["created_at"] or "")
    return docs_data


async def _run_comparison(
    docs_data: list, question: str, api_key: str
) -> DecisionResponse:
    """Call Gemini with all documents in chronological order and parse the structured response."""
    # Build document block — max 2500 chars each to stay within context
    docs_text = ""
    for i, d in enumerate(docs_data, 1):
        excerpt = (d["ocr_text"] or "")[:2500]
        docs_text += (
            f"\n\n--- DOCUMENTO {i} ---\n"
            f"ID: {d['doc_id']}\n"
            f"Titolo: {d['title']}\n"
            f"Data: {d['date'] or 'non specificata'}\n\n"
            f"{excerpt}"
        )

    question_line = f"\n\nDOMANDA SPECIFICA: {question.strip()}" if question.strip() else ""

    prompt = f"""Sei un consulente decisionale aziendale specializzato nell'analisi documentale comparativa.

Di seguito trovi {len(docs_data)} documenti in ordine cronologico che trattano un argomento comune.
Il tuo compito è analizzare l'evoluzione della discussione e fornire una raccomandazione decisionale chiara e azionabile.
{docs_text}{question_line}

Analizza i documenti e rispondi ESCLUSIVAMENTE con un JSON valido nel seguente formato (nessun testo prima o dopo):

{{
  "topic_summary": "descrizione concisa dell'argomento comune in 1-2 frasi",
  "timeline": [
    {{
      "doc_id": "<id esatto del documento>",
      "title": "<titolo>",
      "date": "<data o null>",
      "key_point": "<punto chiave di questo documento in 1 frase>",
      "stance": "<favorevole|contrario|neutro|incerto>"
    }}
  ],
  "evolution": "come è evoluta la posizione/discussione nel tempo (2-3 frasi)",
  "contradictions": ["contraddizione specifica 1", "contraddizione 2"],
  "agreements": ["punto di accordo 1", "punto di accordo 2"],
  "decision_recommendation": "raccomandazione decisionale finale, chiara e azionabile (2-3 frasi)",
  "confidence": <numero da 0.0 a 1.0>,
  "reasoning": "ragionamento che giustifica la raccomandazione (2-4 frasi)"
}}

Regole:
- JSON valido e completo, zero testo fuori dal JSON
- Usa i doc_id esatti forniti
- Sii specifico: cita nomi, date, importi dai documenti
- La raccomandazione deve essere concreta e immediatamente azionabile
- Se i documenti sono insufficienti per decidere, usa confidence < 0.4"""

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemini-1.5-flash")

    def _call() -> str:
        resp = model.generate_content(prompt)
        return resp.text or "{}"

    raw = await asyncio.get_event_loop().run_in_executor(None, _call)
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        raw = raw.rsplit("```", 1)[0].strip()

    result = json.loads(raw)

    timeline = [
        TimelineItem(
            doc_id=str(item.get("doc_id", "")),
            title=item.get("title", ""),
            date=item.get("date"),
            key_point=item.get("key_point", ""),
            stance=item.get("stance", "neutro"),
        )
        for item in result.get("timeline", [])
    ]

    return DecisionResponse(
        topic_summary=result.get("topic_summary", ""),
        timeline=timeline,
        evolution=result.get("evolution", ""),
        contradictions=result.get("contradictions", []),
        agreements=result.get("agreements", []),
        decision_recommendation=result.get("decision_recommendation", ""),
        confidence=float(result.get("confidence", 0.5)),
        reasoning=result.get("reasoning", ""),
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/compare", response_model=DecisionResponse)
async def compare_and_decide(
    body: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confronta i documenti selezionati in ordine cronologico e produce
    un'analisi decisionale strutturata con raccomandazione finale.
    Richiede almeno 2 documenti, massimo 8.
    """
    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini non configurato.")
    if len(body.document_ids) < 2:
        raise HTTPException(status_code=400, detail="Servono almeno 2 documenti per il confronto.")
    if len(body.document_ids) > 8:
        raise HTTPException(status_code=400, detail="Massimo 8 documenti per confronto.")

    docs_data = await _fetch_docs_data(body.document_ids, current_user, db)
    if len(docs_data) < 2:
        raise HTTPException(status_code=422, detail="Documenti accessibili insufficienti per il confronto.")
    if not any(d["ocr_text"].strip() for d in docs_data):
        raise HTTPException(status_code=422, detail="Nessun testo disponibile (OCR in corso?).")

    try:
        return await _run_comparison(docs_data, body.question, settings.GEMINI_API_KEY)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Errore nell'analisi AI: {exc}")


@router.get("/compare-anchor/{doc_id}", response_model=DecisionResponse)
async def compare_from_anchor(
    doc_id: UUID,
    question: str = Query(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Usa il documento indicato come ancora semantica: trova automaticamente
    i documenti più simili via pgvector e genera l'analisi decisionale comparativa.
    """
    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini non configurato.")

    anchor_content = (
        await db.execute(select(DocumentContent).where(DocumentContent.document_id == doc_id))
    ).scalar_one_or_none()
    if not anchor_content or anchor_content.embedding is None:
        raise HTTPException(
            status_code=422,
            detail="Embedding non disponibile per questo documento (OCR in corso?).",
        )

    # Find semantically similar documents (cosine distance < 0.55 = high similarity)
    sim_stmt = text("""
        SELECT d.id
        FROM documents d
        JOIN doc_content c ON c.document_id = d.id
        WHERE d.id != :anchor_id
          AND d.is_deleted = false
          AND c.embedding IS NOT NULL
          AND (d.owner_id = :user_id OR d.is_restricted = false)
          AND (c.embedding <=> :emb::vector) < 0.55
        ORDER BY (c.embedding <=> :emb::vector) ASC
        LIMIT 5
    """)
    rows = (
        await db.execute(
            sim_stmt,
            {"anchor_id": str(doc_id), "user_id": str(current_user.id), "emb": str(anchor_content.embedding)},
        )
    ).fetchall()

    related_ids = [UUID(str(r[0])) for r in rows]
    all_ids = [doc_id] + related_ids

    if len(all_ids) < 2:
        raise HTTPException(
            status_code=422,
            detail="Nessun documento semanticamente simile trovato. Carica altri documenti sullo stesso argomento.",
        )

    docs_data = await _fetch_docs_data(all_ids, current_user, db)
    if len(docs_data) < 2:
        raise HTTPException(status_code=422, detail="Documenti insufficienti per il confronto.")

    try:
        return await _run_comparison(docs_data, question, settings.GEMINI_API_KEY)
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Errore nell'analisi AI: {exc}")
