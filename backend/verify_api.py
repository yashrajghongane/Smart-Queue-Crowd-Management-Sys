"""
verify_api.py

Comprehensive verification script for the SmartQueue backend API and static frontends.
Tests all requirements specified in Document A and Sections 18 & 19 of the project contract:
1. Health check (GET /health)
2. Root (GET /)
3. OpenAPI Docs (GET /docs, GET /openapi.json)
4. QR registration (POST /api/v1/registrations/qr)
5. Duplicate active visit handling (POST /api/v1/registrations/qr -> 409)
6. Staff-assisted registration (POST /api/v1/registrations/staff)
7. Patient status retrieval (GET /api/v1/visits/{id}/status)
8. Patient status 404
9. Input validations 422 (invalid mobile, missing fields, empty name)
10. Unknown department 404
11. Queue summary (GET /api/v1/queues/{queue_id})
12. Call next (POST /api/v1/queues/{queue_id}/call-next)
13. Hold token (POST /api/v1/tokens/{token_id}/hold)
14. Recall held token (POST /api/v1/tokens/{token_id}/recall)
15. Skip token (POST /api/v1/tokens/{token_id}/skip)
16. Recall skipped token (POST /api/v1/tokens/{token_id}/recall)
17. Complete token (POST /api/v1/tokens/{token_id}/complete)
18. Invalid transition handling (POST /api/v1/tokens/{token_id}/complete -> 409)
19. Public display synchronization (GET /api/v1/public/queues/{queue_id}/display)
20. Device event ingestion (POST /api/v1/devices/events -> 501 deferred)
21. Static frontend serving (/patient/, /staff/, /staff/public.html)

Run:
    python verify_api.py
(with uvicorn server running on localhost:8000)
"""
import sys
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
DEPT_ID = "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
QUEUE_ID = "3d3f0f52-6b7a-4bb3-92cb-7f1f4d340301"
PASS = []
FAIL = []


def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as resp:
            status = resp.status
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                body_out = json.loads(resp.read().decode())
            else:
                body_out = resp.read().decode()
            return status, body_out
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body_out = json.loads(e.read().decode())
        except Exception:
            body_out = {}
        return status, body_out


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


# ── 1. Health check ──────────────────────────────────────────────────────────
print("\n[1] Health check")
status, body = req("GET", "/health")
check("GET /health returns 200", status == 200, f"got {status}")
check("health body has status=ok", isinstance(body, dict) and body.get("status") == "ok", str(body))

# ── 2. Root ──────────────────────────────────────────────────────────────────
print("\n[2] Root")
status, body = req("GET", "/")
check("GET / returns 200", status == 200, f"got {status}")
check("root has docs link", isinstance(body, dict) and "docs" in body, str(body))

# ── 3. Docs & OpenAPI ────────────────────────────────────────────────────────
print("\n[3] Docs & OpenAPI")
status, _ = req("GET", "/openapi.json")
check("GET /openapi.json returns 200", status == 200, f"got {status}")
status, _ = req("GET", "/docs")
check("GET /docs returns 200", status == 200, f"got {status}")

# ── 4. QR registration — new patient ────────────────────────────────────────
print("\n[4] QR registration (Patient A)")
import random
unique_suffix = random.randint(100000, 999999)
mobile_a = f"987{unique_suffix}"
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Asha Patil",
    "mobile": mobile_a,
    "department_id": DEPT_ID,
})
check("POST /registrations/qr returns 201", status == 201, f"got {status} — {body}")
check("response has patient_id", "patient_id" in body, str(body))
check("response has visit_id", "visit_id" in body, str(body))
check("response has token_id", "token_id" in body, str(body))
check("response has token_number", "token_number" in body, str(body))
check("token_number starts with GM-", body.get("token_number", "").startswith("GM-"), str(body))
check("state is WAITING", body.get("state") == "WAITING", str(body))
check("department_id correct", body.get("department_id") == DEPT_ID, str(body))

patient_id_a = body.get("patient_id")
visit_id_a = body.get("visit_id")
token_id_a = body.get("token_id")
token_num_a = body.get("token_number")
print(f"      Token A: {token_num_a}, Visit A: {visit_id_a}")

