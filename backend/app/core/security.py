"""
app/core/security.py

Security foundation for SmartQueue:
- Password hashing & verification using bcrypt.
- JWT token generation and validation.
- Device credential hashing & validation.
- Role-based access helpers.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    if not hashed_password or not plain_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def hash_device_credential(credential: str) -> str:
    """Hash an ESP32 device pre-shared key/token."""
    return hash_password(credential)


def verify_device_credential(plain_credential: str, hashed_credential: str) -> bool:
    """Verify an ESP32 device pre-shared key."""
    return verify_password(plain_credential, hashed_credential)


def create_access_token(
    subject: str,
    role: str,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT access token for staff users.
    Contains: sub (staff user id), role, iat, exp.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        to_encode.update(extra_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    Returns the payload dict if valid, or None if expired/tampered.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None
