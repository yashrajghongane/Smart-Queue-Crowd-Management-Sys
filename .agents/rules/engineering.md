# SmartQueue — Engineering Rules

## Authority
The following documents are the source of truth. Code must implement them, not redefine them.
1. `Workflow & Behavior Document.md`
2. `Document_A_System_Software_Specification.md`
3. `Document_B_Hardware_Operations_Specification.md`

## What you must not do
- Rename documented API endpoints
- Change documented HTTP methods or response codes
- Change documented JSON request/response keys
- Invent database fields not in Doc A
- Remove documented fields
- Change documented token states (WAITING, SERVING, HOLD, SKIPPED, COMPLETED)
- Move queue-state logic out of `queue_service.py`
- Move occupancy logic out of `occupancy_service.py`
- Put business logic inside route handlers
- Put database logic randomly inside service or schema modules
- Duplicate registration logic between QR and staff flows
- Create a second independent backend
- Create ESP32/sensor code before the hardware milestone

## Module ownership (Doc A §5 — non-negotiable)
- `app/main.py` — startup, routers, /health only
- `app/api/registration.py` — registration routes only
- `app/api/queue.py` — queue-action routes only
- `app/api/patient.py` — patient status route only
- `app/api/public_display.py` — public display route only
- `app/api/device.py` — device ingestion only
- `app/services/registration_service.py` — SOLE owner of patient/visit/token creation
- `app/services/queue_service.py` — SOLE owner of token state transitions
- `app/services/occupancy_service.py` — SOLE owner of occupancy transitions (hardware milestone)
- `app/services/display_service.py` — read-only views, no state changes
- `app/models/` — ORM models only
- `app/repositories/` — DB reads/writes only
- `app/schemas/` — validation models only
- `app/core/config.py` — configuration only

## Before editing existing code
- Read the file and understand its responsibility
- Identify the authoritative module for the change
- Do not duplicate existing logic

## Git discipline
- Never commit: .venv/, smartqueue.db, __pycache__, *.pyc, .env, node_modules/
- Commit per logical milestone, not per file
- Do not push broken work

## Hardware milestone deferral
- Do not implement ESP32 firmware until the hardware milestone
- Do not implement occupancy_service logic until the hardware milestone
- device.py routes remain stubs until the hardware milestone

## Testing requirement
- Important behavior must be tested, not merely generated
- Run the server and verify real HTTP responses before claiming a feature works

## Undecided values
- Capacity alert thresholds (Zone.moderate/high/critical_threshold) are UNDECIDED per Doc A §3.8
- Placeholder demo values in seed.py must be reviewed before the final demo configuration
- Do not hardcode threshold values in application logic; always read from Zone configuration
