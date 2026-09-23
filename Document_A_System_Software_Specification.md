# Document A — System & Software Specification

## 0. Scope and reference

This document is the technical contract for the software/system implementation.

**Behavior source of truth:** `Workflow & Behavior Document` already completed. This document implements that behavior and does not redefine it.

**Frozen decisions:**
- Physical sensing: 1 ESP32 + 2 wired IR sensors at one waiting-area doorway.
- Occupancy is always separate from digital queue count.
- Capacity alert levels: `NORMAL`, `MODERATE`, `HIGH`, `CRITICAL`.
- Demo power: ESP32 powered from USB/power bank.
- No MT3608 in the demo.
- Backend: FastAPI + SQLite for development; PostgreSQL when hosted.

---

## 1. Architecture

```text
 Patient Web / QR        Staff Web / Mobile        ESP32 Sensor Device
        │                       │                         │
        └───────────────┬───────┴─────────────────────────┘
                        │
                        ▼
                ┌─────────────────┐
                │     FastAPI     │
                │                 │
                │ Registration    │
                │ Queue Service   │
                │ Occupancy       │
                │ Public Display  │
                └────────┬────────┘
                         │
                ┌────────┴────────┐
                │                 │
                ▼                 ▼
          SQLite (dev)     PostgreSQL (hosted)
                │                 │
                └────────┬────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
        Staff Dashboard  Patient   Public Display
                         Status
```

---

## 2. API contract

### Common response rules

| Item | Contract |
|---|---|
| Content type | `application/json` |
| Date/time format | ISO-8601 UTC, e.g. `2026-09-23T16:10:32.420Z` |
| IDs | UUID strings |
| Token states | `WAITING`, `SERVING`, `HOLD`, `SKIPPED`, `COMPLETED` |
| Action | `RECALL` is an action, not a persistent state |
| Queue action errors | HTTP `409` when the requested transition is not valid for current state |
| Validation errors | HTTP `422` |
| Missing resource | HTTP `404` |

### 2.1 QR registration

**POST** `/api/v1/registrations/qr`

Request:

```json
{
  "full_name": "Asha Patil",
  "mobile": "9876543210",
  "department_id": "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
}
```

Response `201`:

```json
{
  "patient_id": "6e13b8b2-4d8f-4b95-8737-6a9a6e7c0101",
  "visit_id": "7b1c9d60-7c19-4b4a-8e2c-c7c2cc120102",
  "token_id": "8c7b9d71-6d20-4c5b-9f3d-d8d3dd230203",
  "token_number": "GM-104",
  "state": "WAITING",
  "department_id": "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
}
```

Duplicate active registration response `409`:

```json
{
  "error": "ACTIVE_VISIT_EXISTS",
  "message": "An active visit already exists for this patient and department.",
  "visit_id": "7b1c9d60-7c19-4b4a-8e2c-c7c2cc120102",
  "token_id": "8c7b9d71-6d20-4c5b-9f3d-d8d3dd230203",
  "token_number": "GM-104"
}
```

### 2.2 Staff-assisted registration

**POST** `/api/v1/registrations/staff`

Request:

```json
{
  "full_name": "Ramesh Jadhav",
  "mobile": "9123456789",
  "department_id": "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
}
```

Response `201`: same response structure as QR registration, with a newly created Patient/Visit/Token when no active visit exists.

Duplicate active registration: same `409 ACTIVE_VISIT_EXISTS` contract as QR registration.

### 2.3 Queue summary for staff dashboard

**GET** `/api/v1/queues/{queue_id}`

Response `200`:

```json
{
  "queue_id": "3d3f0f52-6b7a-4bb3-92cb-7f1f4d340301",
  "department_id": "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001",
  "waiting_count": 7,
  "serving_token": "GM-104",
  "serving_token_id": "8c7b9d71-6d20-4c5b-9f3d-d8d3dd230203",
  "updated_at": "2026-09-23T16:10:32.420Z"
}
```

