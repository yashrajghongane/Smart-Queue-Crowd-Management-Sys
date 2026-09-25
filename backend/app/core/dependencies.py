"""
app/core/dependencies.py

FastAPI dependencies for authentication, authorization, and device validation.
"""
from typing import Optional, Callable
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token, verify_device_credential
from app.models.models import StaffUser, Device
from app.repositories.database import get_db


def get_current_staff(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> StaffUser:
    """
    Validates JWT Bearer token and returns the authenticated StaffUser.
    In production: strictly requires valid Authorization header.
    In development: if Authorization is omitted, allows default seeded staff context.
    """
    if authorization:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected 'Bearer <token>'.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1]
        payload = decode_access_token(token)
        if not payload or "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = payload["sub"]
        user = db.query(StaffUser).filter(StaffUser.id == user_id).first()
        if not user or not user.active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Staff user account is inactive or does not exist.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    # No authorization header provided:
    if settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In local development only, fallback to first active staff user
    default_staff = db.query(StaffUser).filter(StaffUser.active.is_(True)).first()
    if default_staff:
        return default_staff

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(*allowed_roles: str) -> Callable:
    """
    Role-based access control (RBAC) dependency factory.
    Roles: 'RECEPTION', 'DEPARTMENT_STAFF', 'ADMIN'.
    """
    def _role_checker(current_user: StaffUser = Depends(get_current_staff)) -> StaffUser:
        if current_user.role not in allowed_roles and current_user.role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{current_user.role}'. Required: {allowed_roles}",
            )
        return current_user
    return _role_checker


def authenticate_device(
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    x_device_key: Optional[str] = Header(None, alias="X-Device-Key"),
    db: Session = Depends(get_db),
) -> Device:
    """
    Validates ESP32 device credentials.
    Headers required:
      - X-Device-ID: device_code (e.g. 'DEV-001') or device UUID
      - X-Device-Key: device secret pre-shared key
    """
    if not x_device_id or not x_device_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device authentication headers 'X-Device-ID' and 'X-Device-Key' are required.",
        )

    # Lookup device by code or id
    device = (
        db.query(Device)
        .filter((Device.device_code == x_device_id) | (Device.id == x_device_id))
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unrecognized device identifier.",
        )

    if not device.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device has been deactivated.",
        )

    # Verify credential
    if not device.credential_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device has no credential provisioned.",
        )

    if not verify_device_credential(x_device_key, device.credential_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials.",
        )

    return device
