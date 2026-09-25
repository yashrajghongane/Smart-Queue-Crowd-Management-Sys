# SmartQueue Agent Contract

## Architecture
- One central FastAPI backend.
- One source-of-truth database.
- Separate patient and staff frontends.
- Frontends use HTML + JavaScript + Tailwind CSS.
- No React, Vite, or shadcn/ui.
- ESP32 is a later milestone.

## Database
- SQLite for development.
- PostgreSQL for hosted deployment.
- DATABASE_URL controls the target database.
- SQLAlchemy/Alembic code must remain portable.
- No separate patient/staff databases.

## Document authority
- Document A is the technical contract.
- Preserve documented API paths, methods, JSON keys, schema, relationships, token states, and module ownership.
- Do not invent alternative API contracts.

## Backend ownership
- registration.py: registration routes only.
- queue.py: queue-level routes only.
- token.py: token action routes only.
- patient.py: patient status route only.
- public_display.py: public display route only.
- device.py: device ingestion route only.
- registration_service.py: Patient/Visit/Token creation and duplicate-active-visit rule.
- queue_service.py: all token transitions and CALL NEXT concurrency.
- occupancy_service.py: occupancy transitions/idempotency.
- display_service.py: read models only.
- repositories/: database access only.
- schemas/: validation/serialization only.
- core/config.py: configuration only.

## Git and quality
- Work on branches and integrate through PRs.
- Never force-push shared branches.
- Run the actual application and tests before claiming success.
- Browser-test important frontend flows.
- Never commit secrets or local databases.
