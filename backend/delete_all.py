import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def delete_all():
    url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/documentale"
    engine = create_async_engine(url)
    
    async with engine.begin() as conn:
        # PostgreSQL CASCADE on DELETE
        try:
            # We delete the parent, and if FKs are CASCADE, it wipes everything.
            # If not, we do it manually in reverse order.
            tables = [
                "doc_version_tags", "doc_conflicts", "document_shares", 
                "doc_metadata", "doc_content", "governance_segnalazione_history", 
                "governance_segnalazioni", "audit_logs", "doc_versions", "documents"
            ]
            for t in tables:
                await conn.execute(text(f"DELETE FROM {t};"))
                print(f"Deleted from {t}")
            
            res = await conn.execute(text("SELECT count(*) FROM documents;"))
            print(f"Final Count: {res.scalar()}")
        except Exception as e:
            print(f"Error: {e}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(delete_all())
