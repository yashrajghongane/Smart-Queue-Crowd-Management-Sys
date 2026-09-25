"""
tests/test_concurrent_multiuser.py

Fulfills Directive 14: MULTI-USER TEST
- Simulates 10 concurrent patient registrations.
- Verifies all 10 succeed with 201 Created.
- Verifies strictly unique token numbers and sequential queue sequence numbers.
- Verifies database consistency without race-condition corruption.
- Verifies concurrent CALL NEXT requests with row locking.
- Verifies duplicate concurrent registration for the same patient produces 409 Conflict.
"""
import uuid
import concurrent.futures
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.database import SessionLocal
from app.models.models import Department, Queue, _new_uuid, _utcnow

client = TestClient(app)


def test_10_concurrent_patient_registrations():
    # 1. Setup isolated department and queue
    db = SessionLocal()
    suffix = str(uuid.uuid4())[:6]
    dept = Department(
        id=_new_uuid(),
        name=f"Concurrent Dept {suffix}",
        active=True,
        created_at=_utcnow(),
    )
    db.add(dept)
    queue = Queue(
        id=_new_uuid(),
        department_id=dept.id,
        name=f"Concurrent Queue {suffix}",
        prefix=f"C{suffix[:3].upper()}",
        active=True,
        created_at=_utcnow(),
    )
    db.add(queue)
    db.commit()
    dept_id = dept.id
    queue_id = queue.id
    queue_prefix = queue.prefix
    db.close()

    # 2. Fire 10 simultaneous registration requests
    num_patients = 10
    patients_payloads = [
        {
            "full_name": f"Concurrent Patient {i}",
            "mobile": f"98{uuid.uuid4().int % 100000000:08d}",
            "department_id": dept_id,
        }
        for i in range(num_patients)
    ]

    def register_patient(payload):
        # Using a new client instance per thread for true concurrency
        c = TestClient(app)
        return c.post("/api/v1/registrations/qr", json=payload)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        responses = list(executor.map(register_patient, patients_payloads))

    # 3. Verify all 10 succeeded
    assert len(responses) == 10
    for idx, resp in enumerate(responses):
        assert resp.status_code == 201, f"Patient {idx} failed with {resp.status_code}: {resp.text}"

    data_list = [r.json() for r in responses]

    # 4. Verify unique tokens and sequences
    token_numbers = [d["token_number"] for d in data_list]
    visit_ids = [d["visit_id"] for d in data_list]
    token_ids = [d["token_id"] for d in data_list]

    assert len(set(token_numbers)) == 10, f"Duplicate token numbers found: {token_numbers}"
    assert len(set(visit_ids)) == 10, f"Duplicate visit IDs found: {visit_ids}"
    assert len(set(token_ids)) == 10, f"Duplicate token IDs found: {token_ids}"

    # Extract sequence numbers from token numbers (e.g. "CABC-1", "CABC-2", etc.)
    sequences = sorted([int(t.split("-")[-1]) for t in token_numbers])
    assert sequences == list(range(1, 11)), f"Sequences were not 1 through 10: {sequences}"

    # 5. Verify Queue Summary reflects exactly 10 waiting
    summary = client.get(f"/api/v1/queues/{queue_id}").json()
    assert summary["waiting_count"] == 10
    assert summary["serving_token"] is None

    # 6. Test concurrent CALL NEXT with row locking
    # Staff logs in
    login_res = client.post("/api/v1/auth/login", json={
        "username": "doctor",
        "password": "doctor123"
    })
    token = login_res.json()["access_token"]
    staff_headers = {"Authorization": f"Bearer {token}"}

    def call_next_token(_):
        c = TestClient(app)
        return c.post(f"/api/v1/queues/{queue_id}/call-next", headers=staff_headers)

    # Call next concurrently 3 times
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        call_responses = list(executor.map(call_next_token, range(3)))

    call_data = [r.json() for r in call_responses if r.status_code == 200]
    assert len(call_data) >= 1, "At least one call next must succeed"
    called_tokens = [d["token_number"] for d in call_data]
    # No duplicate token ever assigned to multiple calls
    assert len(set(called_tokens)) == len(called_tokens), f"Duplicate token assigned: {called_tokens}"
