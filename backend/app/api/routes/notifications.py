from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
router=APIRouter(prefix="/notifications",tags=["Notifications"])
@router.get("")
def list_n(db:Session=Depends(get_db),user=Depends(get_current_user)):
    rows=db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(100).all(); return {"success":True,"unread_count":sum(not x.is_read for x in rows),"data":rows}
@router.patch("/{nid}/read")
def read(nid:int,db:Session=Depends(get_db),user=Depends(get_current_user)):
    n=db.query(Notification).filter(Notification.id==nid,Notification.user_id==user.id).first()
    if not n: raise HTTPException(404,"Notification not found")
    n.is_read=True; db.commit(); return {"success":True}
@router.patch("/read-all")
def allread(db:Session=Depends(get_db),user=Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id==user.id,Notification.is_read==False).update({"is_read":True},synchronize_session=False); db.commit(); return {"success":True}
