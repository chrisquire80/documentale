import google.generativeai as genai
import logging
from typing import List, Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

# Configura l'SDK solo se abilitato e con chiave presente
if settings.GEMINI_ENABLED and settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
else:
    genai = None

async def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Genera il text-embedding vettoriale usando Gemini.
    Model: text-embedding-004 (768 dimensions by default)
    """
    if not genai or not text.strip():
        return None

    try:
        # truncate for embedding model limit ~2048 tokens / ~8000 chars roughly. Let's do 10000 limit.
        truncate_text = text[:10000]
        
        # Generazione dell'embedding
        # Il task_type=RETRIEVAL_DOCUMENT ottimizza l'embedding per essere memorizzato nel DB
        response = await genai.embed_content_async(
            model='models/gemini-embedding-001',
            content=truncate_text,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return response['embedding']
    except Exception as e:
        logger.error(f"Errore durante la generazione dell'embedding con Gemini: {e}")
        return None

async def generate_query_embedding(query: str) -> Optional[List[float]]:
    """
    Genera l'embedding vettoriale per la frase di ricerca dell'utente.
    """
    if not genai or not query.strip():
        return None

    try:
        response = await genai.embed_content_async(
            model='models/gemini-embedding-001',
            content=query,
            task_type="RETRIEVAL_QUERY"
        )
        return response['embedding']
    except Exception as e:
        logger.error(f"Errore generazione query embedding con Gemini: {e}")
        return None
