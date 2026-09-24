# AGENTS.md

This file establishes the shared operating contract and coordination guidelines for all coding agents working on the SmartQueue repository.

## PROJECT ARCHITECTURE
- one FastAPI backend
- one source-of-truth database
- separate patient frontend and staff frontend
- HTML + JavaScript + Tailwind CSS
- no React
- no Vite
- no shadcn/ui
- ESP32 is a later milestone

## DATABASE
- SQLite development
- PostgreSQL hosted
- DATABASE_URL
- SQLAlchemy/Alembic database portability
- no separate patient/staff databases

## DOCUMENT AUTHORITY
- Document A is the technical contract
- exact API paths/methods/JSON/schema
- no invented contracts

## MODULE OWNERSHIP
- preserve the responsibilities defined in Document A
- ownership rule: `app/services/queue_service.py` is the sole owner of token transitions. `app/services/occupancy_service.py` is the sole owner of occupancy transitions.

## GIT
- work on branches
- small logical commits
- PR-based integration
- never commit secrets
- never silently rewrite architecture

## QUALITY
- tests required
- browser verification for frontend
- actual runtime verification
- no claiming success without running the system

## ENGINEERING EXECUTION PLAN

### 1. backend completion
- **objective**: Implement missing backend logic (e.g. queue transitions, occupancy tracking) based on Document A.
- **dependencies**: Document A, existing skeleton.
- **files/directories likely involved**: `backend/app/services/*`, `backend/app/api/*`, `backend/app/models/*`, `backend/app/schemas/*`
- **acceptance criteria**: All endpoints in Document A implemented and returning exact JSON contracts.
- **tests required**: Pytest unit/integration tests for API endpoints and services.
- **risks**: Race conditions in `call-next`, incorrect dependency on sensors for token state.

### 2. staff dashboard
- **objective**: Create staff frontend to manage queues and view separate occupancy.
- **dependencies**: backend completion.
- **files/directories likely involved**: `frontend-staff/*`
- **acceptance criteria**: Dashboard shows waiting/occupancy separately, staff can call/hold/skip/complete tokens.
- **tests required**: Browser verification, interaction tests.
- **risks**: Confusion between queue demand and physical occupancy.

### 3. public display
- **objective**: Build the public display showing serving/next tokens.
- **dependencies**: backend completion.
- **files/directories likely involved**: `frontend-staff/display.html` or similar, `backend/app/api/public_display.py`
- **acceptance criteria**: Display accurately reflects `call-next` events.
- **tests required**: Browser verification.
- **risks**: Stale state if not refreshed or polled properly.

### 4. patient final polish
- **objective**: Finalize the patient frontend UX/UI and status tracking.
- **dependencies**: backend completion.
- **files/directories likely involved**: `frontend-patient/*`
- **acceptance criteria**: Patients can register via QR/web and track status (WAITING, SERVING, etc.).
- **tests required**: Cross-browser manual testing, end-to-end flow.
- **risks**: UI inconsistencies.

### 5. integration and QA
- **objective**: Test the entire flow from registration to token completion.
- **dependencies**: Milestones 1-4.
- **files/directories likely involved**: Whole system.
- **acceptance criteria**: Full workflow matches `Workflow & Behavior Document`.
- **tests required**: E2E runtime verification, manual checklist (Section 3 of Document B).
- **risks**: Unhandled edge cases, hardware/software sync issues.

### 6. PostgreSQL/hosting
- **objective**: Transition backend from SQLite to PostgreSQL and host.
- **dependencies**: backend completion.
- **files/directories likely involved**: `backend/.env`, hosting configurations, `backend/app/core/config.py`
- **acceptance criteria**: App runs successfully against PostgreSQL.
- **tests required**: DB schema migration tests.
- **risks**: Alembic portability issues, missing env variables.

### 7. final demo readiness
- **objective**: Prepare the demo-day script flow.
- **dependencies**: Milestones 1-6.
- **files/directories likely involved**: Docs, demo scripts.
- **acceptance criteria**: System operates flawlessly under demo conditions.
- **tests required**: Full demo run-through.
- **risks**: Demo effect, unpredicted user input.

### 8. ESP32 later
- **objective**: Integrate actual ESP32 hardware sensing.
- **dependencies**: Backend endpoint `/api/v1/devices/events` completion.
- **files/directories likely involved**: Hardware firmware, `Document B`.
- **acceptance criteria**: ESP32 successfully POSTs ENTRY/EXIT events updating occupancy.
- **tests required**: Hardware-in-the-loop tests, Sensor A/B detection checks.
- **risks**: Sensor reliability, ambiguous movements.
