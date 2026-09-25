"""
app/api/auth.py

Authentication endpoints for Staff and Admin users.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_staff
from app.models.models import StaffUser
from app.repositories.database import get_db
from app.schemas.schemas import LoginRequest, TokenResponse, StaffUserResponse

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Staff/Admin Login",
    description="Authenticates staff user by username and password, returning JWT access token.",
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    # Lookup staff user by username
    user = (
        db.query(StaffUser)
        .filter(StaffUser.username == body.username)
        .first()
    )

    # Constant-time comparison safely handled by bcrypt
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    # Create JWT
    token = create_access_token(
        subject=user.id,
        role=user.role,
        extra_claims={"username": user.username, "display_name": user.display_name},
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=user.role,
        display_name=user.display_name,
        user_id=user.id,
    )


@router.get(
    "/me",
    response_model=StaffUserResponse,
    summary="Get Current User Profile",
    description="Returns profile information for the authenticated staff user.",
)
def get_me(current_user: StaffUser = Depends(get_current_staff)):
    return StaffUserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        role=current_user.role,
        active=current_user.active,
    )
