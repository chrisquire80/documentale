import asyncio
import sys
from sqlalchemy import text
from app.db import engine

async def repair_db():
    try:
        async with engine.begin() as conn:
            query = """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='documents' AND column_name='deleted_at') THEN
                    ALTER TABLE documents ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
                END IF;
            END $$;
            """
            await conn.execute(text(query))
            print("Successfully added deleted_at to documents table")
    except Exception as e:
        print(f"Error altering table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(repair_db())
