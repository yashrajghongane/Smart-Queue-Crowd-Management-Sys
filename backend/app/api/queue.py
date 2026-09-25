"""
app/api/queue.py

Staff queue-action routes — CALL NEXT, HOLD, RECALL, SKIP, COMPLETE, and queue summary.
Owns: queue action route definitions and HTTP semantics only.
All token state logic is in queue_service.py. Doc A §2.3–2.8.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.services.queue_service import QueueService
from app.services.display_service import DisplayService
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

@router.get(
    "/{queue_id}",
    response_model=QueueSummaryResponse,
    summary="Queue summary",
)
def get_queue_summary(queue_id: str, db: Session = Depends(get_db)):
    service = DisplayService(db)
    summary = service.get_queue_summary(queue_id)
    return summary

@router.post(
    "/{queue_id}/call-next",
    response_model=CallNextResponse,
    summary="Call next token",
)
def call_next(queue_id: str, db: Session = Depends(get_db)):
    service = QueueService(db)
    return service.call_next(queue_id)

@router.post(
    "/tokens/{token_id}/hold",
    response_model=TokenStateChangeResponse,
    summary="Hold token",
)
def hold_token(token_id: str, body: HoldRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    return service.hold(token_id, body.reason)

@router.post(
    "/tokens/{token_id}/recall",
    response_model=TokenStateChangeResponse,
    summary="Recall token",
)
def recall_token(token_id: str, body: RecallRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    return service.recall(token_id)

@router.post(
    "/tokens/{token_id}/skip",
    response_model=TokenStateChangeResponse,
    summary="Skip token",
)
def skip_token(token_id: str, body: SkipRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    return service.skip(token_id, body.reason)

@router.post(
    "/tokens/{token_id}/complete",
    response_model=CompleteResponse,
    summary="Complete token",
)
def complete_token(token_id: str, body: CompleteRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    return service.complete(token_id)
