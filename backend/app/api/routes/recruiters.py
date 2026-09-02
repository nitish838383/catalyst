from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.user import User,UserRole
from app.models.company import Company
from app.models.college import College
from app.models.student import Student
from app.models.skill import Skill
from app.models.opportunity import Opportunity,OpportunitySkill
from app.models.application import Application,ApplicationStatus
from app.models.interview import Interview
from app.models.collaboration import Collaboration,CollaborationSkill
from app.schemas.company import CompanyCreate
from app.schemas.opportunity import OpportunityCreate,OpportunitySkillCreate
from app.schemas.application import ApplicationStatusUpdate,InterviewScheduleRequest
from app.schemas.collaboration import CollaborationCreate
from app.services.matching import calculate_match
from app.services.notifications import create_notification
router=APIRouter(prefix="/recruiters",tags=["Recruiters"])
def get_company(db,uid):
    c=db.query(Company).filter(Company.user_id==uid).first()
    if not c: raise HTTPException(404,"Create company profile first")
    return c
@router.post("/company")
def create_company(data:CompanyCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))):
    if db.query(Company).filter(Company.user_id==user.id).first(): raise HTTPException(409,"Company profile already exists")
    c=Company(user_id=user.id,**data.model_dump()); db.add(c); db.commit(); db.refresh(c); return c
@router.get("/company")
def company(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))): return get_company(db,user.id)
@router.post("/opportunities")
def create_opp(data:OpportunityCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))):
    c=get_company(db,user.id); o=Opportunity(company_id=c.id,**data.model_dump()); db.add(o); db.commit(); db.refresh(o); return o
@router.post("/opportunities/{oid}/skills")
def add_opp_skill(oid:int,data:OpportunitySkillCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))):
    c=get_company(db,user.id); o=db.query(Opportunity).filter(Opportunity.id==oid,Opportunity.company_id==c.id).first()
    if not o: raise HTTPException(404,"Opportunity not found")
    name=data.skill_name.strip().lower(); sk=db.query(Skill).filter(Skill.name==name).first()
    if not sk: sk=Skill(name=name,category=data.category); db.add(sk); db.flush()
    if db.query(OpportunitySkill).filter(OpportunitySkill.opportunity_id==oid,OpportunitySkill.skill_id==sk.id).first(): raise HTTPException(409,"Skill already added")
    row=OpportunitySkill(opportunity_id=oid,skill_id=sk.id,is_required=data.is_required,weight=data.weight); db.add(row); db.commit(); return {"success":True}
@router.get("/opportunities/{oid}/applications")
def applicants(oid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))):
    c=get_company(db,user.id); o=db.query(Opportunity).filter(Opportunity.id==oid,Opportunity.company_id==c.id).first()
    if not o: raise HTTPException(404,"Opportunity not found")
    rows=db.query(Application,Student,User).join(Student,Application.student_id==Student.id).join(User,Student.user_id==User.id).filter(Application.opportunity_id==oid).all(); out=[]
    for a,s,u in rows:
        m=calculate_match(db,s.id,oid); out.append({"application_id":a.id,"student_id":s.id,"name":u.full_name,"email":u.email,"match_score":m['score'],"matched_skills":m['matched_skills'],"missing_skills":m['missing_skills'],"status":a.status})
    return {"success":True,"candidates":sorted(out,key=lambda x:x['match_score'],reverse=True)}
@router.patch("/applications/{aid}/status")
def status(aid:int,data:ApplicationStatusUpdate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))):
    c=get_company(db,user.id); row=db.query(Application,Opportunity,Student).join(Opportunity,Application.opportunity_id==Opportunity.id).join(Student,Application.student_id==Student.id).filter(Application.id==aid,Opportunity.company_id==c.id).first()
    if not row: raise HTTPException(404,"Application not found")
    a,o,s=row; a.status=data.status; a.recruiter_note=data.recruiter_note; create_notification(db,s.user_id,f"Application Update: {o.title}",f"Status changed to {data.status.value}.","application_update",a.id); db.commit(); return {"success":True,"status":a.status}
@router.post("/applications/{aid}/interview")
def interview(aid:int,data:InterviewScheduleRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))):
    c=get_company(db,user.id); row=db.query(Application,Opportunity,Student).join(Opportunity,Application.opportunity_id==Opportunity.id).join(Student,Application.student_id==Student.id).filter(Application.id==aid,Opportunity.company_id==c.id).first()
    if not row: raise HTTPException(404,"Application not found")
    a,o,s=row; iv=db.query(Interview).filter(Interview.application_id==aid).first()
    if iv:
        for k,v in data.model_dump().items(): setattr(iv,k,v)
    else: db.add(Interview(application_id=aid,**data.model_dump()))
    a.status=ApplicationStatus.interview; create_notification(db,s.user_id,"Interview Scheduled",f"Interview scheduled for {o.title}.","interview",aid); db.commit(); return {"success":True}
@router.post("/collaborations")
def create_collab(data:CollaborationCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))):
    c=get_company(db,user.id); college=db.query(College).filter(College.id==data.college_id).first()
    if not college: raise HTTPException(404,"College not found")
    coll=Collaboration(company_id=c.id,college_id=college.id,collaboration_type=data.collaboration_type,title=data.title,description=data.description,proposed_date=data.proposed_date,location=data.location,mode=data.mode); db.add(coll); db.flush()
    for n in data.skills:
        name=n.strip().lower(); sk=db.query(Skill).filter(Skill.name==name).first()
        if not sk: sk=Skill(name=name); db.add(sk); db.flush()
        db.add(CollaborationSkill(collaboration_id=coll.id,skill_id=sk.id))
    create_notification(db,college.user_id,"New Industry Collaboration Proposal",f"{c.name} proposed {coll.title}","collaboration",coll.id); db.commit(); return {"success":True,"id":coll.id}
