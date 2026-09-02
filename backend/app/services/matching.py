from sqlalchemy.orm import Session
from app.models.skill import Skill, StudentSkill
from app.models.opportunity import OpportunitySkill

def calculate_match(db: Session, student_id: int, opportunity_id: int):
    student_rows = db.query(StudentSkill, Skill).join(Skill, StudentSkill.skill_id == Skill.id).filter(StudentSkill.student_id == student_id).all()
    req_rows = db.query(OpportunitySkill, Skill).join(Skill, OpportunitySkill.skill_id == Skill.id).filter(OpportunitySkill.opportunity_id == opportunity_id).all()
    student_ids = {s.id for _, s in student_rows}
    total = matched = 0.0; matched_skills=[]; missing_skills=[]
    for req, skill in req_rows:
        total += req.weight
        if skill.id in student_ids:
            matched += req.weight; matched_skills.append(skill.name)
        else:
            missing_skills.append(skill.name)
    score = 0 if total == 0 else matched / total * 100
    return {"score": round(score, 2), "matched_skills": matched_skills, "missing_skills": missing_skills, "total_required_skills": len(req_rows)}