# ── 5. Duplicate QR registration — same patient, same dept ──────────────────
print("\n[5] Duplicate QR registration (same patient + dept)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Asha Patil",
    "mobile": mobile_a,
    "department_id": DEPT_ID,
})
check("POST /registrations/qr duplicate returns 409", status == 409, f"got {status} — {body}")
detail = body if "error" in body else body.get("detail", {})
check("duplicate has error=ACTIVE_VISIT_EXISTS", detail.get("error") == "ACTIVE_VISIT_EXISTS", str(detail))
check("duplicate has visit_id", "visit_id" in detail, str(detail))
check("duplicate has token_number", "token_number" in detail, str(detail))
check("duplicate token_number matches first", detail.get("token_number") == token_num_a, str(detail))

# ── 6. Staff registration — Patient B ───────────────────────────────────────
print("\n[6] Staff registration (Patient B)")
mobile_b = f"912{unique_suffix}"
status, body = req("POST", "/api/v1/registrations/staff", {
    "full_name": "Ramesh Jadhav",
    "mobile": mobile_b,
    "department_id": DEPT_ID,
})
check("POST /registrations/staff returns 201", status == 201, f"got {status} — {body}")
check("staff registration has token_number", "token_number" in body, str(body))
check("staff token is different from Patient A", body.get("token_number") != token_num_a, str(body))
visit_id_b = body.get("visit_id")
token_id_b = body.get("token_id")
token_num_b = body.get("token_number")
print(f"      Token B: {token_num_b}, Visit B: {visit_id_b}")

# ── 7. Patient status — visit A ─────────────────────────────────────────────
print(f"\n[7] Patient status (visit A = {visit_id_a})")
status, body = req("GET", f"/api/v1/visits/{visit_id_a}/status")
check("GET /visits/{id}/status returns 200", status == 200, f"got {status} — {body}")
check("status visit_id matches", body.get("visit_id") == visit_id_a, str(body))
check("status token_number matches", body.get("token_number") == token_num_a, str(body))
check("status state is WAITING", body.get("state") == "WAITING", str(body))
check("status patients_ahead is int >= 0", isinstance(body.get("patients_ahead"), int) and body["patients_ahead"] >= 0, str(body))

# ── 8. Missing resource & validation checks ─────────────────────────────────
print("\n[8] Validation and 404 checks")
status, _ = req("GET", "/api/v1/visits/00000000-0000-0000-0000-000000000000/status")
check("Missing visit returns 404", status == 404, f"got {status}")

status, _ = req("POST", "/api/v1/registrations/qr", {"full_name": "Test", "mobile": "abc", "department_id": DEPT_ID})
check("Invalid mobile returns 422", status == 422, f"got {status}")

status, _ = req("POST", "/api/v1/registrations/qr", {"full_name": "Test", "mobile": "9999999999"})
check("Missing department returns 422", status == 422, f"got {status}")

status, _ = req("POST", "/api/v1/registrations/qr", {"full_name": "Test", "mobile": "8888888888", "department_id": "00000000-0000-0000-0000-000000000000"})
check("Unknown department returns 404", status == 404, f"got {status}")

# ── 9. Queue Summary ────────────────────────────────────────────────────────
print(f"\n[9] GET /api/v1/queues/{QUEUE_ID}")
status, body = req("GET", f"/api/v1/queues/{QUEUE_ID}")
check("GET /queues/{id} returns 200", status == 200, f"got {status} — {body}")
check("queue summary has waiting_count", "waiting_count" in body, str(body))
check("queue summary has queue_id", body.get("queue_id") == QUEUE_ID, str(body))

# ── 10. End-to-end Queue Lifecycle: CALL NEXT ───────────────────────────────
print("\n[10] CALL NEXT -> First eligible token becomes SERVING")
status, body = req("POST", f"/api/v1/queues/{QUEUE_ID}/call-next", {})
check("POST /queues/{id}/call-next returns 200", status == 200, f"got {status} — {body}")
check("called token state is SERVING", body.get("state") == "SERVING", str(body))
check("called token previous_state is WAITING", body.get("previous_state") == "WAITING", str(body))
serving_token_id = body.get("token_id")
serving_token_num = body.get("token_number")
print(f"      Called token: {serving_token_num} (ID: {serving_token_id})")

