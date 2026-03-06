import google.generativeai as genai
import json
import logging
from ..core.config import settings
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Configura l'SDK solo se abilitato e con chiave presente
if settings.GEMINI_ENABLED and settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    # Use gemini-2.0-flash as it is fast and suitable for extraction
    model = genai.GenerativeModel('models/gemini-2.0-flash')
else:
    model = None

async def extract_metadata_from_text(text: str) -> Dict[str, Any]:
    """
    Usa Gemini per eseguire una "Deep Analysis" del documento:
    1. Classificazione categoria
    2. Estrazione entità (Date, Importi, Firmatari)
    3. Auto-tagging con citazione pagina
    4. Reasoning (Glass-Box)
    """
    if not model or not text.strip():
        logger.warning("Gemini API not configured or text is empty, skipping deep analysis.")
        return {
            "tags": [], 
            "category": "Generale", 
            "summary": "", 
            "entities": {}, 
            "reasoning": "Dati insufficienti per l'analisi."
        }

    # Limit text to roughly 20000 characters for flash model
    truncate_text = text[:20000]

    prompt = f"""
    Sei un esperto analista di documenti aziendali (stile Dual Basement).
    Esegui una "Deep Analysis" del seguente testo e restituisci ESATTAMENTE e SOLO un JSON valido (nessun preambolo).
    
    OBIETTIVI:
    1. Identificazione Classe: Determina categoria del documento (HR, Legal, Finance, etc).
    2. Tagging Gerarchico: Estrai tag divisi per Dominio (contenuto), Governance (riservatezza), Azione (workflow).
    3. NER: Estrai entità critiche (Date, Importi, Firmatari, Riferimenti Normativi come 'Art. X').
    4. Confidenza: Assegna un punteggio da 0.0 a 1.0 per ogni tag ed entità.
    5. Citazioni: Indica sempre la pagina di riferimento dove possibile.
    6. Reasoning (Glass-Box): Per ogni tag, spiega brevemente perché è stato suggerito (es. "Trovato riferimento a X a pagina Y").

    STRUTTURA JSON RICHIESTA:
    {{
        "category": "HR|Legal|IT|Finance|Generale",
        "tags": [
            {{
                "name": "tag1", 
                "page": 1, 
                "confidence": 0.95,
                "reasoning": "Descrizione del perché è stato estratto"
            }}
        ],
        "entities": {{
            "dates": ["YYYY-MM-DD"],
            "amounts": ["€..."],
            "signatories": ["Nome Cognome"],
            "references": ["Art. X"]
        }},
        "summary": "Massimo 3 righe in italiano",
        "global_reasoning": "Spiegazione complessiva della logica di estrazione (AI Act compliance)"
    }}

    TESTO DA ANALIZZARE:
    {truncate_text}
    """

    try:
        response = await model.generate_content_async(prompt)
        content = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        
        return {
            "category": data.get("category", "Generale"),
            "tags": data.get("tags", []),
            "entities": data.get("entities", {}),
            "summary": data.get("summary", ""),
            "reasoning": data.get("global_reasoning", "Analisi eseguita basandosi sui pattern testuali rilevati.")
        }
    except Exception as e:
        logger.error(f"Errore Deep Analysis Gemini: {e}")
        return {
            "tags": [], 
            "category": "Generale", 
            "summary": "", 
            "entities": {}, 
            "reasoning": f"Errore tecnico: {str(e)}"
        }
