from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import User,UserRole
from app.models.student import Student
from app.models.chat import ChatSession,ChatMessage
from app.schemas.chat import CreateChatRequest,ChatRequest
from app.services.student_context import build_student_context
from app.services.ai_career import generate_career_response
router=APIRouter(prefix="/career-chat",tags=["AI Career Assistant"])
def student(db,uid):
    s=db.query(Student).filter(Student.user_id==uid).first()
    if not s: raise HTTPException(404,"Student profile not found")
    return s
@router.post("/sessions")
def create(data:CreateChatRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=student(db,user.id); x=ChatSession(student_id=s.id,title=data.title or "Career Conversation"); db.add(x); db.commit(); db.refresh(x); return {"success":True,"data":{"session_id":x.id,"title":x.title}}
@router.get("/sessions")
def sessions(db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=student(db,user.id); rows=db.query(ChatSession).filter(ChatSession.student_id==s.id).order_by(ChatSession.id.desc()).all(); return {"success":True,"data":rows}
@router.post("/sessions/{sid}/messages")
def send(sid:int,data:ChatRequest,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=student(db,user.id); sess=db.query(ChatSession).filter(ChatSession.id==sid,ChatSession.student_id==s.id).first()
    if not sess: raise HTTPException(404,"Chat session not found")
    db.add(ChatMessage(session_id=sid,role="user",content=data.message)); db.commit(); hist=db.query(ChatMessage).filter(ChatMessage.session_id==sid).order_by(ChatMessage.id.desc()).limit(10).all()[::-1]
    answer=generate_career_response(build_student_context(db,s,data.opportunity_id),data.message,[{"role":m.role,"content":m.content} for m in hist]); msg=ChatMessage(session_id=sid,role="assistant",content=answer); db.add(msg); db.commit(); db.refresh(msg); return {"success":True,"data":{"message_id":msg.id,"answer":answer}}
@router.get("/sessions/{sid}/messages")
def messages(sid:int,db:Session=Depends(get_db),user:User=Depends(require_roles(UserRole.student))):
    s=student(db,user.id); sess=db.query(ChatSession).filter(ChatSession.id==sid,ChatSession.student_id==s.id).first()
    if not sess: raise HTTPException(404,"Chat session not found")
    return {"success":True,"data":db.query(ChatMessage).filter(ChatMessage.session_id==sid).order_by(ChatMessage.id.asc()).all()}
