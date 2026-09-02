from fastapi import APIRouter,Depends
from app.api.deps import get_current_user
from app.schemas.user import UserResponse
router=APIRouter(prefix="/users",tags=["Users"])
@router.get("/me",response_model=UserResponse)
def me(user=Depends(get_current_user)): return user
