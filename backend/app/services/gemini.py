import json
import google.generativeai as genai
from typing import Dict, Any
from ..core.config import settings


class GeminiService:
    def __init__(self, api_key: str = settings.GEMINI_API_KEY, enabled: bool = settings.GEMINI_ENABLED):
        self.enabled = enabled and api_key is not None
        if self.enabled:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                "gemini-1.5-flash-8b",
                system_instruction=(
                    "Sei un assistente di analisi documentale italiano. "
                    "Restituisci sempre e solo JSON valido senza markdown."
                ),
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                ),
            )
        else:
            self.model = None

    async def get_tags_and_summary(self, text: str) -> Dict[str, Any]:
        """
        Sends a snippet of text to Gemini to generate tags and a summary.
        """
        if not self.enabled or not text:
            return {"tags": [], "summary": "Gemini interaction disabled or no content provided."}

        snippet = text[:4000]
        prompt = (
            "Analizza il seguente testo di documento. Restituisci un oggetto JSON con:\n"
            "- 'tags': lista di 3-5 parole chiave in italiano\n"
            "- 'summary': riassunto di 2 frasi in italiano\n\n"
            f"TESTO:\n{snippet}"
        )

        try:
            response = await self.model.generate_content_async(prompt)
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini API failure: {e}")
            return {"tags": [], "summary": "Classification failed."}


def get_gemini_service() -> GeminiService:
    return GeminiService()
