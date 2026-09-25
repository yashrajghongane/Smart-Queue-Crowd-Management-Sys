"""
app/api/device.py

ESP32 device event ingestion route. Document A §2.11.
Accepts authenticated ENTRY/EXIT events from the ESP32 sensor device.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_device_credential
from app.models.models import Device
from app.repositories.database import get_db
from app.schemas.schemas import DeviceEventRequest, DeviceEventResponse
from app.services.occupancy_service import (
    OccupancyService,
    ZoneNotFoundError,
    DeviceNotFoundError,
    DeviceInactiveError,
    InvalidDeviceEventError,
)

router = APIRouter()


@router.post(
    "/events",
    response_model=DeviceEventResponse,
    summary="Device Event Ingestion",
    description=(
        "Accepts authenticated ENTRY/EXIT events from the ESP32 sensor device. "
        "Enforces idempotency via (device_id, sequence) uniqueness. Document A §2.11."
    ),
)
def ingest_device_event(
    body: DeviceEventRequest,
    x_device_key: Optional[str] = Header(None, alias="X-Device-Key"),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    db: Session = Depends(get_db),
):
    # Determine device identifier (from header or request body)
    dev_identifier = x_device_id or body.device_id

    # 1. Device Authentication
    device = (
        db.query(Device)
        .filter((Device.id == dev_identifier) | (Device.device_code == dev_identifier))
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{dev_identifier}' not found.",
        )

    if not device.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Device '{device.device_code}' is deactivated.",
        )

    # If device has a credential provisioned, require and verify X-Device-Key
    if device.credential_hash:
        if not x_device_key or not verify_device_credential(x_device_key, device.credential_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing device credentials (X-Device-Key header required).",
            )
    else:
        # In production, uncredentialed devices are rejected
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Device is not provisioned with security credentials.",
            )

    # 2. Process device event through OccupancyService
    service = OccupancyService(db)
    try:
        result = service.process_device_event(
            device_id=device.id,
            zone_id=body.zone_id,
            sequence=body.sequence,
            event_type=body.event_type,
            event_at=body.event_at,
            firmware_version=body.firmware_version,
        )
        return DeviceEventResponse(**result)

    except (DeviceNotFoundError, ZoneNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DeviceInactiveError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except InvalidDeviceEventError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
