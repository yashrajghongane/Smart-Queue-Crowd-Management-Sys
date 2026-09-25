"""
app/services/queue_service.py

Token state transitions and CALL NEXT concurrency logic.
This is the sole owner of all queue state changes (Doc A §5 ownership rule).
"""
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.repositories.token_repository import TokenRepository
from app.models.models import _utcnow, QueueEvent

class QueueService:
    """
    Owns all token state transitions.
    No route handler may implement queue state logic directly.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._tokens = TokenRepository(db)

    def call_next(self, queue_id: str) -> dict:
        """WAITING → SERVING for the lowest-sequence WAITING token."""
        token = self._tokens.find_next_waiting(queue_id)
        if not token:
            raise HTTPException(status_code=409, detail="NO_WAITING_TOKENS")

        previous_state = token.state
        token.state = "SERVING"
        token.called_at = _utcnow()
        token.updated_at = _utcnow()

        event = QueueEvent(
            token_id=token.id,
            event_type="CALL_NEXT",
            from_state=previous_state,
            to_state="SERVING",
            actor_type="STAFF"
        )
        self.db.add(event)
        self.db.commit()

        return {
            "token_id": token.id,
            "token_number": token.token_number,
            "previous_state": previous_state,
            "state": token.state,
            "called_at": token.called_at
        }

    def hold(self, token_id: str, reason: str | None) -> dict:
        """WAITING|SERVING → HOLD."""
        token = self._tokens.find_by_id(token_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")

        if token.state not in ["WAITING", "SERVING"]:
            raise HTTPException(status_code=400, detail=f"Cannot hold from {token.state}")

        previous_state = token.state
        token.state = "HOLD"
        token.updated_at = _utcnow()

        event = QueueEvent(
            token_id=token.id,
            event_type="HOLD",
            from_state=previous_state,
            to_state="HOLD",
            actor_type="STAFF",
            reason=reason
        )
        self.db.add(event)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": token.state
        }

    def recall(self, token_id: str) -> dict:
        """HOLD|SKIPPED → WAITING; SERVING → SERVING."""
        token = self._tokens.find_by_id(token_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")

        if token.state not in ["HOLD", "SKIPPED", "SERVING"]:
            raise HTTPException(status_code=400, detail=f"Cannot recall from {token.state}")

        previous_state = token.state
        if token.state in ["HOLD", "SKIPPED"]:
            token.state = "WAITING"

        token.updated_at = _utcnow()

        event = QueueEvent(
            token_id=token.id,
            event_type="RECALL",
            from_state=previous_state,
            to_state=token.state,
            actor_type="STAFF"
        )
        self.db.add(event)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": token.state
        }

    def skip(self, token_id: str, reason: str | None) -> dict:
        """WAITING|SERVING|HOLD → SKIPPED."""
        token = self._tokens.find_by_id(token_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")

        if token.state not in ["WAITING", "SERVING", "HOLD"]:
            raise HTTPException(status_code=400, detail=f"Cannot skip from {token.state}")

        previous_state = token.state
        token.state = "SKIPPED"
        token.updated_at = _utcnow()

        event = QueueEvent(
            token_id=token.id,
            event_type="SKIP",
            from_state=previous_state,
            to_state="SKIPPED",
            actor_type="STAFF",
            reason=reason
        )
        self.db.add(event)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": token.state
        }

    def complete(self, token_id: str) -> dict:
        """SERVING → COMPLETED."""
        token = self._tokens.find_by_id(token_id)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")

        if token.state != "SERVING":
            raise HTTPException(status_code=400, detail=f"Cannot complete from {token.state}")

        previous_state = token.state
        token.state = "COMPLETED"
        token.completed_at = _utcnow()
        token.updated_at = _utcnow()

        event = QueueEvent(
            token_id=token.id,
            event_type="COMPLETE",
            from_state=previous_state,
            to_state="COMPLETED",
            actor_type="STAFF"
        )
        self.db.add(event)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": token.state,
            "completed_at": token.completed_at
        }
