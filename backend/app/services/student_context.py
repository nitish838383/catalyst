from app.models.skill import Skill, StudentSkill
from app.models.project import Project
from app.models.certification import Certification
from app.models.opportunity import Opportunity
from app.services.readiness import calculate_readiness
from app.services.matching import calculate_match

def build_student_context(db, student, opportunity_id=None):
    skill_rows=db.query(StudentSkill,Skill).join(Skill,StudentSkill.skill_id==Skill.id).filter(StudentSkill.student_id==student.id).all()
    projects=db.query(Project).filter(Project.student_id==student.id).all(); certs=db.query(Certification).filter(Certification.student_id==student.id).all()
    readiness=None
    if student.career_goal:
        r=calculate_readiness(db,student,student.career_goal)
        if "error" not in r: readiness=r
    opp_ctx=None
    if opportunity_id:
        opp=db.query(Opportunity).filter(Opportunity.id==opportunity_id,Opportunity.is_active==True).first()
        if opp: opp_ctx={"id":opp.id,"title":opp.title,"description":opp.description,"location":opp.location,"match":calculate_match(db,student.id,opp.id)}
    return {"profile":{"branch":student.branch,"year":student.year,"semester":student.semester,"career_goal":student.career_goal,"bio":student.bio,"github":student.github_url,"linkedin":student.linkedin_url,"portfolio":student.portfolio_url},"skills":[{"name":s.name,"level":ss.level,"verified":ss.is_verified,"source":ss.source} for ss,s in skill_rows],"projects":[{"title":p.title,"description":p.description,"technologies":p.technologies} for p in projects],"certifications":[{"name":c.name,"organization":c.organization} for c in certs],"readiness":readiness,"selected_opportunity":opp_ctx}
