import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from sqlalchemy import text

async def migrate():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.connect() as conn:
        print("Modificando il tipo di 'ai_reasoning' in 'doc_versions' a TEXT...")
        try:
            async with conn.begin():
                await conn.execute(text("ALTER TABLE doc_versions ALTER COLUMN ai_reasoning TYPE TEXT;"))
        except Exception as e:
            print(f"Errore / Alter column: {e}")

    await engine.dispose()
    print("Migrazione completata!")

if __name__ == "__main__":
    asyncio.run(migrate())
