import google.generativeai as genai
import json
import logging
from ..core.config import settings
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Configura l'SDK solo se abilitato e con chiave presente
if settings.GEMINI_ENABLED and settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    # Use gemini-1.5-flash as it is fast and suitable for extraction
    model = genai.GenerativeModel('models/gemini-1.5-flash')
else:
    model = None

async def extract_metadata_from_text(text: str) -> Dict[str, Any]:
    """
    Usa Gemini per analizzare il testo di un documento e suggerire tag e un dipartimento.
    """
    if not model or not text.strip():
        logger.warning("Gemini API not configured or text is empty, skipping auto-tagging.")
        return {"tags": [], "department": "Generale"}

    # Limit text to roughly 15000 characters to save tokens and inference time
    truncate_text = text[:15000]

    prompt = f"""
    Sei un assistente per un Document Management System aziendale.
    Analizza il seguente testo estratto da un documento e restituisci ESATTAMENTE e SOLO un JSON valido con questa struttura (nessun preambolo, nessun blocco markdown come ```json):
    {{
        "tags": ["keyword1", "keyword2", "keyword3"],
        "department": "NomeDipartimento"
    }}

    Regole:
    - Estrai al massimo 5 tags (max 15 caratteri l'uno, pertinenti).
    - Suggerisci un dipartimento tra questi: "IT", "Risorse Umane", "Amministrazione", "Marketing", "Vendite", "Legale", "Direzione", "Generale". Se non sei sicuro, rispondi "Generale".

    Testo da analizzare:
    {truncate_text}
    """

    try:
        response = await model.generate_content_async(prompt)
        content = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        
        return {
            "tags": data.get("tags", []),
            "department": data.get("department", "Generale")
        }
    except Exception as e:
        logger.error(f"Errore durante l'estrazione metadata con Gemini: {e}")
        return {"tags": [], "department": "Generale"}
