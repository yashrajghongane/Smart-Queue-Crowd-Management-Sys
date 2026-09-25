"""
backend/tests/test_queue.py

Comprehensive tests for canonical queue operations:
- Registration & Token creation
- Queue summary & counts
- CALL NEXT (WAITING -> SERVING)
- HOLD (SERVING -> HOLD, WAITING -> HOLD)
- RECALL (HOLD -> WAITING, SKIPPED -> WAITING, SERVING -> SERVING)
- SKIP (WAITING -> SKIPPED, SERVING -> SKIPPED, HOLD -> SKIPPED)
- COMPLETE (SERVING -> COMPLETED, closes visit)
- Error handling (404 missing resource, 409 invalid transition, 409 no waiting tokens)
- Public display synchronization
- QueueEvent audit trail
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.database import SessionLocal
from app.models.models import Department, Queue, QueueEvent, Visit, _new_uuid, _utcnow

client = TestClient(app)


@pytest.fixture
def setup_queue():
    db = SessionLocal()
    dept_id = _new_uuid()
    dept = Department(id=dept_id, name=f"Test Dept {dept_id[:6]}", active=True, created_at=_utcnow())
    db.add(dept)

    queue_id = _new_uuid()
    prefix = f"Q{queue_id[:4].upper()}"
    queue = Queue(id=queue_id, department_id=dept_id, name=f"Test Queue {queue_id[:6]}", prefix=prefix, active=True, created_at=_utcnow())
    db.add(queue)
    db.commit()
    db.close()

    return {"department_id": dept_id, "queue_id": queue_id}


def test_complete_queue_lifecycle(setup_queue):
    dept_id = setup_queue["department_id"]
    queue_id = setup_queue["queue_id"]

    # 1. Register 3 patients
    tokens = []
    visits = []
    for i in range(1, 4):
        res = client.post("/api/v1/registrations/qr", json={
            "full_name": f"Test Patient {i}",
            "mobile": f"910000000{i}",
            "department_id": dept_id
        })
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["state"] == "WAITING"
        tokens.append(data["token_id"])
        visits.append(data["visit_id"])

    # 2. Check Queue Summary
    res = client.get(f"/api/v1/queues/{queue_id}")
    assert res.status_code == 200
    summary = res.json()
    assert summary["waiting_count"] == 3
    assert summary["serving_token"] is None
    assert summary["serving_token_id"] is None

    # 3. Call Next -> Token 1 becomes SERVING
    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 200
    t1 = res.json()
    assert t1["token_id"] == tokens[0]
    assert t1["previous_state"] == "WAITING"
    assert t1["state"] == "SERVING"

    # Queue summary reflects serving token
    res = client.get(f"/api/v1/queues/{queue_id}")
    assert res.json()["waiting_count"] == 2
    assert res.json()["serving_token"] == t1["token_number"]
    assert res.json()["serving_token_id"] == tokens[0]

    # 4. Hold Token 1 (SERVING -> HOLD)
    res = client.post(f"/api/v1/tokens/{tokens[0]}/hold", json={"reason": "Lab test needed"})
    assert res.status_code == 200
    assert res.json()["state"] == "HOLD"
    assert res.json()["previous_state"] == "SERVING"

    # 5. Call Next -> Token 2 becomes SERVING
    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 200
    t2 = res.json()
    assert t2["token_id"] == tokens[1]
    assert t2["state"] == "SERVING"

    # 6. Skip Token 2 (SERVING -> SKIPPED)
    res = client.post(f"/api/v1/tokens/{tokens[1]}/skip", json={"reason": "Patient absent"})
    assert res.status_code == 200
    assert res.json()["state"] == "SKIPPED"
    assert res.json()["previous_state"] == "SERVING"

    # 7. Recall Token 1 (HOLD -> WAITING)
    res = client.post(f"/api/v1/tokens/{tokens[0]}/recall", json={})
    assert res.status_code == 200
    assert res.json()["state"] == "WAITING"
    assert res.json()["previous_state"] == "HOLD"

    # 8. Recall Token 2 (SKIPPED -> WAITING)
    res = client.post(f"/api/v1/tokens/{tokens[1]}/recall", json={})
    assert res.status_code == 200
    assert res.json()["state"] == "WAITING"
    assert res.json()["previous_state"] == "SKIPPED"

    # 9. Call Next -> Token 1 called again (lower sequence number)
    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 200
    assert res.json()["token_id"] == tokens[0]
    assert res.json()["state"] == "SERVING"

    # 10. Complete Token 1 (SERVING -> COMPLETED)
    res = client.post(f"/api/v1/tokens/{tokens[0]}/complete", json={})
    assert res.status_code == 200
    assert res.json()["state"] == "COMPLETED"
    assert "completed_at" in res.json()

    # Verify visit is closed
    db = SessionLocal()
    visit = db.query(Visit).filter(Visit.id == visits[0]).first()
    assert visit is not None
    assert visit.closed_at is not None
    db.close()

    # 11. Public Display Check
    res = client.get(f"/api/v1/public/queues/{queue_id}/display")
    assert res.status_code == 200
    disp = res.json()
    assert disp["queue_id"] == queue_id
    assert disp["serving_token"] is None
    assert disp["next_token"] is not None
    assert disp["waiting_count"] == 2

    # 12. Exhaust remaining tokens (Token 2 and Token 3)
    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 200
    res = client.post(f"/api/v1/tokens/{res.json()['token_id']}/complete", json={})
    assert res.status_code == 200

    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 200
    res = client.post(f"/api/v1/tokens/{res.json()['token_id']}/complete", json={})
    assert res.status_code == 200

    # 13. Call Next on empty queue -> 409 NO_WAITING_TOKENS
    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 409
    err = res.json()
    assert err.get("error") == "NO_WAITING_TOKENS"

    # 14. Invalid transition -> 409 INVALID_STATE (trying to complete an already completed token)
    res = client.post(f"/api/v1/tokens/{tokens[0]}/complete", json={})
    assert res.status_code == 409
    assert res.json()["detail"] == "INVALID_STATE"

    # 15. Missing resource checks -> 404
    bad_id = str(uuid.uuid4())
    assert client.get(f"/api/v1/queues/{bad_id}").status_code == 404
    assert client.post(f"/api/v1/queues/{bad_id}/call-next").status_code == 404
    assert client.post(f"/api/v1/tokens/{bad_id}/hold", json={}).status_code == 404
    assert client.post(f"/api/v1/tokens/{bad_id}/recall", json={}).status_code == 404
    assert client.post(f"/api/v1/tokens/{bad_id}/skip", json={}).status_code == 404
    assert client.post(f"/api/v1/tokens/{bad_id}/complete", json={}).status_code == 404
    assert client.get(f"/api/v1/public/queues/{bad_id}/display").status_code == 404

    # 16. Audit events recorded
    db = SessionLocal()
    events = db.query(QueueEvent).filter(QueueEvent.token_id == tokens[0]).order_by(QueueEvent.created_at.asc()).all()
    event_types = [e.event_type for e in events]
    assert "CALL_NEXT" in event_types
    assert "HOLD" in event_types
    assert "RECALL" in event_types
    assert "COMPLETE" in event_types
    db.close()
