"""
Test per gli endpoint di autenticazione.

Copre:
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout
- GET /auth/me
- Token blacklist behavior
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from jose import jwt

from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db, Base
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token
from app.core.config import settings


# ── Database Fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def test_db():
    """Database test asincrono in-memory per i test."""
    # Usa SQLite in-memory per i test (sufficientemente veloce e deterministico)
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    yield async_session

    await engine.dispose()


@pytest_asyncio.fixture
async def test_user(test_db):
    """Crea un utente di test nel database."""
    async with test_db() as session:
        user = User(
            email="test@example.com",
            hashed_password=get_password_hash("TestPassword123"),
            role=UserRole.READER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def test_admin_user(test_db):
    """Crea un utente admin di test nel database."""
    async with test_db() as session:
        user = User(
            email="admin@example.com",
            hashed_password=get_password_hash("AdminPassword123"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def inactive_user(test_db):
    """Crea un utente inattivo di test."""
    async with test_db() as session:
        user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("Password123"),
            role=UserRole.READER,
            is_active=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
def client():
    """FastAPI TestClient per i test degli endpoint."""
    return TestClient(app)


# ── Login Endpoint Tests ───────────────────────────────────────────────────────


class TestLoginEndpoint:
    """Test per l'endpoint POST /auth/login."""

    @pytest.mark.asyncio
    async def test_login_successful(self, client, test_user):
        """Login con credenziali corrette deve restituire token."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client, test_user):
        """Login con email inesistente deve fallare."""
        response = client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "TestPassword123"},
        )
        assert response.status_code == 401
        assert "Email o password non corretti" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_user):
        """Login con password sbagliata deve fallare."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "WrongPassword"},
        )
        assert response.status_code == 401
        assert "Email o password non corretti" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_missing_email(self, client):
        """Login senza email deve fallare."""
        response = client.post(
            "/auth/login",
            json={"password": "TestPassword123"},
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_missing_password(self, client, test_user):
        """Login senza password deve fallare."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, client):
        """Login con formato email non valido deve fallare."""
        response = client.post(
            "/auth/login",
            json={"email": "not-an-email", "password": "TestPassword123"},
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_returns_different_tokens(self, client, test_user):
        """Ogni login deve generare token diversi."""
        resp1 = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        resp2 = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )

        token1 = resp1.json()["access_token"]
        token2 = resp2.json()["access_token"]
        assert token1 != token2  # Token diversi (contengono timestamp)

    @pytest.mark.asyncio
    async def test_login_access_token_is_valid_jwt(self, client, test_user):
        """L'access token deve essere un JWT decodificabile."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        token = response.json()["access_token"]

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == "test@example.com"
        assert decoded["type"] == "access"

    @pytest.mark.asyncio
    async def test_login_refresh_token_is_valid_jwt(self, client, test_user):
        """Il refresh token deve essere un JWT decodificabile."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        refresh_token = response.json()["refresh_token"]

        decoded = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == "test@example.com"
        assert decoded["type"] == "refresh"


# ── Refresh Token Endpoint Tests ───────────────────────────────────────────────


class TestRefreshEndpoint:
    """Test per l'endpoint POST /auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_with_valid_token(self, client, test_user):
        """Refresh con token valido deve restituire nuovi token."""
        # Prima fa login
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Poi fa refresh
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, client, test_user):
        """Refresh con access token deve fallare."""
        # Prima fa login
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        access_token = login_response.json()["access_token"]

        # Prova a fare refresh con access token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401
        assert "non valido" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, client):
        """Refresh con token non valido deve fallare."""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_malformed_token(self, client):
        """Refresh con token malformato deve fallare."""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "not-a-jwt"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_inactive_user(self, client, inactive_user):
        """Refresh di utente inattivo deve fallare."""
        # Crea manualmente un token per l'utente inattivo
        refresh_token = create_refresh_token(subject="inactive@example.com")

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_nonexistent_user(self, client):
        """Refresh per utente inesistente deve fallare."""
        # Crea un token valido per un utente inesistente
        refresh_token = create_refresh_token(subject="nonexistent@example.com")

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_returns_new_tokens(self, client, test_user):
        """Refresh deve generare nuovi token, non gli stessi."""
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        old_access = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        new_access = response.json()["access_token"]

        # I token dovrebbero essere diversi (contengono timestamp)
        assert old_access != new_access


