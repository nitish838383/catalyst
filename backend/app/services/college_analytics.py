from sqlalchemy import func
from app.models.student import Student
from app.models.skill import Skill, StudentSkill
from app.models.application import Application, ApplicationStatus
from app.models.opportunity import Opportunity, OpportunitySkill

def get_college_summary(db,college_id):
    student_ids=[r.id for r in db.query(Student.id).filter(Student.college_id==college_id).all()]
    if not student_ids: return {"total_students":0,"total_skills":0,"applications":0,"shortlisted":0,"interviews":0,"selected":0}
    q=lambda status=None: db.query(Application).filter(Application.student_id.in_(student_ids), *([Application.status==status] if status else [])).count()
    return {"total_students":len(student_ids),"total_skills":db.query(StudentSkill).filter(StudentSkill.student_id.in_(student_ids)).count(),"applications":q(),"shortlisted":q(ApplicationStatus.shortlisted),"interviews":q(ApplicationStatus.interview),"selected":q(ApplicationStatus.selected)}

def get_top_student_skills(db,college_id,limit=10):
    rows=db.query(Skill.name,func.count(StudentSkill.id)).join(StudentSkill,StudentSkill.skill_id==Skill.id).join(Student,Student.id==StudentSkill.student_id).filter(Student.college_id==college_id).group_by(Skill.id,Skill.name).order_by(func.count(StudentSkill.id).desc()).limit(limit).all()
    return [{"skill":n,"students":c} for n,c in rows]

def get_industry_skill_demand(db,limit=15):
    rows=db.query(Skill.name,func.count(OpportunitySkill.id)).join(OpportunitySkill,OpportunitySkill.skill_id==Skill.id).join(Opportunity,Opportunity.id==OpportunitySkill.opportunity_id).filter(Opportunity.is_active==True).group_by(Skill.id,Skill.name).order_by(func.count(OpportunitySkill.id).desc()).limit(limit).all()
    return [{"skill":n,"demand":c} for n,c in rows]

def get_skill_gap_analysis(db,college_id):
    total_students=db.query(Student).filter(Student.college_id==college_id).count(); total_opps=db.query(Opportunity).filter(Opportunity.is_active==True).count()
    if not total_students or not total_opps: return []
    demand=db.query(Skill.id,Skill.name,func.count(OpportunitySkill.id)).join(OpportunitySkill,OpportunitySkill.skill_id==Skill.id).join(Opportunity,Opportunity.id==OpportunitySkill.opportunity_id).filter(Opportunity.is_active==True).group_by(Skill.id,Skill.name).all(); out=[]
    for sid,name,count in demand:
        sc=db.query(StudentSkill).join(Student,Student.id==StudentSkill.student_id).filter(Student.college_id==college_id,StudentSkill.skill_id==sid).count(); d=count/total_opps*100; s=sc/total_students*100; gap=d-s
        out.append({"skill":name,"industry_demand_percentage":round(d,2),"student_supply_percentage":round(s,2),"gap_percentage":round(gap,2),"severity":"high" if gap>=30 else "medium" if gap>=15 else "low"})
    return sorted(out,key=lambda x:x['gap_percentage'],reverse=True)
