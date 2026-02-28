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
    analysis_version: str = "1.0"
    analyzed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Prompt ────────────────────────────────────────────────────────────────────

_TAXONOMY_HINT = "\n".join(
    f"  {cat}: {', '.join(subs)}" for cat, subs in TAXONOMY.items()
)

_PROMPT_TEMPLATE = """\
Sei un esperto analista di documenti aziendali italiani.
Analizza il seguente documento e restituisci ESCLUSIVAMENTE un oggetto JSON valido
con la struttura indicata sotto. Nessun markdown, nessun testo extra.

STRUTTURA JSON RICHIESTA:
{{
  "classification": {{
    "primary_category": "<una tra: {categories}>",
    "subcategory": "<sottocategoria specifica>",
    "doc_type": "<tipo preciso, es. contratto_fornitura_servizi>",
    "intent": "<una tra: {intents}>",
    "language": "<codice ISO 639-1, es. it>",
    "confidence": <float 0.0-1.0>,
    "keywords": ["<kw1>", "<kw2>", ...]
  }},
  "relationships": [
    {{
      "subject": "<entità soggetto>",
      "predicate": "<relazione in italiano>",
      "object": "<entità o valore oggetto>",
      "confidence": <float 0.0-1.0>
    }}
  ],
  "risk_indicators": [
    {{
      "risk_type": "<tipo rischio>",
      "severity": "<una tra: {severities}>",
      "description": "<spiegazione in italiano>",
      "value": "<valore specifico o null>"
    }}
  ],
  "timeline": [
    {{
      "date": "<data come appare nel documento>",
      "normalized_date": "<ISO-8601 o null>",
      "event": "<descrizione evento in italiano>",
      "significance": "<alta|media|bassa>"
    }}
  ],
  "executive_summary": "<una frase riassuntiva>",
  "key_points": ["<punto 1>", "<punto 2>", ...],
  "detailed_summary": "<1-2 paragrafi di analisi approfondita>"
}}

REGOLE:
- primary_category deve essere uno di: {categories}
- intent deve essere uno di: {intents}
- severity deve essere uno di: {severities}
- confidence deve essere un numero tra 0.0 e 1.0
- key_points: minimo 3, massimo 7 voci
- Elenca SOLO i risk_indicators rilevanti per questo documento (lista vuota se nessuno)
- Elenca SOLO le relazioni significative (non banali)
- Se la data non è convertibile in ISO-8601 usa null per normalized_date
- Tutto il testo descrittivo deve essere in italiano
- Tieni conto delle entità già estratte: {entities_hint}

TASSONOMIA SUBCATEGORIE:
{taxonomy}

TITOLO: {title}

TESTO (max 15000 caratteri):
{text}
"""


# ── Gemini call ───────────────────────────────────────────────────────────────

def _build_prompt(
    text: str,
    title: str,
    entities_hint: str,
) -> str:
    return _PROMPT_TEMPLATE.format(
        categories=", ".join(TAXONOMY.keys()),
        intents=", ".join(INTENT_TYPES),
        severities=", ".join(SEVERITY_LEVELS),
        taxonomy=_TAXONOMY_HINT,
        title=title,
        text=text[:15_000],
        entities_hint=entities_hint or "nessuna entità pre-estratta",
    )


def _parse_response(raw: str) -> dict[str, Any]:
    """Strip optional markdown fences and parse JSON."""
    content = raw.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(content)


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
            value=ri.get("value"),
        )
        for ri in data.get("risk_indicators", [])
        if ri.get("risk_type")
    ]

    timeline = sorted(
        [
            TimelineEvent(
                date=ev.get("date", ""),
                normalized_date=ev.get("normalized_date"),
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
) -> DocumentAnalysis | None:
    """
    Run deep analysis on *text* using a single Gemini call.

    Args:
        text:     Full OCR text of the document.
        title:    Document title.
        api_key:  Gemini API key.
        entities: Pre-extracted entities from LangExtract (optional hint).

    Returns:
        DocumentAnalysis dataclass, or None on failure.
    """
    if not text.strip():
        return None

    # Build a compact hint from already-extracted entities
    entities_hint = ""
    if entities:
        party_names = [e["text"] for e in entities if e.get("class") == "party"][:5]
        dates = [e["text"] for e in entities if e.get("class") == "date"][:5]
        amounts = [e["text"] for e in entities if e.get("class") == "amount"][:3]
        hint_parts = []
        if party_names:
            hint_parts.append("parti: " + ", ".join(party_names))
        if dates:
            hint_parts.append("date: " + ", ".join(dates))
        if amounts:
            hint_parts.append("importi: " + ", ".join(amounts))
        entities_hint = "; ".join(hint_parts)

    prompt = _build_prompt(text, title, entities_hint)

    def _call() -> DocumentAnalysis | None:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            "models/gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"},
        )
        response = model.generate_content(prompt)
        data = _parse_response(response.text)
        return _dict_to_analysis(data)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _call)
        logger.info(
            "Analisi completata per '%s': categoria=%s, rischi=%d",
            title,
            result.classification.primary_category if result else "n/a",
            len(result.risk_indicators) if result else 0,
        )
        return result
    except Exception as exc:
        logger.warning("document_analyzer failed for '%s': %s", title, exc)
        return None


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
