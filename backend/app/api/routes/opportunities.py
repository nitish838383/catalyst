from fastapi import APIRouter,Depends,Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.opportunity import Opportunity,OpportunitySkill
from app.models.skill import Skill
router=APIRouter(prefix="/opportunities",tags=["Opportunities"])
@router.get("")
def list_opportunities(search:str|None=None,opportunity_type:str|None=None,location:str|None=None,page:int=Query(1,ge=1),limit:int=Query(20,ge=1,le=100),db:Session=Depends(get_db)):
    q=db.query(Opportunity).filter(Opportunity.is_active==True)
    if search:
        p=f"%{search}%"; q=q.filter(or_(Opportunity.title.ilike(p),Opportunity.description.ilike(p)))
    if opportunity_type: q=q.filter(Opportunity.opportunity_type==opportunity_type)
    if location: q=q.filter(Opportunity.location.ilike(f"%{location}%"))
    total=q.count(); rows=q.offset((page-1)*limit).limit(limit).all(); data=[]
    for o in rows:
        sk=db.query(OpportunitySkill,Skill).join(Skill,OpportunitySkill.skill_id==Skill.id).filter(OpportunitySkill.opportunity_id==o.id).all()
        data.append({"id":o.id,"title":o.title,"description":o.description,"type":o.opportunity_type,"location":o.location,"stipend":o.stipend,"skills":[{"name":s.name,"required":r.is_required,"weight":r.weight} for r,s in sk]})
    return {"success":True,"pagination":{"page":page,"limit":limit,"total":total},"data":data}
