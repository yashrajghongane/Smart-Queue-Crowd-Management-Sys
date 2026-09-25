"""
tests/test_privacy.py

Verifies the Patient Privacy Model and Public Endpoint Exposure rules (Sections 3 & 10).
Ensures patient endpoints and public display endpoints never leak:
- Other patients' names or mobile numbers
- Internal database identifiers where unnecessary
- Internal staff user IDs or action details
- Sensor/device IDs or credentials
- Internal audit logs
"""
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DEPT_ID = "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
QUEUE_ID = "3d3f0f52-6b7a-4bb3-92cb-7f1f4d340301"


def test_patient_registration_and_status_privacy():
    # Register patient
    unique_mobile = f"99{uuid.uuid4().int % 100000000:08d}"
    reg_res = client.post("/api/v1/registrations/qr", json={
        "full_name": "Private Patient Name",
        "mobile": unique_mobile,
        "department_id": DEPT_ID,
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    visit_id = reg_data["visit_id"]

    # Call patient status endpoint
    status_res = client.get(f"/api/v1/visits/{visit_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()

    # Allowed patient-facing fields:
    allowed_keys = {
        "visit_id",
        "token_number",
        "state",
        "patients_ahead",
        "serving_token",
        "department_id",
        "queue_name",
        "estimated_wait_minutes",
        "updated_at",
    }
    for key in status_data.keys():
        assert key in allowed_keys, f"Sensitive or unexpected key '{key}' found in patient status response!"

    # Forbidden sensitive fields that must NOT appear:
    forbidden_keys = [
        "full_name",
        "mobile",
        "patient_id",
        "staff_id",
        "actor_id",
        "device_id",
        "device_code",
        "credential_hash",
        "password_hash",
        "events",
        "audit",
    ]
    for key in forbidden_keys:
        assert key not in status_data, f"Forbidden key '{key}' leaked in patient status!"


def test_public_display_privacy():
    res = client.get(f"/api/v1/public/queues/{QUEUE_ID}/display")
    assert res.status_code == 200
    display_data = res.json()

    # Allowed public display keys:
    allowed_keys = {
        "queue_id",
        "serving_token",
        "next_token",
        "waiting_count",
        "updated_at",
    }
    for key in display_data.keys():
        assert key in allowed_keys, f"Unexpected key '{key}' found in public display response!"

    # Forbidden sensitive fields:
    forbidden_keys = [
        "patients",
        "full_name",
        "mobile",
        "patient_id",
        "staff",
        "device",
        "occupancy",
        "audit",
        "token_id",
    ]
    for key in forbidden_keys:
        assert key not in display_data, f"Forbidden key '{key}' leaked in public display!"
