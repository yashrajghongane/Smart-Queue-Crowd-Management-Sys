"""
app/repositories/token_repository.py

Database read/write operations for the Token table.
No state-transition business logic here — that belongs in queue_service.py.
"""
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Token, _new_uuid, _utcnow


class TokenRepository:
    """Encapsulates all Token table operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def find_by_id(self, token_id: str) -> Optional[Token]:
        """Return token by primary key, or None."""
        return self.db.query(Token).filter(Token.id == token_id).first()

    def find_by_visit_id(self, visit_id: str) -> Optional[Token]:
        """Return the token associated with a visit, or None."""
        return self.db.query(Token).filter(Token.visit_id == visit_id).first()

    def next_sequence_number(self, queue_id: str) -> int:
        """
        Return the next available sequence number for a queue.
        Sequence numbers are globally incrementing per queue (no daily reset in this milestone).
        token_number uniqueness is enforced by the DB unique constraint on token_number.
        """
        current_max = (
            self.db.query(func.max(Token.sequence_number))
            .filter(Token.queue_id == queue_id)
            .scalar()
        )
        return (current_max or 0) + 1

    def count_patients_ahead(self, queue_id: str, sequence_number: int) -> int:
        """
        Count WAITING tokens in the same queue with a lower sequence_number.
        This gives the 'patients_ahead' value for the patient status endpoint.
        """
        return (
            self.db.query(func.count(Token.id))
            .filter(
                Token.queue_id == queue_id,
                Token.state == "WAITING",
                Token.sequence_number < sequence_number,
            )
            .scalar()
            or 0
        )

    def find_serving_token(self, queue_id: str) -> Optional[Token]:
        """Return the currently SERVING token in a queue, or None."""
        return (
            self.db.query(Token)
            .filter(Token.queue_id == queue_id, Token.state == "SERVING")
            .first()
        )

    def find_next_waiting(self, queue_id: str) -> Optional[Token]:
        """
        Return the WAITING token with the lowest sequence_number (next to be called).
        Used by queue_service for CALL NEXT.
        """
        return (
            self.db.query(Token)
            .filter(Token.queue_id == queue_id, Token.state == "WAITING")
            .order_by(Token.sequence_number.asc())
            .first()
        )

    def count_waiting(self, queue_id: str) -> int:
        """Count all WAITING tokens in a queue."""
        return (
            self.db.query(func.count(Token.id))
            .filter(Token.queue_id == queue_id, Token.state == "WAITING")
            .scalar()
            or 0
        )

    def create(
        self,
        visit_id: str,
        queue_id: str,
        token_number: str,
        sequence_number: int,
        state: str = "WAITING",
    ) -> Token:
        """
        Insert a new Token row.
        Caller is responsible for calling db.commit() after all related inserts.
        """
        token = Token(
            id=_new_uuid(),
            visit_id=visit_id,
            queue_id=queue_id,
            token_number=token_number,
            sequence_number=sequence_number,
            state=state,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.db.add(token)
        self.db.flush()
        return token
