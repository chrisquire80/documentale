import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/documentale"
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT count(*) FROM documents"))
        print(f"COUNT={res.scalar()}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
