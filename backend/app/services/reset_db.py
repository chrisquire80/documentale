import asyncio
import os
import shutil
from sqlalchemy import text
from sqlalchemy.sql import quoted_name
from ..db import SessionLocal, engine
from ..core.config import settings

# Whitelist rigida delle tabelle che possono essere svuotate per sicurezza
ALLOWED_TABLES = {
    "doc_version_tags",
    "doc_conflicts",
    "document_shares",
    "doc_metadata",
    "doc_content",
    "governance_segnalazione_history",
    "governance_segnalazioni",
    "audit_logs",
    "doc_versions",
    "documents"
}

async def reset_database():
    print("⚠️  ATTENZIONE: Questo script eliminerà TUTTI i documenti, versioni, metadati e segnalazioni.")
    print("Gli utenti e le impostazioni di sistema verranno mantenuti.")
    
    # Conferma manuale se eseguito direttamente (ma qui lo prepariamo per l'utente)
    
    async with engine.begin() as conn:
        print("Svuotamento tabelle in corso...")
        # L'ordine è importante per le chiavi esterne se non si usa CASCADE
        tables = [
            "doc_version_tags",
            "doc_conflicts",
            "document_shares",
            "doc_metadata",
            "doc_content",
            "governance_segnalazione_history",
            "governance_segnalazioni",
            "audit_logs",
            "doc_versions",
            "documents"
        ]
        
        for table in tables:
            if table not in ALLOWED_TABLES:
                print(f"⚠️  Salto tabella non autorizzata: {table}")
                continue
            try:
                # Usiamo quoted_name per gestire correttamente gli identificatori SQL
                safe_table = quoted_name(table, quote=True)
                await conn.execute(text(f"TRUNCATE TABLE {safe_table} RESTART IDENTITY CASCADE;"))
                print(f" - Tabella {table} svuotata.")
            except Exception as e:
                print(f" - Errore su {table}: {e}")

    # Pulizia storage fisico
    storage_path = settings.STORAGE_PATH
    if os.path.exists(storage_path):
        print(f"Pulizia cartella storage: {storage_path}")
        for filename in os.listdir(storage_path):
            file_path = os.path.join(storage_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                print(f" - Rimosso: {filename}")
            except Exception as e:
                print(f" - Impossibile rimuovere {file_path}: {e}")
                
    # Pulizia marker Watchdog
    watch_dir = settings.WATCH_DIR
    if os.path.exists(watch_dir):
        print(f"Pulizia marker Watchdog in: {watch_dir}")
        for filename in os.listdir(watch_dir):
            if filename.endswith(".processed"):
                file_path = os.path.join(watch_dir, filename)
                try:
                    os.unlink(file_path)
                    print(f" - Rimosso marker: {filename}")
                except Exception as e:
                    print(f" - Impossibile rimuovere marker {file_path}: {e}")

    print("\n✅ Reset completato con successo. Il sistema è ora pulito.")

if __name__ == "__main__":
    asyncio.run(reset_database())
