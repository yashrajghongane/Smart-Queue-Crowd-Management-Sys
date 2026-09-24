from fastapi.testclient import TestClient
from app.main import app
from app.repositories.database import get_db, SessionLocal
from app.models.models import Department, Queue, Patient, Visit, Token, QueueEvent, _new_uuid, _utcnow
from datetime import date

client = TestClient(app)

def test_queue_flow():
    db = SessionLocal()

    # 1. Setup Data
    dept_id = _new_uuid()
    dept = Department(id=dept_id, name="Test Dept 2", active=True)
    db.add(dept)

    queue_id = _new_uuid()
    queue = Queue(id=queue_id, department_id=dept_id, name="Test Queue 2", prefix="TQ2", active=True)
    db.add(queue)

    db.commit()

    # 2. Register a few tokens
    for i in range(1, 4):
         res = client.post("/api/v1/registrations/qr", json={
             "full_name": f"Test {i}",
             "mobile": f"900000000{i}",
             "department_id": dept_id
         })
         assert res.status_code == 201

    # 3. Test Queue Summary
    res = client.get(f"/api/v1/queues/{queue_id}")
    assert res.status_code == 200
    assert res.json()["waiting_count"] == 3
    assert res.json()["serving_token"] is None

    # 4. Call Next
    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 200
    assert res.json()["token_number"] == "TQ2-1"
    assert res.json()["state"] == "SERVING"

    token1_id = res.json()["token_id"]

    res = client.get(f"/api/v1/queues/{queue_id}")
    assert res.json()["waiting_count"] == 2
    assert res.json()["serving_token"] == "TQ2-1"

    # 5. Hold
    res = client.post(f"/api/v1/tokens/{token1_id}/hold", json={"reason": "hold please"})
    assert res.status_code == 200
    assert res.json()["state"] == "HOLD"

    # 6. Call Next again (should get TQ2-2)
    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 200
    assert res.json()["token_number"] == "TQ2-2"
    token2_id = res.json()["token_id"]

    # 7. Complete TQ2-2
    res = client.post(f"/api/v1/tokens/{token2_id}/complete", json={})
    assert res.status_code == 200
    assert res.json()["state"] == "COMPLETED"

    # 8. Recall TQ2-1
    res = client.post(f"/api/v1/tokens/{token1_id}/recall", json={})
    assert res.status_code == 200
    assert res.json()["state"] == "WAITING"

    # 9. Skip TQ2-1
    res = client.post(f"/api/v1/tokens/{token1_id}/skip", json={})
    assert res.status_code == 200
    assert res.json()["state"] == "SKIPPED"

    # 10. Public Display
    res = client.get(f"/api/v1/public/queues/{queue_id}/display")
    assert res.status_code == 200
    assert res.json()["waiting_count"] == 1
    assert res.json()["next_token"] == "TQ2-3"

    # 11. Test Error handling (409) - Exhaust the queue
    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 200
    assert res.json()["token_number"] == "TQ2-3"

    res = client.post(f"/api/v1/queues/{queue_id}/call-next")
    assert res.status_code == 409
    assert res.json()["error"] == "NO_WAITING_TOKENS"
    assert res.json()["message"] == "No eligible waiting token is available."

    # 12. Invalid Transition (Completing a waiting token should fail)
    res = client.post(f"/api/v1/registrations/qr", json={
        "full_name": f"Test 4",
        "mobile": f"9000000004",
        "department_id": dept_id
    })
    token4_id = res.json()["token_id"]

    res = client.post(f"/api/v1/tokens/{token4_id}/complete", json={})
    assert res.status_code == 422
    assert res.json()["detail"] == "INVALID_STATE"

    # 13. Audit events check
    events = db.query(QueueEvent).filter(QueueEvent.token_id == token4_id).order_by(QueueEvent.created_at.asc()).all()
    assert len(events) == 1
    assert events[0].event_type == "CREATED"

    db.close()
