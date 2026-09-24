from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Union

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
    ErrorResponse
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
        return QueueSummaryResponse(**data)
    except ValueError as e:
        if str(e) == "QUEUE_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Queue not found")
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/{queue_id}/call-next",
    response_model=CallNextResponse,
    responses={
        409: {"model": NoWaitingTokensResponse}
    },
    summary="Call next token",
)
def call_next(queue_id: str, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.call_next(queue_id)
        return CallNextResponse(**data)
    except ValueError as e:
        if str(e) == "NO_WAITING_TOKENS":
            # Document A §2.4 says:
            # { "error": "NO_WAITING_TOKENS", "message": "No eligible waiting token is available." }
            # To get this EXACT json at root instead of {"detail": ...} we must return JSONResponse
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=NoWaitingTokensResponse().model_dump()
            )
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/tokens/{token_id}/hold",
    response_model=TokenStateChangeResponse,
    summary="Hold token",
)
def hold_token(token_id: str, body: HoldRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.hold(token_id, body.reason)
        return TokenStateChangeResponse(**data)
    except ValueError as e:
        if str(e) == "TOKEN_NOT_FOUND":
             raise HTTPException(status_code=404, detail=str(e))
        if str(e) == "INVALID_STATE":
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/tokens/{token_id}/recall",
    response_model=TokenStateChangeResponse,
    summary="Recall token",
)
def recall_token(token_id: str, body: RecallRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.recall(token_id)
        return TokenStateChangeResponse(**data)
    except ValueError as e:
        if str(e) == "TOKEN_NOT_FOUND":
             raise HTTPException(status_code=404, detail=str(e))
        if str(e) == "INVALID_STATE":
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/tokens/{token_id}/skip",
    response_model=TokenStateChangeResponse,
    summary="Skip token",
)
def skip_token(token_id: str, body: SkipRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.skip(token_id, body.reason)
        return TokenStateChangeResponse(**data)
    except ValueError as e:
        if str(e) == "TOKEN_NOT_FOUND":
             raise HTTPException(status_code=404, detail=str(e))
        if str(e) == "INVALID_STATE":
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@router.post(
    "/tokens/{token_id}/complete",
    response_model=CompleteResponse,
    summary="Complete token",
)
def complete_token(token_id: str, body: CompleteRequest, db: Session = Depends(get_db)):
    service = QueueService(db)
    try:
        data = service.complete(token_id)
        return CompleteResponse(**data)
    except ValueError as e:
        if str(e) == "TOKEN_NOT_FOUND":
             raise HTTPException(status_code=404, detail=str(e))
        if str(e) == "INVALID_STATE":
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
