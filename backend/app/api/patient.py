"""
app/api/patient.py

Patient-facing read endpoint: token/queue status.
Owns: patient status route only. Doc A §2.9.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.schemas import PatientStatusResponse
from app.services.display_service import DisplayService

router = APIRouter()


@router.get(
    "/visits/{visit_id}/status",
    response_model=PatientStatusResponse,
    summary="Patient token status",
    description=(
        "Returns the patient's current token state, position in queue, "
        "and the currently serving token. "
        "Frontend should poll this endpoint to refresh status. Doc A §2.9."
    ),
)
def get_patient_status(
    visit_id: str,
    db: Session = Depends(get_db),
):
    service = DisplayService(db)
    status = service.get_patient_status(visit_id)
    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"Visit '{visit_id}' not found.",
        )
    return PatientStatusResponse(**status)
