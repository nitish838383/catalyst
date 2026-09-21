from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse
from app.services.auth import (
    get_user_by_email,
    create_user,
    authenticate_user,
)
from app.core.security import create_access_token
from app.api.deps import get_current_user
from app.models.user import User, UserRole


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================
# REGISTER
# PUBLIC REGISTRATION
# Admin accounts must NEVER be created from this endpoint.
# ============================================================

@router.post("/register", response_model=AuthResponse)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    # Prevent public admin registration.
    if data.role == UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Admin accounts cannot be created through public registration",
        )

    # Prevent duplicate email accounts.
    if get_user_by_email(db, data.email):
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    user = create_user(
        db,
        data.full_name,
        data.email,
        data.password,
        data.role,
    )

    return {
        "success": True,
        "message": "Registration successful",
        "access_token": create_access_token(user.id),
    }


# ============================================================
# LOGIN
# Same endpoint is used by Student / College / Recruiter / Admin.
# Authorization is enforced by role checks after login.
# ============================================================

@router.post("/login", response_model=AuthResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db,
        data.email,
        data.password,
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account disabled",
        )

    return {
        "success": True,
        "message": "Login successful",
        "access_token": create_access_token(user.id),
    }


# ============================================================
# CURRENT USER
# Used by frontend after login to decide the correct dashboard.
# ============================================================

@router.get("/me")
def me(
    current_user: User = Depends(get_current_user),
):
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "role": current_user.role.value,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
        },
    }
