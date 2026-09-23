"""
app/services/queue_service.py

Token state transitions and CALL NEXT concurrency logic.
This is the sole owner of all queue state changes (Doc A §5 ownership rule).

CURRENT STATUS: Stub — queue operations are implemented in the next milestone
after the patient-side digital flow is verified.

All transition methods raise NotImplementedError so they surface clearly
rather than silently returning wrong data.
"""
from sqlalchemy.orm import Session


class QueueService:
    """
    Owns all token state transitions.
    No route handler may implement queue state logic directly.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def call_next(self, queue_id: str) -> dict:
        """WAITING → SERVING for the lowest-sequence WAITING token. Doc A §2.4."""
        raise NotImplementedError("Queue operations are implemented in the next milestone.")

    def hold(self, token_id: str, reason: str | None) -> dict:
        """WAITING|SERVING → HOLD. Doc A §2.5."""
        raise NotImplementedError("Queue operations are implemented in the next milestone.")

    def recall(self, token_id: str) -> dict:
        """HOLD|SKIPPED → WAITING; SERVING → SERVING. Doc A §2.6."""
        raise NotImplementedError("Queue operations are implemented in the next milestone.")

    def skip(self, token_id: str, reason: str | None) -> dict:
        """WAITING|SERVING|HOLD → SKIPPED. Doc A §2.7."""
        raise NotImplementedError("Queue operations are implemented in the next milestone.")

    def complete(self, token_id: str) -> dict:
        """SERVING → COMPLETED. Doc A §2.8."""
        raise NotImplementedError("Queue operations are implemented in the next milestone.")
