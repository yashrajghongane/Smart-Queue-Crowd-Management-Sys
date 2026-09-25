"""
tests/test_integrated_lifecycle.py

Complete 25-step integration test implementing Section 14 verbatim:
1. App / DB ready.
2. Seed verification.
3. Register patient 1.
4. Verify token 1.
5. Register patient 2.
6. CALL NEXT -> token 1 SERVING.
7. Verify patient status for token 1.
8. HOLD token 1.
9. RECALL token 1 back to WAITING.
10. CALL NEXT -> token 1 SERVING.
11. SKIP token 1.
12. RECALL token 1 back to WAITING.
13. CALL NEXT -> token 1 SERVING.
14. COMPLETE token 1.
15. Verify visit 1 closed.
16. Send authenticated ENTRY event.
17. Verify occupancy increased.
18. Send duplicate ENTRY sequence.
19. Verify occupancy did not increment twice.
20. Send EXIT.
21. Verify occupancy decreased.
22. Verify capacity status.
23. Verify staff crowd dashboard API.
24. Verify public display remains non-sensitive.
25. Verify patient frontend does not expose staff/device information.
"""
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.database import SessionLocal
from app.models.models import Department, Queue, _new_uuid, _utcnow

client = TestClient(app)

ZONE_ID    = "zone-0001-0000-0000-0000-000000000001"
DEVICE_ID  = "devi-0001-0000-0000-0000-000000000001"
DEVICE_KEY = "esp32-secret-key-001"


