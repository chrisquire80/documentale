import google.generativeai as genai
from typing import Optional, List, Dict, Any
from ..core.config import settings

class GeminiService:
    def __init__(self, api_key: str = settings.GEMINI_API_KEY, enabled: bool = settings.GEMINI_ENABLED):
        self.enabled = enabled and api_key is not None
        if self.enabled:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None

    async def get_tags_and_summary(self, text: str) -> Dict[str, Any]:
        """
        Sends a snippet of text to Gemini to generate tags and a summary.
        """
        if not self.enabled or not text:
            return {"tags": [], "summary": "Gemini interaction disabled or no content provided."}

        # Data minimization: Send only the first 4000 characters
        snippet = text[:4000]
        
        prompt = (
            "Analyze the following document text. "
            "Return a JSON object with 'tags' (a list of 3-5 keywords) and 'summary' (a 2-sentence summary). "
            "Output ONLY the JSON object.\n\n"
            f"TEXT: {snippet}"
        )

        try:
            # Note: The official library might not be fully async, 
            # for a production app consider running in a threadpool if it blocks.
            response = self.model.generate_content(prompt)
            # Basic parsing (in a real app, use more robust JSON cleaning)
            content = response.text.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            
            import json
            return json.loads(content)
        except Exception as e:
            # Log failure but don't break the app
            print(f"Gemini API failure: {e}")
            return {"tags": [], "summary": "Classification failed."}

def get_gemini_service() -> GeminiService:
    return GeminiService()