### 2.4 Call next

**POST** `/api/v1/queues/{queue_id}/call-next`

Request:

```json
{}
```

Response `200`:

```json
{
  "token_id": "8c7b9d71-6d20-4c5b-9f3d-d8d3dd230203",
  "token_number": "GM-104",
  "previous_state": "WAITING",
  "state": "SERVING",
  "called_at": "2026-09-23T16:10:32.420Z"
}
```

No eligible token response `409`:

```json
{
  "error": "NO_WAITING_TOKENS",
  "message": "No eligible waiting token is available."
}
```

**Concurrency rule:** the database transaction must select and update exactly one eligible `WAITING` token atomically. Two simultaneous requests cannot select the same token.

### 2.5 Hold

**POST** `/api/v1/tokens/{token_id}/hold`

Request:

```json
{
  "reason": "Patient temporarily unavailable"
}
```

Response `200`:

```json
{
  "token_id": "8c7b9d71-6d20-4c5b-9f3d-d8d3dd230203",
  "previous_state": "SERVING",
  "state": "HOLD"
}
```

Valid source states: `WAITING`, `SERVING`.

### 2.6 Recall

**POST** `/api/v1/tokens/{token_id}/recall`

Request:

```json
{}
```

Response `200`:

```json
{
  "token_id": "8c7b9d71-6d20-4c5b-9f3d-d8d3dd230203",
  "previous_state": "HOLD",
  "state": "WAITING"
}
```

Rules:
- `HOLD → WAITING`
- `SKIPPED → WAITING`
- `SERVING → SERVING` when recalling the same patient for another call.

### 2.7 Skip

**POST** `/api/v1/tokens/{token_id}/skip`

Request:

```json
{
  "reason": "Patient did not appear"
}
```

Response `200`:

```json
{
  "token_id": "8c7b9d71-6d20-4c5b-9f3d-d8d3dd230203",
  "previous_state": "WAITING",
  "state": "SKIPPED"
}
```

Valid source states: `WAITING`, `SERVING`, `HOLD`.

### 2.8 Complete

**POST** `/api/v1/tokens/{token_id}/complete`

Request:

```json
{}
```

Response `200`:

```json
{
  "token_id": "8c7b9d71-6d20-4c5b-9f3d-d8d3dd230203",
  "previous_state": "SERVING",
  "state": "COMPLETED",
  "completed_at": "2026-09-23T16:15:12.420Z"
}
```

Valid source state: `SERVING` only.

### 2.9 Patient status

**GET** `/api/v1/visits/{visit_id}/status`

Response `200`:

```json
{
  "visit_id": "7b1c9d60-7c19-4b4a-8e2c-c7c2cc120102",
  "token_number": "GM-104",
  "state": "WAITING",
  "patients_ahead": 4,
  "serving_token": "GM-100",
  "department_id": "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001",
  "updated_at": "2026-09-23T16:10:32.420Z"
}
```

### 2.10 Zone occupancy for staff dashboard

**GET** `/api/v1/zones/{zone_id}/occupancy`

Response `200`:

```json
{
  "zone_id": "ZONE-001",
  "occupancy": 8,
  "capacity": 10,
  "capacity_alert": "HIGH",
  "updated_at": "2026-09-23T16:10:32.420Z"
}
```

This endpoint is read-only. It never changes queue/token state.

### 2.10 Public display

**GET** `/api/v1/public/queues/{queue_id}/display`

Response `200`:

```json
{
  "queue_id": "3d3f0f52-6b7a-4bb3-92cb-7f1f4d340301",
  "serving_token": "GM-104",
  "next_token": "GM-105",
  "waiting_count": 7,
  "updated_at": "2026-09-23T16:10:32.420Z"
}
```

### 2.11 Device event ingestion

**POST** `/api/v1/devices/events`

Request JSON is the exact contract used by the ESP32:

