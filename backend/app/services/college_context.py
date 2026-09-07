from sqlalchemy.orm import Session

from app.models.college import College
from app.models.department import Department
from app.models.collaboration import Collaboration

from app.services.college_analytics import (
    get_college_summary,
    get_top_student_skills,
    get_industry_skill_demand,
    get_skill_gap_analysis,
)


def build_college_context(
    db: Session,
    college: College
):
    """
    Logged-in college ke real backend data ko
    College AI ke liye context me convert karta hai.
    """

    # ========================================================
    # Departments
    # ========================================================

    departments = (
        db.query(Department)
        .filter(
            Department.college_id == college.id
        )
        .order_by(
            Department.name.asc()
        )
        .all()
    )

    # ========================================================
    # Collaborations
    # ========================================================

    collaborations = (
        db.query(Collaboration)
        .filter(
            Collaboration.college_id == college.id
        )
        .all()
    )

    collaboration_data = []

    for row in collaborations:

        collaboration_type = (
            getattr(row, "type", None)
            or getattr(
                row,
                "collaboration_type",
                None
            )
        )

        collaboration_status = getattr(
            row,
            "status",
            None
        )

        collaboration_data.append(
            {
                "id": row.id,

                "company_id": getattr(
                    row,
                    "company_id",
                    None
                ),

                "title": getattr(
                    row,
                    "title",
                    None
                ),

                "description": getattr(
                    row,
                    "description",
                    None
                ),

                "type": (
                    collaboration_type.value
                    if hasattr(
                        collaboration_type,
                        "value"
                    )
                    else (
                        str(collaboration_type)
                        if collaboration_type
                        else None
                    )
                ),

                "status": (
                    collaboration_status.value
                    if hasattr(
                        collaboration_status,
                        "value"
                    )
                    else (
                        str(collaboration_status)
                        if collaboration_status
                        else None
                    )
                ),

                "mode": getattr(
                    row,
                    "mode",
                    None
                ),

                "location": getattr(
                    row,
                    "location",
                    None
                ),

                "proposed_date": getattr(
                    row,
                    "proposed_date",
                    None
                ),

                "college_note": getattr(
                    row,
                    "college_note",
                    None
                ),
            }
        )

    # ========================================================
    # Existing College Analytics
    # ========================================================

    summary = get_college_summary(
        db,
        college.id
    )

    student_skills = get_top_student_skills(
        db,
        college.id,
        limit=15
    )

    industry_demand = get_industry_skill_demand(
        db,
        limit=15
    )

    skill_gap = get_skill_gap_analysis(
        db,
        college.id
    )

    # ========================================================
    # Final College AI Context
    # ========================================================

    return {

        "college": {
            "id": college.id,
            "name": college.name,
            "university": college.university,
            "city": college.city,
            "state": college.state,
            "website": college.website,
            "is_verified": college.is_verified,
        },

        "departments": [
            {
                "id": row.id,
                "name": row.name,
                "code": row.code,
            }
            for row in departments
        ],

        "summary": summary,

        "student_skills": student_skills,

        "industry_demand": industry_demand,

        "skill_gap": skill_gap,

        "collaborations": collaboration_data,
    }