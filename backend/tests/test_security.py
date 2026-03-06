from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.security import create_access_token
from app.core.config import settings

def test_create_access_token_default_expire():
    subject = "test-subject"
    token = create_access_token(subject=subject)

    decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert decoded_token["sub"] == subject
    assert "exp" in decoded_token

    # Check that expiration is within a reasonable range (around 7 days from now as per default)
    expected_expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    actual_expire = datetime.fromtimestamp(decoded_token["exp"], timezone.utc)

    # Check that they are within 10 seconds of each other
    assert abs((expected_expire - actual_expire).total_seconds()) < 10

def test_create_access_token_custom_expire():
    subject = "test-subject-custom"
    expires_delta = timedelta(minutes=30)
    token = create_access_token(subject=subject, expires_delta=expires_delta)

    decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    assert decoded_token["sub"] == subject
    assert "exp" in decoded_token

    expected_expire = datetime.now(timezone.utc) + expires_delta
    actual_expire = datetime.fromtimestamp(decoded_token["exp"], timezone.utc)

    assert abs((expected_expire - actual_expire).total_seconds()) < 10

def test_create_access_token_subject_types():
    # Test with string
    token1 = create_access_token(subject="user123")
    decoded1 = jwt.decode(token1, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded1["sub"] == "user123"

    # Test with integer
    token2 = create_access_token(subject=12345)
    decoded2 = jwt.decode(token2, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded2["sub"] == "12345"
