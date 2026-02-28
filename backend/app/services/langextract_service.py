"""
Structured entity extraction for business documents using LangExtract.

LangExtract (https://github.com/google/langextract) wraps LLMs to produce
source-grounded, schema-consistent structured output — every extraction maps
to an exact character span in the original text.

This service extracts the following entity classes from Italian business docs:

  • document_type   – type of document (contratto, fattura, verbale, …)
  • date            – any date mentioned (with role attribute: emissione, scadenza, …)
  • party           – company or person name (with role: emittente, destinatario, …)
  • amount          – monetary figure (with currency attribute)
  • reference       – external reference number (protocol, invoice ID, …)
  • key_term        – domain-specific technical keyword

Results are stored in DocumentMetadata.metadata_json under the key
"extracted_entities" as a list of dicts ready for JSONB querying.
"""

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Prompt ────────────────────────────────────────────────────────────────────

_PROMPT = (
    "Sei un assistente di estrazione dati per documenti aziendali italiani. "
    "Estrai le seguenti entità usando il testo ESATTO presente nel documento:\n"
    "- document_type: tipo di documento (es. contratto, fattura, verbale, delibera, "
    "circolare, relazione, offerta, ordine di acquisto, lettera, ricevuta)\n"
    "- date: qualsiasi data menzionata; attributo 'role': emissione | scadenza | "
    "riferimento | pagamento | decorrenza | altro\n"
    "- party: nome di azienda o persona; attributo 'role': emittente | destinatario | "
    "contraente | firmatario | altro\n"
    "- amount: importo monetario; attributo 'currency': EUR | USD | altro\n"
    "- reference: codice identificativo esterno (numero protocollo, ID fattura, "
    "numero ordine, CIG, CUP)\n"
    "- key_term: termine tecnico o settoriale rilevante\n\n"
    "Usa solo testo che appare letteralmente nel documento. "
    "Non parafrasare. Non sovrapporre entità dello stesso tipo."
)

# ── Few-shot examples (Italian business documents) ────────────────────────────

def _build_examples():
    """Build few-shot ExampleData objects for LangExtract."""
    try:
        import langextract as lx

        return [
            lx.data.ExampleData(
                text=(
                    "CONTRATTO DI FORNITURA N. 2024/087\n"
                    "Tra Alfa S.r.l. (emittente) e Beta S.p.A. (destinatario).\n"
                    "Data di emissione: 15 marzo 2024. Scadenza: 31 dicembre 2024.\n"
                    "Importo totale: € 48.500,00. Riferimento CIG: 9F3A12BC45."
                ),
                extractions=[
                    lx.data.Extraction(
                        extraction_class="document_type",
                        extraction_text="CONTRATTO DI FORNITURA",
                    ),
                    lx.data.Extraction(
                        extraction_class="reference",
                        extraction_text="2024/087",
                    ),
                    lx.data.Extraction(
                        extraction_class="party",
                        extraction_text="Alfa S.r.l.",
                        attributes={"role": "emittente"},
                    ),
                    lx.data.Extraction(
                        extraction_class="party",
                        extraction_text="Beta S.p.A.",
                        attributes={"role": "destinatario"},
                    ),
                    lx.data.Extraction(
                        extraction_class="date",
                        extraction_text="15 marzo 2024",
                        attributes={"role": "emissione"},
                    ),
                    lx.data.Extraction(
                        extraction_class="date",
                        extraction_text="31 dicembre 2024",
                        attributes={"role": "scadenza"},
                    ),
                    lx.data.Extraction(
                        extraction_class="amount",
                        extraction_text="€ 48.500,00",
                        attributes={"currency": "EUR"},
                    ),
                    lx.data.Extraction(
                        extraction_class="reference",
                        extraction_text="9F3A12BC45",
                    ),
                ],
            ),
            lx.data.ExampleData(
                text=(
                    "FATTURA N. FT-2024-0312\n"
                    "Emessa da: Gamma Consulting S.r.l.\n"
                    "Cliente: Comune di Roma\n"
                    "Data fattura: 02/04/2024  Scadenza pagamento: 02/05/2024\n"
                    "Imponibile: USD 12.000,00  IVA 22%: USD 2.640,00\n"
                    "Oggetto: Servizi di consulenza informatica"
                ),
                extractions=[
                    lx.data.Extraction(
                        extraction_class="document_type",
                        extraction_text="FATTURA",
                    ),
                    lx.data.Extraction(
                        extraction_class="reference",
                        extraction_text="FT-2024-0312",
                    ),
                    lx.data.Extraction(
                        extraction_class="party",
                        extraction_text="Gamma Consulting S.r.l.",
                        attributes={"role": "emittente"},
                    ),
                    lx.data.Extraction(
                        extraction_class="party",
                        extraction_text="Comune di Roma",
                        attributes={"role": "destinatario"},
                    ),
                    lx.data.Extraction(
                        extraction_class="date",
                        extraction_text="02/04/2024",
                        attributes={"role": "emissione"},
                    ),
                    lx.data.Extraction(
                        extraction_class="date",
                        extraction_text="02/05/2024",
                        attributes={"role": "pagamento"},
                    ),
                    lx.data.Extraction(
                        extraction_class="amount",
                        extraction_text="USD 12.000,00",
                        attributes={"currency": "USD"},
                    ),
                    lx.data.Extraction(
                        extraction_class="key_term",
                        extraction_text="consulenza informatica",
                    ),
                ],
            ),
        ]
    except Exception as exc:
        logger.warning("langextract not available, skipping few-shot examples: %s", exc)
        return []


