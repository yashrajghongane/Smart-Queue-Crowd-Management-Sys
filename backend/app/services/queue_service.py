from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func
from app.models.models import Token, Queue, QueueEvent, Department, _utcnow
import logging

class QueueService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _log_event(self, token_id: str, event_type: str, from_state: str, to_state: str, reason: str = None) -> None:
        event = QueueEvent(
            token_id=token_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            actor_type="STAFF",
            reason=reason
        )
        self.db.add(event)

    def get_queue_summary(self, queue_id: str) -> dict:
        queue = self.db.query(Queue).filter(Queue.id == queue_id).first()
        if not queue:
            return None

        waiting_count = self.db.query(Token).filter(
            Token.queue_id == queue_id,
            Token.state == "WAITING"
        ).count()

        serving_token = self.db.query(Token).filter(
            Token.queue_id == queue_id,
            Token.state == "SERVING"
        ).first()

        return {
            "queue_id": queue.id,
            "department_id": queue.department_id,
            "waiting_count": waiting_count,
            "serving_token": serving_token.token_number if serving_token else None,
            "serving_token_id": serving_token.id if serving_token else None,
            "updated_at": _utcnow()
        }

    def call_next(self, queue_id: str) -> dict:
        next_token = self.db.query(Token).filter(
            Token.queue_id == queue_id,
            Token.state == "WAITING"
        ).order_by(Token.sequence_number.asc()).with_for_update().first()

        if not next_token:
            return None

        prev_state = next_token.state
        next_token.state = "SERVING"
        next_token.called_at = _utcnow()
        next_token.updated_at = _utcnow()

        self._log_event(next_token.id, "CALL_NEXT", prev_state, "SERVING")
        self.db.commit()

        return {
            "token_id": next_token.id,
            "token_number": next_token.token_number,
            "previous_state": prev_state,
            "state": "SERVING",
            "called_at": next_token.called_at
        }

    def hold(self, token_id: str, reason: str | None) -> dict:
        token = self.db.query(Token).filter(Token.id == token_id).with_for_update().first()
        if not token:
            return None

        if token.state not in ("WAITING", "SERVING"):
            raise ValueError(f"Cannot hold token in state {token.state}")

        prev_state = token.state
        token.state = "HOLD"
        token.updated_at = _utcnow()

        self._log_event(token.id, "HOLD", prev_state, "HOLD", reason)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": prev_state,
            "state": "HOLD"
        }

    def recall(self, token_id: str) -> dict:
        token = self.db.query(Token).filter(Token.id == token_id).with_for_update().first()
        if not token:
            return None

        if token.state not in ("HOLD", "SKIPPED", "SERVING"):
            raise ValueError(f"Cannot recall token in state {token.state}")

        prev_state = token.state
        new_state = "SERVING" if token.state == "SERVING" else "WAITING"
        token.state = new_state
        token.updated_at = _utcnow()

        self._log_event(token.id, "RECALL", prev_state, new_state)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": prev_state,
            "state": new_state
        }

    def skip(self, token_id: str, reason: str | None) -> dict:
        token = self.db.query(Token).filter(Token.id == token_id).with_for_update().first()
        if not token:
            return None

        if token.state not in ("WAITING", "SERVING", "HOLD"):
            raise ValueError(f"Cannot skip token in state {token.state}")

        prev_state = token.state
        token.state = "SKIPPED"
        token.updated_at = _utcnow()

        self._log_event(token.id, "SKIP", prev_state, "SKIPPED", reason)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": prev_state,
            "state": "SKIPPED"
        }

    def complete(self, token_id: str) -> dict:
        token = self.db.query(Token).filter(Token.id == token_id).with_for_update().first()
        if not token:
            return None

        if token.state != "SERVING":
            raise ValueError(f"Cannot complete token in state {token.state}")

        prev_state = token.state
        token.state = "COMPLETED"
        token.completed_at = _utcnow()
        token.updated_at = _utcnow()

        self._log_event(token.id, "COMPLETE", prev_state, "COMPLETED")
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": prev_state,
            "state": "COMPLETED",
            "completed_at": token.completed_at
        }
