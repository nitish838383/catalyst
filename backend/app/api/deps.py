from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, UserRole

security=HTTPBearer()
def get_current_user(credentials:HTTPAuthorizationCredentials=Depends(security),db:Session=Depends(get_db)):
    try:
        payload=jwt.decode(credentials.credentials,settings.SECRET_KEY,algorithms=[settings.ALGORITHM]); uid=payload.get("sub")
        if not uid: raise HTTPException(401,"Invalid token")
    except JWTError: raise HTTPException(401,"Invalid or expired token")
    user=db.query(User).filter(User.id==int(uid)).first()
    if not user: raise HTTPException(401,"User not found")
    if not user.is_active: raise HTTPException(403,"Account disabled")
    return user

def require_roles(*roles:UserRole):
    def checker(user:User=Depends(get_current_user)):
        if user.role not in roles: raise HTTPException(403,"You do not have permission")
        return user
    return checker
