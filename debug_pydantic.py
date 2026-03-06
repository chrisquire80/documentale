import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.db import SessionLocal
from app.models.document import Document, DocumentVersion, DocumentVersionTag
from app.schemas.doc_schemas import DocumentResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def find_failing_doc():
    async with SessionLocal() as db:
        stmt = (
            select(Document)
            .options(
                selectinload(Document.metadata_entries),
                selectinload(Document.owner),
                selectinload(Document.content),
                selectinload(Document.versions).selectinload(DocumentVersion.tags).selectinload(DocumentVersionTag.tag),
                selectinload(Document.current_version_rel)
            )
        )
        results = await db.execute(stmt)
        docs = results.scalars().unique().all()
        
        print(f"Checking {len(docs)} documents...")
        failed_count = 0
        for doc in docs:
            # Mock the attributes we set in search
            setattr(doc, 'highlight_snippet', "test snippet")
            setattr(doc, 'is_indexed', True)
            setattr(doc, 'relevance_score', 95.5)
            
            try:
                DocumentResponse.model_validate(doc)
            except Exception as e:
                failed_count += 1
                print(f"FAILED doc: {doc.id} - {doc.title}")
                print(f"  Error: {e}")
        
        print(f"Done. Failed: {failed_count}")

if __name__ == "__main__":
    asyncio.run(find_failing_doc())
