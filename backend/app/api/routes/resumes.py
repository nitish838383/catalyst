from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db

from app.models.user import User, UserRole
from app.models.student import Student
from app.models.resume import Resume, ResumeSkill
from app.models.skill import Skill, StudentSkill

from app.services.resume_parser import extract_pdf_text
from app.services.skill_extractor import extract_skills


router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"]
)


def get_student(db, uid):
    s = (
        db.query(Student)
        .filter(Student.user_id == uid)
        .first()
    )

    if not s:
        raise HTTPException(
            404,
            "Student profile not found"
        )

    return s


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    )
):
    s = get_student(
        db,
        user.id
    )

    if file.content_type != "application/pdf":
        raise HTTPException(
            400,
            "Only PDF resumes are supported"
        )

    content = await file.read()

    max_bytes = (
        settings.MAX_RESUME_SIZE_MB
        * 1024
        * 1024
    )

    if len(content) > max_bytes:
        raise HTTPException(
            413,
            "Resume too large"
        )

    folder = (
        Path(settings.UPLOAD_DIR)
        / "resumes"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    stored = f"{uuid4()}.pdf"

    path = folder / stored

    path.write_bytes(content)

    r = Resume(
        student_id=s.id,
        original_filename=(
            file.filename
            or "resume.pdf"
        ),
        stored_filename=stored,
        file_path=str(path)
    )

    db.add(r)

    db.commit()

    db.refresh(r)

    return {
        "success": True,
        "resume_id": r.id
    }


@router.post("/{rid}/analyze")
def analyze(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    )
):
    s = get_student(
        db,
        user.id
    )

    r = (
        db.query(Resume)
        .filter(
            Resume.id == rid,
            Resume.student_id == s.id
        )
        .first()
    )

    if not r:
        raise HTTPException(
            404,
            "Resume not found"
        )

    # Extract resume text using Python
    text = extract_pdf_text(
        r.file_path
    )

    # Detect skills using Python skill extractor
    detected = extract_skills(
        text
    )

    r.extracted_text = text
    r.is_processed = True

    (
        db.query(ResumeSkill)
        .filter(
            ResumeSkill.resume_id == r.id
        )
        .delete()
    )

    for d in detected:

        sk = (
            db.query(Skill)
            .filter(
                Skill.name == d["name"]
            )
            .first()
        )

        if not sk:

            sk = Skill(
                name=d["name"]
            )

            db.add(sk)

            db.flush()

        resume_skill = ResumeSkill(
            resume_id=r.id,
            skill_id=sk.id,
            confidence=d["confidence"]
        )

        db.add(resume_skill)

    db.commit()

    return {
        "success": True,
        "detected_skills": detected
    }


@router.get("/{rid}/analysis")
def analysis(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    )
):
    s = get_student(
        db,
        user.id
    )

    r = (
        db.query(Resume)
        .filter(
            Resume.id == rid,
            Resume.student_id == s.id
        )
        .first()
    )

    if not r:
        raise HTTPException(
            404,
            "Resume not found"
        )

    rows = (
        db.query(
            ResumeSkill,
            Skill
        )
        .join(
            Skill,
            ResumeSkill.skill_id == Skill.id
        )
        .filter(
            ResumeSkill.resume_id == rid
        )
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "resume_skill_id": rs.id,
                "name": sk.name,
                "confidence": rs.confidence,
                "accepted": rs.is_accepted
            }
            for rs, sk in rows
        ]
    }


@router.post("/{rid}/accept-skills")
def accept(
    rid: int,
    resume_skill_ids: list[int],
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    )
):
    s = get_student(
        db,
        user.id
    )

    r = (
        db.query(Resume)
        .filter(
            Resume.id == rid,
            Resume.student_id == s.id
        )
        .first()
    )

    if not r:
        raise HTTPException(
            404,
            "Resume not found"
        )

    rows = (
        db.query(ResumeSkill)
        .filter(
            ResumeSkill.resume_id == rid,
            ResumeSkill.id.in_(
                resume_skill_ids
            )
        )
        .all()
    )

    for rs in rows:

        rs.is_accepted = True

        existing_skill = (
            db.query(StudentSkill)
            .filter(
                StudentSkill.student_id == s.id,
                StudentSkill.skill_id == rs.skill_id
            )
            .first()
        )

        if not existing_skill:

            student_skill = StudentSkill(
                student_id=s.id,
                skill_id=rs.skill_id,
                level="beginner",
                source="resume",
                confidence_score=rs.confidence
            )

            db.add(student_skill)

    db.commit()

    return {
        "success": True,
        "accepted": len(rows)
    }