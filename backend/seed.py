"""
seed.py

Development seed script — inserts the minimum data needed to exercise the API:
  - 1 Department: General Medicine
  - 1 Queue: prefix "GM", linked to the department
  - 1 Zone: General OPD Waiting Area (capacity alert thresholds are UNDECIDED per Doc A;
            placeholder demo values used here — must be reviewed before final demo config)
  - 1 Device: DEV-001 linked to the zone with credential_hash provisioned
  - Staff users: ADMIN, RECEPTION, DEPARTMENT_STAFF with hashed passwords

Run once after 'alembic upgrade head':
    python seed.py

Safe to re-run — checks for existing records before inserting.
"""
import sys
import os

# ── Ensure backend/ is on path ────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from app.repositories.database import SessionLocal, engine, Base
from app.models.models import Department, Queue, Zone, Device, StaffUser, _new_uuid, _utcnow
from app.core.security import hash_password, hash_device_credential

# Fixed UUIDs for seed data — stable across re-runs.
# These match the example IDs referenced in Document A §2 examples.
DEPT_GM_ID   = "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
QUEUE_GM_ID  = "3d3f0f52-6b7a-4bb3-92cb-7f1f4d340301"
ZONE_001_ID  = "a0000001-0000-4000-8000-000000000001"
DEVICE_001_ID = "b0000001-0000-4000-8000-000000000001"

STAFF_ADMIN_ID = "c0000001-0000-4000-8000-000000000001"
STAFF_RECEP_ID = "c0000002-0000-4000-8000-000000000001"
STAFF_DOCT_ID  = "c0000003-0000-4000-8000-000000000001"

DEFAULT_DEVICE_SECRET = "esp32-secret-key-001"


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
        zone = db.query(Zone).filter(Zone.id == ZONE_001_ID).first()
        if zone is None:
            zone = Zone(
                id=ZONE_001_ID,
                name="General OPD Waiting Area",
                capacity=10,
                current_occupancy=0,
                moderate_threshold=6,
                high_threshold=8,
                critical_threshold=10,
                alert_enabled=True,
                created_at=_utcnow(),
            )
            db.add(zone)
            print("  [+] Zone: General OPD Waiting Area (capacity=10)")
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
                credential_hash=hash_device_credential(DEFAULT_DEVICE_SECRET),
                last_sequence=0,
                active=True,
                last_seen_at=None,
                created_at=_utcnow(),
            )
            db.add(device)
            print(f"  [+] Device: DEV-001 -> ZONE-001 (secret: {DEFAULT_DEVICE_SECRET})")
        else:
            if not device.credential_hash:
                device.credential_hash = hash_device_credential(DEFAULT_DEVICE_SECRET)
                print(f"  [*] Device DEV-001 provisioned with default secret: {DEFAULT_DEVICE_SECRET}")
            else:
                print("  [=] Device already exists: DEV-001")

        # ── Staff Users ──────────────────────────────────────────────────────
        admin_user = db.query(StaffUser).filter(StaffUser.username == "admin").first()
        if admin_user is None:
            admin_user = StaffUser(
                id=STAFF_ADMIN_ID,
                username="admin",
                password_hash=hash_password("smartqueue-admin-2026"),
                display_name="System Administrator",
                role="ADMIN",
                active=True,
                created_at=_utcnow(),
            )
            db.add(admin_user)
            print("  [+] Staff User: admin (role: ADMIN, password: smartqueue-admin-2026)")
        else:
            print("  [=] Staff user 'admin' already exists")

        doctor_user = db.query(StaffUser).filter(StaffUser.username == "doctor").first()
        if doctor_user is None:
            doctor_user = StaffUser(
                id=STAFF_DOCT_ID,
                username="doctor",
                password_hash=hash_password("doctor123"),
                display_name="Dr. Sharma",
                role="DEPARTMENT_STAFF",
                active=True,
                created_at=_utcnow(),
            )
            db.add(doctor_user)
            print("  [+] Staff User: doctor (role: DEPARTMENT_STAFF, password: doctor123)")
        else:
            print("  [=] Staff user 'doctor' already exists")

        recep_user = db.query(StaffUser).filter(StaffUser.username == "reception").first()
        if recep_user is None:
            recep_user = StaffUser(
                id=STAFF_RECEP_ID,
                username="reception",
                password_hash=hash_password("reception123"),
                display_name="Front Desk Reception",
                role="RECEPTION",
                active=True,
                created_at=_utcnow(),
            )
            db.add(recep_user)
            print("  [+] Staff User: reception (role: RECEPTION, password: reception123)")
        else:
            print("  [=] Staff user 'reception' already exists")

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
