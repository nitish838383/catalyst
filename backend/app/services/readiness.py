from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.skill import Skill, StudentSkill
from app.models.project import Project
from app.models.certification import Certification
from app.services.career_roles import CAREER_ROLES


def _normalize_skill_name(value: str) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def calculate_readiness(
    db: Session,
    student,
    role: str,
    selected_skill_ids: Optional[Iterable[int]] = None,
):
    """
    Calculate career readiness.

    selected_skill_ids:
        - If provided, ONLY these confirmed skills are used for the
          skill score. This is the correct mode for Resume AI.
        - If omitted, the function falls back to all StudentSkill rows,
          preserving compatibility with the normal student profile flow.
    """

    role_key = str(role or "").strip().lower()
    cfg = CAREER_ROLES.get(role_key)

    if not cfg:
        return {
            "error": "Unsupported career role"
        }

    # --------------------------------------------------
    # SKILLS USED FOR THIS ANALYSIS
    # --------------------------------------------------
    if selected_skill_ids is not None:
        skill_ids = {
            int(skill_id)
            for skill_id in selected_skill_ids
            if skill_id is not None
        }

        if skill_ids:
            skill_rows = (
                db.query(Skill)
                .filter(Skill.id.in_(skill_ids))
                .all()
            )

            student_skill_names = {
                _normalize_skill_name(skill.name)
                for skill in skill_rows
            }
        else:
            student_skill_names = set()

        analysis_source = "confirmed_resume_skills"

    else:
        rows = (
            db.query(StudentSkill, Skill)
            .join(
                Skill,
                StudentSkill.skill_id == Skill.id,
            )
            .filter(
                StudentSkill.student_id == student.id
            )
            .all()
        )

        student_skill_names = {
            _normalize_skill_name(skill.name)
            for _, skill in rows
        }

        analysis_source = "student_profile_skills"

    # --------------------------------------------------
    # ROLE REQUIREMENTS
    # --------------------------------------------------
    required_skills = [
        _normalize_skill_name(skill)
        for skill in cfg.get("required_skills", [])
        if _normalize_skill_name(skill)
    ]

    matched_skills = [
        skill
        for skill in required_skills
        if skill in student_skill_names
    ]

    missing_skills = [
        skill
        for skill in required_skills
        if skill not in student_skill_names
    ]

    skill_score = (
        len(matched_skills)
        / len(required_skills)
        * 100
        if required_skills
        else 0
    )

    # --------------------------------------------------
    # PROJECT / CERTIFICATION / PROFILE COMPONENTS
    # --------------------------------------------------
    project_count = (
        db.query(Project)
        .filter(Project.student_id == student.id)
        .count()
    )

    project_score = min(
        project_count * 25,
        100,
    )

    certification_count = (
        db.query(Certification)
        .filter(Certification.student_id == student.id)
        .count()
    )

    certification_score = min(
        certification_count * 20,
        100,
    )

    profile_fields = [
        getattr(student, "college_name", None),
        getattr(student, "branch", None),
        getattr(student, "year", None),
        getattr(student, "semester", None),
        getattr(student, "career_goal", None),
        getattr(student, "bio", None),
        getattr(student, "github_url", None),
        getattr(student, "linkedin_url", None),
        getattr(student, "portfolio_url", None),
    ]

    completed_profile_fields = sum(
        value not in (None, "")
        for value in profile_fields
    )

    profile_score = (
        completed_profile_fields
        / len(profile_fields)
        * 100
        if profile_fields
        else 0
    )

    # --------------------------------------------------
    # FINAL READINESS
    # --------------------------------------------------
    final_score = (
        0.55 * skill_score
        + 0.20 * project_score
        + 0.10 * certification_score
        + 0.15 * profile_score
    )

    return {
        "target_role": role_key,
        "analysis_source": analysis_source,
        "readiness_score": round(final_score, 2),
        "skill_score": round(skill_score, 2),
        "project_score": round(project_score, 2),
        "certification_score": round(certification_score, 2),
        "profile_score": round(profile_score, 2),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "confirmed_skill_count": len(student_skill_names),
        "required_skill_count": len(required_skills),
    }
