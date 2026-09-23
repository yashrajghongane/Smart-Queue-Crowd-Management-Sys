"""
seed.py

Development seed script — inserts the minimum data needed to exercise the API:
  - 1 Department: General Medicine
  - 1 Queue: prefix "GM", linked to the department
  - 1 Zone: General OPD Waiting Area (capacity alert thresholds are UNDECIDED per Doc A;
            placeholder demo values used here — must be reviewed before final demo config)
  - 1 Device: DEV-001 linked to the zone

Run once after 'alembic upgrade head':
    python seed.py

Safe to re-run — checks for existing records before inserting.
"""
import sys
import os

# ── Ensure backend/ is on path ────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from app.repositories.database import SessionLocal, engine, Base
from app.models.models import Department, Queue, Zone, Device, _new_uuid, _utcnow

# Fixed UUIDs for seed data — stable across re-runs.
# These match the example IDs referenced in Document A §2 examples.
DEPT_GM_ID   = "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
QUEUE_GM_ID  = "3d3f0f52-6b7a-4bb3-92cb-7f1f4d340301"
ZONE_001_ID  = "zone-0001-0000-0000-0000-000000000001"
DEVICE_001_ID = "devi-0001-0000-0000-0000-000000000001"


def seed():
    db = SessionLocal()
    try:
        # ── Department ──────────────────────────────────────────────────────
        dept = db.query(Department).filter(Department.id == DEPT_GM_ID).first()
        if dept is None:
            dept = Department(
                id=DEPT_GM_ID,
                name="General Medicine",
                active=True,
                created_at=_utcnow(),
            )
            db.add(dept)
            print("  [+] Department: General Medicine")
        else:
            print("  [=] Department already exists: General Medicine")

        # ── Queue ───────────────────────────────────────────────────────────
        queue = db.query(Queue).filter(Queue.id == QUEUE_GM_ID).first()
        if queue is None:
            queue = Queue(
                id=QUEUE_GM_ID,
                department_id=DEPT_GM_ID,
                name="General Medicine Queue",
                prefix="GM",
                active=True,
                created_at=_utcnow(),
            )
            db.add(queue)
            print("  [+] Queue: GM (General Medicine)")
        else:
            print("  [=] Queue already exists: GM")

        # ── Zone ────────────────────────────────────────────────────────────
        # UNDECIDED: capacity alert thresholds per Doc A §3.8.
        # Placeholder demo values below match the Workflow doc §16 worked example.
        # Review these before the final demo configuration.
        zone = db.query(Zone).filter(Zone.id == ZONE_001_ID).first()
        if zone is None:
            zone = Zone(
                id=ZONE_001_ID,
                name="General OPD Waiting Area",
                capacity=10,
                # UNDECIDED thresholds — demo placeholders only:
                moderate_threshold=6,
                high_threshold=8,
                critical_threshold=10,
                alert_enabled=True,
                created_at=_utcnow(),
            )
            db.add(zone)
            print("  [+] Zone: General OPD Waiting Area (capacity=10, thresholds UNDECIDED)")
        else:
            print("  [=] Zone already exists: General OPD Waiting Area")

        # ── Device ──────────────────────────────────────────────────────────
        device = db.query(Device).filter(Device.id == DEVICE_001_ID).first()
        if device is None:
            device = Device(
                id=DEVICE_001_ID,
                device_code="DEV-001",
                zone_id=ZONE_001_ID,
                firmware_version="0.1.0",
                active=True,
                last_seen_at=None,
                created_at=_utcnow(),
            )
            db.add(device)
            print("  [+] Device: DEV-001 -> ZONE-001")
        else:
            print("  [=] Device already exists: DEV-001")

        db.commit()
        print("\nSeed completed successfully.")

    except Exception as exc:
        db.rollback()
        print(f"\nSeed FAILED: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("SmartQueue — seeding development database...")
    print(f"Database: {os.path.abspath('smartqueue.db')}\n")
    seed()
