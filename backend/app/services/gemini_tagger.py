"""
Auto-tagging di documenti tramite Google Gemini.

Uso: chiama `suggest_tags(text, title)` per ottenere una lista di tag
da aggiungere ai metadati del documento.

Richiede GEMINI_API_KEY configurato in .env / env del container.
Se la chiave non è configurata o la chiamata fallisce, restituisce [] in
modo silenzioso, garantendo graceful degradation.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


async def suggest_tags(text: str, title: str = "") -> List[str]:
    """
    Propone una lista di tag per il documento usando Gemini.

    Args:
        text:  Testo estratto dal documento (fulltext_content).
        title: Titolo del documento (per contesto aggiuntivo).

    Returns:
        Lista di stringhe (tag) — al massimo 8.
        Lista vuota in caso di errore o chiave API non configurata.
    """
    from ..core.config import settings  # import lazy per evitare cicli

    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return []

    # Tronca il testo al massimo a 4000 caratteri per contenere i costi
    excerpt = (text or "")[:4000].strip()
    if not excerpt and not title:
        return []

    prompt = (
        "Sei un assistente di classificazione documentale. "
        "Analizza il seguente testo e restituisci una lista di tag in italiano "
        "(massimo 8 tag, separati da virgola) che descrivono l'argomento "
        "principale del documento. Rispondi SOLO con i tag, nessun testo aggiuntivo.\n\n"
        f"Titolo: {title}\n\nTesto:\n{excerpt}"
    )

    try:
        import asyncio
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        # Gemini SDK è sincrono; eseguiamo in thread-pool
        def _call() -> str:
            response = model.generate_content(prompt)
            return response.text or ""

        raw = await asyncio.get_event_loop().run_in_executor(None, _call)

        tags = [t.strip().lower() for t in raw.split(",") if t.strip()]
        return tags[:8]

    except Exception as exc:
        logger.warning("Gemini auto-tag fallito: %s", exc)
        return []
