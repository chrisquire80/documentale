import os
import shutil
import asyncio
import uuid
import json
from pathlib import Path
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
import aiofiles

from ..db import SessionLocal
from ..models.user import User
from ..models.document import Document, DocumentVersion, DocumentMetadata, DocumentContent
from ..models.audit import AuditLog
from ..core.storage import LocalStorage
from ..core.config import settings
from ..api.ws import manager
from ..services.ocr import extract_text as ocr_extract_text
from ..services.llm_metadata import extract_metadata_from_text
from ..services.embeddings import generate_embedding
from sqlalchemy import select

# Mappa estensione → MIME type per l'OCR
_EXT_MIME = {
    '.pdf':  'application/pdf',
    '.txt':  'text/plain',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png':  'image/png',
}

class AutoIngestHandler(FileSystemEventHandler):
    def __init__(self, loop):
        self.loop = loop
        self.storage = LocalStorage(settings.STORAGE_PATH)
        self.processing_files = set() # Track files currently being ingested

    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            ext = os.path.splitext(file_path)[1].lower()
            if ext in settings.ALLOWED_EXTENSIONS:
                if file_path in self.processing_files:
                    return
                
                print(f"Watchdog: Detected new file {file_path}. Scheduling ingestion...")
                self.processing_files.add(file_path)
                # Schedule the async ingestion task safely onto the main loop
                self.loop.call_soon_threadsafe(
                    lambda p: self.loop.create_task(self.process_file_safe(p)),
                    file_path
                )

    async def get_system_user(self, db: AsyncSession):
        stmt = select(User).where(User.email == settings.AUTO_USER_EMAIL)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def process_file_safe(self, file_path: str):
        try:
            await self.process_file(file_path)
        finally:
            if file_path in self.processing_files:
                self.processing_files.remove(file_path)

    async def process_file(self, file_path: str):
        # Wait a bit to ensure the file is completely written (copied) by the host OS
        await asyncio.sleep(2)
        
        if not os.path.exists(file_path):
            return

        marker_file = f"{file_path}.processed"
        if os.path.exists(marker_file):
            print(f"Watchdog: {file_path} already processed. Skipping.")
            return

        filename = os.path.basename(file_path)
        print(f"Watchdog: Starting ingestion for {filename}")

        async with SessionLocal() as db:
            try:
                system_user = await self.get_system_user(db)
                if not system_user:
                    print(f"Watchdog Error: System user {settings.AUTO_USER_EMAIL} not found. Cannot assign document.")
                    return

                # Read file into memory to pass to storage (simulating UploadFile behavior)
                file_size = os.path.getsize(file_path)
                with open(file_path, 'rb') as f:
                    # 1. Save file to storage
                    file_rel_path = await self.storage.save_file(f, filename)
                
                # 2. Create Document entry
                doc = Document(
                    title=filename,
                    owner_id=system_user.id,
                    is_restricted=False
                )
                db.add(doc)
                await db.flush() # Get ID
                
                # 3. Create Version entry
                version = DocumentVersion(
                    document_id=doc.id,
                    version_num=1,
                    file_path=file_rel_path
                )
                db.add(version)
                
                # 4. Create Metadata entry (auto-tagged)
                meta = DocumentMetadata(
                    document_id=doc.id,
                    metadata_json={"tags": ["auto-ingest"]}
                )
                db.add(meta)

                # 5. Estrai testo via OCR e crea DocumentContent per FTS
                ext = os.path.splitext(filename)[1].lower()
                content_type = _EXT_MIME.get(ext, 'application/octet-stream')
                abs_path = await self.storage.get_file_path(file_rel_path)
                ocr_text = await ocr_extract_text(abs_path, content_type)
                corpus = f"{filename} {ocr_text}".strip() if ocr_text else filename
                doc_content = DocumentContent(
                    document_id=doc.id,
                    fulltext_content=corpus,
                )
                db.add(doc_content)
                
                # 5.5 Auto-tagging con Gemini
                ai_metadata = await extract_metadata_from_text(corpus)
                if ai_metadata:
                    current_json = meta.metadata_json
                    existing_tags = set(current_json.get("tags", []))
                    ai_tags = set(ai_metadata.get("tags", []))
                    current_json["tags"] = list(existing_tags.union(ai_tags))
                    
                    if ai_metadata.get("department") and ai_metadata["department"] != "Generale":
                        current_json["dept"] = ai_metadata["department"]
                        
                    meta.metadata_json = dict(current_json)

                # 5.6 Semantic Embeddings
                ai_embedding = await generate_embedding(corpus)
                if ai_embedding:
                    doc_content.embedding = ai_embedding

                # 6. Audit log
                audit = AuditLog(user_id=system_user.id, action="AUTO_UPLOAD", target_id=doc.id, details="Ingested by Documentale Watchdog")
                db.add(audit)

                await db.commit()
                print(f"Watchdog: Successfully ingested {filename}. Marking as processed...")
                
                # Invia notifica WebSocket
                try:
                    await manager.broadcast({
                        "type": "DOCUMENT_INGESTED",
                        "document": {
                            "id": str(doc.id),
                            "title": doc.title
                        },
                        "message": f"Nuovo documento importato: {doc.title}"
                    })
                except Exception as e:
                    print(f"Watchdog: Impossibile inviare notifica WS: {e}")
                
                # Create a marker file so it doesn't get processed again
                marker_file = f"{file_path}.processed"
                with open(marker_file, 'w') as mf:
                    mf.write(f"Ingested as Document ID: {doc.id}")
                
            except Exception as e:
                await db.rollback()
                print(f"Watchdog Error processing {filename}: {e}")

# Global observer instance
observer = None

def start_watcher():
    global observer
    if not os.path.exists(settings.WATCH_DIR):
        os.makedirs(settings.WATCH_DIR, exist_ok=True)
        
    loop = asyncio.get_running_loop()
    event_handler = AutoIngestHandler(loop)
    
    # We use PollingObserver because standard inotify doesn't work well across Windows->WSL->Docker volume boundaries
    observer = PollingObserver()
    observer.schedule(event_handler, settings.WATCH_DIR, recursive=False)
    observer.start()
    print(f"Watchdog: Started monitoring {settings.WATCH_DIR}")

def stop_watcher():
    global observer
    if observer:
        observer.stop()
        observer.join()
        print("Watchdog: Stopped monitoring.")
