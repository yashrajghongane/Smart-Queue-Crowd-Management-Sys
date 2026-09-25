"""Queue business logic and token state transitions. Sole owner of queue state changes."""
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.models import QueueEvent, Queue, Token, _new_uuid, _utcnow
from app.repositories.queue_repository import QueueRepository
from app.repositories.token_repository import TokenRepository

class QueueServiceError(ValueError): pass
class QueueNotFoundError(QueueServiceError): pass
class TokenNotFoundError(QueueServiceError): pass
class NoWaitingTokensError(QueueServiceError): pass
class InvalidTransitionError(QueueServiceError): pass

class QueueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._queues = QueueRepository(db)
        self._tokens = TokenRepository(db)

    def _get_queue(self, queue_id: str) -> Queue:
        queue = self._queues.find_by_id(queue_id)
        if queue is None:
            raise QueueNotFoundError()
        return queue

    def _get_token_for_update(self, token_id: str) -> Token:
        token = self.db.execute(
            select(Token).where(Token.id == token_id).with_for_update()
        ).scalar_one_or_none()
        if token is None:
            raise TokenNotFoundError()
        return token

    def _record_event(
        self, token: Token, event_type: str, from_state: str, to_state: str, reason: str | None = None
    ) -> None:
        self.db.add(
            QueueEvent(
                id=_new_uuid(),
                token_id=token.id,
                event_type=event_type,
                from_state=from_state,
                to_state=to_state,
                actor_type="STAFF",
                actor_id=None,
                reason=reason,
                created_at=_utcnow(),
            )
        )

    def get_queue_summary(self, queue_id: str) -> dict:
        queue = self._get_queue(queue_id)
        serving = self._tokens.find_serving_token(queue_id)
        return {
            "queue_id": queue.id,
            "department_id": queue.department_id,
            "waiting_count": self._tokens.count_waiting(queue_id),
            "serving_token": serving.token_number if serving else None,
            "serving_token_id": serving.id if serving else None,
            "updated_at": serving.updated_at if serving else _utcnow(),
        }

    def call_next(self, queue_id: str) -> dict:
        self._get_queue(queue_id)
        stmt = (
            select(Token)
            .where(and_(Token.queue_id == queue_id, Token.state == "WAITING"))
            .order_by(Token.sequence_number.asc())
            .limit(1)
            .with_for_update()
        )
        token = self.db.execute(stmt).scalar_one_or_none()
        if token is None:
            raise NoWaitingTokensError()

        previous_state = token.state
        now = _utcnow()
        token.state = "SERVING"
        token.called_at = now
        token.updated_at = now
        self._record_event(token, "CALL_NEXT", previous_state, "SERVING")
        self.db.commit()
        return {
            "token_id": token.id,
            "token_number": token.token_number,
            "previous_state": previous_state,
            "state": "SERVING",
            "called_at": now,
        }

    def hold(self, token_id: str, reason: str | None) -> dict:
        token = self._get_token_for_update(token_id)
        if token.state not in ("WAITING", "SERVING"):
            raise InvalidTransitionError()
        previous_state = token.state
        token.state = "HOLD"
        self._record_event(token, "HOLD", previous_state, "HOLD", reason)
        self.db.commit()
        return {"token_id": token.id, "previous_state": previous_state, "state": "HOLD"}

    def recall(self, token_id: str) -> dict:
        token = self._get_token_for_update(token_id)
        previous_state = token.state
        if previous_state in ("HOLD", "SKIPPED"):
            new_state = "WAITING"
        elif previous_state == "SERVING":
            new_state = "SERVING"
        else:
            raise InvalidTransitionError()
        token.state = new_state
        self._record_event(token, "RECALL", previous_state, new_state)
        self.db.commit()
        return {"token_id": token.id, "previous_state": previous_state, "state": new_state}

    def skip(self, token_id: str, reason: str | None) -> dict:
        token = self._get_token_for_update(token_id)
        if token.state not in ("WAITING", "SERVING", "HOLD"):
            raise InvalidTransitionError()
        previous_state = token.state
        token.state = "SKIPPED"
        self._record_event(token, "SKIP", previous_state, "SKIPPED", reason)
        self.db.commit()
        return {"token_id": token.id, "previous_state": previous_state, "state": "SKIPPED"}

    def complete(self, token_id: str) -> dict:
        token = self._get_token_for_update(token_id)
        if token.state != "SERVING":
            raise InvalidTransitionError()
        previous_state = token.state
        now = _utcnow()
        token.state = "COMPLETED"
        token.completed_at = now
        token.updated_at = now
        if token.visit is not None:
            token.visit.closed_at = now
        self._record_event(token, "COMPLETE", previous_state, "COMPLETED")
        self.db.commit()
        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": "COMPLETED",
            "completed_at": now,
        }
