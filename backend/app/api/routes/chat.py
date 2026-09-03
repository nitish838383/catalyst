import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db

from app.models.user import User, UserRole
from app.models.student import Student
from app.models.chat import ChatSession, ChatMessage
from app.models.company import Company
from app.models.opportunity import Opportunity

from app.schemas.chat import CreateChatRequest, ChatRequest

from app.services.student_context import build_student_context
from app.services.ai_career import generate_career_response


router = APIRouter(
    prefix="/career-chat",
    tags=["AI Career Assistant"]
)


def student(db, uid):

    s = (
        db.query(Student)
        .filter(
            Student.user_id == uid
        )
        .first()
    )

    if not s:

        raise HTTPException(
            404,
            "Student profile not found"
        )

    return s


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
    keyword: str
):

    pattern = (
        rf"{keyword}\s*"
        rf"(?:id)?\s*"
        rf"#?\s*(\d+)"
    )

    match = re.search(
        pattern,
        message,
        re.IGNORECASE
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


# =========================================================
# Basic database chat
# =========================================================

def basic_database_response(
    db: Session,
    message: str
):

    text = message.strip().lower()


    # =====================================================
    # STUDENT ID
    # =====================================================

    student_id = extract_id(
        text,
        "student"
    )


    if student_id is not None:

        row = (
            db.query(
                Student,
                User
            )
            .join(
                User,
                Student.user_id == User.id
            )
            .filter(
                Student.id == student_id
            )
            .first()
        )


        if not row:

            return (
                f"Student ID #{student_id} "
                f"not found."
            )


        s, u = row


        return (
            f"Student Details\n\n"
            f"Student ID: #{s.id}\n"
            f"Name: {u.full_name}\n"
            f"Email: {u.email}\n"
            f"College: "
            f"{getattr(s, 'college_name', None) or '—'}\n"
            f"Branch: "
            f"{getattr(s, 'branch', None) or '—'}\n"
            f"Year: "
            f"{getattr(s, 'year', None) or '—'}\n"
            f"Semester: "
            f"{getattr(s, 'semester', None) or '—'}\n"
            f"Career Goal: "
            f"{getattr(s, 'career_goal', None) or '—'}"
        )


    # =====================================================
    # COMPANY ID
    # =====================================================

    company_id = extract_id(
        text,
        "company"
    )


    if company_id is not None:

        company = (
            db.query(Company)
            .filter(
                Company.id == company_id
            )
            .first()
        )


        if not company:

            return (
                f"Company ID #{company_id} "
                f"not found."
            )


        opportunities = (
            db.query(Opportunity)
            .filter(
                Opportunity.company_id ==
                company.id
            )
            .all()
        )


        opportunity_text = "None"


        if opportunities:

            opportunity_text = "\n".join(
                [
                    (
                        f"#{o.id} - "
                        f"{o.title} "
                        f"({enum_value(o.opportunity_type)})"
                    )
                    for o in opportunities
                ]
            )


        return (
            f"Company Details\n\n"
            f"Company ID: #{company.id}\n"
            f"Name: {company.name}\n"
            f"Industry: "
            f"{getattr(company, 'industry', None) or '—'}\n"
            f"Location: "
            f"{getattr(company, 'location', None) or '—'}\n"
            f"Website: "
            f"{getattr(company, 'website', None) or '—'}\n\n"
            f"Opportunities:\n"
            f"{opportunity_text}"
        )


    # =====================================================
    # OPPORTUNITY ID
    # =====================================================

    opportunity_id = extract_id(
        text,
        "opportunity"
    )


    if opportunity_id is None:

        opportunity_id = extract_id(
            text,
            "job"
        )


    if opportunity_id is None:

        opportunity_id = extract_id(
            text,
            "internship"
        )


    if opportunity_id is not None:

        row = (
            db.query(
                Opportunity,
                Company
            )
            .join(
                Company,
                Opportunity.company_id ==
                Company.id
            )
            .filter(
                Opportunity.id ==
                opportunity_id
            )
            .first()
        )


        if not row:

            return (
                f"Opportunity ID #{opportunity_id} "
                f"not found."
            )


        opportunity, company = row


        return (
            f"Opportunity Details\n\n"
            f"Opportunity ID: #{opportunity.id}\n"
            f"Title: {opportunity.title}\n"
            f"Company: {company.name}\n"
            f"Company ID: #{company.id}\n"
            f"Type: "
            f"{enum_value(opportunity.opportunity_type)}\n"
            f"Location: "
            f"{opportunity.location or '—'}\n"
            f"Stipend: "
            f"{opportunity.stipend or '—'}\n"
            f"Experience: "
            f"{opportunity.experience_required or '—'}\n"
            f"Description: "
            f"{opportunity.description or '—'}"
        )


    # Basic command nahi mila
    return None


# =========================================================
# CREATE SESSION
# =========================================================

@router.post("/sessions")
def create(
    data: CreateChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.student
        )
    )
):

    s = student(
        db,
        user.id
    )


    x = ChatSession(
        student_id=s.id,
        title=data.title or
        "Career Conversation"
    )


    db.add(x)

    db.commit()

    db.refresh(x)


    return {
        "success": True,
        "data": {
            "session_id": x.id,
            "title": x.title
        }
    }


