from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.user import User,UserRole
from app.models.company import Company
from app.models.college import College
router=APIRouter(prefix="/admin",tags=["Admin"])
@router.get("/dashboard")
def dash(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.admin))): return {"success":True,"data":{"users":db.query(User).count(),"companies":db.query(Company).count(),"colleges":db.query(College).count(),"pending_companies":db.query(Company).filter(Company.is_verified==False).count(),"pending_colleges":db.query(College).filter(College.is_verified==False).count()}}
@router.patch("/companies/{cid}/verify")
def vc(cid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.admin))):
    c=db.query(Company).filter(Company.id==cid).first();
    if not c: raise HTTPException(404,"Company not found")
    c.is_verified=True; db.commit(); return {"success":True}
@router.patch("/colleges/{cid}/verify")
def vcol(cid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.admin))):
    c=db.query(College).filter(College.id==cid).first();
    if not c: raise HTTPException(404,"College not found")
    c.is_verified=True; db.commit(); return {"success":True}
@router.patch("/users/{uid}/block")
def block(uid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.admin))):
    if uid==user.id: raise HTTPException(400,"Cannot block yourself")
    u=db.query(User).filter(User.id==uid).first();
    if not u: raise HTTPException(404,"User not found")
    u.is_active=False; db.commit(); return {"success":True}
