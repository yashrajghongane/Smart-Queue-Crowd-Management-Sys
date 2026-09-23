"""
app/repositories/patient_repository.py

Database read/write operations for the Patient table.
No business logic or state-transition decisions here.
"""
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import Patient, _new_uuid, _utcnow


class PatientRepository:
    """Encapsulates all Patient table operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def find_by_mobile(self, mobile: str) -> Optional[Patient]:
        """Return the patient with the given normalised mobile number, or None."""
        return self.db.query(Patient).filter(Patient.mobile == mobile).first()

    def find_by_id(self, patient_id: str) -> Optional[Patient]:
        """Return patient by primary key, or None."""
        return self.db.query(Patient).filter(Patient.id == patient_id).first()

    def create(self, full_name: str, mobile: str) -> Patient:
        """
        Insert a new Patient row.
        Caller is responsible for calling db.commit() after all related inserts.
        """
        patient = Patient(
            id=_new_uuid(),
            full_name=full_name,
            mobile=mobile,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.db.add(patient)
        self.db.flush()  # Populate id without committing the transaction
        return patient
