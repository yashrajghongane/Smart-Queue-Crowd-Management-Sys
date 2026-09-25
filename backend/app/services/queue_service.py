"""
app/services/queue_service.py

Token state transitions and CALL NEXT concurrency logic.
This is the sole owner of all queue state changes (Doc A §5 ownership rule).
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, exc
from datetime import datetime
import uuid

from app.models.models import Token, QueueEvent, Queue, _utcnow, _new_uuid

class QueueService:
    """
    Owns all token state transitions.
    No route handler may implement queue state logic directly.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_queue_by_id(self, queue_id: str) -> Queue:
        queue = self.db.execute(select(Queue).where(Queue.id == queue_id)).scalar_one_or_none()
        if not queue:
            raise ValueError(f"Queue {queue_id} not found")
        return queue

    def _get_token_by_id(self, token_id: str) -> Token:
        token = self.db.execute(select(Token).where(Token.id == token_id)).scalar_one_or_none()
        if not token:
            raise ValueError(f"Token {token_id} not found")
        return token

    def _record_event(self, token: Token, event_type: str, from_state: str, to_state: str, reason: str | None = None):
        event = QueueEvent(
            id=_new_uuid(),
            token_id=token.id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            actor_type="STAFF",
            actor_id=None, # In a real system, extract staff ID from JWT context
            reason=reason,
            created_at=_utcnow()
        )
        self.db.add(event)

    def call_next(self, queue_id: str) -> dict:
        """WAITING → SERVING for the lowest-sequence WAITING token. Doc A §2.4."""
        self._get_queue_by_id(queue_id)

        # Select the lowest sequence number waiting token FOR UPDATE SKIP LOCKED
        # (Using sqlite for dev, so FOR UPDATE might not be fully featured, but ORM supports with_for_update)
        try:
            # We want the next token
            # Note: with_for_update(skip_locked=True) is not supported by SQLite
            # but is perfect for PostgreSQL. Since SQLite is only for dev, we omit skip_locked
            # or handle it gracefully if we want dual-support. For simplicity and
            # SQLite dev compatibility, we just use with_for_update() and rely on
            # serializable transactions or retry logic in a real setup.
            stmt = select(Token).where(
                and_(Token.queue_id == queue_id, Token.state == "WAITING")
            ).order_by(Token.sequence_number.asc()).limit(1).with_for_update()

            token = self.db.execute(stmt).scalar_one_or_none()
            if not token:
                raise ValueError("No eligible waiting token is available.")

            # Doc A rule: Only one SERVING token allowed?
            # The spec doesn't explicitly restrict having multiple SERVING if multiple staff.
            # but we assume calling next makes that specific token SERVING.

            previous_state = token.state
            token.state = "SERVING"
            token.called_at = _utcnow()

            self._record_event(token, "CALL_NEXT", previous_state, "SERVING")
            self.db.commit()

            return {
                "token_id": token.id,
                "token_number": token.token_number,
                "previous_state": previous_state,
                "state": token.state,
                "called_at": token.called_at.isoformat() + "Z"
            }
        except exc.IntegrityError:
            self.db.rollback()
            raise ValueError("Concurrency conflict while calling next token.")

    def hold(self, token_id: str, reason: str | None) -> dict:
        """WAITING|SERVING → HOLD. Doc A §2.5."""
        token = self._get_token_by_id(token_id)
        if token.state not in ("WAITING", "SERVING"):
            raise ValueError(f"Cannot hold token in state {token.state}")

        previous_state = token.state
        token.state = "HOLD"

        self._record_event(token, "HOLD", previous_state, "HOLD", reason)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": token.state
        }

    def recall(self, token_id: str) -> dict:
        """HOLD|SKIPPED → WAITING; SERVING → SERVING. Doc A §2.6."""
        token = self._get_token_by_id(token_id)
        if token.state not in ("HOLD", "SKIPPED", "SERVING"):
            raise ValueError(f"Cannot recall token in state {token.state}")

        previous_state = token.state
        if token.state in ("HOLD", "SKIPPED"):
            token.state = "WAITING"
            # It retains its sequence_number so it stays prioritized
            self._record_event(token, "RECALL", previous_state, "WAITING")
        elif token.state == "SERVING":
            self._record_event(token, "RECALL", previous_state, "SERVING")

        self.db.commit()
        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": token.state
        }

    def skip(self, token_id: str, reason: str | None) -> dict:
        """WAITING|SERVING|HOLD → SKIPPED. Doc A §2.7."""
        token = self._get_token_by_id(token_id)
        if token.state not in ("WAITING", "SERVING", "HOLD"):
            raise ValueError(f"Cannot skip token in state {token.state}")

        previous_state = token.state
        token.state = "SKIPPED"

        self._record_event(token, "SKIP", previous_state, "SKIPPED", reason)
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": token.state
        }

    def complete(self, token_id: str) -> dict:
        """SERVING → COMPLETED. Doc A §2.8."""
        token = self._get_token_by_id(token_id)
        if token.state != "SERVING":
            raise ValueError(f"Cannot complete token in state {token.state}")

        previous_state = token.state
        token.state = "COMPLETED"
        token.completed_at = _utcnow()

        # also close the visit
        if token.visit:
            token.visit.closed_at = token.completed_at

        self._record_event(token, "COMPLETE", previous_state, "COMPLETED")
        self.db.commit()

        return {
            "token_id": token.id,
            "previous_state": previous_state,
            "state": token.state,
            "completed_at": token.completed_at.isoformat() + "Z"
        }

    def get_queue_summary(self, queue_id: str) -> dict:
        """Queue summary for staff dashboard. Doc A §2.3"""
        queue = self._get_queue_by_id(queue_id)

        waiting_count = self.db.execute(
            select(Token).where(and_(Token.queue_id == queue_id, Token.state == "WAITING"))
        ).scalars().all()

        serving_token = self.db.execute(
            select(Token).where(and_(Token.queue_id == queue_id, Token.state == "SERVING"))
            .order_by(Token.updated_at.desc()).limit(1)
        ).scalar_one_or_none()

        return {
            "queue_id": queue.id,
            "department_id": queue.department_id,
            "waiting_count": len(waiting_count),
            "serving_token": serving_token.token_number if serving_token else None,
            "serving_token_id": serving_token.id if serving_token else None,
            "updated_at": _utcnow().isoformat() + "Z"
        }