# ── Public API ────────────────────────────────────────────────────────────────

async def extract_entities(text: str, api_key: str) -> list[dict[str, Any]]:
    """
    Run LangExtract over *text* and return a flat list of entity dicts.

    Each dict has the shape::

        {
            "class":      "party",
            "text":       "Alfa S.r.l.",
            "attributes": {"role": "emittente"},
            "char_start": 42,
            "char_end":   53,
        }

    Returns an empty list on any error so callers never have to handle
    exceptions — graceful degradation is preserved.

    Args:
        text:    Full OCR text of the document (will be truncated to 20 000 chars).
        api_key: Gemini API key (reuses the project's GEMINI_API_KEY).
    """
    if not text or not text.strip():
        return []

    # Truncate: LangExtract handles chunking internally, but we cap cost/latency.
    excerpt = text[:20_000]

    def _sync_extract() -> list[dict[str, Any]]:
        import langextract as lx  # lazy import; absent in test env → returns []

        examples = _build_examples()
        if not examples:
            return []

        result = lx.extract(
            text_or_documents=excerpt,
            prompt_description=_PROMPT,
            examples=examples,
            model_id="gemini-1.5-flash",
            api_key=api_key,
        )

        entities: list[dict[str, Any]] = []
        # result may be a single AnnotatedDocument or a list
        docs = result if isinstance(result, list) else [result]
        for doc in docs:
            for extraction in getattr(doc, "extractions", []):
                entities.append(
                    {
                        "class": getattr(extraction, "extraction_class", ""),
                        "text": getattr(extraction, "extraction_text", ""),
                        "attributes": dict(getattr(extraction, "attributes", {}) or {}),
                        "char_start": getattr(extraction, "char_start", None),
                        "char_end": getattr(extraction, "char_end", None),
                    }
                )
        return entities

    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_extract)
    except ImportError:
        logger.warning("langextract not installed — skipping structured extraction")
        return []
    except Exception as exc:
        logger.warning("LangExtract extraction failed: %s", exc)
        return []


def entities_to_metadata_patch(entities: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Convert the flat entity list into fields suitable for merging into
    DocumentMetadata.metadata_json.

    Returns a dict with:
        extracted_entities  – full entity list (for querying / display)
        doc_type            – first document_type extraction (string)
        parties             – deduplicated list of party name strings
        dates               – list of {"text": …, "role": …} dicts
        amounts             – list of {"text": …, "currency": …} dicts
        references          – list of reference strings
    """
    patch: dict[str, Any] = {
        "extracted_entities": entities,
        "doc_type": None,
        "parties": [],
        "dates": [],
        "amounts": [],
        "references": [],
    }
    seen_parties: set[str] = set()

    for e in entities:
        cls = e.get("class", "")
        text = e.get("text", "").strip()
        attrs = e.get("attributes", {})

        if not text:
            continue

        if cls == "document_type" and patch["doc_type"] is None:
            patch["doc_type"] = text

        elif cls == "party" and text not in seen_parties:
            seen_parties.add(text)
            patch["parties"].append({"name": text, "role": attrs.get("role", "")})

        elif cls == "date":
            patch["dates"].append({"text": text, "role": attrs.get("role", "")})

        elif cls == "amount":
            patch["amounts"].append(
                {"text": text, "currency": attrs.get("currency", "EUR")}
            )

        elif cls == "reference":
            if text not in patch["references"]:
                patch["references"].append(text)

    return patch