```json
{
  "device_id": "DEV-001",
  "zone_id": "ZONE-001",
  "sequence": 123,
  "event_type": "ENTRY",
  "event_at": "2026-09-23T16:10:32.420Z",
  "firmware_version": "0.1.0"
}
```

Allowed `event_type`: `ENTRY`, `EXIT`.

Response `200`:

```json
{
  "device_id": "DEV-001",
  "zone_id": "ZONE-001",
  "sequence": 123,
  "accepted": true,
  "event_type": "ENTRY",
  "occupancy": 8,
  "capacity_alert": "HIGH",
  "processed_at": "2026-09-23T16:10:32.470Z"
}
```

Duplicate sequence response `200`:

```json
{
  "device_id": "DEV-001",
  "zone_id": "ZONE-001",
  "sequence": 123,
  "accepted": false,
  "event_type": "ENTRY",
  "occupancy": 8,
  "capacity_alert": "HIGH",
  "processed_at": "2026-09-23T16:10:32.470Z"
}
```

**Idempotency rule:** `(device_id, sequence)` is unique. A repeated event must not change occupancy twice.

**Undecided value:** numeric thresholds for `NORMAL/MODERATE/HIGH/CRITICAL` are not yet fixed. The Zone configuration must hold them; application code must not hard-code them.

---

## 3. Database schema

The same logical schema is used in SQLite and PostgreSQL. Use UUID-as-text in SQLite and UUID in PostgreSQL; timestamps are stored as UTC.

### 3.1 Department

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | Department identifier |
| name | VARCHAR(100) | UNIQUE | e.g. General Medicine |
| active | BOOLEAN | | |
| created_at | TIMESTAMP | | UTC |

### 3.2 Queue

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | Queue identifier |
| department_id | UUID | FK → Department.id | |
| name | VARCHAR(100) | | Display name |
| prefix | VARCHAR(10) | UNIQUE | e.g. GM |
| active | BOOLEAN | | |
| created_at | TIMESTAMP | | UTC |

### 3.3 Patient

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | |
| full_name | VARCHAR(150) | | |
| mobile | VARCHAR(15) | | Normalized digits |
| created_at | TIMESTAMP | | UTC |
| updated_at | TIMESTAMP | | UTC |

### 3.4 Visit

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | |
| patient_id | UUID | FK → Patient.id | |
| department_id | UUID | FK → Department.id | |
| queue_id | UUID | FK → Queue.id | |
| registration_source | VARCHAR(20) | | `QR` or `STAFF` |
| visit_date | DATE | | Local clinic date |
| created_at | TIMESTAMP | | UTC |
| closed_at | TIMESTAMP NULL | | Set when visit reaches terminal handling |

### 3.5 Token

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | |
| visit_id | UUID | FK → Visit.id, UNIQUE | One active token record per visit |
| queue_id | UUID | FK → Queue.id | |
| token_number | VARCHAR(20) | UNIQUE | e.g. `GM-104` |
| sequence_number | INTEGER | | Numeric order inside queue/date |
| state | VARCHAR(20) | | WAITING/SERVING/HOLD/SKIPPED/COMPLETED |
| created_at | TIMESTAMP | | UTC |
| called_at | TIMESTAMP NULL | | |
| completed_at | TIMESTAMP NULL | | |
| updated_at | TIMESTAMP | | UTC |

Required uniqueness: `(queue_id, visit_date, sequence_number)`; token_number is unique within the active deployment.

### 3.6 QueueEvent

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | |
| token_id | UUID | FK → Token.id | |
| event_type | VARCHAR(30) | | `CREATED`, `CALL_NEXT`, `HOLD`, `RECALL`, `SKIP`, `COMPLETE` |
| from_state | VARCHAR(20) NULL | | |
| to_state | VARCHAR(20) | | |
| actor_type | VARCHAR(20) | | `PATIENT`, `STAFF`, `SYSTEM` |
| actor_id | UUID NULL | FK → StaffUser.id when actor_type = STAFF | |
| reason | VARCHAR(255) NULL | | Optional action reason |
| created_at | TIMESTAMP | | UTC |

