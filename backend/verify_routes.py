"""Verify token and queue stub routes exist at correct paths."""
import urllib.request, json, sys

BASE = "http://127.0.0.1:8000"
PASS, FAIL = [], []

def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    r = urllib.request.Request(BASE+path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {}

import urllib.error

def check(name, cond, detail=""):
    if cond: PASS.append(name); print(f"  PASS  {name}")
    else:    FAIL.append(name); print(f"  FAIL  {name}  ->  {detail}")

# Queue routes
status, _ = req("GET",  "/api/v1/queues/some-id")
check("GET /api/v1/queues/{id} is 501", status == 501, f"got {status}")

status, _ = req("POST", "/api/v1/queues/some-id/call-next")
check("POST /api/v1/queues/{id}/call-next is 501", status == 501, f"got {status}")

# Token routes — pass valid bodies so we get to the stub (not 422 validation error)
status, _ = req("POST", "/api/v1/tokens/some-id/hold", {"reason": None})
check("POST /api/v1/tokens/{id}/hold is 501", status == 501, f"got {status}")

status, _ = req("POST", "/api/v1/tokens/some-id/recall", {})
check("POST /api/v1/tokens/{id}/recall is 501", status == 501, f"got {status}")

status, _ = req("POST", "/api/v1/tokens/some-id/skip", {"reason": None})
check("POST /api/v1/tokens/{id}/skip is 501", status == 501, f"got {status}")

status, _ = req("POST", "/api/v1/tokens/some-id/complete", {})
check("POST /api/v1/tokens/{id}/complete is 501", status == 501, f"got {status}")

# /docs loads (OpenAPI)
status, _ = req("GET", "/openapi.json")
check("OpenAPI spec loads (200)", status == 200, f"got {status}")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(0 if not FAIL else 1)
