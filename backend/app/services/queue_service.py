from app.models.models import QueueEvent, _new_uuid, _utcnow
from app.repositories.token_repository import TokenRepository
from app.repositories.queue_repository import QueueRepository
from sqlalchemy.orm import Session

class QueueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._tokens = TokenRepository(db)
        self._queues = QueueRepository(db)

    def _record_event(self, token, event_type: str, from_state: str, to_state: str, reason: str = None) -> None:
        event = QueueEvent(
            id=_new_uuid(),
            token_id=token.id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            actor_type="STAFF",
            reason=reason,
            created_at=_utcnow()
        )
        self.db.add(event)

    def get_queue_summary(self, queue_id: str) -> dict:
        queue = self._queues.find_by_id(queue_id)
        if not queue:
            raise ValueError("QUEUE_NOT_FOUND")

        waiting_count = self._tokens.count_waiting(queue_id)
        serving_token = self._tokens.find_serving_token(queue_id)

        now = _utcnow()
        if serving_token:
            updated_at = serving_token.updated_at
        else:
            updated_at = now

        return {
            "queue_id": queue_id,
            "department_id": queue.department_id,
            "waiting_count": waiting_count,
            "serving_token": serving_token.token_number if serving_token else None,
            "serving_token_id": serving_token.id if serving_token else None,
            "updated_at": updated_at
        }

    def call_next(self, queue_id: str) -> dict:
        from app.models.models import Token

        # Need skip_locked for proper concurrency control in postgres (even though it's ignored in sqlite)
        token = self.db.query(Token).filter(
            Token.queue_id == queue_id,
            Token.state == "WAITING"
        ).with_for_update(skip_locked=True).order_by(Token.sequence_number.asc()).first()

        if not token:
            raise ValueError("NO_WAITING_TOKENS")

        previous_state = token.state
        token.state = "SERVING"
        token.called_at = _utcnow()

        self._record_event(token, "CALL_NEXT", previous_state, "SERVING")
        self.db.commit()

        return {
            "token_id": token.id,
            "token_number": token.token_number,
            "previous_state": previous_state,
            "state": "SERVING",
            "called_at": token.called_at
        }

    def hold(self, token_id: str, reason: str | None) -> dict:
        from app.models.models import Token
        token = self.db.query(Token).filter(Token.id == token_id).with_for_update().first()

        if not token:
            raise ValueError("TOKEN_NOT_FOUND")

        if token.state not in ("WAITING", "SERVING"):
            raise ValueError("INVALID_STATE")

        previous_state = token.state
        token.state = "HOLD"

        self._record_event(token, "HOLD", previous_state, "HOLD", reason)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": "HOLD"
        }

    def recall(self, token_id: str) -> dict:
        from app.models.models import Token
        token = self.db.query(Token).filter(Token.id == token_id).with_for_update().first()

        if not token:
            raise ValueError("TOKEN_NOT_FOUND")

        previous_state = token.state

        if previous_state in ("HOLD", "SKIPPED"):
            new_state = "WAITING"
        elif previous_state == "SERVING":
            new_state = "SERVING"
        else:
            raise ValueError("INVALID_STATE")

        token.state = new_state
        self._record_event(token, "RECALL", previous_state, new_state)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": new_state
        }

    def skip(self, token_id: str, reason: str | None) -> dict:
        from app.models.models import Token
        token = self.db.query(Token).filter(Token.id == token_id).with_for_update().first()

        if not token:
            raise ValueError("TOKEN_NOT_FOUND")

        if token.state not in ("WAITING", "SERVING", "HOLD"):
            raise ValueError("INVALID_STATE")

        previous_state = token.state
        token.state = "SKIPPED"

        self._record_event(token, "SKIP", previous_state, "SKIPPED", reason)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": "SKIPPED"
        }

    def complete(self, token_id: str) -> dict:
        from app.models.models import Token
        token = self.db.query(Token).filter(Token.id == token_id).with_for_update().first()

        if not token:
            raise ValueError("TOKEN_NOT_FOUND")

        if token.state != "SERVING":
            raise ValueError("INVALID_STATE")

        previous_state = token.state
        token.state = "COMPLETED"
        token.completed_at = _utcnow()

        self._record_event(token, "COMPLETE", previous_state, "COMPLETED")
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": "COMPLETED",
            "completed_at": token.completed_at
        }
