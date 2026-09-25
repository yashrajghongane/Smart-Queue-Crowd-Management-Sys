"""
tests/test_occupancy.py

Test suite for ESP32 device events, occupancy transitions, capacity alerts,
idempotency via (device_id, sequence), and staff crowd APIs.
"""
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DEVICE_ID = "devi-0001-0000-0000-0000-000000000001"
ZONE_ID   = "zone-0001-0000-0000-0000-000000000001"
DEVICE_KEY = "esp32-secret-key-001"


def test_device_event_auth_rejection():
    # Missing key -> 401
    res = client.post("/api/v1/devices/events", json={
        "device_id": DEVICE_ID,
        "zone_id": ZONE_ID,
        "sequence": 1,
        "event_type": "ENTRY",
        "event_at": datetime.now(timezone.utc).isoformat(),
        "firmware_version": "0.1.0"
    })
    assert res.status_code == 401

    # Wrong key -> 401
    res2 = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": "incorrect-key"},
        json={
            "device_id": DEVICE_ID,
            "zone_id": ZONE_ID,
            "sequence": 1,
            "event_type": "ENTRY",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert res2.status_code == 401


def test_occupancy_entry_and_idempotency():
    # Read initial occupancy
    occ_res = client.get(f"/api/v1/zones/{ZONE_ID}/occupancy")
    assert occ_res.status_code == 200
    initial_occ = occ_res.json()["occupancy"]

    seq = int(uuid.uuid4().int % 10000000) + 100

    # 1. First ENTRY event with sequence seq
    res1 = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": DEVICE_KEY},
        json={
            "device_id": DEVICE_ID,
            "zone_id": ZONE_ID,
            "sequence": seq,
            "event_type": "ENTRY",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["accepted"] is True
    assert data1["occupancy"] == initial_occ + 1

    # 2. Duplicate same sequence -> accepted=False, occupancy NOT incremented twice
    res2 = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": DEVICE_KEY},
        json={
            "device_id": DEVICE_ID,
            "zone_id": ZONE_ID,
            "sequence": seq,
            "event_type": "ENTRY",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["accepted"] is False
    assert data2["occupancy"] == initial_occ + 1

    # 3. EXIT event with seq + 1 -> occupancy decrements back
    res3 = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": DEVICE_KEY},
        json={
            "device_id": DEVICE_ID,
            "zone_id": ZONE_ID,
            "sequence": seq + 1,
            "event_type": "EXIT",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["accepted"] is True
    assert data3["occupancy"] == initial_occ


def test_capacity_thresholds():
    # Test alert calculation across levels
    from app.repositories.database import SessionLocal
    from app.services.occupancy_service import OccupancyService
    from app.models.models import Zone

    db = SessionLocal()
    try:
        zone = db.query(Zone).filter(Zone.id == ZONE_ID).first()
        svc = OccupancyService(db)

        # Capacity=10, mod=6, high=8, crit=10
        assert svc._calculate_capacity_alert(0, zone) == "NORMAL"
        assert svc._calculate_capacity_alert(5, zone) == "NORMAL"
        assert svc._calculate_capacity_alert(6, zone) == "MODERATE"
        assert svc._calculate_capacity_alert(7, zone) == "MODERATE"
        assert svc._calculate_capacity_alert(8, zone) == "HIGH"
        assert svc._calculate_capacity_alert(9, zone) == "HIGH"
        assert svc._calculate_capacity_alert(10, zone) == "CRITICAL"
        assert svc._calculate_capacity_alert(15, zone) == "CRITICAL"
    finally:
        db.close()


def test_crowd_detail_endpoint():
    # Login staff
    login_res = client.post("/api/v1/auth/login", json={
        "username": "doctor",
        "password": "doctor123"
    })
    token = login_res.json()["access_token"]

    res = client.get(
        f"/api/v1/zones/{ZONE_ID}/crowd",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "occupancy" in data
    assert "capacity" in data
    assert "utilization_percent" in data
    assert "capacity_alert" in data
    assert "device_status" in data
    assert data["zone_id"] == ZONE_ID
