from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.skill import Skill, StudentSkill
from app.models.opportunity import OpportunitySkill


def calculate_match(
    db: Session,
    student_id: int,
    opportunity_id: int,
    selected_skill_ids: Optional[Iterable[int]] = None,
):
    """
    Calculate opportunity match.

    If selected_skill_ids is provided, ONLY those skills are used.
    This is useful for Resume AI after the student confirms the skills
    detected in the current resume.

    If selected_skill_ids is None, the function falls back to the
    student's saved StudentSkill profile so existing pages keep working.
    """

    # --------------------------------------------------
    # STUDENT SKILLS
    # --------------------------------------------------
    if selected_skill_ids is not None:
        student_ids = {
            int(skill_id)
            for skill_id in selected_skill_ids
            if skill_id is not None
        }
    else:
        student_rows = (
            db.query(StudentSkill, Skill)
            .join(
                Skill,
                StudentSkill.skill_id == Skill.id,
            )
            .filter(
                StudentSkill.student_id == student_id,
            )
            .all()
        )

        student_ids = {
            skill.id
            for _, skill in student_rows
        }

    # --------------------------------------------------
    # OPPORTUNITY REQUIRED SKILLS
    # --------------------------------------------------
    req_rows = (
        db.query(OpportunitySkill, Skill)
        .join(
            Skill,
            OpportunitySkill.skill_id == Skill.id,
        )
        .filter(
            OpportunitySkill.opportunity_id == opportunity_id,
        )
        .all()
    )

    # No required skills defined for this opportunity.
    if not req_rows:
        return {
            "score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
            "total_required_skills": 0,
            "message": "No required skills defined for this opportunity",
        }

    total_weight = 0.0
    matched_weight = 0.0

    matched_skills = []
    missing_skills = []

    # --------------------------------------------------
    # MATCHING
    # --------------------------------------------------
    for requirement, skill in req_rows:
        weight = float(
            getattr(requirement, "weight", 1) or 1
        )

        total_weight += weight

        if skill.id in student_ids:
            matched_weight += weight
            matched_skills.append(skill.name)
        else:
            missing_skills.append(skill.name)

    score = (
        0.0
        if total_weight == 0
        else (matched_weight / total_weight) * 100
    )

    return {
        "score": round(score, 2),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "total_required_skills": len(req_rows),
    }
