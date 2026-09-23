"""
app/services/registration_service.py

Patient and visit registration — the authoritative business logic for creating
Patient / Visit / Token records.

Ownership (Doc A §5):
  - patient lookup/create
  - duplicate active-visit rule
  - Visit creation
  - Token creation

Both the QR and staff-assisted registration endpoints converge here.
No registration logic exists anywhere else in the codebase.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.models import Department, Queue, QueueEvent, _new_uuid, _utcnow
from app.repositories.patient_repository import PatientRepository
from app.repositories.visit_repository import VisitRepository
from app.repositories.token_repository import TokenRepository


class RegistrationService:
    """
    Handles the complete registration flow for a patient.
    Used by both QR and staff-assisted registration routes.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._patients = PatientRepository(db)
        self._visits = VisitRepository(db)
        self._tokens = TokenRepository(db)

    def register(
        self,
        full_name: str,
        mobile: str,
        department_id: str,
        source: str,  # "QR" or "STAFF"
    ) -> tuple[bool, dict]:
        """
        Register a patient for a department.

        Returns:
            (is_duplicate, data)

            If is_duplicate is True:
                data contains {visit_id, token_id, token_number} of the existing active visit.
                The caller must return HTTP 409.

            If is_duplicate is False:
                data contains {patient_id, visit_id, token_id, token_number, state, department_id}.
                The caller must return HTTP 201.

        Raises:
            ValueError: if department or queue is not found/active.
        """
        # ── 1. Validate department ──────────────────────────────────────────────
        department = (
            self.db.query(Department)
            .filter(Department.id == department_id, Department.active.is_(True))
            .first()
        )
        if department is None:
            raise ValueError(f"Department '{department_id}' not found or not active.")

        # ── 2. Find the active queue for this department ────────────────────────
        queue = (
            self.db.query(Queue)
            .filter(Queue.department_id == department_id, Queue.active.is_(True))
            .first()
        )
        if queue is None:
            raise ValueError(
                f"No active queue found for department '{department_id}'."
            )

        # ── 3. Find or create patient by mobile number ──────────────────────────
        # mobile has already been normalised (digits only) by the Pydantic schema.
        patient = self._patients.find_by_mobile(mobile)
        if patient is None:
            patient = self._patients.create(full_name=full_name, mobile=mobile)

        # ── 4. Check for duplicate active visit ────────────────────────────────
        # Workflow §9A / Doc A §2.1: if the patient already has an active token
        # (WAITING, SERVING, or HOLD) for the same department today, return 409.
        existing_visit = self._visits.find_active_visit(patient.id, department_id)
        if existing_visit is not None:
            existing_token = self._tokens.find_by_visit_id(existing_visit.id)
            return True, {
                "visit_id": existing_visit.id,
                "token_id": existing_token.id,
                "token_number": existing_token.token_number,
            }

        # ── 5. Create Visit ─────────────────────────────────────────────────────
        visit = self._visits.create(
            patient_id=patient.id,
            department_id=department_id,
            queue_id=queue.id,
            registration_source=source,
            visit_date=date.today(),
        )

        # ── 6. Generate token number ────────────────────────────────────────────
        sequence_number = self._tokens.next_sequence_number(queue.id)
        token_number = f"{queue.prefix}-{sequence_number}"

        # ── 7. Create Token in WAITING state ───────────────────────────────────
        token = self._tokens.create(
            visit_id=visit.id,
            queue_id=queue.id,
            token_number=token_number,
            sequence_number=sequence_number,
            state="WAITING",
        )

        # ── 8. Record CREATED event in audit log ────────────────────────────────
        actor_type = "PATIENT" if source == "QR" else "STAFF"
        event = QueueEvent(
            id=_new_uuid(),
            token_id=token.id,
            event_type="CREATED",
            from_state=None,
            to_state="WAITING",
            actor_type=actor_type,
            actor_id=None,
            reason=None,
            created_at=_utcnow(),
        )
        self.db.add(event)

        # ── 9. Commit the whole transaction ────────────────────────────────────
        self.db.commit()

        return False, {
            "patient_id": patient.id,
            "visit_id": visit.id,
            "token_id": token.id,
            "token_number": token_number,
            "state": "WAITING",
            "department_id": department_id,
        }
