import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from sqlalchemy import text

async def migrate():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.connect() as conn:
        print("Migrazione 'doc_version_tags'...")
        
        cols_to_add = [
            ("status", "VARCHAR"),
            ("page_number", "INTEGER"),
            ("is_ai_generated", "BOOLEAN DEFAULT FALSE")
        ]
        
        for col_name, col_type in cols_to_add:
            try:
                await conn.execute(text(f"ALTER TABLE doc_version_tags ADD COLUMN {col_name} {col_type};"))
                await conn.commit()
                print(f" - Colonna '{col_name}' aggiunta con successo.")
            except Exception as e:
                print(f" - Colonna '{col_name}' gi esistente o errore: {e}")

    await engine.dispose()
    print("Fine migrazione.")

if __name__ == "__main__":
    asyncio.run(migrate())
