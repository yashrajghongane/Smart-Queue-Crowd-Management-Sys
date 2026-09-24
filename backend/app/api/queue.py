"""
app/api/queue.py

Staff queue-action routes — CALL NEXT and queue summary.
Token-specific actions (hold/recall/skip/complete) are in token.py.

Owns: queue action route definitions and HTTP semantics only.
All token state logic belongs in queue_service.py. Doc A §2.3–2.4.

CURRENT STATUS: All stubs returning 501 — queue operations are the next milestone.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.schemas import (
    QueueSummaryResponse,
    CallNextResponse,
)

router = APIRouter()

_NEXT_MILESTONE_MSG = (
    "Queue operations are implemented in the next milestone. "
    "Only the patient registration flow is active in this milestone."
)


@router.get(
    "/{queue_id}",
    response_model=QueueSummaryResponse,
    summary="Queue summary (STUB)",
    description="Returns current queue summary. Implemented in the staff dashboard milestone.",
)
def get_queue_summary(queue_id: str, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)


@router.post(
    "/{queue_id}/call-next",
    response_model=CallNextResponse,
    status_code=200,
    summary="Call next token (STUB)",
    description="Calls the next WAITING token into SERVING state. Implemented in the staff dashboard milestone.",
)
def call_next(queue_id: str, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)
