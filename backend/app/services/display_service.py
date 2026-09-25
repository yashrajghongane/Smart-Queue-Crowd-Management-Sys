"""Read-only display models for patient status and public display."""
from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, select

from app.models.models import Token, _utcnow
from app.repositories.queue_repository import QueueRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.visit_repository import VisitRepository

class DisplayService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._tokens = TokenRepository(db)
        self._visits = VisitRepository(db)
        self._queues = QueueRepository(db)

    def get_patient_status(self, visit_id: str) -> Optional[dict]:
        visit = self._visits.find_by_id(visit_id)
        if visit is None:
            return None
        token = self._tokens.find_by_visit_id(visit_id)
        if token is None:
            return None
        queue = self._queues.find_by_id(token.queue_id)
        patients_ahead = self._tokens.count_patients_ahead(token.queue_id, token.sequence_number)
        serving = self._tokens.find_serving_token(token.queue_id)
        estimated_wait = (patients_ahead * 5) if token.state == "WAITING" else 0
        return {
            "visit_id": visit.id,
            "token_number": token.token_number,
            "state": token.state,
            "patients_ahead": patients_ahead,
            "serving_token": serving.token_number if serving else None,
            "department_id": visit.department_id,
            "queue_name": queue.name if queue else "OPD Queue",
            "estimated_wait_minutes": estimated_wait,
            "updated_at": token.updated_at,
        }

    def get_public_display(self, queue_id: str) -> Optional[dict]:
        queue = self._queues.find_by_id(queue_id)
        if queue is None:
            return None
        serving = self._tokens.find_serving_token(queue_id)
        next_token = self._tokens.find_next_waiting(queue_id)
        waiting_count = self._tokens.count_waiting(queue_id)
        return {
            "queue_id": queue_id,
            "serving_token": serving.token_number if serving else None,
            "next_token": next_token.token_number if next_token else None,
            "waiting_count": waiting_count,
            "updated_at": serving.updated_at if serving else _utcnow(),
        }
