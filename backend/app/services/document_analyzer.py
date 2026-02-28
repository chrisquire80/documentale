"""
Deep document analysis and categorization service.

Produces a comprehensive DocumentAnalysis in a single batched Gemini call:

  • Classification  — 7 primary categories × subcategories, intent,
                      language, confidence, key-words
  • Relationships   — subject-predicate-object triples with confidence
  • Risk indicators — expiry, high amounts, compliance gaps, severity
  • Timeline        — ordered key events with significance
  • Multi-level summary
      - executive   (1 sentence)
      - key_points  (3–7 bullets)
      - detailed    (1–2 paragraphs)

Results are stored in DocumentMetadata.metadata_json["analysis"] and
exposed through POST /ai/analyze/{doc_id}.

Gemini usage
------------
  • Model:            gemini-2.0-flash  (better reasoning, faster than 1.5-pro)
  • response_schema:  OpenAPI dict — guaranteed structure, no JSON parsing hacks
  • system_instruction: separates role definition from document content
  • generate_content_async: truly async, no thread-pool executor
  • File API (optional): when pdf_path is provided, Gemini reads the PDF
    natively — better quality than text extraction, especially for scanned
    documents, tables and complex layouts.

Taxonomy
--------
primary_category  subcategory examples
─────────────────────────────────────────────────
legale            contratto | accordo | parere_legale | delibera |
                  verbale | statuto | sentenza | ricorso
finanziario       fattura | preventivo | ordine_acquisto |
                  nota_credito | bilancio | rendiconto | estratto_conto
risorse_umane     curriculum | contratto_lavoro | lettera_assunzione |
                  valutazione | policy_ferie | formazione
tecnico           specifiche_tecniche | manuale | report_tecnico |
                  proposta_progetto | architettura
amministrativo    circolare | comunicazione | relazione | procedura | policy
commerciale       offerta | proposta_commerciale | contratto_vendita |
                  catalogo | report_vendite
corrispondenza    email | lettera | memo | nota_interna

Intent types: obbligo | informazione | autorizzazione |
              richiesta | approvazione | rendiconto
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── Taxonomy ──────────────────────────────────────────────────────────────────

TAXONOMY: dict[str, list[str]] = {
    "legale": [
        "contratto", "accordo", "parere_legale", "delibera",
        "verbale", "statuto", "sentenza", "ricorso", "nda",
    ],
    "finanziario": [
        "fattura", "preventivo", "ordine_acquisto", "nota_credito",
        "bilancio", "rendiconto", "estratto_conto", "quietanza",
    ],
    "risorse_umane": [
        "curriculum", "contratto_lavoro", "lettera_assunzione",
        "valutazione", "policy_ferie", "formazione", "organigramma",
    ],
    "tecnico": [
        "specifiche_tecniche", "manuale", "report_tecnico",
        "proposta_progetto", "architettura", "sla", "rfp",
    ],
    "amministrativo": [
        "circolare", "comunicazione", "relazione", "procedura",
        "policy", "regolamento", "modulo",
    ],
    "commerciale": [
        "offerta", "proposta_commerciale", "contratto_vendita",
        "catalogo", "report_vendite", "piano_marketing",
    ],
    "corrispondenza": [
        "email", "lettera", "memo", "nota_interna", "pec",
    ],
}

INTENT_TYPES = [
    "obbligo", "informazione", "autorizzazione",
    "richiesta", "approvazione", "rendiconto",
]

RISK_TYPES = [
    "data_scadenza_imminente",   # ≤ 30 days
    "data_scaduta",              # already past
    "importo_elevato",           # > €50 000
    "firme_mancanti",
    "informazioni_incomplete",
    "clausola_penale",
    "dati_personali_sensibili",
    "conflitto_interessi",
]

SEVERITY_LEVELS = ["bassa", "media", "alta", "critica"]


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class DocumentClassification:
    primary_category: str        # legale | finanziario | …
    subcategory: str             # contratto | fattura | …
    doc_type: str                # più specifico (es. contratto_fornitura)
    intent: str                  # obbligo | informazione | …
    language: str                # it | en | fr | …
    confidence: float            # 0.0 – 1.0
    keywords: list[str] = field(default_factory=list)


@dataclass
class EntityRelationship:
    subject: str
    predicate: str               # es. "paga", "è responsabile di", "ha scadenza"
    object: str
    confidence: float            # 0.0 – 1.0


@dataclass
class RiskIndicator:
    risk_type: str               # see RISK_TYPES
    severity: str                # bassa | media | alta | critica
    description: str             # human-readable Italian explanation
    value: str | None = None     # specific triggering value (date/amount/…)


@dataclass
class TimelineEvent:
    date: str                    # as appears in the document
    normalized_date: str | None  # ISO-8601 if parseable, else None
    event: str                   # Italian description
    significance: str            # alta | media | bassa


@dataclass
class DocumentAnalysis:
    classification: DocumentClassification
    relationships: list[EntityRelationship]
    risk_indicators: list[RiskIndicator]
    timeline: list[TimelineEvent]
    executive_summary: str       # 1 sentence
    key_points: list[str]        # 3–7 bullets
    detailed_summary: str        # 1–2 paragraphs
    analysis_version: str = "2.0"
    analyzed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Model config ──────────────────────────────────────────────────────────────

_MODEL_ID = "models/gemini-2.0-flash"

_SYSTEM_INSTRUCTION = (
    "Sei un esperto analista di documenti aziendali italiani. "
    "Rispondi esclusivamente con JSON valido rispettando la struttura richiesta. "
    "Tutto il testo descrittivo deve essere in italiano. "
    "Includi solo risk_indicators e relazioni effettivamente presenti nel documento."
)

# ── Response schema (OpenAPI format — guaranteed structure) ───────────────────

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "classification": {
            "type": "object",
            "properties": {
                "primary_category": {"type": "string"},
                "subcategory": {"type": "string"},
                "doc_type": {"type": "string"},
                "intent": {"type": "string"},
                "language": {"type": "string"},
                "confidence": {"type": "number"},
                "keywords": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["primary_category", "subcategory", "doc_type",
                         "intent", "language", "confidence"],
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "object": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["subject", "predicate", "object", "confidence"],
            },
        },
        "risk_indicators": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "risk_type": {"type": "string"},
                    "severity": {"type": "string"},
                    "description": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["risk_type", "severity", "description"],
            },
        },
        "timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "normalized_date": {"type": "string"},
                    "event": {"type": "string"},
                    "significance": {"type": "string"},
                },
                "required": ["date", "event", "significance"],
            },
        },
        "executive_summary": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "detailed_summary": {"type": "string"},
    },
    "required": [
        "classification", "relationships", "risk_indicators", "timeline",
        "executive_summary", "key_points", "detailed_summary",
    ],
}


# ── Prompt ────────────────────────────────────────────────────────────────────

_TAXONOMY_HINT = "\n".join(
    f"  {cat}: {', '.join(subs)}" for cat, subs in TAXONOMY.items()
)

_PROMPT_TEXT = """\
TITOLO: {title}
{entities_hint}
TASSONOMIA SUBCATEGORIE:
{taxonomy}

