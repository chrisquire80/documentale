import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from sqlalchemy import text

async def migrate():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.connect() as conn:
        print("Aggiungendo la colonna 'category' a 'documents'...")
        try:
            async with conn.begin():
                await conn.execute(text("ALTER TABLE documents ADD COLUMN category VARCHAR;"))
        except Exception as e:
            print(f"Errore / Colonna gi esistente: {e}")

        print("Aggiungendo 'ai_entities' a 'doc_versions'...")
        try:
            async with conn.begin():
                await conn.execute(text("ALTER TABLE doc_versions ADD COLUMN ai_entities JSONB;"))
        except Exception as e:
            print(f"Errore / Colonna gi esistente: {e}")
            
        print("Aggiungendo 'ai_reasoning' a 'doc_versions'...")
        try:
            async with conn.begin():
                await conn.execute(text("ALTER TABLE doc_versions ADD COLUMN ai_reasoning JSONB;"))
        except Exception as e:
            print(f"Errore / Colonna gi esistente: {e}")

    await engine.dispose()
    print("Migrazione completata!")

if __name__ == "__main__":
    asyncio.run(migrate())
