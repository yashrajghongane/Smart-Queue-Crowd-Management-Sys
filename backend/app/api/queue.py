from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.schemas import (
    QueueSummaryResponse,
    CallNextResponse,
    NoWaitingTokensResponse,
    HoldRequest,
    TokenStateChangeResponse,
    RecallRequest,
    SkipRequest,
    CompleteRequest,
    CompleteResponse,
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
    summary = service.get_queue_summary(queue_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Queue not found")
    return summary


@router.post(
    "/{queue_id}/call-next",
    response_model=CallNextResponse,
    summary="Call next token",
    responses={404: {"model": NoWaitingTokensResponse}}
)
def call_next(queue_id: str, db: Session = Depends(get_db)):
    service = QueueService(db)
    result = service.call_next(queue_id)
    if not result:
        # FastAPI handles validation of response_model for 2xx responses.
        # But if we raise an exception, the detail has to match what the client expects, or we just rely on standard HTTP responses.
        # The prompt says 404 should return a specific model, so we can return a JSONResponse
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content=NoWaitingTokensResponse().model_dump())
    return result


@router.post(
    "/tokens/{token_id}/hold",
    response_model=TokenStateChangeResponse,
    summary="Hold token",
)
def hold_token(token_id: str, body: HoldRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        result = service.hold(token_id, body.reason)
        if not result:
            raise HTTPException(status_code=404, detail="Token not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post(
    "/tokens/{token_id}/recall",
    response_model=TokenStateChangeResponse,
    summary="Recall token",
)
def recall_token(token_id: str, body: RecallRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        result = service.recall(token_id)
        if not result:
            raise HTTPException(status_code=404, detail="Token not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post(
    "/tokens/{token_id}/skip",
    response_model=TokenStateChangeResponse,
    summary="Skip token",
)
def skip_token(token_id: str, body: SkipRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        result = service.skip(token_id, body.reason)
        if not result:
            raise HTTPException(status_code=404, detail="Token not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post(
    "/tokens/{token_id}/complete",
    response_model=CompleteResponse,
    summary="Complete token",
)
def complete_token(token_id: str, body: CompleteRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        result = service.complete(token_id)
        if not result:
            raise HTTPException(status_code=404, detail="Token not found")
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
