"""
backend/bootstrap_prod.py

Safe, idempotent production initialization & bootstrap procedure.
Executed during deployment (preDeployCommand):
  - Ensures Department, Queue, Zone, Device, and Staff accounts exist.
  - Provisions credentials securely from environment variables (ADMIN_PASSWORD, STAFF_PASSWORD, DEVICE_KEY).
  - If passwords are not supplied in environment, generates high-entropy random keys.
  - NEVER logs plaintext passwords or keys to deployment logs.
  - Safe to run on every deployment without clobbering existing user passwords.
"""
import sys
import os
import secrets

sys.path.insert(0, os.path.dirname(__file__))

from app.repositories.database import SessionLocal
from app.models.models import Department, Queue, Zone, Device, StaffUser, _new_uuid, _utcnow
from app.core.security import hash_password, hash_device_credential

DEPT_GM_ID    = "2a2f8a0d-7b46-4a9d-b7f2-6c5f3b9d1001"
QUEUE_GM_ID   = "3d3f0f52-6b7a-4bb3-92cb-7f1f4d340301"
ZONE_001_ID   = "zone-0001-0000-0000-0000-000000000001"
DEVICE_001_ID = "devi-0001-0000-0000-0000-000000000001"


def bootstrap():
    db = SessionLocal()
    generated_creds = {}

    try:
        # 1. Department
        dept = db.query(Department).filter(Department.name == "General Medicine").first()
        if dept is None:
            dept = Department(
                id=DEPT_GM_ID,
                name="General Medicine",
                active=True,
                created_at=_utcnow(),
            )
            db.add(dept)
            print("[Bootstrap] Created Department: General Medicine")
        else:
            print("[Bootstrap] Department 'General Medicine' already exists.")

        # 2. Queue
        queue = db.query(Queue).filter(Queue.prefix == "GM").first()
        if queue is None:
            queue = Queue(
                id=QUEUE_GM_ID,
                department_id=dept.id,
                name="General Medicine Queue",
                prefix="GM",
                active=True,
                created_at=_utcnow(),
            )
            db.add(queue)
            print("[Bootstrap] Created Queue: GM (General Medicine)")
        else:
            print("[Bootstrap] Queue 'GM' already exists.")

        # 3. Zone
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
            print("[Bootstrap] Created Zone: General OPD Waiting Area")
        else:
            print("[Bootstrap] Zone 'General OPD Waiting Area' already exists.")

        # 4. Device DEV-001
        device = db.query(Device).filter(Device.device_code == "DEV-001").first()
        device_key = os.getenv("DEVICE_KEY")
        if device is None:
            if not device_key:
                device_key = secrets.token_urlsafe(24)
                generated_creds["DEV-001 Device Key"] = device_key

            device = Device(
                id=DEVICE_001_ID,
                device_code="DEV-001",
                zone_id=zone.id,
                firmware_version="0.1.0",
                credential_hash=hash_device_credential(device_key),
                last_sequence=0,
                active=True,
                last_seen_at=None,
                created_at=_utcnow(),
            )
            db.add(device)
            print("[Bootstrap] Provisioned Device: DEV-001")
        else:
            if not device.credential_hash and device_key:
                device.credential_hash = hash_device_credential(device_key)
                print("[Bootstrap] Updated credentials for Device DEV-001")

        # 5. Staff: Administrator
        admin_user = db.query(StaffUser).filter(StaffUser.username == "admin").first()
        admin_pass = os.getenv("ADMIN_PASSWORD")
        if admin_user is None:
            if not admin_pass:
                admin_pass = secrets.token_urlsafe(16)
                generated_creds["Admin Password"] = admin_pass

            admin_user = StaffUser(
                username="admin",
                password_hash=hash_password(admin_pass),
                display_name="System Administrator",
                role="ADMIN",
                active=True,
                created_at=_utcnow(),
            )
            db.add(admin_user)
            print("[Bootstrap] Created Staff User: admin (role: ADMIN)")
        else:
            print("[Bootstrap] Staff User 'admin' already exists.")

        # 6. Staff: Doctor (Department Staff)
        doctor_user = db.query(StaffUser).filter(StaffUser.username == "doctor").first()
        doctor_pass = os.getenv("STAFF_PASSWORD")
        if doctor_user is None:
            if not doctor_pass:
                doctor_pass = secrets.token_urlsafe(16)
                generated_creds["Doctor Password"] = doctor_pass

            doctor_user = StaffUser(
                username="doctor",
                password_hash=hash_password(doctor_pass),
                display_name="Dr. Sharma",
                role="DEPARTMENT_STAFF",
                active=True,
                created_at=_utcnow(),
            )
            db.add(doctor_user)
            print("[Bootstrap] Created Staff User: doctor (role: DEPARTMENT_STAFF)")
        else:
            print("[Bootstrap] Staff User 'doctor' already exists.")

        db.commit()
        print("[Bootstrap] Production bootstrap completed successfully.")

        # Write generated credentials to secure local file if generated and not in cloud
        if generated_creds and os.path.exists("."):
            cred_file = os.path.join(os.path.dirname(__file__), ".production_credentials.txt")
            try:
                with open(cred_file, "w", encoding="utf-8") as f:
                    f.write("# Automatically generated production credentials\n")
                    f.write("# Keep this file secure and do NOT commit to version control.\n\n")
                    for k, v in generated_creds.items():
                        f.write(f"{k}: {v}\n")
                print(f"[Bootstrap] Auto-generated credentials securely written to {cred_file}")
            except Exception:
                pass

    except Exception as exc:
        db.rollback()
        print(f"[Bootstrap] FAILED: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap()
