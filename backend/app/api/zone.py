"""
app/api/zone.py

Zone occupancy endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.repositories.database import get_db
from app.models.models import Zone, _utcnow

router = APIRouter()

@router.get(
    "/{zone_id}/occupancy",
    summary="Get zone occupancy"
)
def get_zone_occupancy(zone_id: str, db: Session = Depends(get_db)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    return {
        "zone_id": zone.id,
        "occupancy": 0,  # Hardware milestone
        "capacity": zone.capacity,
        "capacity_alert": "NORMAL",
        "updated_at": _utcnow()
    }
