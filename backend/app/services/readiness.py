from sqlalchemy.orm import Session
from app.models.skill import Skill, StudentSkill
from app.models.project import Project
from app.models.certification import Certification
from app.services.career_roles import CAREER_ROLES

def calculate_readiness(db: Session, student, role: str):
    cfg = CAREER_ROLES.get(role.strip().lower())
    if not cfg: return {"error":"Unsupported career role"}
    rows = db.query(StudentSkill, Skill).join(Skill, StudentSkill.skill_id == Skill.id).filter(StudentSkill.student_id == student.id).all()
    names = {s.name for _, s in rows}; req = cfg["required_skills"]
    matched=[s for s in req if s in names]; missing=[s for s in req if s not in names]
    skill_score = len(matched)/len(req)*100 if req else 0
    project_score = min(db.query(Project).filter(Project.student_id==student.id).count()*25,100)
    cert_score = min(db.query(Certification).filter(Certification.student_id==student.id).count()*20,100)
    fields=[student.college_name,student.branch,student.year,student.semester,student.career_goal,student.bio,student.github_url,student.linkedin_url,student.portfolio_url]
    profile_score = sum(v not in (None,"") for v in fields)/len(fields)*100
    final = .55*skill_score+.20*project_score+.10*cert_score+.15*profile_score
    return {"target_role":role,"readiness_score":round(final,2),"skill_score":round(skill_score,2),"project_score":project_score,"certification_score":cert_score,"profile_score":round(profile_score,2),"matched_skills":matched,"missing_skills":missing}
