"""Built-in plugin: adds word / character statistics to document metadata."""
from typing import Optional

from ..base import DocumentPlugin, MetadataContext


class WordCountPlugin(DocumentPlugin):
    """Appends ``word_count``, ``char_count``, and ``avg_word_length`` to
    the document's metadata JSON after AI extraction completes."""

    name = "word_count"
    version = "1.0.0"
    description = (
        "Aggiunge conteggio parole, caratteri e lunghezza media delle parole "
        "ai metadati del documento."
    )

    async def on_metadata_extracted(self, ctx: MetadataContext) -> Optional[dict]:
        if not ctx.corpus:
            return None
        words = ctx.corpus.split()
        if not words:
            return None
        return {
            "word_count": len(words),
            "char_count": len(ctx.corpus),
            "avg_word_length": round(
                sum(len(w) for w in words) / len(words), 2
            ),
        }