def test_25_step_integrated_lifecycle():
    # Setup isolated department and queue to prevent interference from other test fixtures
    db = SessionLocal()
    suffix = str(uuid.uuid4())[:6]
    test_dept = Department(
        id=_new_uuid(),
        name=f"Integrated Dept {suffix}",
        active=True,
        created_at=_utcnow(),
    )
    db.add(test_dept)
    test_queue = Queue(
        id=_new_uuid(),
        department_id=test_dept.id,
        name=f"Integrated Queue {suffix}",
        prefix=f"I{suffix[:3].upper()}",
        active=True,
        created_at=_utcnow(),
    )
    db.add(test_queue)
    db.commit()
    dept_id = test_dept.id
    queue_id = test_queue.id
    queue_prefix = test_queue.prefix
    db.close()

    # Step 1 & 2: Login staff
    login_res = client.post("/api/v1/auth/login", json={
        "username": "doctor",
        "password": "doctor123"
    })
    assert login_res.status_code == 200, "Step 1 & 2: Staff login failed"
    token = login_res.json()["access_token"]
    staff_headers = {"Authorization": f"Bearer {token}"}

    # Step 3: Register patient 1
    m1 = f"98{uuid.uuid4().int % 100000000:08d}"
    r1 = client.post("/api/v1/registrations/qr", json={
        "full_name": "Integrated Patient One",
        "mobile": m1,
        "department_id": dept_id,
    })
    assert r1.status_code == 201, "Step 3: Register patient 1 failed"
    p1 = r1.json()
    t1_id = p1["token_id"]
    v1_id = p1["visit_id"]

    # Step 4: Verify token 1
    assert p1["state"] == "WAITING", "Step 4: Token 1 should be WAITING"
    assert p1["token_number"].startswith(queue_prefix), "Step 4: Invalid token number format"

    # Step 5: Register second patient
    m2 = f"97{uuid.uuid4().int % 100000000:08d}"
    r2 = client.post("/api/v1/registrations/qr", json={
        "full_name": "Integrated Patient Two",
        "mobile": m2,
        "department_id": dept_id,
    })
    assert r2.status_code == 201, "Step 5: Register patient 2 failed"
    p2 = r2.json()

    # Step 6: CALL NEXT
    call_res = client.post(f"/api/v1/queues/{queue_id}/call-next", headers=staff_headers)
    assert call_res.status_code == 200, "Step 6: CALL NEXT failed"
    called_token = call_res.json()
    assert called_token["token_id"] == t1_id
    assert called_token["state"] == "SERVING", "Step 6: Token must be SERVING"

    # Step 7: Verify patient status
    st_res = client.get(f"/api/v1/visits/{v1_id}/status")
    assert st_res.status_code == 200, "Step 7: Patient status fetch failed"
    st = st_res.json()
    assert st["token_number"] == p1["token_number"]

    # Step 8: HOLD
    hold_res = client.post(
        f"/api/v1/tokens/{t1_id}/hold",
        headers=staff_headers,
        json={"reason": "Lab tests required"}
    )
    assert hold_res.status_code == 200, "Step 8: HOLD failed"
    assert hold_res.json()["state"] == "HOLD"

    # Step 9: RECALL
    recall_res1 = client.post(f"/api/v1/tokens/{t1_id}/recall", headers=staff_headers, json={})
    assert recall_res1.status_code == 200, "Step 9: RECALL failed"
    assert recall_res1.json()["state"] == "WAITING"

    # Step 10: CALL NEXT (t1 was sequence 1, t2 was sequence 2 -> t1 is recalled and called first)
    call_res2 = client.post(f"/api/v1/queues/{queue_id}/call-next", headers=staff_headers)
    assert call_res2.status_code == 200, "Step 10: CALL NEXT after recall failed"
    assert call_res2.json()["token_id"] == t1_id
    assert call_res2.json()["state"] == "SERVING"

    # Step 11: SKIP
    skip_res = client.post(
        f"/api/v1/tokens/{t1_id}/skip",
        headers=staff_headers,
        json={"reason": "Patient stepped out"}
    )
    assert skip_res.status_code == 200, "Step 11: SKIP failed"
    assert skip_res.json()["state"] == "SKIPPED"

    # Step 12: RECALL
    recall_res2 = client.post(f"/api/v1/tokens/{t1_id}/recall", headers=staff_headers, json={})
    assert recall_res2.status_code == 200, "Step 12: RECALL from skipped failed"
    assert recall_res2.json()["state"] == "WAITING"

    # Step 13: CALL NEXT
    call_res3 = client.post(f"/api/v1/queues/{queue_id}/call-next", headers=staff_headers)
    assert call_res3.status_code == 200, "Step 13: CALL NEXT failed"
    assert call_res3.json()["token_id"] == t1_id
    assert call_res3.json()["state"] == "SERVING"

    # Step 14: COMPLETE
    comp_res = client.post(f"/api/v1/tokens/{t1_id}/complete", headers=staff_headers, json={})
    assert comp_res.status_code == 200, "Step 14: COMPLETE failed"
    assert comp_res.json()["state"] == "COMPLETED"

    # Step 15: Verify visit closed
    final_st = client.get(f"/api/v1/visits/{v1_id}/status").json()
    assert final_st["state"] == "COMPLETED", "Step 15: Visit state should be COMPLETED"

    # Step 16: Send authenticated ENTRY event
    occ_before = client.get(f"/api/v1/zones/{ZONE_ID}/occupancy", headers=staff_headers).json()["occupancy"]
    test_seq = int(uuid.uuid4().int % 10000000) + 500

    entry_res = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": DEVICE_KEY},
        json={
            "device_id": DEVICE_ID,
            "zone_id": ZONE_ID,
            "sequence": test_seq,
            "event_type": "ENTRY",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert entry_res.status_code == 200, "Step 16: ENTRY event rejected"
    assert entry_res.json()["accepted"] is True

    # Step 17: Verify occupancy increased
    occ_after_entry = client.get(f"/api/v1/zones/{ZONE_ID}/occupancy", headers=staff_headers).json()["occupancy"]
    assert occ_after_entry == occ_before + 1, "Step 17: Occupancy did not increase"

    # Step 18: Send duplicate ENTRY sequence
    dup_res = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": DEVICE_KEY},
        json={
            "device_id": DEVICE_ID,
            "zone_id": ZONE_ID,
            "sequence": test_seq,
            "event_type": "ENTRY",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["accepted"] is False, "Step 18: Duplicate sequence was not recognized as duplicate"

    # Step 19: Verify occupancy did not increment twice
    occ_after_dup = client.get(f"/api/v1/zones/{ZONE_ID}/occupancy", headers=staff_headers).json()["occupancy"]
    assert occ_after_dup == occ_after_entry, "Step 19: Duplicate sequence changed occupancy"

    # Step 20: Send EXIT
    exit_res = client.post(
        "/api/v1/devices/events",
        headers={"X-Device-Key": DEVICE_KEY},
        json={
            "device_id": DEVICE_ID,
            "zone_id": ZONE_ID,
            "sequence": test_seq + 1,
            "event_type": "EXIT",
            "event_at": datetime.now(timezone.utc).isoformat(),
            "firmware_version": "0.1.0"
        }
    )
    assert exit_res.status_code == 200
    assert exit_res.json()["accepted"] is True

    # Step 21: Verify occupancy decreased
    occ_after_exit = client.get(f"/api/v1/zones/{ZONE_ID}/occupancy", headers=staff_headers).json()["occupancy"]
    assert occ_after_exit == occ_before, "Step 21: Occupancy did not decrease after EXIT"

    # Step 22: Verify capacity status
    crowd = client.get(f"/api/v1/zones/{ZONE_ID}/crowd", headers=staff_headers).json()
    assert crowd["capacity_alert"] in ("NORMAL", "MODERATE", "HIGH", "CRITICAL"), "Step 22: Bad capacity alert"

    # Step 23: Verify staff crowd dashboard API
    assert "entries_today" in crowd
    assert "exits_today" in crowd
    assert "net_change_today" in crowd
    assert crowd["device_status"] in ("ONLINE", "STALE", "OFFLINE")

    # Step 24: Verify public display remains non-sensitive
    pub = client.get(f"/api/v1/public/queues/{queue_id}/display").json()
    for sensitive_key in ("patient", "mobile", "device", "occupancy", "secret"):
        for k in pub.keys():
            assert sensitive_key not in k.lower(), f"Step 24: Sensitive key '{k}' exposed in public display"

    # Step 25: Verify patient frontend does not expose staff/device information
    pt_status = client.get(f"/api/v1/visits/{v1_id}/status").json()
    for forbidden in ("device", "staff", "actor", "occupancy", "password"):
        for k in pt_status.keys():
            assert forbidden not in k.lower(), f"Step 25: Key '{k}' exposed in patient status"