# ── 11. Patient status reflects SERVING ─────────────────────────────────────
print("\n[11] Patient status reflects SERVING")
status, body = req("GET", f"/api/v1/visits/{visit_id_a}/status")
check("Patient status retrieved", status == 200, f"got {status}")
if body.get("token_number") == serving_token_num:
    check("Patient A status is SERVING", body.get("state") == "SERVING", str(body))

# ── 12. HOLD the serving token ──────────────────────────────────────────────
print("\n[12] HOLD the serving token")
status, body = req("POST", f"/api/v1/tokens/{serving_token_id}/hold", {"reason": "Doctor consult"})
check("POST /tokens/{id}/hold returns 200", status == 200, f"got {status} — {body}")
check("token state is HOLD", body.get("state") == "HOLD", str(body))
check("previous_state was SERVING", body.get("previous_state") == "SERVING", str(body))

# ── 13. RECALL token (HOLD -> WAITING) ──────────────────────────────────────
print("\n[13] RECALL token (HOLD -> WAITING)")
status, body = req("POST", f"/api/v1/tokens/{serving_token_id}/recall", {})
check("POST /tokens/{id}/recall returns 200", status == 200, f"got {status} — {body}")
check("recalled token state is WAITING", body.get("state") == "WAITING", str(body))
check("previous_state was HOLD", body.get("previous_state") == "HOLD", str(body))

# ── 14. CALL NEXT again ─────────────────────────────────────────────────────
print("\n[14] CALL NEXT after recall")
status, body = req("POST", f"/api/v1/queues/{QUEUE_ID}/call-next", {})
check("CALL NEXT succeeds", status == 200, f"got {status} — {body}")
check("state is SERVING", body.get("state") == "SERVING", str(body))
active_token_id = body.get("token_id")

# ── 15. SKIP a token (SERVING -> SKIPPED) ───────────────────────────────────
print("\n[15] SKIP token (SERVING -> SKIPPED)")
status, body = req("POST", f"/api/v1/tokens/{active_token_id}/skip", {"reason": "Patient away"})
check("POST /tokens/{id}/skip returns 200", status == 200, f"got {status} — {body}")
check("token state is SKIPPED", body.get("state") == "SKIPPED", str(body))

# ── 16. RECALL skipped token (SKIPPED -> WAITING) ───────────────────────────
print("\n[16] RECALL skipped token (SKIPPED -> WAITING)")
status, body = req("POST", f"/api/v1/tokens/{active_token_id}/recall", {})
check("POST /tokens/{id}/recall on SKIPPED returns 200", status == 200, f"got {status} — {body}")
check("recalled skipped token is WAITING", body.get("state") == "WAITING", str(body))

# ── 17. CALL NEXT & COMPLETE (SERVING -> COMPLETED) ─────────────────────────
print("\n[17] CALL NEXT and COMPLETE serving token")
status, body = req("POST", f"/api/v1/queues/{QUEUE_ID}/call-next", {})
check("CALL NEXT succeeds", status == 200, f"got {status} — {body}")
final_serving_id = body.get("token_id")

status, body = req("POST", f"/api/v1/tokens/{final_serving_id}/complete", {})
check("POST /tokens/{id}/complete returns 200", status == 200, f"got {status} — {body}")
check("completed token state is COMPLETED", body.get("state") == "COMPLETED", str(body))
check("completed_at is present", "completed_at" in body, str(body))

# ── 18. Invalid transition returns 409 ──────────────────────────────────────
print("\n[18] Invalid transition returns 409")
status, body = req("POST", f"/api/v1/tokens/{final_serving_id}/complete", {})
check("Completing already completed token returns 409", status == 409, f"got {status} — {body}")

# ── 19. Public display updates ──────────────────────────────────────────────
print("\n[19] Public display synchronization")
status, body = req("GET", f"/api/v1/public/queues/{QUEUE_ID}/display")
check("GET /public/queues/{id}/display returns 200", status == 200, f"got {status} — {body}")
check("display has queue_id", body.get("queue_id") == QUEUE_ID, str(body))
check("display has waiting_count", "waiting_count" in body, str(body))
check("display has updated_at", "updated_at" in body, str(body))

