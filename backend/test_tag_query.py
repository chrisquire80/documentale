import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/documentale"

async def test():
    engine = create_async_engine(URL)
    async with engine.begin() as conn:
        # Probabile problema di precedenza virgola vs JOIN
        query = text("""
            SELECT tag, count(*) 
            FROM doc_metadata, jsonb_array_elements_text(COALESCE(metadata_json->'tags', '[]'::jsonb)) as tag
            JOIN documents ON documents.id = doc_metadata.document_id
            WHERE documents.is_deleted = false
            GROUP BY tag
            ORDER BY count(*) DESC
            LIMIT 20
        """)
        try:
            res = await conn.execute(query)
            print("Query (original) works!")
            for row in res:
                print(row)
        except Exception as e:
            print(f"Original Query failed: {e}")

        # Test fix
        query_fix = text("""
            SELECT tag, count(*) 
            FROM doc_metadata dm
            CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(dm.metadata_json->'tags', '[]'::jsonb)) as tag
            JOIN documents d ON d.id = dm.document_id
            WHERE d.is_deleted = false
            GROUP BY tag
            ORDER BY count(*) DESC
            LIMIT 20
        """)
        try:
            res = await conn.execute(query_fix)
            print("Fixed Query works!")
            for row in res:
                print(row)
        except Exception as e:
            print(f"Fixed Query failed: {e}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test())
