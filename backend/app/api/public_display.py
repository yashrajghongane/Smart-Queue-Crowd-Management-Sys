"""
app/api/public_display.py

Public display route — token board for waiting-area screens. Doc A §2.10.
CURRENT STATUS: Stub — implemented in the staff/display milestone.
"""
from fastapi import APIRouter, HTTPException
from app.schemas.schemas import PublicDisplayResponse

router = APIRouter()


@router.get(
    "/queues/{queue_id}/display",
    response_model=PublicDisplayResponse,
    summary="Public display (STUB)",
)
def get_public_display(queue_id: str):
    raise HTTPException(
        status_code=501,
        detail="Public display is implemented in the staff/display milestone.",
    )