Categorie primarie: {categories}
Intent: {intents}
Severity: {severities}

Regole:
- key_points: minimo 3, massimo 7 voci
- Elenca SOLO risk_indicators rilevanti (lista vuota se nessuno)
- Elenca SOLO relazioni significative (non banali)
- normalized_date: ISO-8601 o stringa vuota se non convertibile
- value in risk_indicators: stringa vuota se non applicabile

TESTO (max 15000 caratteri):
{text}
"""

_PROMPT_FILE_API = """\
TITOLO: {title}
{entities_hint}
TASSONOMIA SUBCATEGORIE:
{taxonomy}

Categorie primarie: {categories}
Intent: {intents}
Severity: {severities}

Regole:
- Analizza l'intero documento PDF allegato
- key_points: minimo 3, massimo 7 voci
- Elenca SOLO risk_indicators rilevanti (lista vuota se nessuno)
- Elenca SOLO relazioni significative (non banali)
- normalized_date: ISO-8601 o stringa vuota se non convertibile
- value in risk_indicators: stringa vuota se non applicabile
"""


def _build_entities_hint(entities: list[dict] | None) -> str:
    if not entities:
        return ""
    party_names = [e["text"] for e in entities if e.get("class") == "party"][:5]
    dates = [e["text"] for e in entities if e.get("class") == "date"][:5]
    amounts = [e["text"] for e in entities if e.get("class") == "amount"][:3]
    parts = []
    if party_names:
        parts.append("parti: " + ", ".join(party_names))
    if dates:
        parts.append("date: " + ", ".join(dates))
    if amounts:
        parts.append("importi: " + ", ".join(amounts))
    return "Entità pre-estratte: " + "; ".join(parts) + "\n" if parts else ""


def _format_prompt(template: str, title: str, entities_hint: str, text: str = "") -> str:
    return template.format(
        title=title,
        entities_hint=entities_hint,
        taxonomy=_TAXONOMY_HINT,
        categories=", ".join(TAXONOMY.keys()),
        intents=", ".join(INTENT_TYPES),
        severities=", ".join(SEVERITY_LEVELS),
        text=text[:15_000],
    )


# ── File API helper ────────────────────────────────────────────────────────────

async def _upload_pdf_async(pdf_path: str, api_key: str) -> Any:
    """Upload a PDF to Gemini File API and wait until it is active."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    def _sync_upload() -> Any:
        f = genai.upload_file(pdf_path, mime_type="application/pdf")
        for _ in range(30):  # poll up to 30 s
            if f.state.name != "PROCESSING":
                break
            time.sleep(1)
            f = genai.get_file(f.name)
        if f.state.name == "FAILED":
            raise RuntimeError("File API processing failed")
        return f

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_upload)


# ── Output parsing ─────────────────────────────────────────────────────────────

