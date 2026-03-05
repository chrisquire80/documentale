"""
Fixtures condivise per la test suite di Documentale.

Per i test di integrazione (che richiedono PostgreSQL attivo) usare il marker:
    @pytest.mark.integration

Per i test unitari le dipendenze DB/Redis vengono sostituite con mock/fake.
"""
import pytest
import pytest_asyncio
import fakeredis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient
from app.main import app
from app.db import Base, get_db
from app.core.config import settings


@pytest_asyncio.fixture
async def fake_redis():
    """Redis in-memory (fakeredis) utilizzabile senza un server Redis reale."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(settings.DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_engine):
    SessionLocal = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    
    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    from app import db as app_db
    original_session_local = app_db.SessionLocal
    original_engine = app_db.engine
    
    app_db.SessionLocal = SessionLocal
    app_db.engine = db_engine
    app.dependency_overrides[get_db] = override_get_db
    
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
    app_db.SessionLocal = original_session_local
    app_db.engine = original_engine


@pytest_asyncio.fixture
async def db_session(db_engine):
    SessionLocal = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with SessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def admin_user(db_session):
    from app.models.user import User, UserRole
    from app.core.security import get_password_hash
    from sqlalchemy.future import select

    # Check if user already exists
    stmt = select(User).where(User.email == "admin_test@example.com")
    existing_user = (await db_session.execute(stmt)).scalar_one_or_none()
    if existing_user:
        return existing_user

    user = User(
        email="admin_test@example.com",
        hashed_password=get_password_hash("password123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(admin_user):
    from app.core.security import create_access_token
    token = create_access_token(subject=admin_user.email)
    return {"Authorization": f"Bearer {token}"}
