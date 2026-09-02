from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.user import User,UserRole
from app.models.student import Student
from app.models.skill import Skill,StudentSkill
from app.models.project import Project
from app.models.certification import Certification
from app.models.opportunity import Opportunity
from app.models.application import Application,ApplicationStatus
from app.models.assessment import SkillAssessment
from app.models.collaboration import Collaboration,CollaborationStatus
from app.models.collaboration_participant import CollaborationParticipant
from app.schemas.student import StudentProfileCreate,StudentProfileUpdate,StudentProfileResponse
from app.schemas.skill import AddSkillRequest,AssessmentSubmit
from app.schemas.project import ProjectCreate,ProjectResponse
from app.schemas.certification import CertificationCreate,CertificationResponse
from app.services.matching import calculate_match
router=APIRouter(prefix="/students",tags=["Students"])
def get_student(db,uid):
    s=db.query(Student).filter(Student.user_id==uid).first()
    if not s: raise HTTPException(404,"Create student profile first")
    return s
@router.post("/profile",response_model=StudentProfileResponse)
def create_profile(data:StudentProfileCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    if db.query(Student).filter(Student.user_id==user.id).first(): raise HTTPException(409,"Student profile already exists")
    s=Student(user_id=user.id,**data.model_dump()); db.add(s); db.commit(); db.refresh(s); return s
@router.get("/profile",response_model=StudentProfileResponse)
def profile(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))): return get_student(db,user.id)
@router.patch("/profile",response_model=StudentProfileResponse)
def update_profile(data:StudentProfileUpdate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id)
    for k,v in data.model_dump(exclude_unset=True).items(): setattr(s,k,v)
    db.commit(); db.refresh(s); return s
@router.post("/skills")
def add_skill(data:AddSkillRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); name=data.name.strip().lower(); skill=db.query(Skill).filter(Skill.name==name).first()
    if not skill: skill=Skill(name=name,category=data.category); db.add(skill); db.flush()
    if db.query(StudentSkill).filter(StudentSkill.student_id==s.id,StudentSkill.skill_id==skill.id).first(): raise HTTPException(409,"Skill already added")
    ss=StudentSkill(student_id=s.id,skill_id=skill.id,level=data.level,source="manual"); db.add(ss); db.commit(); return {"success":True,"id":ss.id,"skill":skill.name}
@router.get("/skills")
def skills(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); rows=db.query(StudentSkill,Skill).join(Skill,StudentSkill.skill_id==Skill.id).filter(StudentSkill.student_id==s.id).all(); return {"success":True,"data":[{"id":ss.id,"name":sk.name,"level":ss.level,"source":ss.source,"verified":ss.is_verified} for ss,sk in rows]}
@router.delete("/skills/{sid}")
def del_skill(sid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); r=db.query(StudentSkill).filter(StudentSkill.id==sid,StudentSkill.student_id==s.id).first()
    if not r: raise HTTPException(404,"Skill not found")
    db.delete(r); db.commit(); return {"success":True}
@router.post("/projects",response_model=ProjectResponse)
def project(data:ProjectCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); p=Project(student_id=s.id,**data.model_dump()); db.add(p); db.commit(); db.refresh(p); return p
@router.get("/projects",response_model=list[ProjectResponse])
def projects(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); return db.query(Project).filter(Project.student_id==s.id).all()
@router.post("/certifications",response_model=CertificationResponse)
def cert(data:CertificationCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); c=Certification(student_id=s.id,**data.model_dump()); db.add(c); db.commit(); db.refresh(c); return c
@router.get("/certifications",response_model=list[CertificationResponse])
def certs(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); return db.query(Certification).filter(Certification.student_id==s.id).all()
@router.get("/opportunities/{oid}/match")
def match(oid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); o=db.query(Opportunity).filter(Opportunity.id==oid,Opportunity.is_active==True).first()
    if not o: raise HTTPException(404,"Opportunity not found")
    return {"success":True,"match":calculate_match(db,s.id,o.id)}
@router.post("/opportunities/{oid}/apply")
def apply(oid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); o=db.query(Opportunity).filter(Opportunity.id==oid,Opportunity.is_active==True).first()
    if not o: raise HTTPException(404,"Opportunity not found")
    if db.query(Application).filter(Application.student_id==s.id,Application.opportunity_id==oid).first(): raise HTTPException(409,"Already applied")
    a=Application(student_id=s.id,opportunity_id=oid); db.add(a); db.commit(); db.refresh(a); return {"success":True,"application_id":a.id,"status":a.status}
@router.get("/applications")
def applications(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); rows=db.query(Application,Opportunity).join(Opportunity,Application.opportunity_id==Opportunity.id).filter(Application.student_id==s.id).all(); return {"success":True,"data":[{"application_id":a.id,"opportunity_id":o.id,"title":o.title,"status":a.status,"recruiter_note":a.recruiter_note,"applied_at":a.applied_at} for a,o in rows]}
@router.patch("/applications/{aid}/withdraw")
def withdraw(aid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); a=db.query(Application).filter(Application.id==aid,Application.student_id==s.id).first()
    if not a: raise HTTPException(404,"Application not found")
    if a.status in [ApplicationStatus.selected,ApplicationStatus.rejected,ApplicationStatus.withdrawn]: raise HTTPException(400,"Cannot withdraw")
    a.status=ApplicationStatus.withdrawn; db.commit(); return {"success":True}
@router.post("/assessments")
def assessment(data:AssessmentSubmit,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id)
    if data.total_questions<=0 or data.correct_answers<0 or data.correct_answers>data.total_questions: raise HTTPException(400,"Invalid assessment values")
    score=data.correct_answers/data.total_questions*100; level="advanced" if score>=80 else "intermediate" if score>=50 else "beginner"
    a=SkillAssessment(student_id=s.id,skill_id=data.skill_id,score=round(score,2),level=level,total_questions=data.total_questions,correct_answers=data.correct_answers); db.add(a)
    ss=db.query(StudentSkill).filter(StudentSkill.student_id==s.id,StudentSkill.skill_id==data.skill_id).first()
    if ss: ss.level=level; ss.is_verified=True; ss.source="assessment"; ss.confidence_score=score/100
    db.commit(); return {"success":True,"score":round(score,2),"level":level}
@router.post("/collaborations/{cid}/register")
def collab_register(cid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=get_student(db,user.id); c=db.query(Collaboration).filter(Collaboration.id==cid,Collaboration.status.in_([CollaborationStatus.approved,CollaborationStatus.ongoing])).first()
    if not c: raise HTTPException(404,"Collaboration not available")
    if db.query(CollaborationParticipant).filter(CollaborationParticipant.collaboration_id==cid,CollaborationParticipant.student_id==s.id).first(): raise HTTPException(409,"Already registered")
    p=CollaborationParticipant(collaboration_id=cid,student_id=s.id); db.add(p); db.commit(); return {"success":True,"registration_id":p.id}
