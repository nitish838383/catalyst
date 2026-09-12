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
    """
    Deterministic recruiter answers for private company data.

    This layer handles common database-backed recruiter questions
    before falling back to the AI service.
    """

    text = " ".join(
        (message or "")
        .strip()
        .lower()
        .split()
    )

    if not text:
        return None


    # =====================================================
    # COMPANY PROFILE
    # =====================================================

    if any(
        phrase in text
        for phrase in [
            "my company",
            "company profile",
            "company details",
            "show company",
            "our company",
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
    # OPPORTUNITY SUMMARY
    # =====================================================

    if any(
        phrase in text
        for phrase in [
            "my opportunities",
            "active opportunities",
            "my jobs",
            "my internships",
            "show opportunities",
            "show jobs",
            "show internships",
        ]
    ):
        rows = (
            db.query(Opportunity)
            .filter(
                Opportunity.company_id == company.id
            )
            .order_by(
                Opportunity.id.desc()
            )
            .all()
        )

        if not rows:
            return (
                "Your company has not created any opportunities yet."
            )

        lines = []

        for opportunity in rows:
            applicant_count = (
                db.query(Application)
                .filter(
                    Application.opportunity_id == opportunity.id
                )
                .count()
            )

            status = (
                "Active"
                if opportunity.is_active
                else "Inactive"
            )

            opportunity_type = enum_value(
                getattr(
                    opportunity,
                    "opportunity_type",
                    None,
                )
            ) or "Opportunity"

            lines.append(
                f"• #{opportunity.id} "
                f"{opportunity.title} "
                f"— {opportunity_type} "
                f"— {status} "
                f"— {applicant_count} applicants"
            )

        return (
            f"Your Opportunities ({len(rows)})\n\n"
            + "\n".join(lines)
        )


    # =====================================================
    # TOTAL APPLICANTS / APPLICATION SUMMARY
    # =====================================================

    if any(
        phrase in text
        for phrase in [
            "total applicants",
            "total applications",
            "how many applicants",
            "how many applications",
            "application summary",
            "applicant summary",
        ]
    ):
        opportunities = (
            db.query(Opportunity)
            .filter(
                Opportunity.company_id == company.id
            )
            .all()
        )

        if not opportunities:
            return (
                "Your company has no opportunities yet, "
                "so there are no applications to summarize."
            )

        lines = []
        grand_total = 0

        for opportunity in opportunities:
            count = (
                db.query(Application)
                .filter(
                    Application.opportunity_id == opportunity.id
                )
                .count()
            )

            grand_total += count

            lines.append(
                f"• #{opportunity.id} "
                f"{opportunity.title}: "
                f"{count} applicants"
            )

        return (
            f"Application Summary\n\n"
            f"Total applicants across your opportunities: {grand_total}\n\n"
            + "\n".join(lines)
        )


    # =====================================================
    # COLLABORATIONS
    # =====================================================

    if any(
        phrase in text
        for phrase in [
            "my collaborations",
            "collaboration list",
            "collaboration proposals",
            "my proposals",
            "proposal history",
            "show collaborations",
        ]
    ):
        rows = (
            db.query(
                Collaboration,
                College
            )
            .join(
                College,
                Collaboration.college_id == College.id
            )
            .filter(
                Collaboration.company_id == company.id
            )
            .order_by(
                Collaboration.id.desc()
            )
            .all()
        )

        if not rows:
            return (
                "Your company has no collaboration proposals yet."
            )

        lines = []

        for collaboration, college in rows:
            collaboration_type = enum_value(
                getattr(
                    collaboration,
                    "collaboration_type",
                    None,
                )
            ) or "Collaboration"

            status = enum_value(
                getattr(
                    collaboration,
                    "status",
                    None,
                )
            ) or "pending"

            mode = enum_value(
                getattr(
                    collaboration,
                    "mode",
                    None,
                )
            )

            proposed_date = getattr(
                collaboration,
                "proposed_date",
                None,
            )

            detail_parts = [
                f"#{collaboration.id}",
                collaboration.title,
                college.name,
                str(collaboration_type),
                str(status),
            ]

            if mode:
                detail_parts.append(str(mode))

            if proposed_date:
                detail_parts.append(str(proposed_date))

            lines.append(
                "• " + " — ".join(detail_parts)
            )

        return (
            f"Your Collaborations ({len(rows)})\n\n"
            + "\n".join(lines)
        )


    # =====================================================
    # FILTER COLLABORATIONS BY STATUS
    # =====================================================

    requested_status = None

    if "pending collaboration" in text or "pending proposal" in text:
        requested_status = "pending"
    elif "approved collaboration" in text or "approved proposal" in text:
        requested_status = "approved"
    elif "rejected collaboration" in text or "rejected proposal" in text:
        requested_status = "rejected"
    elif "ongoing collaboration" in text:
        requested_status = "ongoing"

    if requested_status:
        rows = (
            db.query(
                Collaboration,
                College
            )
            .join(
                College,
                Collaboration.college_id == College.id
            )
            .filter(
                Collaboration.company_id == company.id
            )
            .order_by(
                Collaboration.id.desc()
            )
            .all()
        )

        filtered = []

        for collaboration, college in rows:
            status = str(
                enum_value(
                    getattr(
                        collaboration,
                        "status",
                        None,
                    )
                ) or "pending"
            ).lower()

            if status == requested_status:
                filtered.append(
                    (
                        collaboration,
                        college,
                        status,
                    )
                )

        if not filtered:
            return (
                f"You currently have no {requested_status} "
                f"collaboration proposals."
            )

        lines = [
            (
                f"• #{collaboration.id} "
                f"{collaboration.title} "
                f"— {college.name} "
                f"— {status}"
            )
            for collaboration, college, status
            in filtered
        ]

        return (
            f"{requested_status.title()} Collaborations "
            f"({len(filtered)})\n\n"
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
                Opportunity.id == opportunity_id,
                Opportunity.company_id == company.id
            )
            .first()
        )

        # Security: another company's opportunity is never exposed.
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
                Application.student_id == Student.id
            )
            .join(
                User,
                Student.user_id == User.id
            )
            .filter(
                Application.opportunity_id == opportunity.id
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
                "name": student_user.full_name,
                "student_id": student.id,
                "score": float(
                    match.get(
                        "score",
                        0
                    ) or 0
                ),
                "status": enum_value(
                    application.status
                ) or "applied",
                "matched": match.get(
                    "matched_skills",
                    []
                ),
                "missing": match.get(
                    "missing_skills",
                    []
                ),
            })

        ranked.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        if not ranked:
            return (
                f"{opportunity.title} currently has no applicants."
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
                f"— {round(candidate['score'], 2)}% match "
                f"— {candidate['status']}\n"
                f"   Matched: "
                f"{', '.join(candidate['matched']) or 'none'}\n"
                f"   Missing: "
                f"{', '.join(candidate['missing']) or 'none'}"
            )

        return (
            f"Applicants for {opportunity.title}\n\n"
            + "\n".join(lines)
        )


    # =====================================================
    # NATURAL TOP-CANDIDATE QUERY WITHOUT OPPORTUNITY ID
    # =====================================================

    if any(
        phrase in text
        for phrase in [
            "best candidates",
            "top candidates",
            "top applicants",
            "best applicants",
            "rank candidates",
            "rank applicants",
        ]
    ):
        return (
            "Please include the opportunity ID so I can rank only "
            "the applicants for your company's specific role.\n\n"
            "Example: “Show top candidates for opportunity 5”"
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

        try:
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

        except Exception as error:
            print(
                "[recruiter-chat] AI fallback failed:",
                error
            )

            answer = (
                "I could not generate the AI response right now. "
                "You can still ask me about your company, opportunities, "
                "applicants, match scores or collaboration proposals."
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