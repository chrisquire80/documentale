import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def delete_all():
    url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/documentale"
    engine = create_async_engine(url)
    
    async with engine.connect() as conn:
        # Break circular dependency
        try:
            await conn.execute(text("UPDATE documents SET current_version_id = NULL;"))
            await conn.commit()
            print("✅ Current version IDs nulled.")
        except Exception as e:
            print(f"❌ Error nulling versions: {e}")

    tables = [
        "doc_version_tags",
        "doc_conflicts",
        "document_shares",
        "document_comments",
        "document_public_shares",
        "doc_metadata",
        "doc_content",
        "governance_segnalazioni_history",
        "governance_segnalazioni",
        "audit_logs",
        "doc_versions",
        "documents"
    ]
    
    for t in tables:
        async with engine.connect() as conn:
            try:
                await conn.execute(text(f"DELETE FROM {t};"))
                await conn.commit()
                print(f"✅ Deleted from {t}")
            except Exception as e:
                print(f"❌ Error on {t}: {e}")
                
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT count(*) FROM documents;"))
        print(f"Final Count: {res.scalar()}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(delete_all())
