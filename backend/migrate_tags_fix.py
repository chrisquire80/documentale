import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from sqlalchemy import text

async def migrate():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.connect() as conn:
        print("Aggiungendo colonne a 'doc_version_tags'...")
        try:
            async with conn.begin():
                # Note: 'status' is an enum in the model, but let's use VARCHAR for simplicity in migration if the enum type doesn't exist yet, 
                # or just use plain VARCHAR for the migration. 
                # Actually, the model uses TagStatus enum.
                await conn.execute(text("ALTER TABLE doc_version_tags ADD COLUMN status VARCHAR;"))
                await conn.execute(text("ALTER TABLE doc_version_tags ADD COLUMN page_number INTEGER;"))
                # If is_ai_generated is also missing
                await conn.execute(text("ALTER TABLE doc_version_tags ADD COLUMN is_ai_generated BOOLEAN DEFAULT FALSE;"))
        except Exception as e:
            print(f"Errore / Colonne gi esistenti: {e}")

    await engine.dispose()
    print("Migrazione completata!")

if __name__ == "__main__":
    asyncio.run(migrate())
