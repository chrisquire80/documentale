import asyncio
import os
from sqlalchemy import text
from app.db import engine
from app.core.config import settings

async def reset():
    print(f"Using DATABASE_URL: {settings.DATABASE_URL}")
    async with engine.begin() as conn:
        tables = [
            "doc_version_tags", "doc_conflicts", "document_shares", 
            "doc_metadata", "doc_content", "governance_segnalazione_history", 
            "governance_segnalazioni", "audit_logs", "doc_versions", "documents"
        ]
        for table in tables:
            try:
                await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                print(f"Truncated {table}")
            except Exception as e:
                print(f"Failed {table}: {e}")

if __name__ == "__main__":
    asyncio.run(reset())
