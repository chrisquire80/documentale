"""
Auto-tagging di documenti tramite Google Gemini.

Uso: chiama `suggest_tags(text, title)` per ottenere una lista di tag
da aggiungere ai metadati del documento.

Richiede GEMINI_API_KEY configurato in .env / env del container.
Se la chiave non è configurata o la chiamata fallisce, restituisce [] in
modo silenzioso, garantendo graceful degradation.
"""
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

_MODEL = "gemini-1.5-flash-8b"
_SYSTEM = (
    "Sei un assistente di classificazione documentale italiano. "
    "Rispondi sempre e solo con JSON valido, nessun testo aggiuntivo."
)


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

    excerpt = (text or "")[:4000].strip()
    if not excerpt and not title:
        return []

    prompt = (
        "Analizza il seguente documento e restituisci una lista di tag in italiano "
        "(massimo 8, stringhe lowercase) che descrivono l'argomento principale.\n"
        'Formato risposta: {"tags": ["tag1", "tag2", ...]}\n\n'
        f"Titolo: {title}\n\nTesto:\n{excerpt}"
    )

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            _MODEL,
            system_instruction=_SYSTEM,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        response = await model.generate_content_async(prompt)
        data = json.loads(response.text)
        tags = [t.strip().lower() for t in data.get("tags", []) if t.strip()]
        return tags[:8]

    except Exception as exc:
        logger.warning("Gemini auto-tag fallito: %s", exc)
        return []
