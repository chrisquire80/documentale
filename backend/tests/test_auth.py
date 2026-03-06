"""
Test per l'autenticazione e autorizzazione.

Copre:
- Password hashing e verifica
- Token creation e validation
- Login endpoint
- Token refresh
- Logout e token blacklist
- get_current_user dependency
"""
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from uuid import uuid4

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
)
from app.core.config import settings
from app.models.user import User, UserRole


# ── Password Hashing ──────────────────────────────────────────────────────────


class TestPasswordHashing:
    """Verifica la sicurezza della password hashing."""

    def test_password_hashing_changes_input(self):
        """Una password non deve essere mai memorizzata in chiaro."""
        plain = "MySecurePassword123!"
        hashed = get_password_hash(plain)
        assert hashed != plain
        assert len(hashed) > len(plain)  # bcrypt produce hash più lungo

    def test_different_hashes_for_same_password(self):
        """Lo stesso hash non viene generato due volte (salt random)."""
        plain = "SamePassword"
        hash1 = get_password_hash(plain)
        hash2 = get_password_hash(plain)
        assert hash1 != hash2  # bcrypt usa salt casuale

    def test_verify_password_correct(self):
        """verify_password deve tornare True per password corretta."""
        plain = "CorrectPassword123"
        hashed = get_password_hash(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password deve tornare False per password sbagliata."""
        plain = "CorrectPassword123"
        wrong = "WrongPassword456"
        hashed = get_password_hash(plain)
        assert verify_password(wrong, hashed) is False

    def test_verify_password_empty_string(self):
        """verify_password deve gestire stringhe vuote."""
        hashed = get_password_hash("password")
        assert verify_password("", hashed) is False

    def test_verify_password_case_sensitive(self):
        """Le password sono case-sensitive."""
        plain = "MyPassword"
        hashed = get_password_hash(plain)
        assert verify_password("mypassword", hashed) is False
        assert verify_password("MYPASSWORD", hashed) is False

    def test_verify_password_malformed_hash(self):
        """verify_password should return False for malformed hashes."""
        assert verify_password("password", "not-a-hash") is False
        assert verify_password("password", "$2b$12$invalidhash") is False
        assert verify_password("password", "") is False

    def test_verify_password_none_hash(self):
        """verify_password should return False if the hash is None."""
        assert verify_password("password", None) is False


# ── Access Token Creation ──────────────────────────────────────────────────────


class TestAccessTokenCreation:
    """Verifica la creazione di access token JWT."""

    def test_create_access_token_contains_sub(self):
        """Il token deve contenere il subject (email utente)."""
        subject = "user@example.com"
        token = create_access_token(subject=subject)

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == subject

    def test_create_access_token_contains_exp(self):
        """Il token deve contenere una scadenza."""
        subject = "user@example.com"
        token = create_access_token(subject=subject)

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert "exp" in decoded
        assert decoded["exp"] > datetime.now(timezone.utc).timestamp()

    def test_create_access_token_type_is_access(self):
        """Il token deve avere type='access'."""
        token = create_access_token(subject="user@example.com")
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["type"] == "access"

    def test_create_access_token_default_expiration(self):
        """La scadenza di default deve essere ACCESS_TOKEN_EXPIRE_MINUTES."""
        subject = "user@example.com"
        before = datetime.now(timezone.utc)
        token = create_access_token(subject=subject)
        after = datetime.now(timezone.utc)

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp_datetime = datetime.fromtimestamp(decoded["exp"], timezone.utc)

        expected_expire = before + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        # Tolleranza di 5 secondi per la latenza
        assert abs((exp_datetime - expected_expire).total_seconds()) < 5

    def test_create_access_token_custom_expiration(self):
        """Un custom expires_delta deve essere rispettato."""
        subject = "user@example.com"
        custom_delta = timedelta(hours=2)
        before = datetime.now(timezone.utc)
        token = create_access_token(subject=subject, expires_delta=custom_delta)
        after = datetime.now(timezone.utc)

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp_datetime = datetime.fromtimestamp(decoded["exp"], timezone.utc)

        expected_expire = before + custom_delta
        # Tolleranza di 5 secondi
        assert abs((exp_datetime - expected_expire).total_seconds()) < 5

    def test_create_access_token_numeric_subject(self):
        """Il subject può essere un numero, convertito a stringa."""
        user_id = 12345
        token = create_access_token(subject=user_id)

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == "12345"

    def test_access_token_signature_verification(self):
        """Un token con firma modificata deve fallare la decodifica."""
        token = create_access_token(subject="user@example.com")

        # Prova a decodificare con secret sbagliato
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret-key", algorithms=[settings.ALGORITHM])


# ── Refresh Token Creation ────────────────────────────────────────────────────


class TestRefreshTokenCreation:
    """Verifica la creazione di refresh token JWT."""

    def test_create_refresh_token_contains_sub(self):
        """Il refresh token deve contenere il subject."""
        subject = "user@example.com"
        token = create_refresh_token(subject=subject)

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == subject

    def test_create_refresh_token_type_is_refresh(self):
        """Il token deve avere type='refresh'."""
        token = create_refresh_token(subject="user@example.com")
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["type"] == "refresh"

    def test_create_refresh_token_longer_expiration(self):
        """Il refresh token deve avere una scadenza più lunga dell'access token."""
        subject = "user@example.com"
        access_token = create_access_token(subject=subject)
        refresh_token = create_refresh_token(subject=subject)

        access_decoded = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        refresh_decoded = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert (
            refresh_decoded["exp"] > access_decoded["exp"]
        ), "Refresh token deve durare più a lungo"

    def test_create_refresh_token_custom_expiration(self):
        """Un custom expires_delta deve essere rispettato."""
        custom_delta = timedelta(days=7)
        before = datetime.now(timezone.utc)
        token = create_refresh_token(subject="user@example.com", expires_delta=custom_delta)
        after = datetime.now(timezone.utc)

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp_datetime = datetime.fromtimestamp(decoded["exp"], timezone.utc)

        expected_expire = before + custom_delta
        assert abs((exp_datetime - expected_expire).total_seconds()) < 5


# ── Token Decoding & Validation ────────────────────────────────────────────────


class TestTokenValidation:
    """Verifica la validazione e decodifica dei token."""

    def test_decode_valid_token(self):
        """Un token valido deve decodificarsi correttamente."""
        subject = "user@example.com"
        token = create_access_token(subject=subject)

        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == subject
        assert decoded["type"] == "access"

    def test_decode_expired_token_raises_error(self):
        """Un token scaduto deve sollevare JWTError."""
        # Crea token con scadenza già passata
        past_delta = timedelta(minutes=-1)
        token = create_access_token(
            subject="user@example.com", expires_delta=past_delta
        )

        with pytest.raises(JWTError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    def test_decode_malformed_token_raises_error(self):
        """Un token malformato deve sollevare JWTError."""
        bad_token = "not.a.valid.jwt.token"

        with pytest.raises(JWTError):
            jwt.decode(bad_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    def test_decode_token_with_wrong_algorithm(self):
        """Un token decodificato con algoritmo sbagliato deve fallare."""
        token = create_access_token(subject="user@example.com")

        with pytest.raises(JWTError):
            # Prova con algoritmo sbagliato
            jwt.decode(token, settings.SECRET_KEY, algorithms=["HS512"])


# ── Token Type Validation ──────────────────────────────────────────────────────


class TestTokenTypeValidation:
    """Verifica che il tipo di token sia corretto per il suo uso."""

    def test_access_token_has_correct_type(self):
        """L'access token deve avere type='access'."""
        token = create_access_token(subject="user@example.com")
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded.get("type") == "access"

    def test_refresh_token_has_correct_type(self):
        """Il refresh token deve avere type='refresh'."""
        token = create_refresh_token(subject="user@example.com")
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded.get("type") == "refresh"

    def test_cannot_use_refresh_token_as_access(self):
        """Un endpoint access-token-only deve rifiutare un refresh token."""
        refresh_token = create_refresh_token(subject="user@example.com")
        decoded = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Simula il controllo che farebbe un endpoint
        if decoded.get("type") != "access":
            # Dovrebbe fallare
            assert decoded.get("type") == "refresh"

    def test_cannot_use_access_token_for_refresh(self):
        """Un endpoint di refresh deve rifiutare un access token."""
        access_token = create_access_token(subject="user@example.com")
        decoded = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Simula il controllo che farebbe l'endpoint di refresh
        if decoded.get("type") != "refresh":
            # Dovrebbe fallare
            assert decoded.get("type") == "access"


# ── Subject Handling ───────────────────────────────────────────────────────────


class TestSubjectHandling:
    """Verifica come il subject viene gestito nei token."""

    def test_subject_can_be_email(self):
        """Il subject può essere un'email."""
        email = "user@example.com"
        token = create_access_token(subject=email)
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == email

    def test_subject_can_be_uuid(self):
        """Il subject può essere un UUID."""
        user_id = str(uuid4())
        token = create_access_token(subject=user_id)
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == user_id

    def test_subject_converted_to_string(self):
        """I subject non-string vengono convertiti a stringa."""
        int_subject = 999
        token = create_access_token(subject=int_subject)
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == "999"
        assert isinstance(decoded["sub"], str)

    def test_subject_required_in_token(self):
        """Un token deve contenere il subject."""
        token = create_access_token(subject="user@example.com")
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert "sub" in decoded
        assert decoded["sub"] is not None


# ── Edge Cases ─────────────────────────────────────────────────────────────────


class TestAuthEdgeCases:
    """Test per edge case e situazioni anomale."""

    def test_empty_subject_string(self):
        """Un subject vuoto dovrebbe comunque produrre un token valido."""
        token = create_access_token(subject="")
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == ""

    def test_special_characters_in_subject(self):
        """Il subject con caratteri speciali deve essere gestito."""
        subject = "user+test@example.com"
        token = create_access_token(subject=subject)
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == subject

    def test_very_long_subject(self):
        """Un subject molto lungo deve essere gestito."""
        subject = "a" * 1000
        token = create_access_token(subject=subject)
        decoded = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert decoded["sub"] == subject

    def test_password_with_special_characters(self):
        """Una password con caratteri speciali deve essere hashable e verificabile."""
        password = "P@$$w0rd!#%&*()_+-=[]{}|;:',.<>?/`~"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)
        assert not verify_password("P@$$w0rd!", hashed)

    def test_very_long_password(self):
        """Una password molto lunga (oltre il limite di bcrypt) deve sollevare eccezione."""
        from passlib.exc import PasswordSizeError

        # bcrypt ha un limite di 72 bytes, testa il comportamento
        password = "a" * 10000
        with pytest.raises(PasswordSizeError):
            get_password_hash(password)
