import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from sqlalchemy import text

async def migrate():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.connect() as conn:
        print("Migrazione Wave 10...")
        
        # 1. Aggiunta colonne a doc_version_tags
        try:
            await conn.execute(text("ALTER TABLE doc_version_tags ADD COLUMN confidence FLOAT;"))
            await conn.execute(text("ALTER TABLE doc_version_tags ADD COLUMN ai_reasoning TEXT;"))
            await conn.commit()
            print(" - Colonne added to 'doc_version_tags'.")
        except Exception as e:
            print(f" - Errore 'doc_version_tags': {e}")

        # 2. Creazione tabella doc_conflicts
        try:
            # Creazione ENUM ConflictStatus
            await conn.execute(text("CREATE TYPE conflictstatus AS ENUM ('pending', 'resolved', 'ignored');"))
            await conn.commit()
            print(" - Enum 'conflictstatus' creato.")
        except Exception as e:
            print(f" - Enum 'conflictstatus' gi esistente o errore: {e}")

        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS doc_conflicts (
                    id UUID PRIMARY KEY,
                    document_id UUID NOT NULL REFERENCES documents(id),
                    reference_doc_id UUID REFERENCES documents(id),
                    field VARCHAR NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    severity VARCHAR NOT NULL DEFAULT 'Medium',
                    explanation TEXT,
                    status conflictstatus DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    resolved_at TIMESTAMPTZ,
                    resolved_by UUID REFERENCES users(id)
                );
            """))
            # Indexing
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_doc_conflicts_doc ON doc_conflicts(document_id);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_doc_conflicts_status ON doc_conflicts(status);"))
            await conn.commit()
            print(" - Tabella 'doc_conflicts' creata.")
        except Exception as e:
            print(f" - Errore 'doc_conflicts': {e}")

    await engine.dispose()
    print("Fine migrazione Wave 10.")

if __name__ == "__main__":
    asyncio.run(migrate())
