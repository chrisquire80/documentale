import asyncio
import sys
sys.path.append('/app')
from app.db import SessionLocal
from app.models.document import Document, DocumentContent
from sqlalchemy import select

async def verify():
    async with SessionLocal() as db:
        # Check total documents
        res = await db.execute(select(Document))
        docs = res.scalars().all()
        print(f"Total documents: {len(docs)}")
        
        # Check embeddings
        res = await db.execute(select(DocumentContent).where(DocumentContent.embedding.isnot(None)))
        contents = res.scalars().all()
        print(f"Documents with embeddings: {len(contents)}")
        
        # Check text
        res = await db.execute(select(DocumentContent).where(DocumentContent.fulltext_content.isnot(None)))
        texts = res.scalars().all()
        print(f"Documents with fulltext: {len(texts)}")

if __name__ == "__main__":
    asyncio.run(verify())
