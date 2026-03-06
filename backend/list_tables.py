import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def list_tables():
    url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/documentale"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"))
        for row in res:
            print(row[0])
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(list_tables())