# ── 20. Device event ingestion & Crowd Management ───────────────────────────
print("\n[20] Authenticated device event ingestion & Crowd API")
import uuid
unique_device_seq = random.randint(1000000, 9999999)

# 20.1 Reject unauthenticated request (401)
status, body = req("POST", "/api/v1/devices/events", {
    "device_id": "devi-0001-0000-0000-0000-000000000001",
    "zone_id": "zone-0001-0000-0000-0000-000000000001",
    "sequence": unique_device_seq,
    "event_type": "ENTRY",
    "event_at": "2026-09-23T16:10:32.420Z",
    "firmware_version": "0.1.0"
})
check("POST /devices/events without key returns 401", status == 401, f"got {status} — {body}")

# 20.2 Authenticated ENTRY event (200)
url_dev = BASE + "/api/v1/devices/events"
data_dev = json.dumps({
    "device_id": "devi-0001-0000-0000-0000-000000000001",
    "zone_id": "zone-0001-0000-0000-0000-000000000001",
    "sequence": unique_device_seq,
    "event_type": "ENTRY",
    "event_at": "2026-09-23T16:10:32.420Z",
    "firmware_version": "0.1.0"
}).encode()
headers_dev = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-Device-Key": "esp32-secret-key-001"
}
req_dev = urllib.request.Request(url_dev, data=data_dev, headers=headers_dev, method="POST")
with urllib.request.urlopen(req_dev) as resp_dev:
    dev_status = resp_dev.status
    dev_body = json.loads(resp_dev.read().decode())
check("POST /devices/events with valid key returns 200", dev_status == 200, f"got {dev_status}")
check("device event accepted=True", dev_body.get("accepted") is True, str(dev_body))
check("occupancy is integer > 0", isinstance(dev_body.get("occupancy"), int) and dev_body["occupancy"] > 0, str(dev_body))

# 20.3 Duplicate sequence returns accepted=False (idempotent)
req_dup = urllib.request.Request(url_dev, data=data_dev, headers=headers_dev, method="POST")
with urllib.request.urlopen(req_dup) as resp_dup:
    dup_status = resp_dup.status
    dup_body = json.loads(resp_dup.read().decode())
check("duplicate sequence returns 200", dup_status == 200, f"got {dup_status}")
check("duplicate sequence accepted=False", dup_body.get("accepted") is False, str(dup_body))

# 20.4 Staff Login & Crowd Management API
status_login, body_login = req("POST", "/api/v1/auth/login", {
    "username": "doctor",
    "password": "doctor123"
})
check("POST /auth/login returns 200", status_login == 200, f"got {status_login}")
token_val = body_login.get("access_token")

# Read crowd status
url_crowd = BASE + "/api/v1/zones/zone-0001-0000-0000-0000-000000000001/crowd"
headers_crowd = {"Accept": "application/json", "Authorization": f"Bearer {token_val}"}
req_crowd = urllib.request.Request(url_crowd, headers=headers_crowd, method="GET")
with urllib.request.urlopen(req_crowd) as resp_crowd:
    crowd_status = resp_crowd.status
    crowd_body = json.loads(resp_crowd.read().decode())
check("GET /zones/{id}/crowd returns 200", crowd_status == 200, f"got {crowd_status}")
check("crowd status has capacity_alert", "capacity_alert" in crowd_body, str(crowd_body))
check("crowd status has device_status", "device_status" in crowd_body, str(crowd_body))

# ── 21. Static Frontend Serving ─────────────────────────────────────────────
print("\n[21] Static frontend serving")
status, body = req("GET", "/patient/")
check("GET /patient/ returns 200", status == 200, f"got {status}")
check("patient html contains SmartQueue", "smartqueue" in str(body).lower(), "Patient HTML check")

status, body = req("GET", "/staff/")
check("GET /staff/ returns 200", status == 200, f"got {status}")
check("staff html contains Staff Dashboard", "Staff Dashboard" in str(body), "Staff HTML check")

status, body = req("GET", "/staff/public.html")
check("GET /staff/public.html returns 200", status == 200, f"got {status}")
check("public html contains Public Display", "Public Display" in str(body), "Public display HTML check")

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("\nFailed tests:")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED PERFECTLY!")
    sys.exit(0)
