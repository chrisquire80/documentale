import asyncio
from sqlalchemy import text
import dotenv
dotenv.load_dotenv()
from app.db import engine

async def migrate_wave_6():
    print("Iniziando migrazione Wave 6 (Aggiunta colonne per Governance / Versioning / RBAC)...")
    async with engine.begin() as conn:
        # 1. Modifiche a documents
        print("Aggiunta colonne a 'documents'...")
        try:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS department VARCHAR;"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_department ON documents (department);"))
        except Exception as e: print(f"Errore su department: {e}")
        
        try:
            # Type ENUM creation correctly
            await conn.execute(text("CREATE TYPE documentstatus AS ENUM ('draft', 'published', 'archived');"))
        except Exception as e: print(f"Type enum err: {e}")

        try:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS status documentstatus DEFAULT 'draft';"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_status ON documents (status);"))
        except Exception as e: print(f"Errore su status: {e}")
        
        try:
            await conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS current_version_id UUID;"))
            await conn.execute(text("ALTER TABLE documents ADD CONSTRAINT fk_doc_current_version FOREIGN KEY (current_version_id) REFERENCES doc_versions (id);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_documents_current_version_id ON documents (current_version_id);"))
        except Exception as e: print(f"Errore su current_version_id: {e}")
        
        # 2. Modifiche a doc_versions
        print("Aggiunta colonne a 'doc_versions'...")
        try:
            # Type ENUM creation correctly
            await conn.execute(text("CREATE TYPE aistatus AS ENUM ('pending', 'processing', 'ready', 'error');"))
        except Exception as e: print(f"Type enum err: {e}")

        try:
            await conn.execute(text("ALTER TABLE doc_versions ADD COLUMN IF NOT EXISTS ai_status aistatus DEFAULT 'pending';"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_doc_versions_ai_status ON doc_versions (ai_status);"))
        except Exception as e: print(f"Errore su ai_status: {e}")

        try:
            await conn.execute(text("ALTER TABLE doc_versions ADD COLUMN IF NOT EXISTS ai_summary TEXT;"))
        except Exception as e: print(f"Errore su ai_summary: {e}")

        try:
            await conn.execute(text("ALTER TABLE doc_versions ADD COLUMN IF NOT EXISTS vector_index_ref VARCHAR;"))
        except Exception as e: print(f"Errore su vector_index_ref: {e}")

    print("Migrazione Wave 6 terminata. Le nuove tabelle (tags, doc_version_tags, audit_logs) verranno create automaticamente al riavvio del backend da Base.metadata.create_all.")

if __name__ == "__main__":
    asyncio.run(migrate_wave_6())
