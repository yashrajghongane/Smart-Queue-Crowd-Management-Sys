"""
app/api/queue.py

Staff queue-action routes — CALL NEXT, HOLD, RECALL, SKIP, COMPLETE, and queue summary.
Owns: queue action route definitions and HTTP semantics only.
All token state logic is in queue_service.py. Doc A §2.3–2.8.
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
    NoWaitingTokensResponse,
)
from app.services.queue_service import QueueService

router = APIRouter()

@router.get(
    "/{queue_id}",
    response_model=QueueSummaryResponse,
    summary="Queue summary",
)
def get_queue_summary(queue_id: str, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.get_queue_summary(queue_id)
        return data
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@router.post(
    "/{queue_id}/call-next",
    response_model=CallNextResponse,
    summary="Call next token",
    responses={409: {"model": NoWaitingTokensResponse}}
)
def call_next(queue_id: str, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.call_next(queue_id)
        return data
    except ValueError as exc:
        if "No eligible waiting token" in str(exc) or "Concurrency conflict" in str(exc):
            raise HTTPException(status_code=409, detail=NoWaitingTokensResponse(message=str(exc)).model_dump())
        raise HTTPException(status_code=404, detail=str(exc))

@router.post(
    "/tokens/{token_id}/hold",
    response_model=TokenStateChangeResponse,
    summary="Hold token",
)
def hold_token(token_id: str, body: HoldRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.hold(token_id, body.reason)
        return data
    except ValueError as exc:
        if "Cannot hold token" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))

@router.post(
    "/tokens/{token_id}/recall",
    response_model=TokenStateChangeResponse,
    summary="Recall token",
)
def recall_token(token_id: str, body: RecallRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.recall(token_id)
        return data
    except ValueError as exc:
        if "Cannot recall token" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))

@router.post(
    "/tokens/{token_id}/skip",
    response_model=TokenStateChangeResponse,
    summary="Skip token",
)
def skip_token(token_id: str, body: SkipRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.skip(token_id, body.reason)
        return data
    except ValueError as exc:
        if "Cannot skip token" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))

@router.post(
    "/tokens/{token_id}/complete",
    response_model=CompleteResponse,
    summary="Complete token",
)
def complete_token(token_id: str, body: CompleteRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.complete(token_id)
        return data
    except ValueError as exc:
        if "Cannot complete token" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc))
        raise HTTPException(status_code=404, detail=str(exc))
