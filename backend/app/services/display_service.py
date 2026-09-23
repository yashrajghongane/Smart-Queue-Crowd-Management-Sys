"""
app/services/display_service.py

Staff and public read models — assembles query results into response-ready dicts.
No state changes made here. Doc A §5.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.token_repository import TokenRepository
from app.repositories.visit_repository import VisitRepository


class DisplayService:
    """
    Builds read-only views for patient status, queue summary, and public display.
    Makes no state changes.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._tokens = TokenRepository(db)
        self._visits = VisitRepository(db)

    def get_patient_status(self, visit_id: str) -> Optional[dict]:
        """
        Assemble the patient status response for GET /api/v1/visits/{visit_id}/status.
        Returns None if the visit is not found.
        Doc A §2.9.
        """
        visit = self._visits.find_by_id(visit_id)
        if visit is None:
            return None

        token = self._tokens.find_by_visit_id(visit_id)
        if token is None:
            return None  # Should not happen in normal operation

        patients_ahead = self._tokens.count_patients_ahead(
            queue_id=token.queue_id,
            sequence_number=token.sequence_number,
        )

        serving = self._tokens.find_serving_token(token.queue_id)
        serving_token_number = serving.token_number if serving else None

        return {
            "visit_id": visit.id,
            "token_number": token.token_number,
            "state": token.state,
            "patients_ahead": patients_ahead,
            "serving_token": serving_token_number,
            "department_id": visit.department_id,
            "updated_at": token.updated_at,
        }
