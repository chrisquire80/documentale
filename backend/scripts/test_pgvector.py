import asyncio
import sys
sys.path.append('/app')
from sqlalchemy import select, func
from app.db import SessionLocal
from app.models.document import DocumentContent
from pgvector.sqlalchemy import Vector

async def test_search():
    query_emb = [0.1] * 768
    async with SessionLocal() as db:
        try:
            # Test simple order by
            print("Testing order_by with cosine_distance...")
            stmt = select(DocumentContent).order_by(DocumentContent.embedding.cosine_distance(query_emb)).limit(1)
            res = await db.execute(stmt)
            print("Order by success!")
            
            # Test where condition
            print("Testing where condition with cosine_distance...")
            stmt2 = select(DocumentContent).where(DocumentContent.embedding.cosine_distance(query_emb) < 0.65).limit(1)
            res2 = await db.execute(stmt2)
            print("Where condition success!")
            
        except Exception as e:
            print("ERROR:", repr(e))
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())
