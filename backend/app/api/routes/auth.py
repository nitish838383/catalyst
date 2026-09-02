from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import RegisterRequest,LoginRequest,AuthResponse
from app.services.auth import get_user_by_email,create_user,authenticate_user
from app.core.security import create_access_token
router=APIRouter(prefix="/auth",tags=["Authentication"])
@router.post("/register",response_model=AuthResponse)
def register(data:RegisterRequest,db:Session=Depends(get_db)):
    if get_user_by_email(db,data.email): raise HTTPException(409,"Email already registered")
    user=create_user(db,data.full_name,data.email,data.password,data.role); return {"success":True,"message":"Registration successful","access_token":create_access_token(user.id)}
@router.post("/login",response_model=AuthResponse)
def login(data:LoginRequest,db:Session=Depends(get_db)):
    user=authenticate_user(db,data.email,data.password)
    if not user: raise HTTPException(401,"Invalid email or password")
    if not user.is_active: raise HTTPException(403,"Account disabled")
    return {"success":True,"message":"Login successful","access_token":create_access_token(user.id)}
