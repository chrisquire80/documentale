import asyncio
import google.generativeai as genai
import sys
sys.path.append('/app')
from app.core.config import settings

async def list_models():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    try:
        print("Listing models...")
        for m in genai.list_models():
            if 'embedContent' in m.supported_generation_methods:
                print(f"Embedding Model: {m.name}")
            if 'generateContent' in m.supported_generation_methods:
                print(f"Generation Model: {m.name}")
    except Exception as e:
        print("ERROR:", repr(e))

if __name__ == "__main__":
    asyncio.run(list_models())
