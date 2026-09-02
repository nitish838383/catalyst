from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User,UserRole
from app.models.student import Student
from app.models.roadmap import LearningRoadmap,RoadmapStep
from app.services.readiness import calculate_readiness
from app.services.roadmap_generator import generate_roadmap_steps
router=APIRouter(prefix="/career",tags=["Career Intelligence"])
def get_student(db,uid):
    s=db.query(Student).filter(Student.user_id==uid).first()
    if not s: raise HTTPException(404,"Student profile not found")
    return s
@router.get("/readiness")
def readiness(role:str,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    r=calculate_readiness(db,get_student(db,user.id),role)
    if "error" in r: raise HTTPException(400,r['error'])
    return {"success":True,"data":r}
@router.post("/roadmap")
def create_roadmap(role:str,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); r=calculate_readiness(db,s,role)
    if "error" in r: raise HTTPException(400,r['error'])
    road=LearningRoadmap(student_id=s.id,target_role=role,title=f"{role.title()} Roadmap"); db.add(road); db.flush()
    steps=generate_roadmap_steps(r['missing_skills'])
    for st in steps: db.add(RoadmapStep(roadmap_id=road.id,**st))
    db.commit(); return {"success":True,"roadmap_id":road.id,"current_readiness":r['readiness_score'],"roadmap":steps}
@router.patch("/roadmap/steps/{sid}/complete")
def complete(sid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); step=db.query(RoadmapStep).join(LearningRoadmap,RoadmapStep.roadmap_id==LearningRoadmap.id).filter(RoadmapStep.id==sid,LearningRoadmap.student_id==s.id).first()
    if not step: raise HTTPException(404,"Roadmap step not found")
    step.completed=True; db.commit(); return {"success":True}
@router.get("/roadmap/{rid}/progress")
def progress(rid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); road=db.query(LearningRoadmap).filter(LearningRoadmap.id==rid,LearningRoadmap.student_id==s.id).first()
    if not road: raise HTTPException(404,"Roadmap not found")
    total=db.query(RoadmapStep).filter(RoadmapStep.roadmap_id==rid).count(); done=db.query(RoadmapStep).filter(RoadmapStep.roadmap_id==rid,RoadmapStep.completed==True).count(); return {"success":True,"total_steps":total,"completed_steps":done,"progress":round(done/total*100,2) if total else 0}
