import asyncio
import os
import sys
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Aggiungi il path del backend per importare i moduli
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from app.db import Base
from app.models.document import Document

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/documentale"

async def check_docs():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Conteggio is_deleted vs deleted_at
        stmt_active_is_deleted = select(func.count(Document.id)).where(Document.is_deleted == False)
        stmt_active_deleted_at = select(func.count(Document.id)).where(Document.deleted_at.is_(None))
        
        count_is_deleted = (await session.execute(stmt_active_is_deleted)).scalar()
        count_deleted_at = (await session.execute(stmt_active_deleted_at)).scalar()
        
        print(f"Documenti con is_deleted=False: {count_is_deleted}")
        print(f"Documenti con deleted_at=None: {count_deleted_at}")
        
        # Campione di documenti problematici
        stmt_problem = select(Document.id, Document.title, Document.is_deleted, Document.deleted_at).where(
            Document.is_deleted == False,
            Document.deleted_at.isnot(None)
        ).limit(5)
        
        problems = (await session.execute(stmt_problem)).all()
        if problems:
            print("\nDocumenti con is_deleted=False MA deleted_at impostato:")
            for p in problems:
                print(f"ID: {p.id}, Title: {p.title}, is_deleted: {p.is_deleted}, deleted_at: {p.deleted_at}")
        else:
            print("\nNessun documento con discrepanza is_deleted/deleted_at trovata.")

if __name__ == "__main__":
    asyncio.run(check_docs())