### 3.7 StaffUser

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | |
| display_name | VARCHAR(100) | | |
| role | VARCHAR(30) | | `RECEPTION`, `DEPARTMENT_STAFF`, `ADMIN` |
| active | BOOLEAN | | |
| created_at | TIMESTAMP | | UTC |

### 3.8 Zone

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | |
| name | VARCHAR(100) | | e.g. General OPD Waiting Area |
| capacity | INTEGER | | Physical capacity |
| moderate_threshold | INTEGER NULL | | **UNDECIDED** until validated |
| high_threshold | INTEGER NULL | | **UNDECIDED** until validated |
| critical_threshold | INTEGER NULL | | **UNDECIDED** until validated |
| alert_enabled | BOOLEAN | | |
| created_at | TIMESTAMP | | UTC |

`NORMAL` is the range below the configured moderate threshold. `MODERATE/HIGH/CRITICAL` thresholds are deployment configuration, not sensor logic.

### 3.9 Device

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | |
| device_code | VARCHAR(30) | UNIQUE | e.g. `DEV-001` |
| zone_id | UUID | FK → Zone.id | One device monitors one zone |
| firmware_version | VARCHAR(30) | | |
| active | BOOLEAN | | |
| last_seen_at | TIMESTAMP NULL | | UTC |
| created_at | TIMESTAMP | | UTC |

### 3.10 OccupancyEvent

| Field | Type | Key | Notes |
|---|---|---|---|
| id | UUID | PK | |
| device_id | UUID | FK → Device.id | |
| zone_id | UUID | FK → Zone.id | |
| sequence | INTEGER | | Unique per device |
| event_type | VARCHAR(10) | | `ENTRY` or `EXIT` |
| event_at | TIMESTAMP | | Device event time, UTC |
| occupancy_after | INTEGER | | Occupancy after event |
| capacity_alert | VARCHAR(20) | | NORMAL/MODERATE/HIGH/CRITICAL |
| firmware_version | VARCHAR(30) | | |
| received_at | TIMESTAMP | | Server receive time, UTC |

Required uniqueness: `(device_id, sequence)`.

---

## 4. Relationships

```text
Department 1 ─── N Queue
Department 1 ─── N Visit
Patient    1 ─── N Visit
Queue      1 ─── N Token
Visit      1 ─── 1 Token
Token      1 ─── N QueueEvent
StaffUser  1 ─── N QueueEvent
Zone       1 ─── N Device
Zone       1 ─── N OccupancyEvent
Device     1 ─── N OccupancyEvent
```

---

## 5. Backend module map

| Module/file | Owns |
|---|---|
| `app/main.py` | FastAPI application startup, router registration, health endpoint only |
| `app/api/registration.py` | QR and staff-assisted registration routes only |
| `app/api/queue.py` | Staff queue-action routes only |
| `app/api/patient.py` | Patient status route only |
| `app/api/public_display.py` | Public display route only |
| `app/api/device.py` | Device event-ingestion route only |
| `app/services/registration_service.py` | Patient lookup/create, duplicate-active-visit rule, Visit/Token creation |
| `app/services/queue_service.py` | **All token state transitions and CALL NEXT concurrency logic** |
| `app/services/occupancy_service.py` | ENTRY/EXIT validation, occupancy update, capacity-alert calculation, idempotency |
| `app/services/display_service.py` | Staff/public read models; no state changes |
| `app/models/` | ORM models only; no business rules |
| `app/repositories/` | Database reads/writes only; no state-transition decisions |
| `app/schemas/` | Request/response validation models only |
| `app/core/config.py` | Environment/configuration only |

**Ownership rule:** no route may implement queue-state logic directly. `queue_service.py` is the sole owner of token transitions. `occupancy_service.py` is the sole owner of occupancy transitions.
