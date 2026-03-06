import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def reset_and_check():
    url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/documentale"
    print(f"Connecting to {url}...")
    engine = create_async_engine(url)
    
    tables = [
        "doc_version_tags", "doc_conflicts", "document_shares", 
        "doc_metadata", "doc_content", "governance_segnalazione_history", 
        "governance_segnalazioni", "audit_logs", "doc_versions", "documents"
    ]
    
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            for table in tables:
                await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                print(f"Truncated {table}")
            await trans.commit()
            print("Transaction Committed.")
        except Exception as e:
            await trans.rollback()
            print(f"Rollback due to: {e}")
            
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT count(*) FROM documents;"))
        print(f"Final Count in script: {res.scalar()}")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_and_check())
