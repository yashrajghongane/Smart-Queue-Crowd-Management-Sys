"""
app/api/zones.py

Zone occupancy and crowd management endpoints for staff dashboard.
Document A §2.10 & Requirements Section 8.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_staff
from app.models.models import StaffUser
from app.repositories.database import get_db
from app.schemas.schemas import ZoneOccupancyResponse, CrowdDetailResponse
from app.services.occupancy_service import OccupancyService

router = APIRouter()


@router.get(
    "/{zone_id}/occupancy",
    response_model=ZoneOccupancyResponse,
    summary="Zone Occupancy Summary",
    description="Returns current physical occupancy and capacity alert for a zone. Document A §2.10.",
)
def get_zone_occupancy(
    zone_id: str,
    db: Session = Depends(get_db),
    current_staff: StaffUser = Depends(get_current_staff),
):
    service = OccupancyService(db)
    data = service.get_zone_occupancy(zone_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_id}' not found.",
        )
    return ZoneOccupancyResponse(**data)


@router.get(
    "/{zone_id}/crowd",
    response_model=CrowdDetailResponse,
    summary="Detailed Zone Crowd Status",
    description=(
        "Returns comprehensive crowd metrics including occupancy, capacity, utilization, "
        "alert level, entries today, exits today, net change, and device diagnostic status. "
        "Section 8 & 9."
    ),
)
def get_zone_crowd(
    zone_id: str,
    db: Session = Depends(get_db),
    current_staff: StaffUser = Depends(get_current_staff),
):
    service = OccupancyService(db)
    data = service.get_crowd_detail(zone_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_id}' not found.",
        )
    return CrowdDetailResponse(**data)
