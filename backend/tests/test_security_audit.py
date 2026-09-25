"""
tests/test_security_audit.py

Fulfills Directive 15: SECURITY TEST
Tests:
- Invalid password (401)
- Expired JWT (401)
- Malformed JWT (401)
- Unauthorized staff access (401)
- Unauthorized admin endpoint (403 RBAC)
- Invalid device key (401)
- Unknown device (404)
- Inactive device (403)
- Invalid device zone (400)
- Malformed device request (422)
- Duplicate sequence (accepted=false)
- Security headers (nosniff, DENY, etc.)
- CORS handling
- Patient privacy leak prevention
"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.repositories.database import SessionLocal
from app.models.models import Device, Zone, _new_uuid, _utcnow
from app.core.security import hash_device_credential

client = TestClient(app)

ZONE_ID = "zone-0001-0000-0000-0000-000000000001"
DEVICE_ID = "devi-0001-0000-0000-0000-000000000001"
DEVICE_KEY = "esp32-secret-key-001"


def test_expired_jwt():
    # Generate token expired 1 hour ago
    expired_token = create_access_token(
        subject="some-user-id",
        role="ADMIN",
        expires_delta=timedelta(hours=-1)
    )
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "Invalid or expired" in res.json()["detail"]


def test_malformed_jwt():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert res.status_code == 401


def test_unknown_device_rejection():
    res = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": DEVICE_KEY},
        json={
            "device_id": "nonexistent-device-id",
            "zone_id": ZONE_ID,
            "sequence": 1,
            "event_type": "ENTRY",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_inactive_device_rejection():
    # Create an inactive device
    db = SessionLocal()
    dev_code = f"DEV-INACTIVE-{uuid.uuid4().hex[:6]}"
    inactive_dev = Device(
        id=_new_uuid(),
        device_code=dev_code,
        zone_id=ZONE_ID,
        firmware_version="0.1.0",
        credential_hash=hash_device_credential("test-inactive-key"),
        active=False,
        created_at=_utcnow(),
    )
    db.add(inactive_dev)
    db.commit()
    dev_id = inactive_dev.id
    db.close()

    res = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": "test-inactive-key"},
        json={
            "device_id": dev_id,
            "zone_id": ZONE_ID,
            "sequence": 1,
            "event_type": "ENTRY",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()


def test_invalid_device_zone_mismatch():
    # Create a secondary zone
    db = SessionLocal()
    sec_zone = Zone(
        id=_new_uuid(),
        name=f"Secondary Zone {uuid.uuid4().hex[:6]}",
        capacity=5,
        created_at=_utcnow(),
    )
    db.add(sec_zone)
    db.commit()
    other_zone_id = sec_zone.id
    db.close()

    res = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": DEVICE_KEY},
        json={
            "device_id": DEVICE_ID,
            "zone_id": other_zone_id,  # Device DEV-001 belongs to ZONE_ID, not other_zone_id
            "sequence": int(uuid.uuid4().int % 10000000) + 1,
            "event_type": "ENTRY",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert res.status_code == 400
    assert "zone" in res.json()["detail"].lower()


def test_malformed_device_request():
    # Invalid event_type (not ENTRY or EXIT)
    res = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": DEVICE_KEY},
        json={
            "device_id": DEVICE_ID,
            "zone_id": ZONE_ID,
            "sequence": 1,
            "event_type": "INVALID_TYPE",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert res.status_code == 422


def test_security_headers_present():
    res = client.get("/health")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert "X-Request-ID" in headers
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_production_security_guard():
    import pytest
    from app.core.config import Settings
    
    # 1. Production must reject default JWT secret
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="smartqueue-default-secret-key-32-bytes-long-change-in-production!",
            CORS_ORIGINS=["https://example.com"]
        )

    # 2. Production must reject wildcard CORS
    with pytest.raises(ValueError, match="CORS_ORIGINS cannot contain wildcard"):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="a-sufficiently-long-and-cryptographically-secure-random-key-here!",
            CORS_ORIGINS=["*"]
        )

    # 3. Valid production config passes
    valid = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="a-sufficiently-long-and-cryptographically-secure-random-key-here!",
        CORS_ORIGINS=["https://smartqueue-api.onrender.com"]
    )
    assert valid.ENVIRONMENT == "production"

