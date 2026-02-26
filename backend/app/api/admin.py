from fastapi import APIRouter, Depends, HTTPException

from ..api.auth import get_current_user
from ..models.user import User, UserRole
from ..core.cache import get_redis

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """Statistiche Redis/cache — solo per amministratori."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Riservato agli amministratori.",
        )

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
