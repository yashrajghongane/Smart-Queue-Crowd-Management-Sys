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

    def get_public_display(self, queue_id: str) -> Optional[dict]:
        """
        Assemble the public display response for GET /api/v1/public/queues/{queue_id}/display.
        Returns None if queue not found.
        Doc A §2.10.
        """
        # Validate queue exists
        # In a real repository we might do self._queues.find_by_id(queue_id),
        # but here we can just use tokens to get serving and next
        serving = self._tokens.find_serving_token(queue_id)
        serving_token_number = serving.token_number if serving else None

        # To find next token, we want the lowest sequence WAITING token
        from sqlalchemy import select, and_
        from app.models.models import Token, _utcnow

        stmt = select(Token).where(
            and_(Token.queue_id == queue_id, Token.state == "WAITING")
        ).order_by(Token.sequence_number.asc()).limit(1)

        next_token_obj = self.db.execute(stmt).scalar_one_or_none()
        next_token_number = next_token_obj.token_number if next_token_obj else None

        from sqlalchemy import func
        waiting_count = self.db.execute(
            select(func.count(Token.id)).where(
                and_(Token.queue_id == queue_id, Token.state == "WAITING")
            )
        ).scalar_one()

        return {
            "queue_id": queue_id,
            "serving_token": serving_token_number,
            "next_token": next_token_number,
            "waiting_count": waiting_count,
            "updated_at": _utcnow().isoformat() + "Z"
        }
