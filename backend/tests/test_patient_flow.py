"""
backend/tests/test_patient_flow.py

Automated tests for Patient Flow QA & Hardening:
- QR and Staff registration (Doc A §2.1 & §2.2)
- Duplicate active registration handling (409)
- Mobile formatting normalization and full_name whitespace trimming
- Patient status retrieval and patients_ahead calculation
- Validation edge cases (422) and missing resources (404)
- Device event endpoint status (501 deferred)
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.database import SessionLocal
from app.models.models import Department, Queue, _new_uuid, _utcnow

client = TestClient(app)


@pytest.fixture
def setup_dept():
    db = SessionLocal()
    dept_id = _new_uuid()
    prefix = f"P{dept_id[:4].upper()}"
    dept = Department(id=dept_id, name=f"General Medicine {dept_id[:6]}", active=True, created_at=_utcnow())
    db.add(dept)

    queue_id = _new_uuid()
    queue = Queue(id=queue_id, department_id=dept_id, name=f"Queue {prefix}", prefix=prefix, active=True, created_at=_utcnow())
    db.add(queue)
    db.commit()
    db.close()

    return {"department_id": dept_id, "queue_id": queue_id, "prefix": prefix}


def test_qr_registration_and_status(setup_dept):
    dept_id = setup_dept["department_id"]
    prefix = setup_dept["prefix"]

    res = client.post("/api/v1/registrations/qr", json={
        "full_name": "  Ananya Sharma  ",
        "mobile": "9876543210",
        "department_id": dept_id,
    })
    assert res.status_code == 201
    data = res.json()
    assert "patient_id" in data
    assert "visit_id" in data
    assert "token_id" in data
    assert data["state"] == "WAITING"
    assert data["token_number"].startswith(f"{prefix}-")
    assert data["department_id"] == dept_id

    # Retrieve patient status
    visit_id = data["visit_id"]
    stat_res = client.get(f"/api/v1/visits/{visit_id}/status")
    assert stat_res.status_code == 200
    stat_data = stat_res.json()
    assert stat_data["visit_id"] == visit_id
    assert stat_data["token_number"] == data["token_number"]
    assert stat_data["state"] == "WAITING"
    assert stat_data["patients_ahead"] == 0


def test_duplicate_registration_returns_409(setup_dept):
    dept_id = setup_dept["department_id"]
    mobile = "9988776655"

    res1 = client.post("/api/v1/registrations/qr", json={
        "full_name": "Duplicate Test User",
        "mobile": mobile,
        "department_id": dept_id,
    })
    assert res1.status_code == 201
    first_token = res1.json()["token_number"]
    first_visit = res1.json()["visit_id"]

    # Duplicate attempt
    res2 = client.post("/api/v1/registrations/qr", json={
        "full_name": "Duplicate Test User",
        "mobile": mobile,
        "department_id": dept_id,
    })
    assert res2.status_code == 409
    body = res2.json()
    err_obj = body if "error" in body else body.get("detail", {})
    assert err_obj.get("error") == "ACTIVE_VISIT_EXISTS"
    assert err_obj.get("token_number") == first_token
    assert err_obj.get("visit_id") == first_visit


def test_mobile_normalization(setup_dept):
    dept_id = setup_dept["department_id"]
    # Register with formatted number: +91 98111-22233
    res1 = client.post("/api/v1/registrations/qr", json={
        "full_name": "Phone Normalization Patient",
        "mobile": "+91 98111-22233",
        "department_id": dept_id,
    })
    assert res1.status_code == 201

    # Attempt duplicate with raw digits: 9811122233
    res2 = client.post("/api/v1/registrations/qr", json={
        "full_name": "Phone Normalization Patient",
        "mobile": "9811122233",
        "department_id": dept_id,
    })
    assert res2.status_code == 409


def test_staff_assisted_registration(setup_dept):
    dept_id = setup_dept["department_id"]
    prefix = setup_dept["prefix"]

    res = client.post("/api/v1/registrations/staff", json={
        "full_name": "Staff Assisted Patient",
        "mobile": "9700000001",
        "department_id": dept_id,
    })
    assert res.status_code == 201
    data = res.json()
    assert data["state"] == "WAITING"
    assert data["token_number"].startswith(f"{prefix}-")


def test_validation_errors(setup_dept):
    dept_id = setup_dept["department_id"]

    # Whitespace-only name -> 422
    res = client.post("/api/v1/registrations/qr", json={
        "full_name": "   ",
        "mobile": "9876543210",
        "department_id": dept_id,
    })
    assert res.status_code == 422

    # Mobile too short (< 7 digits) -> 422
    res = client.post("/api/v1/registrations/qr", json={
        "full_name": "Test User",
        "mobile": "12345",
        "department_id": dept_id,
    })
    assert res.status_code == 422

    # Missing department -> 422
    res = client.post("/api/v1/registrations/qr", json={
        "full_name": "Test User",
        "mobile": "9876543210",
    })
    assert res.status_code == 422

    # Unknown department -> 404
    bad_dept = str(uuid.uuid4())
    res = client.post("/api/v1/registrations/qr", json={
        "full_name": "Test User",
        "mobile": "9876543210",
        "department_id": bad_dept,
    })
    assert res.status_code == 404


def test_device_events_endpoint_authenticated():
    unique_seq = int(uuid.uuid4().int % 10000000) + 1000
    # 1. Without credentials -> 401
    res_no_auth = client.post("/api/v1/devices/events", json={
        "device_id": "b0000001-0000-4000-8000-000000000001",
        "zone_id": "a0000001-0000-4000-8000-000000000001",
        "sequence": unique_seq,
        "event_type": "ENTRY",
        "event_at": "2026-09-23T16:10:32.420Z",
        "firmware_version": "0.1.0"
    })
    assert res_no_auth.status_code == 401

    # 2. With invalid credentials -> 401
    res_bad_auth = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": "wrong-secret-key"},
        json={
            "device_id": "b0000001-0000-4000-8000-000000000001",
            "zone_id": "a0000001-0000-4000-8000-000000000001",
            "sequence": unique_seq,
            "event_type": "ENTRY",
            "event_at": "2026-09-23T16:10:32.420Z",
            "firmware_version": "0.1.0"
        }
    )
    assert res_bad_auth.status_code == 401

    # 3. With valid credentials -> 200 OK
    res_ok = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": "esp32-secret-key-001"},
        json={
            "device_id": "b0000001-0000-4000-8000-000000000001",
            "zone_id": "a0000001-0000-4000-8000-000000000001",
            "sequence": unique_seq,
            "event_type": "ENTRY",
            "event_at": "2026-09-23T16:10:32.420Z",
            "firmware_version": "0.1.0"
        }
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["accepted"] is True
    assert data["event_type"] == "ENTRY"
