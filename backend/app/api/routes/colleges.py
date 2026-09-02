from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User,UserRole
from app.models.college import College
from app.models.department import Department
from app.models.collaboration import Collaboration
from app.schemas.college import CollegeProfileCreate,DepartmentCreate
from app.schemas.collaboration import CollaborationStatusUpdate
from app.services.college_analytics import get_college_summary,get_top_student_skills,get_industry_skill_demand,get_skill_gap_analysis
router=APIRouter(prefix="/colleges",tags=["College / TPO"])
def college(db,uid):
    c=db.query(College).filter(College.user_id==uid).first()
    if not c: raise HTTPException(404,"College profile not found")
    return c
@router.post("/profile")
def profile(data:CollegeProfileCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.college))):
    if db.query(College).filter(College.user_id==user.id).first(): raise HTTPException(409,"College profile exists")
    c=College(user_id=user.id,**data.model_dump()); db.add(c); db.commit(); db.refresh(c); return c
@router.post("/departments")
def dept(data:DepartmentCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.college))):
    c=college(db,user.id); d=Department(college_id=c.id,**data.model_dump()); db.add(d); db.commit(); db.refresh(d); return d
@router.get("/departments")
def depts(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.college))):
    c=college(db,user.id); return {"success":True,"data":db.query(Department).filter(Department.college_id==c.id).all()}
@router.get("/dashboard/summary")
def summary(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.college))): return {"success":True,"data":get_college_summary(db,college(db,user.id).id)}
@router.get("/analytics/student-skills")
def sskills(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.college))): return {"success":True,"data":get_top_student_skills(db,college(db,user.id).id)}
@router.get("/analytics/industry-demand")
def demand(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.college))): college(db,user.id); return {"success":True,"data":get_industry_skill_demand(db)}
@router.get("/analytics/skill-gap")
def gaps(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.college))): return {"success":True,"data":get_skill_gap_analysis(db,college(db,user.id).id)}
@router.get("/collaborations")
def collabs(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.college))):
    c=college(db,user.id); return {"success":True,"data":db.query(Collaboration).filter(Collaboration.college_id==c.id).all()}
@router.patch("/collaborations/{cid}/status")
def cstatus(cid:int,data:CollaborationStatusUpdate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.college))):
    c=college(db,user.id); row=db.query(Collaboration).filter(Collaboration.id==cid,Collaboration.college_id==c.id).first()
    if not row: raise HTTPException(404,"Collaboration not found")
    row.status=data.status; row.college_note=data.college_note; db.commit(); return {"success":True}
