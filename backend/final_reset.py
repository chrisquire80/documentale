import asyncio
import os
import shutil
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/documentale"

async def reset():
    print(f"Connecting to {URL}...")
    engine = create_async_engine(URL)
    
    tables = [
        "doc_version_tags", "doc_conflicts", "document_shares", 
        "doc_metadata", "doc_content", "governance_segnalazione_history", 
        "governance_segnalazioni", "audit_logs", "doc_versions", "documents"
    ]
    
    async with engine.begin() as conn:
        for table in tables:
            try:
                await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                print(f"Truncated {table}")
            except Exception as e:
                print(f"Failed {table}: {e}")
    
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT count(*) FROM documents;"))
        count = res.scalar()
        print(f"Final document count: {count}")
    
    await engine.dispose()

    paths = [
        r"C:\Users\ChristianRobecchi\Downloads\Documentale\backend\storage\documents",
        r"C:\Users\ChristianRobecchi\Downloads\Documentale\backend\auto_ingest"
    ]
    
    for p in paths:
        if os.path.exists(p):
            print(f"Cleaning {p}...")
            for filename in os.listdir(p):
                fpath = os.path.join(p, filename)
                try:
                    if os.path.isfile(fpath):
                        os.unlink(fpath)
                    elif os.path.isdir(fpath):
                        shutil.rmtree(fpath)
                    print(f" - Deleted {filename}")
                except Exception as e:
                    print(f" - Error deleting {filename}: {e}")

if __name__ == "__main__":
    asyncio.run(reset())
