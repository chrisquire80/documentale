import asyncio
from sqlalchemy import text
from app.db import engine

async def check():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT count(*) FROM documents;"))
        print(f"Counts: {res.scalar()}")

if __name__ == "__main__":
    asyncio.run(check())
