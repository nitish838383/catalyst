import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db

from app.models.user import User, UserRole
from app.models.company import Company
from app.models.opportunity import Opportunity
from app.models.application import Application
from app.models.collaboration import Collaboration
from app.models.college import College
from app.models.student import Student

from app.models.recruiter_chat import (
    RecruiterChatSession,
    RecruiterChatMessage,
)

from app.schemas.recruiter_chat import (
    CreateRecruiterChatRequest,
    RecruiterChatRequest,
)

from app.services.recruiter_context import (
    build_recruiter_context,
)

from app.services.ai_recruiter import (
    generate_recruiter_response,
)

from app.services.matching import calculate_match


router = APIRouter(
    prefix="/recruiter-chat",
    tags=["Hiring Intelligence Assistant"],
)


# =========================================================
# GET LOGGED-IN RECRUITER COMPANY
# =========================================================

def get_company(
    db: Session,
    user_id: int,
):

    company = (
        db.query(Company)
        .filter(
            Company.user_id == user_id
        )
        .first()
    )

    if not company:

        raise HTTPException(
            status_code=404,
            detail="Create company profile first",
        )

    return company


# =========================================================
# HELPER
# =========================================================

def enum_value(value):

    if value is None:
        return None

    return getattr(
        value,
        "value",
        value
    )


def extract_id(
    message: str,
    keyword: str,
):

    match = re.search(
        rf"{keyword}\s*(?:id)?\s*#?\s*(\d+)",
        message,
        re.IGNORECASE,
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


# =========================================================
# BASIC DATABASE RESPONSE
# =========================================================

def recruiter_database_response(
    db: Session,
    company: Company,
    message: str,
):

    text = " ".join(
        message
        .strip()
        .lower()
        .split()
    )


    # =====================================================
    # COMPANY PROFILE
    # =====================================================

    if any(
        phrase in text
        for phrase in [
            "my company",
            "company profile",
            "company details",
        ]
    ):

        return (
            "Company Profile\n\n"
            f"Company ID: #{company.id}\n"
            f"Name: {company.name}\n"
            f"Industry: {company.industry or '—'}\n"
            f"Location: {company.location or '—'}\n"
            f"Website: {company.website or '—'}\n"
            f"Verified: {'Yes' if company.is_verified else 'No'}"
        )


    # =====================================================
    # MY OPPORTUNITIES
    # =====================================================

    if any(
        phrase in text
        for phrase in [
            "my opportunities",
            "active opportunities",
            "my jobs",
            "my internships",
        ]
    ):

        rows = (
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


        if not rows:

            return (
                "Your company has not created "
                "any opportunities yet."
            )


        lines = []


        for opportunity in rows:

            applicant_count = (
                db.query(Application)
                .filter(
                    Application.opportunity_id ==
                    opportunity.id
                )
                .count()
            )


            status = (
                "Active"
                if opportunity.is_active
                else "Inactive"
            )


            lines.append(
                f"• #{opportunity.id} "
                f"{opportunity.title} "
                f"— {status} "
                f"— {applicant_count} applicants"
            )


        return (
            f"Your Opportunities ({len(rows)})\n\n"
            + "\n".join(lines)
        )


    # =====================================================
    # MY COLLABORATIONS
    # =====================================================

    if any(
        phrase in text
        for phrase in [
            "my collaborations",
            "collaboration list",
        ]
    ):

        rows = (
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


        if not rows:

            return (
                "Your company has no "
                "collaboration proposals yet."
            )


        lines = [

            (
                f"• #{collaboration.id} "
                f"{collaboration.title} "
                f"— {college.name} "
                f"— {enum_value(collaboration.status)}"
            )

            for collaboration, college
            in rows

        ]


        return (
            f"Your Collaborations ({len(rows)})\n\n"
            + "\n".join(lines)
        )


    # =====================================================
    # OPPORTUNITY / JOB / INTERNSHIP ID
    # =====================================================

    opportunity_id = extract_id(
        text,
        "opportunity",
    )


    if opportunity_id is None:

        opportunity_id = extract_id(
            text,
            "job",
        )


    if opportunity_id is None:

        opportunity_id = extract_id(
            text,
            "internship",
        )


    if opportunity_id is not None:

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


        # Security:
        # dusri company ki opportunity access nahi hogi

        if not opportunity:

            return (
                f"Opportunity #{opportunity_id} "
                f"does not belong to your company "
                f"or was not found."
            )


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


        ranked = []


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


            ranked.append({

                "name":
                    student_user.full_name,

                "student_id":
                    student.id,

                "score":
                    match.get(
                        "score",
                        0
                    ),

                "status":
                    enum_value(
                        application.status
                    ),

                "matched":
                    match.get(
                        "matched_skills",
                        []
                    ),

                "missing":
                    match.get(
                        "missing_skills",
                        []
                    ),
            })


        ranked.sort(
            key=lambda item:
                item["score"],
            reverse=True,
        )


        if not ranked:

            return (
                f"{opportunity.title} "
                f"currently has no applicants."
            )


        lines = []


        for index, candidate in enumerate(
            ranked[:10],
            start=1
        ):

            lines.append(

                f"{index}. "
                f"{candidate['name']} "
                f"(Student #{candidate['student_id']}) "
                f"— {candidate['score']}% match "
                f"— {candidate['status']}\n"

                f"   Matched: "
                f"{', '.join(candidate['matched']) or 'none'}\n"

                f"   Missing: "
                f"{', '.join(candidate['missing']) or 'none'}"

            )


        return (
            f"Applicants for "
            f"{opportunity.title}\n\n"
            + "\n".join(lines)
        )


    return None


# =========================================================
# CREATE CHAT SESSION
# =========================================================

@router.post("/sessions")
def create_session(
    data: CreateRecruiterChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.recruiter
        )
    ),
):

    company = get_company(
        db,
        user.id
    )


    session = RecruiterChatSession(

        company_id=
            company.id,

        title=
            data.title
            or "Hiring Conversation"
    )


    db.add(session)

    db.commit()

    db.refresh(session)


    return {

        "success": True,

        "data": {

            "session_id":
                session.id,

            "title":
                session.title
        }
    }


# =========================================================
# GET MY CHAT SESSIONS
# =========================================================

@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.recruiter
        )
    ),
):

    company = get_company(
        db,
        user.id
    )


    rows = (
        db.query(
            RecruiterChatSession
        )
        .filter(
            RecruiterChatSession.company_id ==
            company.id
        )
        .order_by(
            RecruiterChatSession.id.desc()
        )
        .all()
    )


    return {

        "success": True,

        "data": rows

    }


