from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.collaboration import Collaboration,CollaborationStatus
router=APIRouter(prefix="/collaborations",tags=["Academia Industry Collaboration"])
@router.get("")
def active(db:Session=Depends(get_db)): return {"success":True,"data":db.query(Collaboration).filter(Collaboration.status.in_([CollaborationStatus.approved,CollaborationStatus.ongoing])).all()}
