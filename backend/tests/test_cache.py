"""
Test unitari per la logica di cache Redis.

Non richiedono un server Redis reale: usano il fixture `fake_redis`
(fakeredis in-memory) definito in conftest.py.
"""
import json
import hashlib
import time

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_cache_key(user_id: str, query: str, tag: str, limit: int, offset: int) -> str:
    """Replica esatta della logica di cache key usata in documents.py."""
    raw = f"{query}:{tag}:{limit}:{offset}"
    return f"docs:{user_id}:{hashlib.md5(raw.encode()).hexdigest()}"


SAMPLE_RESPONSE = {
    "items": [{"id": "doc-1", "title": "Contratto", "is_restricted": False}],
    "total": 1,
    "limit": 20,
    "offset": 0,
}


# ── Cache hit ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_stores_and_retrieves(fake_redis):
    """Il valore inserito nella cache deve essere recuperato identico."""
    key = _make_cache_key("user-1", "contratto", "", 20, 0)
    await fake_redis.setex(key, 300, json.dumps(SAMPLE_RESPONSE))

    cached_raw = await fake_redis.get(key)
    assert cached_raw is not None, "La chiave deve essere presente in cache"
    assert json.loads(cached_raw) == SAMPLE_RESPONSE


@pytest.mark.asyncio
async def test_cache_miss_returns_none(fake_redis):
    """Una chiave mai inserita deve restituire None (cache miss)."""
    key = _make_cache_key("user-2", "query-inesistente", "", 20, 0)
    result = await fake_redis.get(key)
    assert result is None


# ── TTL ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_ttl_set_correctly(fake_redis):
    """La cache deve avere TTL di 300 secondi."""
    key = _make_cache_key("user-3", "test-ttl", "", 20, 0)
    await fake_redis.setex(key, 300, json.dumps(SAMPLE_RESPONSE))

    ttl = await fake_redis.ttl(key)
    # fakeredis gestisce il TTL: deve essere tra 1 e 300
    assert 1 <= ttl <= 300, f"TTL inatteso: {ttl}"


# ── Invalidazione upload ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_invalidation_deletes_only_user_keys(fake_redis):
    """
    All'upload, devono essere cancellate solo le chiavi dell'utente che ha
    caricato il file; le chiavi degli altri utenti devono sopravvivere.
    """
    user_a = "user-aaa"
    user_b = "user-bbb"

    key_a1 = _make_cache_key(user_a, "report", "", 20, 0)
    key_a2 = _make_cache_key(user_a, "fattura", "admin", 10, 0)
    key_b1 = _make_cache_key(user_b, "contratto", "", 20, 0)

    await fake_redis.setex(key_a1, 300, json.dumps(SAMPLE_RESPONSE))
    await fake_redis.setex(key_a2, 300, json.dumps(SAMPLE_RESPONSE))
    await fake_redis.setex(key_b1, 300, json.dumps(SAMPLE_RESPONSE))

    # Simula la logica di invalidazione eseguita dopo un upload dell'utente A
    pattern = f"docs:{user_a}:*"
    async for k in fake_redis.scan_iter(pattern):
        await fake_redis.delete(k)

    assert await fake_redis.get(key_a1) is None, "Chiave A1 deve essere stata eliminata"
    assert await fake_redis.get(key_a2) is None, "Chiave A2 deve essere stata eliminata"
    assert await fake_redis.get(key_b1) is not None, "Chiave B1 di altro utente deve sopravvivere"


@pytest.mark.asyncio
async def test_cache_invalidation_with_no_keys(fake_redis):
    """L'invalidazione non deve fallire se l'utente non ha chiavi in cache."""
    pattern = "docs:utente-senza-cache:*"
    count = 0
    async for k in fake_redis.scan_iter(pattern):
        await fake_redis.delete(k)
        count += 1
    assert count == 0


# ── Chiavi diverse per parametri diversi ──────────────────────────────────────

@pytest.mark.asyncio
async def test_different_params_produce_different_keys(fake_redis):
    """
    Query diverse devono produrre chiavi di cache diverse, evitando
    collisioni tra ricerche diverse dello stesso utente.
    """
    user = "user-xyz"

    key_p1 = _make_cache_key(user, "alpha", "", 20, 0)
    key_p2 = _make_cache_key(user, "beta", "", 20, 0)
    key_p3 = _make_cache_key(user, "alpha", "", 20, 20)   # stessa query, pagina diversa

    assert key_p1 != key_p2, "Query diverse → chiavi diverse"
    assert key_p1 != key_p3, "Offset diversi → chiavi diverse"
    assert key_p2 != key_p3


@pytest.mark.asyncio
async def test_same_params_produce_same_key(fake_redis):
    """Gli stessi parametri devono produrre sempre la stessa chiave (determinismo)."""
    k1 = _make_cache_key("user-det", "query", "tag", 20, 40)
    k2 = _make_cache_key("user-det", "query", "tag", 20, 40)
    assert k1 == k2
