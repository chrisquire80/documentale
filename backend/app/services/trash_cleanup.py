import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from ..db import SessionLocal
from ..models.document import Document
from ..services.storage import StorageLayer

logger = logging.getLogger(__name__)

async def cleanup_trash(retention_days: int = 30):
    """
    Remove documents from database and storage that have been in the trash 
    longer than `retention_days`.
    """
    logger.info(f"Starting trash cleanup. Rentention configured for {retention_days} days.")
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    
    storage = StorageLayer()
    deleted_count = 0
    
    try:
        async with SessionLocal() as db:
            stmt = select(Document).where(
                Document.deleted_at.isnot(None),
                Document.deleted_at < cutoff_date
            )
            expired_docs = (await db.execute(stmt)).scalars().all()
            
            for doc in expired_docs:
                try:
                    logger.info(f"Removing document {doc.id} (Trashed since: {doc.deleted_at})")
                    if hasattr(doc, 'versions') and doc.versions:
                        for ver in doc.versions:
                            try:
                                await storage.delete_file(ver.file_path)
                            except Exception as e:
                                logger.error(f"Failed to delete artifact {ver.file_path} for doc {doc.id}: {e}")
                    
                    await db.delete(doc)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error while cleaning up document {doc.id}: {e}")
                    continue
                    
            await db.commit()
            
    except Exception as e:
        logger.error(f"Error during trash cleanup: {e}")
        
    logger.info(f"Trash cleanup finished. Purged {deleted_count} documents.")

async def start_trash_scheduler(interval_hours: int = 24, retention_days: int = 30):
    """
    Background worker that runs continuously and triggers cleanup_trash.
    """
    while True:
        try:
            await cleanup_trash(retention_days)
        except Exception as e:
            logger.error(f"Unhandled error in trash scheduler: {e}")
        
        # Calculate next run time
        await asyncio.sleep(interval_hours * 3600)
