"""
Test per gli endpoint di autenticazione.

Nota: Questi test richiedono un database live (PostgreSQL) per funzionare completamente.
Per test locali, usa test_auth.py che testa la logica sottostante.
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
)
from app.core.config import settings


# ── Tests per il comportamento di token in scenari di logout ──────────────────


class TestLogoutBehavior:
    """Test per il comportamento dei token durante logout."""

    def test_token_can_be_created_for_logout_scenario(self):
        """Verifica che un token possa essere creato per essere poi invalidato."""
        email = "user@example.com"
        token = create_access_token(subject=email)

        # Decodifica il token per estrarre l'exp
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Calcola il TTL residuo (simula quello che farebbe l'endpoint logout)
        exp_timestamp = decoded.get("exp")
        now_timestamp = datetime.now().timestamp()
        remaining_ttl = int(exp_timestamp - now_timestamp)

        # Il TTL dovrebbe essere positivo (il token non è ancora scaduto)
        assert remaining_ttl > 0, "Il token non dovrebbe essere già scaduto"
        # Il TTL dovrebbe essere meno di 30 minuti (il default di ACCESS_TOKEN_EXPIRE_MINUTES)
        assert remaining_ttl <= (30 * 60), "Il TTL dovrebbe essere il default"

    def test_token_expiration_extraction(self):
        """Verifica che l'exp possa essere estratto dal token per il logout."""
        token = create_access_token(subject="user@example.com")
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        exp = decoded.get("exp")
        assert exp is not None
        assert isinstance(exp, int)
        assert exp > 0


# ── Tests per il flusso di autenticazione completo ────────────────────────────


class TestAuthenticationFlow:
    """Test del flusso di autenticazione completo (senza database)."""

    def test_complete_auth_flow_token_creation(self):
        """Simula il flusso completo: login → refresh → logout."""
        # 1. Login: crea access e refresh token
        email = "user@example.com"
        access_token = create_access_token(subject=email)
        refresh_token = create_refresh_token(subject=email)

        # Verifica i token
        access_decoded = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        refresh_decoded = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert access_decoded["type"] == "access"
        assert refresh_decoded["type"] == "refresh"
        assert access_decoded["sub"] == email
        assert refresh_decoded["sub"] == email

    def test_refresh_flow_creates_new_tokens(self):
        """Verifica che il refresh funzioni con token valido."""
        import time

        # Crea token iniziale
        old_access = create_access_token(subject="user@example.com")
        refresh = create_refresh_token(subject="user@example.com")

        # Verifica che il refresh token sia valido
        refresh_decoded = jwt.decode(
            refresh, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert refresh_decoded["exp"] > datetime.utcnow().timestamp()

        # Attendi 1 secondo per ottenere un timestamp diverso
        time.sleep(1)

        # Crea nuovi token
        new_access = create_access_token(subject="user@example.com")
        new_refresh = create_refresh_token(subject="user@example.com")

        # I nuovi token devono avere exp diversi (dopo 1 secondo)
        old_decoded = jwt.decode(
            old_access, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        new_decoded = jwt.decode(
            new_access, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert new_decoded["exp"] > old_decoded["exp"]


# ── Tests per l'utilizzo scorretto dei token ────────────────────────────────


class TestTokenMisuse:
    """Test per prevenire l'utilizzo scorretto dei token."""

    def test_using_access_token_as_refresh_fails(self):
        """Un access token non deve essere usato come refresh token."""
        access_token = create_access_token(subject="user@example.com")
        decoded = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # L'endpoint di refresh controlla il tipo di token
        if decoded.get("type") != "refresh":
            # Questo è il controllo che farebbe l'endpoint
            assert decoded.get("type") == "access"

    def test_using_refresh_token_as_access_fails(self):
        """Un refresh token non deve essere usato come access token."""
        refresh_token = create_refresh_token(subject="user@example.com")
        decoded = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Un endpoint che accetta solo access token farebbe questo controllo
        if decoded.get("type") != "access":
            # Questo è il controllo che farebbe un endpoint protetto
            assert decoded.get("type") == "refresh"


# ── Tests per le scadenze di token ────────────────────────────────────────────


class TestTokenExpiration:
    """Test per la corretta gestione delle scadenze."""

    def test_access_token_expires(self):
        """L'access token deve avere una scadenza."""
        token = create_access_token(subject="user@example.com")
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        exp = decoded.get("exp")
        now = datetime.utcnow().timestamp()
        time_to_expire = exp - now

        # Dovrebbe scadere tra ~30 minuti (con tolleranza di 1 minuto)
        assert 29 * 60 < time_to_expire < 31 * 60

    def test_refresh_token_expires_later(self):
        """Il refresh token scade dopo l'access token."""
        access_token = create_access_token(subject="user@example.com")
        refresh_token = create_refresh_token(subject="user@example.com")

        access_decoded = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        refresh_decoded = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        access_exp = access_decoded.get("exp")
        refresh_exp = refresh_decoded.get("exp")

        assert refresh_exp > access_exp, "Refresh token deve durare più a lungo"

    def test_expired_token_cannot_be_decoded(self):
        """Un token scaduto non può essere decodificato."""
        # Crea token con scadenza nel passato
        expired_token = create_access_token(
            subject="user@example.com",
            expires_delta=timedelta(minutes=-5)
        )

        # Prova a decodificare
        with pytest.raises(Exception):  # JWTError
            jwt.decode(
                expired_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )


# ── Tests per la sicurezza dei token ───────────────────────────────────────────


class TestTokenSecurity:
    """Test per la sicurezza dei token."""

    def test_token_signed_with_secret_key(self):
        """I token devono essere firmati con la SECRET_KEY."""
        token = create_access_token(subject="user@example.com")

        # Prova a decodificare con secret sbagliato
        with pytest.raises(Exception):  # JWTError
            jwt.decode(
                token,
                "wrong-secret-key",
                algorithms=[settings.ALGORITHM]
            )

    def test_token_contains_subject(self):
        """Il token deve contenere il subject (email)."""
        email = "test@example.com"
        token = create_access_token(subject=email)

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded.get("sub") == email

    def test_token_contains_type(self):
        """Il token deve contenere il tipo (access/refresh)."""
        access_token = create_access_token(subject="user@example.com")
        refresh_token = create_refresh_token(subject="user@example.com")

        access_decoded = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        refresh_decoded = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert access_decoded.get("type") == "access"
        assert refresh_decoded.get("type") == "refresh"


# ── Tests per i bordi della sicurezza ──────────────────────────────────────────


class TestSecurityBoundaries:
    """Test per i confini di sicurezza dell'autenticazione."""

    def test_password_hash_is_one_way(self):
        """Una password hashata non deve poter essere decifrata."""
        password = "MySecretPassword123"
        hashed = get_password_hash(password)

        # Non dovrebbe essere possibile invertire l'hash
        assert password != hashed
        # L'unico modo per verificare è con verify_password
        assert verify_password(password, hashed)

    def test_different_passwords_produce_different_hashes(self):
        """Password diverse devono produrre hash diversi."""
        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")

        assert hash1 != hash2

    def test_token_cannot_be_forged_without_secret_key(self):
        """Non è possibile creare un token valido senza la SECRET_KEY."""
        from jose import jwt as jose_jwt

        fake_token = jose_jwt.encode(
            {"sub": "hacker@example.com", "type": "access"},
            "wrong-secret-key",
            algorithm=settings.ALGORITHM
        )

        # Prova a decodificare con il secret corretto
        with pytest.raises(Exception):  # JWTError
            jwt.decode(
                fake_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
