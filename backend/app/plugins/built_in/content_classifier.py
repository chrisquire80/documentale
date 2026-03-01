"""Built-in plugin: infers document type from keyword heuristics."""
from typing import Optional

from ..base import DocumentPlugin, MetadataContext

_KEYWORD_MAP: dict[str, list[str]] = {
    "fattura": [
        "fattura", "importo", "iva", "pagamento", "totale", "imponibile",
        "invoice", "amount due", "tax",
    ],
    "contratto": [
        "contratto", "accordo", "parti", "firmatario", "clausola",
        "obbligazioni", "contract", "agreement", "parties", "clause",
    ],
    "rapporto": [
        "rapporto", "relazione", "analisi", "risultati", "conclusioni",
        "sintesi", "report", "findings", "analysis", "summary",
    ],
    "lettera": [
        "gentile", "cordiali saluti", "in fede", "oggetto",
        "dear", "sincerely", "regards", "subject",
    ],
    "verbale": [
        "verbale", "riunione", "ordine del giorno", "presenti",
        "minutes", "meeting", "agenda", "attendees",
    ],
}


class ContentClassifierPlugin(DocumentPlugin):
    """Infers ``inferred_doc_type`` in document metadata using keyword scoring."""

    name = "content_classifier"
    version = "1.0.0"
    description = (
        "Classifica euristicamente il tipo di documento "
        "(fattura, contratto, rapporto, lettera, verbale) "
        "in base alle parole chiave nel testo estratto."
    )

    async def on_metadata_extracted(self, ctx: MetadataContext) -> Optional[dict]:
        if not ctx.corpus:
            return None

        text_lower = ctx.corpus.lower()
        scores: dict[str, int] = {
            doc_type: sum(1 for kw in keywords if kw in text_lower)
            for doc_type, keywords in _KEYWORD_MAP.items()
        }
        best_type, best_score = max(scores.items(), key=lambda kv: kv[1])
        if best_score == 0:
            return None
        return {"inferred_doc_type": best_type}
