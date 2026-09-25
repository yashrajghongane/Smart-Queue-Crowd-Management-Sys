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

    def get_queue_summary(self, queue_id: str) -> dict:
        """Doc A §2.3 Queue Summary"""
        from fastapi import HTTPException
        from app.models.models import Queue
        queue = self.db.query(Queue).filter(Queue.id == queue_id).first()
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")

        waiting_count = self._tokens.count_waiting(queue_id)
        serving = self._tokens.find_serving_token(queue_id)

        # Get latest update time across queue tokens, or fallback to current time
        from app.models.models import Token, _utcnow
        latest_token = self.db.query(Token).filter(Token.queue_id == queue_id).order_by(Token.updated_at.desc()).first()
        updated_at = latest_token.updated_at if latest_token else _utcnow()

        return {
            "queue_id": queue.id,
            "department_id": queue.department_id,
            "waiting_count": waiting_count,
            "serving_token": serving.token_number if serving else None,
            "serving_token_id": serving.id if serving else None,
            "updated_at": updated_at
        }

    def get_public_display(self, queue_id: str) -> dict:
        """Doc A §2.10 Public display"""
        from fastapi import HTTPException
        from app.models.models import Queue
        queue = self.db.query(Queue).filter(Queue.id == queue_id).first()
        if not queue:
            raise HTTPException(status_code=404, detail="Queue not found")

        serving = self._tokens.find_serving_token(queue_id)
        next_token = self._tokens.find_next_waiting(queue_id)
        waiting_count = self._tokens.count_waiting(queue_id)

        # Get latest update time across queue tokens, or fallback to current time
        from app.models.models import Token, _utcnow
        latest_token = self.db.query(Token).filter(Token.queue_id == queue_id).order_by(Token.updated_at.desc()).first()
        updated_at = latest_token.updated_at if latest_token else _utcnow()

        return {
            "queue_id": queue.id,
            "serving_token": serving.token_number if serving else None,
            "next_token": next_token.token_number if next_token else None,
            "waiting_count": waiting_count,
            "updated_at": updated_at
        }
