"""
Fixtures condivise per la test suite di Documentale.

Per i test di integrazione (che richiedono PostgreSQL attivo) usare il marker:
    @pytest.mark.integration

Per i test unitari le dipendenze DB/Redis vengono sostituite con mock/fake.
"""
import pytest
import pytest_asyncio
import fakeredis


@pytest_asyncio.fixture
async def fake_redis():
    """Redis in-memory (fakeredis) utilizzabile senza un server Redis reale."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring a live PostgreSQL + Redis (excluded in unit test runs)",
    )
