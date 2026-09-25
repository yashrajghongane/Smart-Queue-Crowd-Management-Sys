"""
test_e2e_sequence.py

Performs the EXACT 23-step sequence specified in Section 19 of the project requirements:
1. Register Patient A
2. Confirm: Patient created/found, Visit created, Token created, state = WAITING
3. Register Patient B
4. Confirm: B receives another token
5. GET queue
6. CALL NEXT
7. Confirm first eligible token becomes SERVING
8. GET patient status
9. Confirm patient status reflects SERVING
10. HOLD the serving token
11. Confirm state = HOLD
12. RECALL it
13. Confirm documented transition (HOLD -> WAITING)
14. CALL NEXT when appropriate
15. SKIP a token
16. Confirm state = SKIPPED
17. RECALL skipped token
18. Confirm state = WAITING
19. CALL NEXT again
20. COMPLETE the serving token
21. Confirm: token = COMPLETED, visit = closed
22. Confirm queue summary updates
23. Confirm public display updates
"""
import sys
import json
import urllib.request
import urllib.error
import random
from app.repositories.database import SessionLocal
from app.models.models import Department, Queue, Token, Visit, _new_uuid, _utcnow

BASE = "http://127.0.0.1:8000"

def api(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw}

def run_e2e():
    print("=" * 70)
    print("STARTING END-TO-END 23-STEP DIGITAL QUEUE TEST")
    print("=" * 70)

    # Setup dedicated Department & Queue so test is isolated and clean
    db = SessionLocal()
    dept_id = _new_uuid()
    prefix = f"E{dept_id[:4].upper()}"
    dept = Department(id=dept_id, name=f"E2E Clean Dept {dept_id[:6]}", active=True, created_at=_utcnow())
    db.add(dept)

    queue_id = _new_uuid()
    queue = Queue(id=queue_id, department_id=dept_id, name=f"E2E Clean Queue {queue_id[:6]}", prefix=prefix, active=True, created_at=_utcnow())
    db.add(queue)
    db.commit()
    db.close()

    print(f"Test Environment Initialized: Dept={dept_id}, Queue={queue_id}, Prefix={prefix}")

    # 1. Register Patient A
    rnd = random.randint(100000, 999999)
    phone_a = f"921{rnd}"
    print("\n[Step 1] Register Patient A")
    s, data_a = api("POST", "/api/v1/registrations/qr", {
        "full_name": "E2E Patient A",
        "mobile": phone_a,
        "department_id": dept_id
    })
    assert s == 201, f"Expected 201, got {s}: {data_a}"
    token_a_id = data_a["token_id"]
    token_a_num = data_a["token_number"]
    visit_a_id = data_a["visit_id"]
    print(f"  -> Status {s}: Token {token_a_num}")

    # 2. Confirm Patient A details
    print("\n[Step 2] Confirm: Patient created/found, Visit created, Token created, state = WAITING")
    assert "patient_id" in data_a, "Missing patient_id"
    assert "visit_id" in data_a, "Missing visit_id"
    assert "token_id" in data_a, "Missing token_id"
    assert data_a["state"] == "WAITING", f"Expected WAITING, got {data_a['state']}"
    assert token_a_num == f"{prefix}-1", f"Expected {prefix}-1, got {token_a_num}"
    print(f"  -> Confirmed: Token={token_a_num}, State={data_a['state']}, Visit={visit_a_id}")

    # 3. Register Patient B
    phone_b = f"922{rnd}"
    print("\n[Step 3] Register Patient B")
    s, data_b = api("POST", "/api/v1/registrations/qr", {
        "full_name": "E2E Patient B",
        "mobile": phone_b,
        "department_id": dept_id
    })
    assert s == 201, f"Expected 201, got {s}: {data_b}"
    token_b_id = data_b["token_id"]
    token_b_num = data_b["token_number"]
    visit_b_id = data_b["visit_id"]
    print(f"  -> Status {s}: Token {token_b_num}")

    # 4. Confirm Patient B receives another token
    print("\n[Step 4] Confirm: B receives another token")
    assert token_b_id != token_a_id, "Token B ID should not match Token A"
    assert token_b_num == f"{prefix}-2", f"Expected {prefix}-2, got {token_b_num}"
    assert data_b["state"] == "WAITING"
    print(f"  -> Confirmed distinct token: Token B={token_b_num}")

    # 5. GET queue
    print("\n[Step 5] GET queue")
    s, q_data = api("GET", f"/api/v1/queues/{queue_id}")
    assert s == 200
    assert q_data["waiting_count"] == 2
    assert q_data["serving_token"] is None
    print(f"  -> Queue summary: waiting_count={q_data['waiting_count']}, currently serving={q_data['serving_token']}")

    # 6. CALL NEXT
    print("\n[Step 6] CALL NEXT")
    s, call_data = api("POST", f"/api/v1/queues/{queue_id}/call-next", {})
    assert s == 200, f"Call next failed: {call_data}"
    called_id = call_data["token_id"]
    called_num = call_data["token_number"]
    print(f"  -> Called token: {called_num} (ID: {called_id})")

    # 7. Confirm first eligible token becomes SERVING
    print("\n[Step 7] Confirm first eligible token becomes SERVING")
    assert called_id == token_a_id, f"Expected Token A ({token_a_id}) to be called, got {called_id}"
    assert call_data["state"] == "SERVING"
    assert call_data["previous_state"] == "WAITING"
    print(f"  -> Confirmed: {called_num} is SERVING")

    # 8. GET patient status
    print("\n[Step 8] GET patient status")
    s, stat_data = api("GET", f"/api/v1/visits/{visit_a_id}/status")
    assert s == 200
    print(f"  -> Patient status: token={stat_data['token_number']}, state={stat_data['state']}")

    # 9. Confirm patient status reflects SERVING
    print("\n[Step 9] Confirm patient status reflects SERVING")
    assert stat_data["state"] == "SERVING"
    assert stat_data["token_number"] == token_a_num
    print("  -> Confirmed: Patient status is SERVING")

    # 10. HOLD the serving token
    print(f"\n[Step 10] HOLD the serving token ({token_a_num})")
    s, hold_data = api("POST", f"/api/v1/tokens/{token_a_id}/hold", {"reason": "Patient called away"})
    assert s == 200
    print(f"  -> Hold response: state={hold_data['state']}")

    # 11. Confirm state = HOLD
    print("\n[Step 11] Confirm state = HOLD")
    assert hold_data["state"] == "HOLD"
    assert hold_data["previous_state"] == "SERVING"
    print("  -> Confirmed: State is HOLD")

    # 12. RECALL it
    print(f"\n[Step 12] RECALL token ({token_a_num})")
    s, recall_data = api("POST", f"/api/v1/tokens/{token_a_id}/recall", {})
    assert s == 200
    print(f"  -> Recall response: state={recall_data['state']}")

    # 13. Confirm documented transition
    print("\n[Step 13] Confirm documented transition (HOLD -> WAITING)")
    assert recall_data["state"] == "WAITING"
    assert recall_data["previous_state"] == "HOLD"
    print("  -> Confirmed: HOLD -> WAITING transition verified")

    # 14. CALL NEXT when appropriate
    print("\n[Step 14] CALL NEXT when appropriate")
    s, next_data = api("POST", f"/api/v1/queues/{queue_id}/call-next", {})
    assert s == 200
    assert next_data["token_id"] == token_a_id, "Expected Token A to be recalled to head of queue"
    assert next_data["state"] == "SERVING"
    print(f"  -> Now serving: {next_data['token_number']}")

    # 15. SKIP a token
    print(f"\n[Step 15] SKIP a token ({token_a_num})")
    s, skip_data = api("POST", f"/api/v1/tokens/{token_a_id}/skip", {"reason": "No response"})
    assert s == 200
    print(f"  -> Skip response: state={skip_data['state']}")

    # 16. Confirm state = SKIPPED
    print("\n[Step 16] Confirm state = SKIPPED")
    assert skip_data["state"] == "SKIPPED"
    assert skip_data["previous_state"] == "SERVING"
    print("  -> Confirmed: State is SKIPPED")

    # 17. RECALL skipped token
    print(f"\n[Step 17] RECALL skipped token ({token_a_num})")
    s, recall2_data = api("POST", f"/api/v1/tokens/{token_a_id}/recall", {})
    assert s == 200
    print(f"  -> Recall response: state={recall2_data['state']}")

    # 18. Confirm state = WAITING
    print("\n[Step 18] Confirm state = WAITING")
    assert recall2_data["state"] == "WAITING"
    assert recall2_data["previous_state"] == "SKIPPED"
    print("  -> Confirmed: SKIPPED -> WAITING transition verified")

    # 19. CALL NEXT again
    print("\n[Step 19] CALL NEXT again")
    s, next2_data = api("POST", f"/api/v1/queues/{queue_id}/call-next", {})
    assert s == 200
    assert next2_data["token_id"] == token_a_id
    assert next2_data["state"] == "SERVING"
    print(f"  -> Serving: {next2_data['token_number']}")

    # 20. COMPLETE the serving token
    print(f"\n[Step 20] COMPLETE the serving token ({token_a_num})")
    s, comp_data = api("POST", f"/api/v1/tokens/{token_a_id}/complete", {})
    assert s == 200
    print(f"  -> Complete response: state={comp_data['state']}")

    # 21. Confirm: token = COMPLETED, visit = closed
    print("\n[Step 21] Confirm: token = COMPLETED, visit = closed")
    assert comp_data["state"] == "COMPLETED"
    assert "completed_at" in comp_data and comp_data["completed_at"] is not None
    # Check visit in database
    db = SessionLocal()
    tok_obj = db.query(Token).filter(Token.id == token_a_id).first()
    assert tok_obj is not None and tok_obj.state == "COMPLETED"
    vis_obj = db.query(Visit).filter(Visit.id == tok_obj.visit_id).first()
    assert vis_obj is not None and vis_obj.closed_at is not None, "Visit was not closed!"
    db.close()
    print(f"  -> Confirmed: token={tok_obj.state}, visit.closed_at={vis_obj.closed_at}")

    # 22. Confirm queue summary updates
    print("\n[Step 22] Confirm queue summary updates")
    s, q_final = api("GET", f"/api/v1/queues/{queue_id}")
    assert s == 200
    assert q_final["waiting_count"] == 1
    assert q_final["serving_token"] is None
    print(f"  -> Queue summary: waiting_count={q_final['waiting_count']}, serving_token={q_final['serving_token']}")

    # 23. Confirm public display updates
    print("\n[Step 23] Confirm public display updates")
    s, disp_final = api("GET", f"/api/v1/public/queues/{queue_id}/display")
    assert s == 200
    assert disp_final["queue_id"] == queue_id
    assert disp_final["serving_token"] is None
    assert disp_final["next_token"] == token_b_num
    assert disp_final["waiting_count"] == 1
    print(f"  -> Public display: serving_token={disp_final['serving_token']}, next_token={disp_final['next_token']}, waiting_count={disp_final['waiting_count']}")

    print("\n" + "=" * 70)
    print("ALL 23 STEPS OF THE END-TO-END DIGITAL QUEUE TEST PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e()