# =========================================================
# GET SESSIONS
# =========================================================

@router.get("/sessions")
def sessions(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.student
        )
    )
):

    s = student(
        db,
        user.id
    )


    rows = (
        db.query(ChatSession)
        .filter(
            ChatSession.student_id ==
            s.id
        )
        .order_by(
            ChatSession.id.desc()
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

@router.post("/sessions/{sid}/messages")
def send(
    sid: int,
    data: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.student
        )
    )
):

    s = student(
        db,
        user.id
    )


    sess = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == sid,
            ChatSession.student_id ==
            s.id
        )
        .first()
    )


    if not sess:

        raise HTTPException(
            404,
            "Chat session not found"
        )


    # -----------------------------------------------------
    # Save user message
    # -----------------------------------------------------

    user_message = ChatMessage(
        session_id=sid,
        role="user",
        content=data.message
    )


    db.add(user_message)

    db.commit()


    # -----------------------------------------------------
    # FIRST: Try basic database command
    # -----------------------------------------------------

    answer = basic_database_response(
        db,
        data.message
    )


    # -----------------------------------------------------
    # SECOND: Existing career assistant
    # -----------------------------------------------------

    if answer is None:

        hist = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id ==
                sid
            )
            .order_by(
                ChatMessage.id.desc()
            )
            .limit(10)
            .all()
        )[::-1]


        answer = generate_career_response(

            build_student_context(
                db,
                s,
                data.opportunity_id
            ),

            data.message,

            [
                {
                    "role": m.role,
                    "content": m.content
                }
                for m in hist
            ]
        )


    # -----------------------------------------------------
    # Save assistant response
    # -----------------------------------------------------

    msg = ChatMessage(
        session_id=sid,
        role="assistant",
        content=answer
    )


    db.add(msg)

    db.commit()

    db.refresh(msg)


    return {
        "success": True,
        "data": {
            "message_id": msg.id,
            "answer": answer
        }
    }


# =========================================================
# GET MESSAGES
# =========================================================

@router.get("/sessions/{sid}/messages")
def messages(
    sid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.student
        )
    )
):

    s = student(
        db,
        user.id
    )


    sess = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == sid,
            ChatSession.student_id ==
            s.id
        )
        .first()
    )


    if not sess:

        raise HTTPException(
            404,
            "Chat session not found"
        )


    return {
        "success": True,

        "data": (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id ==
                sid
            )
            .order_by(
                ChatMessage.id.asc()
            )
            .all()
        )
    }