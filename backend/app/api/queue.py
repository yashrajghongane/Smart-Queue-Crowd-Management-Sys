"""Staff queue-level routes. Document A §2.3–§2.4."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.schemas import QueueSummaryResponse, CallNextResponse, NoWaitingTokensResponse
from app.services.queue_service import QueueService, QueueNotFoundError, NoWaitingTokensError

router = APIRouter()

@router.get("/{queue_id}", response_model=QueueSummaryResponse, summary="Queue summary")
def get_queue_summary(queue_id: str, db: Session = Depends(get_db)):
    try:
        return QueueService(db).get_queue_summary(queue_id)
    except QueueNotFoundError:
        raise HTTPException(status_code=404, detail="Queue not found")

@router.post(
    "/{queue_id}/call-next",
    response_model=CallNextResponse,
    status_code=200,
    responses={409: {"model": NoWaitingTokensResponse}},
    summary="Call next token",
)
def call_next(queue_id: str, db: Session = Depends(get_db)):
    try:
        return QueueService(db).call_next(queue_id)
    except QueueNotFoundError:
        raise HTTPException(status_code=404, detail="Queue not found")
    except NoWaitingTokensError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=NoWaitingTokensResponse().model_dump(),
        )
