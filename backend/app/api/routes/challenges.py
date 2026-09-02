from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.user import User,UserRole
from app.models.company import Company
from app.models.student import Student
from app.models.challenge import IndustryChallenge,ChallengeSubmission,ChallengeStatus
from app.schemas.challenge import ChallengeCreate,ChallengeSubmissionCreate,SubmissionEvaluation
router=APIRouter(prefix="/challenges",tags=["Industry Challenges"])
@router.post("")
def create(data:ChallengeCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))):
    c=db.query(Company).filter(Company.user_id==user.id).first()
    if not c: raise HTTPException(404,"Create company profile first")
    x=IndustryChallenge(company_id=c.id,**data.model_dump()); db.add(x); db.commit(); db.refresh(x); return {"success":True,"data":x}
@router.get("")
def listc(db:Session=Depends(get_db)): return {"success":True,"data":db.query(IndustryChallenge).filter(IndustryChallenge.status==ChallengeStatus.open).all()}
@router.post("/{cid}/submit")
def submit(cid:int,data:ChallengeSubmissionCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=db.query(Student).filter(Student.user_id==user.id).first(); c=db.query(IndustryChallenge).filter(IndustryChallenge.id==cid,IndustryChallenge.status==ChallengeStatus.open).first()
    if not s or not c: raise HTTPException(404,"Challenge/student not found")
    if db.query(ChallengeSubmission).filter(ChallengeSubmission.challenge_id==cid,ChallengeSubmission.student_id==s.id).first(): raise HTTPException(409,"Already submitted")
    x=ChallengeSubmission(challenge_id=cid,student_id=s.id,**data.model_dump()); db.add(x); db.commit(); db.refresh(x); return {"success":True,"submission_id":x.id}
@router.patch("/submissions/{sid}/evaluate")
def eval(sid:int,data:SubmissionEvaluation,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.recruiter))):
    c=db.query(Company).filter(Company.user_id==user.id).first(); row=db.query(ChallengeSubmission,IndustryChallenge).join(IndustryChallenge,ChallengeSubmission.challenge_id==IndustryChallenge.id).filter(ChallengeSubmission.id==sid,IndustryChallenge.company_id==c.id).first()
    if not row: raise HTTPException(404,"Submission not found")
    x,_=row; x.status=data.status; x.score=data.score; x.feedback=data.feedback; db.commit(); return {"success":True}