# =========================================================
# SEND MESSAGE
# =========================================================

@router.post(
    "/sessions/{sid}/messages"
)
def send_message(
    sid: int,
    data: RecruiterChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.recruiter
        )
    ),
):

    company = get_company(
        db,
        user.id
    )


    # -----------------------------------------------------
    # Make sure session belongs to logged-in company
    # -----------------------------------------------------

    session = (
        db.query(
            RecruiterChatSession
        )
        .filter(

            RecruiterChatSession.id ==
            sid,

            RecruiterChatSession.company_id ==
            company.id

        )
        .first()
    )


    if not session:

        raise HTTPException(
            status_code=404,
            detail="Chat session not found",
        )


    clean_message = (
        data.message
        or ""
    ).strip()


    if not clean_message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )


    # =====================================================
    # PREVIOUS HISTORY
    # =====================================================

    history_rows = (
        db.query(
            RecruiterChatMessage
        )
        .filter(
            RecruiterChatMessage.session_id ==
            sid
        )
        .order_by(
            RecruiterChatMessage.id.desc()
        )
        .limit(10)
        .all()
    )[::-1]


    history = [

        {
            "role":
                row.role,

            "content":
                row.content
        }

        for row
        in history_rows

    ]


    # =====================================================
    # SAVE RECRUITER MESSAGE
    # =====================================================

    recruiter_message = (
        RecruiterChatMessage(

            session_id=
                sid,

            role=
                "user",

            content=
                clean_message

        )
    )


    db.add(
        recruiter_message
    )

    db.commit()


    # =====================================================
    # BASIC DATABASE RESPONSE
    # =====================================================

    answer = recruiter_database_response(
        db,
        company,
        clean_message
    )


    # =====================================================
    # AI FALLBACK
    # =====================================================

    if answer is None:

        context = build_recruiter_context(
            db,
            company,
            data.opportunity_id
        )


        answer = generate_recruiter_response(
            context,
            clean_message,
            history
        )


    if not answer:

        answer = (
            "I could not generate a response. "
            "Please try again."
        )


    # =====================================================
    # SAVE ASSISTANT RESPONSE
    # =====================================================

    assistant_message = (
        RecruiterChatMessage(

            session_id=
                sid,

            role=
                "assistant",

            content=
                str(answer)

        )
    )


    db.add(
        assistant_message
    )

    db.commit()

    db.refresh(
        assistant_message
    )


    return {

        "success": True,

        "data": {

            "message_id":
                assistant_message.id,

            "answer":
                str(answer)

        }

    }


# =========================================================
# GET CHAT MESSAGES
# =========================================================

@router.get(
    "/sessions/{sid}/messages"
)
def get_messages(
    sid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.recruiter
        )
    ),
):

    company = get_company(
        db,
        user.id
    )


    session = (
        db.query(
            RecruiterChatSession
        )
        .filter(

            RecruiterChatSession.id ==
            sid,

            RecruiterChatSession.company_id ==
            company.id

        )
        .first()
    )


    if not session:

        raise HTTPException(
            status_code=404,
            detail="Chat session not found",
        )


    rows = (
        db.query(
            RecruiterChatMessage
        )
        .filter(
            RecruiterChatMessage.session_id ==
            sid
        )
        .order_by(
            RecruiterChatMessage.id.asc()
        )
        .all()
    )


    return {

        "success": True,

        "data":
            rows

    }