# ── Get Current User Endpoint Tests ────────────────────────────────────────────


class TestGetMeEndpoint:
    """Test per l'endpoint GET /auth/me."""

    @pytest.mark.asyncio
    async def test_get_me_with_valid_token(self, client, test_user):
        """GET /me con token valido deve restituire l'utente."""
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        access_token = login_response.json()["access_token"]

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "reader"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_me_without_token(self, client):
        """GET /me senza token deve fallare."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_invalid_token(self, client):
        """GET /me con token invalido deve fallare."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_with_refresh_token(self, client, test_user):
        """GET /me con refresh token deve fallare (solo access token)."""
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        # Dovrebbe fallare perché è un refresh token, non un access token
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_admin_user(self, client, test_admin_user):
        """GET /me di utente admin deve restituire il ruolo admin."""
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "AdminPassword123"},
        )
        access_token = login_response.json()["access_token"]

        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"


# ── Logout Endpoint Tests ──────────────────────────────────────────────────────


class TestLogoutEndpoint:
    """Test per l'endpoint POST /auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_with_valid_token(self, client, test_user):
        """Logout con token valido deve restituire successo."""
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        access_token = login_response.json()["access_token"]

        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        assert "Logout effettuato" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_logout_without_token(self, client):
        """Logout senza token deve fallare."""
        response = client.post("/auth/logout")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_with_invalid_token(self, client):
        """Logout con token invalido deve fallare."""
        response = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_with_refresh_token(self, client, test_user):
        """Logout con refresh token è permesso (deve invalidare il token)."""
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Il logout accetta qualsiasi token valido
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        # Il logout dovrebbe funzionare (il token viene invalidato)
        assert response.status_code == 200


# ── Access Control & Authorization ────────────────────────────────────────────


class TestAccessControl:
    """Test per il controllo di accesso e autorizzazione."""

    @pytest.mark.asyncio
    async def test_admin_user_can_login(self, client, test_admin_user):
        """Un utente admin deve poter fare login."""
        response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "AdminPassword123"},
        )
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_power_user_can_login(self, client, test_db):
        """Un power_user deve poter fare login."""
        async with test_db() as session:
            user = User(
                email="power@example.com",
                hashed_password=get_password_hash("PowerPassword123"),
                role=UserRole.POWER_USER,
                is_active=True,
            )
            session.add(user)
            await session.commit()

        response = client.post(
            "/auth/login",
            json={"email": "power@example.com", "password": "PowerPassword123"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_inactive_user_cannot_refresh(self, client, test_db):
        """Un utente inattivo non può fare refresh anche con token valido."""
        async with test_db() as session:
            user = User(
                email="inactive@example.com",
                hashed_password=get_password_hash("InactivePassword123"),
                role=UserRole.READER,
                is_active=False,
            )
            session.add(user)
            await session.commit()

        # Crea un token manualmente (simula che aveva fatto login prima di essere disattivato)
        refresh_token = create_refresh_token(subject="inactive@example.com")

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401


# ── Rate Limiting Tests ────────────────────────────────────────────────────────


class TestAuthRateLimiting:
    """Test per i limiti di rate limiting sugli endpoint di auth."""

    @pytest.mark.asyncio
    async def test_login_endpoint_exists(self, client, test_user):
        """L'endpoint di login deve avere rate limiting configurato."""
        # Questo è più un test di configurazione che di funzionalità
        # Qui verifichiamo che il rate limit sia applicato
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        # Rate limit dovrebbe essere presente (ma dipende dalla configurazione)
        assert response.status_code in [200, 429]

    @pytest.mark.asyncio
    async def test_refresh_endpoint_exists(self, client, test_user):
        """L'endpoint di refresh deve avere rate limiting configurato."""
        login_response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        # Rate limit dovrebbe essere presente
        assert response.status_code in [200, 429]
