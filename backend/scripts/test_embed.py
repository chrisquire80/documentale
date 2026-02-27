import asyncio
import google.generativeai as genai
import sys
sys.path.append('/app')
from app.core.config import settings

async def test():
    print(f"Key enabled: {settings.GEMINI_ENABLED}")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    try:
        response = await genai.embed_content_async(
            model='models/gemini-embedding-001',
            content='hi',
            task_type="RETRIEVAL_QUERY"
        )
        print("Success!", len(response['embedding']))
    except Exception as e:
        print("ERROR:", repr(e))

if __name__ == "__main__":
    asyncio.run(test())
