"""
app/repositories/visit_repository.py

Database read/write operations for the Visit table.
No business logic or state-transition decisions here.
"""
from datetime import date as date_type
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import Visit, Token, _new_uuid, _utcnow

# Token states that mean a visit is still "active" (not terminal).
_ACTIVE_TOKEN_STATES = ("WAITING", "SERVING", "HOLD")


class VisitRepository:
    """Encapsulates all Visit table operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def find_by_id(self, visit_id: str) -> Optional[Visit]:
        """Return visit by primary key, or None."""
        return self.db.query(Visit).filter(Visit.id == visit_id).first()

    def find_active_visit(
        self, patient_id: str, department_id: str
    ) -> Optional[Visit]:
        """
        Return the most recent active visit for a patient in a department,
        where 'active' means the associated token is in WAITING, SERVING, or HOLD.

        This enforces the duplicate-registration rule from Doc A §2.1 and the
        Workflow & Behavior Document §9A.
        """
        return (
            self.db.query(Visit)
            .join(Token, Visit.id == Token.visit_id)
            .filter(
                Visit.patient_id == patient_id,
                Visit.department_id == department_id,
                Token.state.in_(_ACTIVE_TOKEN_STATES),
            )
            .first()
        )

    def create(
        self,
        patient_id: str,
        department_id: str,
        queue_id: str,
        registration_source: str,
        visit_date: date_type,
    ) -> Visit:
        """
        Insert a new Visit row.
        Caller is responsible for calling db.commit() after all related inserts.
        """
        visit = Visit(
            id=_new_uuid(),
            patient_id=patient_id,
            department_id=department_id,
            queue_id=queue_id,
            registration_source=registration_source,
            visit_date=visit_date,
            created_at=_utcnow(),
            closed_at=None,
        )
        self.db.add(visit)
        self.db.flush()
        return visit
