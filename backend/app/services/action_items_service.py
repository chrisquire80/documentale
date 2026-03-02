"""
Estrazione automatica di action item, decisioni e questioni aperte
da verbali e note di briefing, tramite Google Gemini.

Usato in _run_ocr_background dopo l'estrazione entità LangExtract.
"""
import asyncio
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def extract_action_items(
    text: str, title: str = "", api_key: str = ""
) -> Dict[str, Any]:
    """
    Usa Gemini per estrarre da una briefing call:
      - decisions:       decisioni prese durante la riunione
      - action_items:    compiti assegnati con responsabile e scadenza
      - open_questions:  questioni rimaste aperte / irrisolte

    Returns:
        Dict con chiavi decisions, action_items, open_questions.
        In caso di errore o testo vuoto ritorna dict con liste vuote.
    """
    if not api_key or not text.strip():
        return {"decisions": [], "action_items": [], "open_questions": []}

    excerpt = text[:8000].strip()

    prompt = f"""Sei un assistente esperto nell'analisi di verbali e note di briefing IT.

Analizza il seguente testo e restituisci ESCLUSIVAMENTE un oggetto JSON con questa struttura:

{{
  "decisions": [
    {{"text": "descrizione della decisione presa", "date": "data se menzionata o null"}}
  ],
  "action_items": [
    {{"action": "cosa deve essere fatto", "owner": "chi è responsabile o null", "deadline": "scadenza o null", "status": "pending"}}
  ],
  "open_questions": [
    {{"text": "questione aperta o irrisolta"}}
  ]
}}

Regole:
- Estrai SOLO elementi esplicitamente menzionati nel testo
- Se non ci sono elementi di una categoria, usa una lista vuota []
- "status" degli action items è sempre "pending"
- Rispondi SOLO con il JSON valido, nessun altro testo

Titolo documento: {title}

Testo:
{excerpt}"""

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        def _call() -> str:
            resp = model.generate_content(prompt)
            return resp.text or "{}"

        raw = await asyncio.get_event_loop().run_in_executor(None, _call)

        # Pulisci eventuali markdown code block
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:])
            if raw.endswith("```"):
                raw = raw[:-3].strip()

        result = json.loads(raw)
        return {
            "decisions": result.get("decisions", []),
            "action_items": result.get("action_items", []),
            "open_questions": result.get("open_questions", []),
        }

    except Exception as exc:
        logger.warning("Action items extraction fallita per '%s': %s", title, exc)
        return {"decisions": [], "action_items": [], "open_questions": []}
