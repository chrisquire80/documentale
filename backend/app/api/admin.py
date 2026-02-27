from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String

from ..api.auth import get_current_user
from ..db import get_db
from ..models.user import User, UserRole
from ..models.document import Document
from ..core.cache import get_redis

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(current_user: User):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Riservato agli amministratori.")


@router.get("/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """Statistiche Redis/cache — solo per amministratori."""
    _require_admin(current_user)

    if not redis:
        return {
            "redis_available": False,
            "message": "Redis non disponibile. La cache è disabilitata.",
        }

    try:
        info_stats = await redis.info("stats")
        info_memory = await redis.info("memory")

        hits: int = info_stats.get("keyspace_hits", 0)
        misses: int = info_stats.get("keyspace_misses", 0)
        total_ops = hits + misses
        hit_rate = round((hits / total_ops * 100), 1) if total_ops > 0 else 0.0

        cached_doc_keys = 0
        async for _ in redis.scan_iter("docs:*"):
            cached_doc_keys += 1

        return {
            "redis_available": True,
            "keyspace_hits": hits,
            "keyspace_misses": misses,
            "hit_rate_percent": hit_rate,
            "total_operations": total_ops,
            "cached_doc_queries": cached_doc_keys,
            "used_memory_human": info_memory.get("used_memory_human", "N/A"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Errore Redis: {exc}")


@router.get("/document-stats")
async def get_document_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Statistiche documenti — solo per amministratori."""
    _require_admin(current_user)

    # Totale e attivi/cancellati
    total_stmt = select(func.count(Document.id))
    total: int = (await db.execute(total_stmt)).scalar() or 0

    deleted_stmt = select(func.count(Document.id)).where(Document.is_deleted == True)
    deleted: int = (await db.execute(deleted_stmt)).scalar() or 0

    # Documenti per tipo MIME
    by_type_stmt = (
        select(Document.file_type, func.count(Document.id).label("count"))
        .where(Document.is_deleted == False)
        .group_by(Document.file_type)
        .order_by(func.count(Document.id).desc())
    )
    by_type_rows = (await db.execute(by_type_stmt)).all()
    by_type = [{"file_type": r.file_type or "unknown", "count": r.count} for r in by_type_rows]

    # Caricamenti per giorno (ultimi 30 giorni)
    by_day_stmt = (
        select(
            func.date_trunc("day", Document.created_at).label("day"),
            func.count(Document.id).label("count"),
        )
        .where(
            Document.is_deleted == False,
            Document.created_at >= func.now() - func.cast("30 days", type_=None),
        )
        .group_by(func.date_trunc("day", Document.created_at))
        .order_by(func.date_trunc("day", Document.created_at))
    )
    by_day_rows = (await db.execute(by_day_stmt)).all()
    by_day = [{"day": str(r.day)[:10], "count": r.count} for r in by_day_rows]

    # Top 5 uploader (per numero di documenti)
    top_uploaders_stmt = (
        select(Document.owner_id, func.count(Document.id).label("count"))
        .where(Document.is_deleted == False)
        .group_by(Document.owner_id)
        .order_by(func.count(Document.id).desc())
        .limit(5)
    )
    top_uploaders_rows = (await db.execute(top_uploaders_stmt)).all()
    top_uploaders = [{"owner_id": str(r.owner_id), "count": r.count} for r in top_uploaders_rows]

    return {
        "total_documents": total,
        "active_documents": total - deleted,
        "deleted_documents": deleted,
        "by_file_type": by_type,
        "uploads_by_day": by_day,
        "top_uploaders": top_uploaders,
    }
