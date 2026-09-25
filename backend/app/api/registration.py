from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.schemas import RegistrationRequest, RegistrationResponse, DuplicateActiveVisitResponse
from app.services.registration_service import RegistrationService

router = APIRouter()

def _run_registration(body: RegistrationRequest, source: str, db: Session):
    service = RegistrationService(db)
    try:
        is_duplicate, data = service.register(
            full_name=body.full_name,
            mobile=body.mobile,
            department_id=body.department_id,
            source=source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if is_duplicate:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=DuplicateActiveVisitResponse(**data).model_dump(),
        )
    return RegistrationResponse(**data)

@router.post("/qr", response_model=RegistrationResponse, status_code=201, responses={409: {"model": DuplicateActiveVisitResponse}})
def register_qr(body: RegistrationRequest, db: Session = Depends(get_db)):
    return _run_registration(body, "QR", db)

@router.post("/staff", response_model=RegistrationResponse, status_code=201, responses={409: {"model": DuplicateActiveVisitResponse}})
def register_staff(body: RegistrationRequest, db: Session = Depends(get_db)):
    return _run_registration(body, "STAFF", db)
