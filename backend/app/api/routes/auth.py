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


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# ============================================================
# REGISTER
# TEMPORARILY DISABLED
# ============================================================

@router.post("/register", response_model=AuthResponse)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    raise HTTPException(
        status_code=403,
        detail="New account registration is temporarily disabled."
    )

    # Registration code preserved for future use
    if get_user_by_email(db, data.email):
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    user = create_user(
        db,
        data.full_name,
        data.email,
        data.password,
        data.role
    )

    return {
        "success": True,
        "message": "Registration successful",
        "access_token": create_access_token(user.id)
    }


# ============================================================
# LOGIN
# Existing accounts can still login
# ============================================================

@router.post("/login", response_model=AuthResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = authenticate_user(
        db,
        data.email,
        data.password
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account disabled"
        )

    return {
        "success": True,
        "message": "Login successful",
        "access_token": create_access_token(user.id)
    }