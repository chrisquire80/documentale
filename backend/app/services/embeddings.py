import google.generativeai as genai
import logging
from typing import List, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)


def _get_configured_genai():
    """Configura e restituisce il modulo genai, o None se non abilitato."""
    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as _genai
        _genai.configure(api_key=settings.GEMINI_API_KEY)
        return _genai
    except Exception as e:
        logger.error(f"Errore configurazione Gemini SDK: {e}")
        return None


async def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Genera il text-embedding vettoriale usando Gemini.
    Model: gemini-embedding-001 (768 dimensions)
    """
    if not text.strip():
        return None
    
    sdk = _get_configured_genai()
    if not sdk:
        logger.warning("Gemini non configurato, embedding saltato.")
        return None

    try:
        truncate_text = text[:10000]
        response = await sdk.embed_content_async(
            model='models/gemini-embedding-001',
            content=truncate_text,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return response['embedding']
    except Exception as e:
        logger.error(f"Errore generazione embedding: {e}")
        return None


async def generate_query_embedding(query: str) -> Optional[List[float]]:
    """
    Genera l'embedding vettoriale per la frase di ricerca dell'utente.
    """
    if not query.strip():
        return None
    
    sdk = _get_configured_genai()
    if not sdk:
        logger.warning("Gemini non configurato, query embedding saltato.")
        return None

    try:
        response = await sdk.embed_content_async(
            model='models/gemini-embedding-001',
            content=query,
            task_type="RETRIEVAL_QUERY"
        )
        return response['embedding']
    except Exception as e:
        logger.error(f"Errore generazione query embedding: {e}")
        return None
