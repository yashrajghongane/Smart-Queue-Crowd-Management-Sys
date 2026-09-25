"""Token-level action routes. Document A §2.5–§2.8."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.schemas import (
    TokenStateChangeResponse, HoldRequest, RecallRequest,
    SkipRequest, CompleteRequest, CompleteResponse,
)
from app.services.queue_service import (
    QueueService, TokenNotFoundError, InvalidTransitionError,
)

router = APIRouter()

def _service_error(exc: ValueError):
    if isinstance(exc, TokenNotFoundError):
        raise HTTPException(status_code=404, detail="Token not found")
    if isinstance(exc, InvalidTransitionError):
        raise HTTPException(status_code=409, detail="INVALID_STATE")
    raise HTTPException(status_code=400, detail=str(exc))

@router.post("/{token_id}/hold", response_model=TokenStateChangeResponse, summary="Hold token")
def hold_token(token_id: str, body: HoldRequest, db: Session = Depends(get_db)):
    try:
        return QueueService(db).hold(token_id, body.reason)
    except ValueError as exc:
        _service_error(exc)

@router.post("/{token_id}/recall", response_model=TokenStateChangeResponse, summary="Recall token")
def recall_token(token_id: str, body: RecallRequest, db: Session = Depends(get_db)):
    try:
        return QueueService(db).recall(token_id)
    except ValueError as exc:
        _service_error(exc)

@router.post("/{token_id}/skip", response_model=TokenStateChangeResponse, summary="Skip token")
def skip_token(token_id: str, body: SkipRequest, db: Session = Depends(get_db)):
    try:
        return QueueService(db).skip(token_id, body.reason)
    except ValueError as exc:
        _service_error(exc)

@router.post("/{token_id}/complete", response_model=CompleteResponse, summary="Complete token")
def complete_token(token_id: str, body: CompleteRequest, db: Session = Depends(get_db)):
    try:
        return QueueService(db).complete(token_id)
    except ValueError as exc:
        _service_error(exc)
