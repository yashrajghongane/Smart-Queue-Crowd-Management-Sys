"""
app/api/queue.py

Staff queue-action routes — CALL NEXT, HOLD, RECALL, SKIP, COMPLETE, and queue summary.
Owns: queue action route definitions and HTTP semantics only.
All token state logic is in queue_service.py. Doc A §2.3–2.8.

CURRENT STATUS: Stubs returning 501 — queue operations are the next milestone
after the patient-side digital flow is verified.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.schemas import (
    QueueSummaryResponse,
    CallNextResponse,
    HoldRequest,
    TokenStateChangeResponse,
    RecallRequest,
    SkipRequest,
    CompleteRequest,
    CompleteResponse,
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
)
def get_queue_summary(queue_id: str, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)


@router.post(
    "/{queue_id}/call-next",
    response_model=CallNextResponse,
    summary="Call next token (STUB)",
)
def call_next(queue_id: str, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)


@router.post(
    "/tokens/{token_id}/hold",
    response_model=TokenStateChangeResponse,
    summary="Hold token (STUB)",
)
def hold_token(token_id: str, body: HoldRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)


@router.post(
    "/tokens/{token_id}/recall",
    response_model=TokenStateChangeResponse,
    summary="Recall token (STUB)",
)
def recall_token(token_id: str, body: RecallRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)


@router.post(
    "/tokens/{token_id}/skip",
    response_model=TokenStateChangeResponse,
    summary="Skip token (STUB)",
)
def skip_token(token_id: str, body: SkipRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)


@router.post(
    "/tokens/{token_id}/complete",
    response_model=CompleteResponse,
    summary="Complete token (STUB)",
)
def complete_token(token_id: str, body: CompleteRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)
