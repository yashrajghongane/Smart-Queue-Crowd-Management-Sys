"""
app/api/registration.py

QR and staff-assisted registration endpoints.
Owns: route definition and HTTP semantics only.
All registration business logic is in registration_service.py.
Doc A §2.1, §2.2.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.schemas import (
    RegistrationRequest,
    RegistrationResponse,
    DuplicateActiveVisitResponse,
)
from app.services.registration_service import RegistrationService

router = APIRouter()


def _run_registration(
    body: RegistrationRequest,
    source: str,
    db: Session,
):
    """
    Shared logic for QR and staff registration — both converge to the same service.
    Returns the appropriate FastAPI response.
    """
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
        # Doc A §2.1 — active visit exists, return 409
        raise HTTPException(
            status_code=409,
            detail=DuplicateActiveVisitResponse(**data).model_dump(),
        )

    # Doc A §2.1 — new registration, return 201
    return RegistrationResponse(**data)


@router.post(
    "/qr",
    response_model=RegistrationResponse,
    status_code=201,
    summary="QR registration",
    description=(
        "Patient self-registers via QR code / web form. "
        "Returns 409 ACTIVE_VISIT_EXISTS if the patient already has an active token "
        "for the same department. Doc A §2.1."
    ),
)
def register_qr(
    body: RegistrationRequest,
    db: Session = Depends(get_db),
):
    return _run_registration(body, source="QR", db=db)


@router.post(
    "/staff",
    response_model=RegistrationResponse,
    status_code=201,
    summary="Staff-assisted registration",
    description=(
        "Staff registers a patient on their behalf. "
        "Uses identical underlying logic as QR registration. "
        "Returns 409 ACTIVE_VISIT_EXISTS on duplicate. Doc A §2.2."
    ),
)
def register_staff(
    body: RegistrationRequest,
    db: Session = Depends(get_db),
):
    return _run_registration(body, source="STAFF", db=db)
