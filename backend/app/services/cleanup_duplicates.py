import asyncio
from sqlalchemy import select, func, and_
from ..db import SessionLocal
from ..models.document import Document
from datetime import timedelta

async def cleanup_duplicates():
    print("Inizio scansione duplicati...")
    async with SessionLocal() as db:
        # Troviamo gruppi di documenti con lo stesso titolo e proprietario
        # che sono stati creati a meno di 5 minuti di distanza
        stmt = (
            select(Document.title, Document.owner_id, func.count(Document.id))
            .where(Document.is_deleted == False)
            .group_by(Document.title, Document.owner_id)
            .having(func.count(Document.id) > 1)
        )
        groups = (await db.execute(stmt)).all()
        
        total_deleted = 0
        for title, owner_id, count in groups:
            # Recupera tutti i documenti per questo gruppo ordinati per data
            docs_stmt = (
                select(Document)
                .where(
                    Document.title == title,
                    Document.owner_id == owner_id,
                    Document.is_deleted == False
                )
                .order_by(Document.created_at.asc())
            )
            docs = (await db.execute(docs_stmt)).scalars().all()
            
            # Mantieni il primo, segna gli altri come eliminati (o eliminali fisicamente)
            # In questo caso facciamo soft delete per sicurezza
            to_keep = docs[0]
            to_delete = docs[1:]
            
            for doc in to_delete:
                # Verifica se sono vicini temporalmente (opzionale, ma consigliato)
                if doc.created_at - to_keep.created_at < timedelta(minutes=10):
                    doc.is_deleted = True
                    total_deleted += 1
        
        await db.commit()
        print(f"Pulizia completata. Documenti duplicati rimossi (soft-delete): {total_deleted}")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
