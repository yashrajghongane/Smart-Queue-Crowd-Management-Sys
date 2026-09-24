from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.repositories.database import get_db
from app.schemas.schemas import PublicDisplayResponse
from app.models.models import Token, Queue, _utcnow

router = APIRouter()

@router.get(
    "/queues/{queue_id}/display",
    response_model=PublicDisplayResponse,
    summary="Public display",
)
def get_public_display(queue_id: str, db: Session = Depends(get_db)):
    queue = db.query(Queue).filter(Queue.id == queue_id).first()
    if not queue:
        raise HTTPException(status_code=404, detail="Queue not found")

    serving_token = db.query(Token).filter(
        Token.queue_id == queue_id,
        Token.state == "SERVING"
    ).first()

    next_token = db.query(Token).filter(
        Token.queue_id == queue_id,
        Token.state == "WAITING"
    ).order_by(Token.sequence_number.asc()).first()

    waiting_count = db.query(Token).filter(
        Token.queue_id == queue_id,
        Token.state == "WAITING"
    ).count()

    return PublicDisplayResponse(
        queue_id=queue.id,
        serving_token=serving_token.token_number if serving_token else None,
        next_token=next_token.token_number if next_token else None,
        waiting_count=waiting_count,
        updated_at=_utcnow()
    )
