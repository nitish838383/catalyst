import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db

from app.models.user import User, UserRole
from app.models.student import Student
from app.models.skill import Skill, StudentSkill
from app.models.project import Project
from app.models.certification import Certification
from app.models.chat import ChatSession, ChatMessage
from app.models.company import Company
from app.models.opportunity import Opportunity
from app.models.application import Application

from app.schemas.chat import CreateChatRequest, ChatRequest

from app.services.student_context import build_student_context
from app.services.ai_career import generate_career_response


router = APIRouter(
    prefix="/career-chat",
    tags=["AI Career Assistant"],
)


def get_student(db: Session, user_id: int) -> Student:
    student = (
        db.query(Student)
        .filter(Student.user_id == user_id)
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found",
        )

    return student


def enum_value(value):
    if value is None:
        return None

    return getattr(value, "value", value)


def extract_id(message: str, keyword: str):
    pattern = rf"{keyword}\s*(?:id)?\s*#?\s*(\d+)"

    match = re.search(
        pattern,
        message,
        re.IGNORECASE,
    )

    if not match:
        return None

    return int(match.group(1))


def normalize_text(message: str) -> str:
    return " ".join(message.strip().lower().split())


def contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def student_database_response(
    db: Session,
    student: Student,
    user: User,
    message: str,
):
    text = normalize_text(message)

    if contains_any(
        text,
        [
            "my profile",
            "my details",
            "meri profile",
            "meri details",
            "mera profile",
            "student details",
            "about me",
        ],
    ):
        return (
            "Your Student Profile\n\n"
            f"Name: {user.full_name}\n"
            f"Email: {user.email}\n"
            f"Student ID: #{student.id}\n"
            f"College ID: {getattr(student, 'college_id', None) or '—'}\n"
            f"Department ID: {getattr(student, 'department_id', None) or '—'}\n"
            f"Branch: {getattr(student, 'branch', None) or '—'}\n"
            f"Year: {getattr(student, 'year', None) or '—'}\n"
            f"Semester: {getattr(student, 'semester', None) or '—'}\n"
            f"Career Goal: {getattr(student, 'career_goal', None) or '—'}"
        )

    if contains_any(
        text,
        [
            "my skills",
            "meri skills",
            "mere skills",
            "skills i have",
            "what skills do i have",
        ],
    ):
        rows = (
            db.query(StudentSkill, Skill)
            .join(
                Skill,
                StudentSkill.skill_id == Skill.id,
            )
            .filter(
                StudentSkill.student_id == student.id
            )
            .order_by(Skill.name.asc())
            .all()
        )

        if not rows:
            return (
                "You have not added any skills yet. "
                "Add your skills from Profile & Skills so SkillBridge "
                "can calculate your skill gap and opportunity match."
            )

        lines = []

        for student_skill, skill in rows:
            level = enum_value(student_skill.level) or "—"
            verified = (
                "Verified"
                if getattr(student_skill, "is_verified", False)
                else "Unverified"
            )

            lines.append(
                f"• {skill.name} — {level} — {verified}"
            )

        return (
            f"Your Skills ({len(lines)})\n\n"
            + "\n".join(lines)
        )

    if contains_any(
        text,
        [
            "my projects",
            "mere projects",
            "meri projects",
            "project list",
        ],
    ):
        rows = (
            db.query(Project)
            .filter(Project.student_id == student.id)
            .order_by(Project.id.desc())
            .all()
        )

        if not rows:
            return (
                "You have not added any projects yet. "
                "Projects act as proof of work and strengthen "
                "your internship and placement profile."
            )

        lines = []

        for project in rows:
            tech = (
                getattr(project, "technologies", None)
                or "Technologies not specified"
            )

            lines.append(
                f"• #{project.id} {project.title}\n"
                f"  Technologies: {tech}"
            )

        return (
            f"Your Projects ({len(rows)})\n\n"
            + "\n".join(lines)
        )

    if contains_any(
        text,
        [
            "my certificates",
            "my certifications",
            "mere certificates",
            "meri certifications",
            "certificate list",
        ],
    ):
        rows = (
            db.query(Certification)
            .filter(
                Certification.student_id == student.id
            )
            .order_by(Certification.id.desc())
            .all()
        )

        if not rows:
            return (
                "You have not added any certifications yet. "
                "Add relevant credentials to strengthen your profile."
            )

        lines = []

        for certificate in rows:
            issuer = (
                getattr(certificate, "organization", None)
                or "Issuer not specified"
            )

            lines.append(
                f"• #{certificate.id} "
                f"{certificate.name} — {issuer}"
            )

        return (
            f"Your Certifications ({len(rows)})\n\n"
            + "\n".join(lines)
        )

    if contains_any(
        text,
        [
            "my applications",
            "application status",
            "meri applications",
            "maine kaha apply",
            "where have i applied",
        ],
    ):
        rows = (
            db.query(Application, Opportunity)
            .join(
                Opportunity,
                Application.opportunity_id == Opportunity.id,
            )
            .filter(
                Application.student_id == student.id
            )
            .order_by(Application.id.desc())
            .all()
        )

        if not rows:
            return (
                "You have not applied to any opportunities yet. "
                "Open Opportunities to check your match score "
                "before applying."
            )

        lines = []

        for application, opportunity in rows:
            status = enum_value(application.status) or "—"

            lines.append(
                f"• {opportunity.title} "
                f"(Opportunity #{opportunity.id}) "
                f"— {status}"
            )

        return (
            f"Your Applications ({len(rows)})\n\n"
            + "\n".join(lines)
        )

    company_id = extract_id(text, "company")

    if company_id is not None:
        company = (
            db.query(Company)
            .filter(Company.id == company_id)
            .first()
        )

        if not company:
            return f"Company ID #{company_id} not found."

        opportunities = (
            db.query(Opportunity)
            .filter(
                Opportunity.company_id == company.id,
                Opportunity.is_active.is_(True),
            )
            .order_by(Opportunity.id.desc())
            .all()
        )

        if opportunities:
            opportunity_text = "\n".join(
                [
                    f"• #{o.id} — {o.title} "
                    f"({enum_value(o.opportunity_type)})"
                    for o in opportunities
                ]
            )
        else:
            opportunity_text = "No active opportunities."

        return (
            "Company Details\n\n"
            f"Company ID: #{company.id}\n"
            f"Name: {company.name}\n"
            f"Industry: {getattr(company, 'industry', None) or '—'}\n"
            f"Location: {getattr(company, 'location', None) or '—'}\n"
            f"Website: {getattr(company, 'website', None) or '—'}\n\n"
            f"Active Opportunities:\n{opportunity_text}"
        )

    opportunity_id = extract_id(text, "opportunity")

    if opportunity_id is None:
        opportunity_id = extract_id(text, "job")

    if opportunity_id is None:
        opportunity_id = extract_id(text, "internship")

    if opportunity_id is not None:
        row = (
            db.query(Opportunity, Company)
            .join(
                Company,
                Opportunity.company_id == Company.id,
            )
            .filter(
                Opportunity.id == opportunity_id,
                Opportunity.is_active.is_(True),
            )
            .first()
        )

        if not row:
            return (
                f"Opportunity ID #{opportunity_id} "
                "not found or inactive."
            )

        opportunity, company = row

        return (
            "Opportunity Details\n\n"
            f"Opportunity ID: #{opportunity.id}\n"
            f"Title: {opportunity.title}\n"
            f"Company: {company.name}\n"
            f"Type: {enum_value(opportunity.opportunity_type) or '—'}\n"
            f"Location: {opportunity.location or '—'}\n"
            f"Stipend: {opportunity.stipend or '—'}\n"
            f"Experience: {opportunity.experience_required or '—'}\n"
            f"Description: {opportunity.description or '—'}"
        )

    return None


