import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from sqlalchemy import text

async def check():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'doc_version_tags';"))
        columns = result.fetchall()
        print("Colonne in 'doc_version_tags':")
        for col in columns:
            print(f" - {col[0]}: {col[1]}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
