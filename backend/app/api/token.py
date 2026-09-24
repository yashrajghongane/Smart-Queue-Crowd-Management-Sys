"""
app/api/token.py

Token-level action routes — HOLD, RECALL, SKIP, COMPLETE.
These act on individual tokens by token_id. Doc A §2.5–2.8.

Owns: token action route definitions and HTTP semantics only.
All state transition logic belongs in queue_service.py.

CURRENT STATUS: All stubs returning 501 — token actions are the next milestone.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.repositories.database import get_db
from app.schemas.schemas import (
    TokenStateChangeResponse,
    HoldRequest,
    RecallRequest,
    SkipRequest,
    CompleteRequest,
    CompleteResponse,
)

router = APIRouter()

_NEXT_MILESTONE_MSG = (
    "Token state actions are implemented in the staff dashboard milestone."
)


@router.post(
    "/{token_id}/hold",
    response_model=TokenStateChangeResponse,
    summary="Hold token (STUB)",
    description="Transitions WAITING or SERVING token to HOLD. Doc A §2.5.",
)
def hold_token(token_id: str, body: HoldRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)


@router.post(
    "/{token_id}/recall",
    response_model=TokenStateChangeResponse,
    summary="Recall token (STUB)",
    description="Returns HOLD or SKIPPED token to WAITING; SERVING stays SERVING. Doc A §2.6.",
)
def recall_token(token_id: str, body: RecallRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)


@router.post(
    "/{token_id}/skip",
    response_model=TokenStateChangeResponse,
    summary="Skip token (STUB)",
    description="Skips a WAITING, SERVING, or HOLD token. Doc A §2.7.",
)
def skip_token(token_id: str, body: SkipRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)


@router.post(
    "/{token_id}/complete",
    response_model=CompleteResponse,
    summary="Complete token (STUB)",
    description="Marks SERVING token as COMPLETED. Doc A §2.8.",
)
def complete_token(token_id: str, body: CompleteRequest, db: Session = Depends(get_db)):
    raise HTTPException(status_code=501, detail=_NEXT_MILESTONE_MSG)
