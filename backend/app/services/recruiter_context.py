from sqlalchemy.orm import Session

from app.models.user import User
from app.models.company import Company
from app.models.college import College
from app.models.student import Student
from app.models.skill import Skill, StudentSkill
from app.models.opportunity import (
    Opportunity,
    OpportunitySkill,
)
from app.models.application import Application
from app.models.collaboration import Collaboration

from app.services.matching import calculate_match


def enum_value(value):

    if value is None:
        return None

    return getattr(
        value,
        "value",
        value
    )


def build_recruiter_context(
    db: Session,
    company: Company,
    opportunity_id: int | None = None
):

    # =====================================================
    # COMPANY OPPORTUNITIES
    # =====================================================

    opportunities = (
        db.query(Opportunity)
        .filter(
            Opportunity.company_id ==
            company.id
        )
        .order_by(
            Opportunity.id.desc()
        )
        .all()
    )


    opportunity_data = []


    for opportunity in opportunities:

        application_count = (
            db.query(Application)
            .filter(
                Application.opportunity_id ==
                opportunity.id
            )
            .count()
        )


        skill_rows = (
            db.query(
                OpportunitySkill,
                Skill
            )
            .join(
                Skill,
                OpportunitySkill.skill_id ==
                Skill.id
            )
            .filter(
                OpportunitySkill.opportunity_id ==
                opportunity.id
            )
            .all()
        )


        opportunity_data.append({

            "id":
                opportunity.id,

            "title":
                opportunity.title,

            "type":
                enum_value(
                    opportunity.opportunity_type
                ),

            "description":
                opportunity.description,

            "location":
                opportunity.location,

            "stipend":
                opportunity.stipend,

            "experience_required":
                opportunity.experience_required,

            "is_active":
                opportunity.is_active,

            "application_count":
                application_count,

            "skills": [

                {
                    "name":
                        skill.name,

                    "required":
                        row.is_required,

                    "weight":
                        row.weight
                }

                for row, skill
                in skill_rows
            ]
        })


    # =====================================================
    # SELECTED OPPORTUNITY
    # =====================================================

    selected_opportunity = None

    candidates = []


    if opportunity_id:

        opportunity = (
            db.query(Opportunity)
            .filter(
                Opportunity.id ==
                opportunity_id,

                Opportunity.company_id ==
                company.id
            )
            .first()
        )


        if opportunity:

            selected_opportunity = {

                "id":
                    opportunity.id,

                "title":
                    opportunity.title,

                "type":
                    enum_value(
                        opportunity.opportunity_type
                    ),

                "description":
                    opportunity.description,

                "location":
                    opportunity.location
            }


            # =================================================
            # APPLICANTS
            # =================================================

            rows = (
                db.query(
                    Application,
                    Student,
                    User
                )
                .join(
                    Student,
                    Application.student_id ==
                    Student.id
                )
                .join(
                    User,
                    Student.user_id ==
                    User.id
                )
                .filter(
                    Application.opportunity_id ==
                    opportunity.id
                )
                .all()
            )


            for (
                application,
                student,
                student_user
            ) in rows:

                match = calculate_match(
                    db,
                    student.id,
                    opportunity.id
                )


                # =============================================
                # STUDENT SKILLS
                # =============================================

                student_skill_rows = (
                    db.query(
                        StudentSkill,
                        Skill
                    )
                    .join(
                        Skill,
                        StudentSkill.skill_id ==
                        Skill.id
                    )
                    .filter(
                        StudentSkill.student_id ==
                        student.id
                    )
                    .all()
                )


                candidates.append({

                    "application_id":
                        application.id,

                    "student_id":
                        student.id,

                    "name":
                        student_user.full_name,

                    "email":
                        student_user.email,

                    "branch":
                        student.branch,

                    "year":
                        student.year,

                    "semester":
                        student.semester,

                    "career_goal":
                        student.career_goal,

                    "status":
                        enum_value(
                            application.status
                        ),

                    "match_score":
                        match.get(
                            "score",
                            0
                        ),

                    "matched_skills":
                        match.get(
                            "matched_skills",
                            []
                        ),

                    "missing_skills":
                        match.get(
                            "missing_skills",
                            []
                        ),

                    "profile_skills": [

                        skill.name

                        for student_skill, skill
                        in student_skill_rows
                    ]
                })


            candidates.sort(

                key=lambda item:
                    item["match_score"],

                reverse=True
            )


    # =====================================================
    # COLLABORATIONS
    # =====================================================

    collaboration_rows = (
        db.query(
            Collaboration,
            College
        )
        .join(
            College,
            Collaboration.college_id ==
            College.id
        )
        .filter(
            Collaboration.company_id ==
            company.id
        )
        .order_by(
            Collaboration.id.desc()
        )
        .all()
    )


    collaborations = [

        {

            "id":
                collaboration.id,

            "title":
                collaboration.title,

            "type":
                enum_value(
                    collaboration.collaboration_type
                ),

            "status":
                enum_value(
                    collaboration.status
                ),

            "college_id":
                college.id,

            "college_name":
                college.name,

            "mode":
                collaboration.mode,

            "location":
                collaboration.location,

            "proposed_date":
                collaboration.proposed_date
        }

        for collaboration, college
        in collaboration_rows
    ]


    # =====================================================
    # FINAL CONTEXT
    # =====================================================

    return {

        "company": {

            "id":
                company.id,

            "name":
                company.name,

            "industry":
                company.industry,

            "website":
                company.website,

            "description":
                company.description,

            "location":
                company.location,

            "is_verified":
                company.is_verified
        },


        "opportunities":
            opportunity_data,


        "selected_opportunity":
            selected_opportunity,


        "candidates":
            candidates,


        "collaborations":
            collaborations
    }