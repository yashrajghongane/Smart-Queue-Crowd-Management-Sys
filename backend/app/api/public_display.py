"""
app/api/public_display.py

Public display route — token board for waiting-area screens. Doc A §2.10.
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schemas.schemas import PublicDisplayResponse
from app.repositories.database import get_db
from app.services.display_service import DisplayService

router = APIRouter()

@router.get(
    "/queues/{queue_id}/display",
    response_model=PublicDisplayResponse,
    summary="Public display",
)
def get_public_display(queue_id: str, db: Session = Depends(get_db)):
    service = DisplayService(db)
    data = service.get_public_display(queue_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Queue not found")
    return data