@router.post("/sessions")
def create_session(
    data: CreateChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(db, user.id)

    session = ChatSession(
        student_id=student.id,
        title=data.title or "Career Conversation",
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "success": True,
        "data": {
            "session_id": session.id,
            "title": session.title,
        },
    }


@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(db, user.id)

    rows = (
        db.query(ChatSession)
        .filter(
            ChatSession.student_id == student.id
        )
        .order_by(ChatSession.id.desc())
        .all()
    )

    return {
        "success": True,
        "data": rows,
    }


@router.post("/sessions/{sid}/messages")
def send_message(
    sid: int,
    data: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(db, user.id)

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == sid,
            ChatSession.student_id == student.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found",
        )

    clean_message = (data.message or "").strip()

    if not clean_message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )

    history_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == sid)
        .order_by(ChatMessage.id.desc())
        .limit(10)
        .all()
    )[::-1]

    history = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in history_rows
    ]

    user_message = ChatMessage(
        session_id=sid,
        role="user",
        content=clean_message,
    )

    db.add(user_message)
    db.commit()

    answer = student_database_response(
        db,
        student,
        user,
        clean_message,
    )

    if answer is None:
        context = build_student_context(
            db,
            student,
            data.opportunity_id,
        )

        answer = generate_career_response(
            context,
            clean_message,
            history,
        )

    if not answer:
        answer = (
            "I could not generate a response. "
            "Please try asking your question again."
        )

    assistant_message = ChatMessage(
        session_id=sid,
        role="assistant",
        content=str(answer),
    )

    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return {
        "success": True,
        "data": {
            "message_id": assistant_message.id,
            "answer": str(answer),
        },
    }


@router.get("/sessions/{sid}/messages")
def get_messages(
    sid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(db, user.id)

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == sid,
            ChatSession.student_id == student.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Chat session not found",
        )

    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == sid)
        .order_by(ChatMessage.id.asc())
        .all()
    )

    return {
        "success": True,
        "data": rows,
    }
