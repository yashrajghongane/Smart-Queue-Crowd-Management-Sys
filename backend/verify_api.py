"""
verify_api.py  (updated)

Smoke-test script for the SmartQueue backend API.
Uses unique mobile numbers per run so tests are idempotent against a live DB.
"""
import sys
import json
import urllib.request
import urllib.error
import time
import uuid

BASE = "http://127.0.0.1:8000"
DEPT_ID = "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
PASS = []
FAIL = []

# Use a unique numeric suffix per run so we never hit duplicate-visit on repeated runs.
# Must be all-digit to pass mobile validation.
import random
_rand = random.randint(1000000, 9999999)
MOBILE_QR    = f"9{_rand:07d}"  # e.g. 91234567
MOBILE_STAFF = f"8{_rand:07d}"  # different first digit, same uniqueness


def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"  PASS  {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL  {name}" + (f"  ->  {detail}" if detail else ""))


print(f"\nQR mobile: {MOBILE_QR}  |  Staff mobile: {MOBILE_STAFF}")

# ── 1. Health ─────────────────────────────────────────────────────────────────
print("\n[1] Health check")
status, body = req("GET", "/health")
check("GET /health returns 200", status == 200, f"got {status}")
check("health body status=ok", body.get("status") == "ok", str(body))

# ── 2. Root ───────────────────────────────────────────────────────────────────
print("\n[2] Root endpoint")
status, body = req("GET", "/")
check("GET / returns 200", status == 200, f"got {status}")

# ── 3. QR registration — fresh patient ───────────────────────────────────────
print("\n[3] QR registration (new patient)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Test Patient QR",
    "mobile": MOBILE_QR,
    "department_id": DEPT_ID,
})
check("POST /registrations/qr returns 201", status == 201, f"got {status} -- {body}")
check("response has patient_id",    "patient_id" in body, str(body))
check("response has visit_id",      "visit_id" in body, str(body))
check("response has token_id",      "token_id" in body, str(body))
check("response has token_number",  "token_number" in body, str(body))
check("token_number starts with GM-", str(body.get("token_number","")).startswith("GM-"), str(body))
check("state is WAITING",           body.get("state") == "WAITING", str(body))
check("department_id correct",      body.get("department_id") == DEPT_ID, str(body))

visit_id_1    = body.get("visit_id")
token_number_1 = body.get("token_number")
print(f"      Token: {token_number_1}, Visit: {visit_id_1}")

# ── 4. Duplicate QR registration ──────────────────────────────────────────────
print("\n[4] Duplicate QR registration (same mobile + dept)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Test Patient QR",
    "mobile": MOBILE_QR,
    "department_id": DEPT_ID,
})
check("duplicate returns 409", status == 409, f"got {status}")
detail = body.get("detail", {})
check("detail.error = ACTIVE_VISIT_EXISTS", detail.get("error") == "ACTIVE_VISIT_EXISTS", str(detail))
check("detail has visit_id",     "visit_id" in detail, str(detail))
check("detail has token_id",     "token_id" in detail, str(detail))
check("detail has token_number", "token_number" in detail, str(detail))
check("duplicate token_number matches first", detail.get("token_number") == token_number_1, str(detail))

# ── 5. Staff registration — different patient ─────────────────────────────────
print("\n[5] Staff registration (different patient)")
status, body = req("POST", "/api/v1/registrations/staff", {
    "full_name": "Test Patient Staff",
    "mobile": MOBILE_STAFF,
    "department_id": DEPT_ID,
})
check("POST /registrations/staff returns 201", status == 201, f"got {status} -- {body}")
check("staff response has token_number", "token_number" in body, str(body))
check("staff token differs from QR token", body.get("token_number") != token_number_1, str(body))
visit_id_2    = body.get("visit_id")
token_number_2 = body.get("token_number")
print(f"      Token: {token_number_2}, Visit: {visit_id_2}")

# ── 6. Patient status — visit 1 ───────────────────────────────────────────────
print(f"\n[6] Patient status (visit 1 = {visit_id_1})")
status, body = req("GET", f"/api/v1/visits/{visit_id_1}/status")
check("GET /visits/{id}/status returns 200", status == 200, f"got {status} -- {body}")
check("status.visit_id correct",    body.get("visit_id") == visit_id_1, str(body))
check("status.token_number correct",body.get("token_number") == token_number_1, str(body))
check("status.state = WAITING",     body.get("state") == "WAITING", str(body))
check("status.patients_ahead >=0",  isinstance(body.get("patients_ahead"), int) and body["patients_ahead"] >= 0, str(body))
check("status.department_id correct",body.get("department_id") == DEPT_ID, str(body))
check("status.updated_at present",  "updated_at" in body, str(body))
print(f"      patients_ahead={body.get('patients_ahead')}, serving_token={body.get('serving_token')}")

# ── 7. Patient status — visit 2 (staff-registered) ───────────────────────────
print(f"\n[7] Patient status (visit 2 staff = {visit_id_2})")
status, body = req("GET", f"/api/v1/visits/{visit_id_2}/status")
check("staff visit status returns 200", status == 200, f"got {status} -- {body}")
check("staff visit token_number correct", body.get("token_number") == token_number_2, str(body))

# ── 8. Patient status — missing visit ─────────────────────────────────────────
print("\n[8] Patient status (missing visit)")
status, body = req("GET", "/api/v1/visits/00000000-0000-0000-0000-000000000000/status")
check("missing visit returns 404", status == 404, f"got {status}")

# ── 9. Validation — invalid mobile ────────────────────────────────────────────
print("\n[9] Validation (bad mobile — too short)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Test",
    "mobile": "abc",
    "department_id": DEPT_ID,
})
check("bad mobile returns 422", status == 422, f"got {status}")

# ── 10. Validation — empty name ────────────────────────────────────────────────
print("\n[10] Validation (empty name)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "",
    "mobile": "9999999999",
    "department_id": DEPT_ID,
})
check("empty name returns 422", status == 422, f"got {status}")

# ── 11. Validation — missing department ───────────────────────────────────────
print("\n[11] Validation (missing department field)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Test",
    "mobile": "9999999999",
})
check("missing department returns 422", status == 422, f"got {status}")

# ── 12. Unknown department ────────────────────────────────────────────────────
print("\n[12] Unknown department (404)")
status, body = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Test",
    "mobile": "7777777777",
    "department_id": "00000000-0000-0000-0000-000000000000",
})
check("unknown dept returns 404", status == 404, f"got {status}")

# ── 13. Mobile normalisation — same digits different formatting ───────────────
print("\n[13] Mobile normalisation (spaces/dashes stripped)")
_rand2 = random.randint(10000000, 99999999)
mobile_digits    = f"77{_rand2}"
mobile_formatted = f"77 {str(_rand2)[:4]}-{str(_rand2)[4:]}"  # same digits, formatted
status1, body1 = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Formatted Mobile Test",
    "mobile": mobile_formatted,
    "department_id": DEPT_ID,
})
check("formatted mobile registers OK", status1 == 201, f"got {status1} -- {body1}")
# Same digits again → should get 409
status2, body2 = req("POST", "/api/v1/registrations/qr", {
    "full_name": "Formatted Mobile Test",
    "mobile": mobile_digits,
    "department_id": DEPT_ID,
})
check("same digits different format = duplicate 409", status2 == 409, f"got {status2}")

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("\nFailed tests:")
    for f in FAIL:
        print(f"  x {f}")
    sys.exit(1)
else:
    print("All tests passed!")
    sys.exit(0)
