import sys
import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
DEPT_ID = "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
PASS = []
FAIL = []


def req(method, path, body=None, expect_status=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as resp:
            status = resp.status
            body_out = json.loads(resp.read())
            return status, body_out
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body_out = json.loads(e.read())
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
check("health body has status=ok", body.get("status") == "ok", str(body))

# ── 2. Root ──────────────────────────────────────────────────────────────────
print("\n[2] Root")
status, body = req("GET", "/")
check("GET / returns 200", status == 200, f"got {status}")

# ── 3. QR registration — new patient ────────────────────────────────────────
print("\n[3] QR registration (new patient)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Asha Patil",
    "mobile": "9876543210",
    "department_id": DEPT_ID,
})
check("POST /registrations/qr returns 201", status == 201, f"got {status} — {body}")
check("response has patient_id", "patient_id" in body, str(body))
check("response has visit_id",   "visit_id" in body, str(body))
check("response has token_id",   "token_id" in body, str(body))
check("response has token_number", "token_number" in body, str(body))
check("token_number starts with GM-", body.get("token_number", "").startswith("GM-"), str(body))
check("state is WAITING",        body.get("state") == "WAITING", str(body))
check("department_id correct",   body.get("department_id") == DEPT_ID, str(body))

visit_id_1 = body.get("visit_id")
token_number_1 = body.get("token_number")
print(f"      Token: {token_number_1}, Visit: {visit_id_1}")

# ── 4. Duplicate QR registration — same patient, same dept ──────────────────
print("\n[4] Duplicate QR registration (same patient + dept)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Asha Patil",
    "mobile": "9876543210",
    "department_id": DEPT_ID,
})
check("POST /registrations/qr duplicate returns 409", status == 409, f"got {status} — {body}")
detail = body.get("detail", body) # Update in script: if we return raw response, there might be no "detail" key. Let's check both
check("duplicate detail has error=ACTIVE_VISIT_EXISTS",
      detail.get("error") == "ACTIVE_VISIT_EXISTS", str(detail))
check("duplicate detail has visit_id", "visit_id" in detail, str(detail))
check("duplicate detail has token_number", "token_number" in detail, str(detail))
check("duplicate token_number matches first",
      detail.get("token_number") == token_number_1, str(detail))

# ── 5. Staff registration — different patient ────────────────────────────────
print("\n[5] Staff registration (different patient)")
status, body = req("POST", "/api/v1/registrations/staff", {
    "full_name": "Ramesh Jadhav",
    "mobile": "9123456789",
    "department_id": DEPT_ID,
})
check("POST /registrations/staff returns 201", status == 201, f"got {status} — {body}")
check("staff registration has token_number", "token_number" in body, str(body))
check("staff token is different from QR token",
      body.get("token_number") != token_number_1, str(body))
visit_id_2 = body.get("visit_id")
token_number_2 = body.get("token_number")
print(f"      Token: {token_number_2}, Visit: {visit_id_2}")

# ── 6. Patient status — visit 1 ─────────────────────────────────────────────
print(f"\n[6] Patient status (visit 1 = {visit_id_1})")
status, body = req("GET", f"/api/v1/visits/{visit_id_1}/status")
check("GET /visits/{id}/status returns 200", status == 200, f"got {status} — {body}")
check("status has visit_id",       body.get("visit_id") == visit_id_1, str(body))
check("status has token_number",   "token_number" in body, str(body))
check("status token_number correct", body.get("token_number") == token_number_1, str(body))
check("status has state",          "state" in body, str(body))
check("state is WAITING",          body.get("state") == "WAITING", str(body))
check("status has patients_ahead", "patients_ahead" in body, str(body))
check("patients_ahead is int >= 0", isinstance(body.get("patients_ahead"), int) and body["patients_ahead"] >= 0, str(body))
check("status has department_id",  body.get("department_id") == DEPT_ID, str(body))
check("status has updated_at",     "updated_at" in body, str(body))
print(f"      patients_ahead={body.get('patients_ahead')}, serving_token={body.get('serving_token')}")

# ── 7. Patient status — missing visit ───────────────────────────────────────
print("\n[7] Patient status (missing visit)")
status, body = req("GET", "/api/v1/visits/00000000-0000-0000-0000-000000000000/status")
check("GET /visits/{bad_id}/status returns 404", status == 404, f"got {status}")

# ── 8. Validation — invalid mobile ──────────────────────────────────────────
print("\n[8] Validation (bad mobile)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Test User",
    "mobile": "abc",
    "department_id": DEPT_ID,
})
check("Invalid mobile returns 422", status == 422, f"got {status}")

# ── 9. Validation — missing department ──────────────────────────────────────
print("\n[9] Validation (missing department field)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Test User",
    "mobile": "9999999999",
})
check("Missing department returns 422", status == 422, f"got {status}")

# ── 10. Unknown department ───────────────────────────────────────────────────
print("\n[10] Unknown department (404)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Test User",
    "mobile": "8888888888",
    "department_id": "00000000-0000-0000-0000-000000000000",
})
check("Unknown department returns 404", status == 404, f"got {status}")

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("\nFailed tests:")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("All tests passed!")
    sys.exit(0)