def _dict_to_analysis(data: dict) -> DocumentAnalysis:
    cls_data = data.get("classification", {})
    classification = DocumentClassification(
        primary_category=cls_data.get("primary_category", "amministrativo"),
        subcategory=cls_data.get("subcategory", "documento"),
        doc_type=cls_data.get("doc_type", ""),
        intent=cls_data.get("intent", "informazione"),
        language=cls_data.get("language", "it"),
        confidence=float(cls_data.get("confidence", 0.5)),
        keywords=cls_data.get("keywords", []),
    )

    relationships = [
        EntityRelationship(
            subject=r.get("subject", ""),
            predicate=r.get("predicate", ""),
            object=r.get("object", ""),
            confidence=float(r.get("confidence", 0.5)),
        )
        for r in data.get("relationships", [])
        if r.get("subject") and r.get("object")
    ]

    risk_indicators = [
        RiskIndicator(
            risk_type=ri.get("risk_type", ""),
            severity=ri.get("severity", "bassa"),
            description=ri.get("description", ""),
            value=ri.get("value") or None,
        )
        for ri in data.get("risk_indicators", [])
        if ri.get("risk_type")
    ]

    timeline = sorted(
        [
            TimelineEvent(
                date=ev.get("date", ""),
                normalized_date=ev.get("normalized_date") or None,
                event=ev.get("event", ""),
                significance=ev.get("significance", "media"),
            )
            for ev in data.get("timeline", [])
            if ev.get("date") and ev.get("event")
        ],
        key=lambda e: e.normalized_date or e.date,
    )

    return DocumentAnalysis(
        classification=classification,
        relationships=relationships,
        risk_indicators=risk_indicators,
        timeline=timeline,
        executive_summary=data.get("executive_summary", ""),
        key_points=data.get("key_points", []),
        detailed_summary=data.get("detailed_summary", ""),
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def analyze_document(
    text: str,
    title: str,
    api_key: str,
    entities: list[dict] | None = None,
    pdf_path: str | None = None,
) -> DocumentAnalysis | None:
    """
    Run deep analysis on a document using a single Gemini call.

    Args:
        text:     Full OCR text of the document (used when pdf_path is absent).
        title:    Document title.
        api_key:  Gemini API key.
        entities: Pre-extracted entities from LangExtract (optional hint).
        pdf_path: Path to the original PDF file. When provided, the PDF is
                  uploaded to Gemini File API so Gemini reads it natively —
                  better quality than text extraction, especially for scanned
                  documents, tables and complex layouts.

    Returns:
        DocumentAnalysis dataclass, or None on failure.
    """
    if not text.strip() and not pdf_path:
        return None

    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        _MODEL_ID,
        system_instruction=_SYSTEM_INSTRUCTION,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
        ),
    )

    entities_hint = _build_entities_hint(entities)
    uploaded_file = None

    try:
        if pdf_path:
            # File API path: upload PDF and let Gemini read it natively
            try:
                uploaded_file = await _upload_pdf_async(pdf_path, api_key)
                prompt = _format_prompt(_PROMPT_FILE_API, title, entities_hint)
                response = await model.generate_content_async([uploaded_file, prompt])
            except Exception as upload_exc:
                logger.warning(
                    "File API upload failed for '%s', falling back to text: %s",
                    title, upload_exc,
                )
                uploaded_file = None
                prompt = _format_prompt(_PROMPT_TEXT, title, entities_hint, text)
                response = await model.generate_content_async(prompt)
        else:
            prompt = _format_prompt(_PROMPT_TEXT, title, entities_hint, text)
            response = await model.generate_content_async(prompt)

        data = json.loads(response.text)
        result = _dict_to_analysis(data)
        logger.info(
            "Analisi completata per '%s': categoria=%s, rischi=%d",
            title,
            result.classification.primary_category,
            len(result.risk_indicators),
        )
        return result

    except Exception as exc:
        logger.warning("document_analyzer failed for '%s': %s", title, exc)
        return None

    finally:
        # Clean up uploaded file from Gemini servers
        if uploaded_file is not None:
            try:
                import google.generativeai as genai
                genai.delete_file(uploaded_file.name)
            except Exception:
                pass


def analysis_to_dict(analysis: DocumentAnalysis) -> dict[str, Any]:
    """Convert DocumentAnalysis to a JSON-serialisable dict."""
    return asdict(analysis)


def get_risk_summary(analysis: DocumentAnalysis) -> dict[str, Any]:
    """Return a compact risk summary suitable for list views."""
    if not analysis.risk_indicators:
        return {"has_risks": False, "max_severity": None, "count": 0}

    severity_order = {"critica": 3, "alta": 2, "media": 1, "bassa": 0}
    max_sev = max(
        analysis.risk_indicators,
        key=lambda r: severity_order.get(r.severity, 0),
    )
    return {
        "has_risks": True,
        "max_severity": max_sev.severity,
        "count": len(analysis.risk_indicators),
        "critical_count": sum(
            1 for r in analysis.risk_indicators if r.severity == "critica"
        ),
    }
