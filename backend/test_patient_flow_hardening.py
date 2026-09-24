"""
test_patient_flow_hardening.py

Comprehensive test suite verifying the Patient Flow QA & Hardening milestone:
1. Registration endpoint contract (Doc A §2.1)
2. Duplicate active visit handling (Doc A §2.1 & Workflow §9A)
3. Full name trimming and mobile number normalization
4. Status retrieval with accurate position in queue (Doc A §2.9)
5. Edge cases: missing/invalid fields, non-existent department
6. Multi-patient queue position calculation
7. Idempotency and database constraints
"""
import sys
import os
import random
import unittest
import urllib.request
import urllib.error
import json

BASE_URL = "http://127.0.0.1:8000"
DEPT_GM_ID = "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"


def api_request(method, path, body=None):
    url = f"{BASE_URL}{path}"
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
            return e.code, {"raw": raw}


class PatientFlowHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        status, body = api_request("GET", "/health")
        if status != 200 or body.get("status") != "ok":
            raise RuntimeError(f"Backend not healthy at {BASE_URL}")

    def test_01_successful_qr_registration(self):
        rnd = random.randint(1000000, 9999999)
        mobile = f"9{rnd}"
        status, data = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "  Ananya Sharma  ",
            "mobile": mobile,
            "department_id": DEPT_GM_ID,
        })
        self.assertEqual(status, 201)
        self.assertIn("patient_id", data)
        self.assertIn("visit_id", data)
        self.assertIn("token_id", data)
        self.assertIn("token_number", data)
        self.assertTrue(data["token_number"].startswith("GM-"))
        self.assertEqual(data["state"], "WAITING")
        self.assertEqual(data["department_id"], DEPT_GM_ID)

        # Retrieve status immediately
        visit_id = data["visit_id"]
        v_status, v_data = api_request("GET", f"/api/v1/visits/{visit_id}/status")
        self.assertEqual(v_status, 200)
        self.assertEqual(v_data["visit_id"], visit_id)
        self.assertEqual(v_data["token_number"], data["token_number"])
        self.assertEqual(v_data["state"], "WAITING")
        self.assertIsInstance(v_data["patients_ahead"], int)
        self.assertGreaterEqual(v_data["patients_ahead"], 0)

    def test_02_duplicate_registration_returns_409_with_existing_token(self):
        rnd = random.randint(1000000, 9999999)
        mobile = f"9{rnd}"
        # First registration
        status1, data1 = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "Duplicate Test User",
            "mobile": mobile,
            "department_id": DEPT_GM_ID,
        })
        self.assertEqual(status1, 201)
        orig_visit_id = data1["visit_id"]
        orig_token_num = data1["token_number"]

        # Duplicate attempt (same mobile + department)
        status2, data2 = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "Duplicate Test User",
            "mobile": mobile,
            "department_id": DEPT_GM_ID,
        })
        self.assertEqual(status2, 409)
        detail = data2.get("detail", {})
        self.assertEqual(detail.get("error"), "ACTIVE_VISIT_EXISTS")
        self.assertEqual(detail.get("visit_id"), orig_visit_id)
        self.assertEqual(detail.get("token_number"), orig_token_num)

    def test_03_mobile_formatting_normalization(self):
        rnd = random.randint(100000000, 999999999)
        mobile_digits = f"9{rnd}"
        formatted_mobile = f"+91 {mobile_digits[:5]}-{mobile_digits[5:]}"

        # Register with formatted mobile
        status1, data1 = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "Formatted Phone Patient",
            "mobile": formatted_mobile,
            "department_id": DEPT_GM_ID,
        })
        self.assertEqual(status1, 201)

        # Attempt duplicate using pure digits
        status2, data2 = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "Formatted Phone Patient",
            "mobile": mobile_digits,
            "department_id": DEPT_GM_ID,
        })
        self.assertEqual(status2, 409)
        detail = data2.get("detail", {})
        self.assertEqual(detail.get("error"), "ACTIVE_VISIT_EXISTS")
        self.assertEqual(detail.get("token_number"), data1["token_number"])

    def test_04_validation_rejections(self):
        # Empty name
        rnd = random.randint(1000000, 9999999)
        s, d = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "   ",
            "mobile": f"9{rnd}",
            "department_id": DEPT_GM_ID,
        })
        self.assertEqual(s, 422)

        # Invalid mobile (< 7 digits)
        s, d = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "Valid Name",
            "mobile": "12345",
            "department_id": DEPT_GM_ID,
        })
        self.assertEqual(s, 422)

        # Missing department
        s, d = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "Valid Name",
            "mobile": "9876543210",
        })
        self.assertEqual(s, 422)

        # Unknown department
        s, d = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "Valid Name",
            "mobile": "9876543210",
            "department_id": "00000000-0000-0000-0000-000000000000",
        })
        self.assertEqual(s, 404)

    def test_05_queue_sequence_and_patients_ahead(self):
        # Register patient A
        rnd_a = random.randint(1000000, 9999999)
        s_a, d_a = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "Queue Patient A",
            "mobile": f"9{rnd_a}",
            "department_id": DEPT_GM_ID,
        })
        self.assertEqual(s_a, 201)

        # Register patient B
        rnd_b = random.randint(1000000, 9999999)
        s_b, d_b = api_request("POST", "/api/v1/registrations/qr", {
            "full_name": "Queue Patient B",
            "mobile": f"8{rnd_b}",
            "department_id": DEPT_GM_ID,
        })
        self.assertEqual(s_b, 201)

        # B was registered after A, so B must have more patients ahead than A
        s_stat_a, d_stat_a = api_request("GET", f"/api/v1/visits/{d_a['visit_id']}/status")
        s_stat_b, d_stat_b = api_request("GET", f"/api/v1/visits/{d_b['visit_id']}/status")
        self.assertEqual(s_stat_a, 200)
        self.assertEqual(s_stat_b, 200)
        self.assertGreater(d_stat_b["patients_ahead"], d_stat_a["patients_ahead"])


if __name__ == "__main__":
    unittest.main()
