from typing import Optional
import redis.asyncio as aioredis
from .config import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Dependency: returns the active Redis client, or None if unavailable."""
    return _redis_client


async def startup_redis() -> None:
    global _redis_client
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await client.ping()
        _redis_client = client
        print("Redis: connesso con successo.")
    except Exception as e:
        _redis_client = None
        print(f"Redis: connessione fallita ({e}). Cache disabilitata.")


async def shutdown_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        print("Redis: connessione chiusa.")
