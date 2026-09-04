from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.skill import Skill
from app.models.application import Application
from app.models.user import User, UserRole


router = APIRouter(
    prefix="/opportunities",
    tags=["Opportunities"]
)


# ============================================================
# LIST ALL ACTIVE OPPORTUNITIES
# ============================================================

@router.get("")
def list_opportunities(
    search: str | None = None,
    opportunity_type: str | None = None,
    location: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):

    q = db.query(Opportunity).filter(
        Opportunity.is_active == True
    )

    # Search by title or description
    if search:

        p = f"%{search}%"

        q = q.filter(
            or_(
                Opportunity.title.ilike(p),
                Opportunity.description.ilike(p)
            )
        )

    # Filter by opportunity type
    if opportunity_type:

        q = q.filter(
            Opportunity.opportunity_type == opportunity_type
        )

    # Filter by location
    if location:

        q = q.filter(
            Opportunity.location.ilike(
                f"%{location}%"
            )
        )

    # Total results
    total = q.count()

    # Pagination
    rows = (
        q.offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    data = []

    # Get skills for every opportunity
    for o in rows:

        skills = (
            db.query(
                OpportunitySkill,
                Skill
            )
            .join(
                Skill,
                OpportunitySkill.skill_id == Skill.id
            )
            .filter(
                OpportunitySkill.opportunity_id == o.id
            )
            .all()
        )

        data.append({
            "id": o.id,
            "title": o.title,
            "description": o.description,
            "type": o.opportunity_type,
            "location": o.location,
            "stipend": o.stipend,
            "skills": [
                {
                    "name": skill.name,
                    "required": opportunity_skill.is_required,
                    "weight": opportunity_skill.weight
                }
                for opportunity_skill, skill in skills
            ]
        })

    return {
        "success": True,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total
        },
        "data": data
    }


# ============================================================
# PUBLIC PLATFORM LIVE STATISTICS
# ============================================================

@router.get("/platform/stats")
def platform_stats(
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # Registered Students
    # --------------------------------------------------------

    students = (
        db.query(User)
        .filter(
            User.role == UserRole.student
        )
        .count()
    )


    # --------------------------------------------------------
    # Registered Colleges
    # --------------------------------------------------------

    colleges = (
        db.query(User)
        .filter(
            User.role == UserRole.college
        )
        .count()
    )


    # --------------------------------------------------------
    # Registered Industry / Recruiters
    # --------------------------------------------------------

    companies = (
        db.query(User)
        .filter(
            User.role == UserRole.recruiter
        )
        .count()
    )


    # --------------------------------------------------------
    # Active Opportunities
    # --------------------------------------------------------

    opportunities = (
        db.query(Opportunity)
        .filter(
            Opportunity.is_active == True
        )
        .count()
    )


    # --------------------------------------------------------
    # Skills Tracked
    # --------------------------------------------------------

    skills = (
        db.query(Skill)
        .count()
    )


    # --------------------------------------------------------
    # Total Applications
    # --------------------------------------------------------

    applications = (
        db.query(Application)
        .count()
    )


    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "success": True,
        "data": {
            "students": students,
            "colleges": colleges,
            "companies": companies,
            "opportunities": opportunities,
            "skills": skills,
            "applications": applications
        }
    }