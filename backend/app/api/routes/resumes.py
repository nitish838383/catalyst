from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
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
    tags=["Resumes"],
)


# ======================================================
# HELPERS
# ======================================================

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


def get_owned_resume(
    db: Session,
    student_id: int,
    resume_id: int,
) -> Resume:
    resume = (
        db.query(Resume)
        .filter(
            Resume.id == resume_id,
            Resume.student_id == student_id,
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    return resume


# ======================================================
# UPLOAD RESUME
# ======================================================

@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(db, user.id)

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF resumes are supported",
        )

    content = await file.read()

    max_bytes = (
        settings.MAX_RESUME_SIZE_MB
        * 1024
        * 1024
    )

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail="Resume too large",
        )

    folder = (
        Path(settings.UPLOAD_DIR)
        / "resumes"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = (
        f"{uuid4()}.pdf"
    )

    path = (
        folder
        / stored_filename
    )

    path.write_bytes(content)

    resume = Resume(
        student_id=student.id,
        original_filename=(
            file.filename
            or "resume.pdf"
        ),
        stored_filename=stored_filename,
        file_path=str(path),
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "success": True,
        "resume_id": resume.id,
    }


# ======================================================
# ANALYZE RESUME
# Detect skills only.
# Do NOT add detected skills to StudentSkill here.
# ======================================================

@router.post("/{rid}/analyze")
def analyze(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(
        db,
        user.id,
    )

    resume = get_owned_resume(
        db,
        student.id,
        rid,
    )

    text = extract_pdf_text(
        resume.file_path
    )

    detected = extract_skills(
        text
    )

    resume.extracted_text = text
    resume.is_processed = True

    # Re-analysis should replace previous detections for this resume.
    (
        db.query(ResumeSkill)
        .filter(
            ResumeSkill.resume_id
            == resume.id
        )
        .delete(
            synchronize_session=False
        )
    )

    for item in detected:
        skill_name = (
            str(item["name"])
            .strip()
            .lower()
        )

        if not skill_name:
            continue

        skill = (
            db.query(Skill)
            .filter(
                Skill.name
                == skill_name
            )
            .first()
        )

        if not skill:
            skill = Skill(
                name=skill_name
            )

            db.add(skill)
            db.flush()

        resume_skill = ResumeSkill(
            resume_id=resume.id,
            skill_id=skill.id,
            confidence=item.get(
                "confidence",
                1.0,
            ),
            is_accepted=False,
        )

        db.add(resume_skill)

    db.commit()

    return {
        "success": True,
        "message": (
            "Resume analyzed. "
            "Review and confirm the skills you actually know."
        ),
        "detected_skills": detected,
    }


# ======================================================
# RESUME ANALYSIS
# Returns detected skills only.
# ======================================================

@router.get("/{rid}/analysis")
def analysis(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(
        db,
        user.id,
    )

    get_owned_resume(
        db,
        student.id,
        rid,
    )

    rows = (
        db.query(
            ResumeSkill,
            Skill,
        )
        .join(
            Skill,
            ResumeSkill.skill_id
            == Skill.id,
        )
        .filter(
            ResumeSkill.resume_id
            == rid
        )
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "resume_skill_id": (
                    resume_skill.id
                ),
                "skill_id": skill.id,
                "name": skill.name,
                "confidence": (
                    resume_skill.confidence
                ),
                "accepted": (
                    resume_skill.is_accepted
                ),
            }
            for resume_skill, skill
            in rows
        ],
    }


# ======================================================
# CONFIRM CURRENT RESUME SKILLS
#
# IMPORTANT:
# - all skills for this resume are reset to unaccepted first
# - only selected resume skills become accepted
# - old StudentSkill rows whose source == "resume" are removed
#   if they are not part of the current confirmation
# - manual / assessment skills are preserved
# ======================================================

@router.post("/{rid}/accept-skills")
def accept(
    rid: int,
    resume_skill_ids: list[int],
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(
        db,
        user.id,
    )

    get_owned_resume(
        db,
        student.id,
        rid,
    )

    if not resume_skill_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Select at least one "
                "skill to confirm"
            ),
        )

    # Remove duplicates from submitted IDs.
    selected_resume_skill_ids = list(
        dict.fromkeys(
            int(value)
            for value
            in resume_skill_ids
        )
    )

    # Load selected rows and guarantee they all belong to THIS resume.
    selected_rows = (
        db.query(
            ResumeSkill,
            Skill,
        )
        .join(
            Skill,
            ResumeSkill.skill_id
            == Skill.id,
        )
        .filter(
            ResumeSkill.resume_id
            == rid,
            ResumeSkill.id.in_(
                selected_resume_skill_ids
            ),
        )
        .all()
    )

    if (
        len(selected_rows)
        != len(
            selected_resume_skill_ids
        )
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "One or more selected skills "
                "do not belong to this resume"
            ),
        )

    # Reset every detected skill from this resume.
    (
        db.query(ResumeSkill)
        .filter(
            ResumeSkill.resume_id
            == rid
        )
        .update(
            {
                ResumeSkill.is_accepted:
                    False
            },
            synchronize_session=False,
        )
    )

    selected_skill_ids = {
        resume_skill.skill_id
        for resume_skill, _
        in selected_rows
    }

    # Remove ONLY old resume-sourced profile skills
    # that the student did not confirm in the current resume.
    old_resume_skills = (
        db.query(StudentSkill)
        .filter(
            StudentSkill.student_id
            == student.id,
            StudentSkill.source
            == "resume",
        )
        .all()
    )

    for student_skill in old_resume_skills:
        if (
            student_skill.skill_id
            not in selected_skill_ids
        ):
            db.delete(
                student_skill
            )

    accepted_data = []

    for resume_skill, skill in selected_rows:
        resume_skill.is_accepted = True

        existing_skill = (
            db.query(StudentSkill)
            .filter(
                StudentSkill.student_id
                == student.id,
                StudentSkill.skill_id
                == resume_skill.skill_id,
            )
            .first()
        )

        if not existing_skill:
            student_skill = StudentSkill(
                student_id=student.id,
                skill_id=resume_skill.skill_id,
                level="beginner",
                source="resume",
                confidence_score=(
                    resume_skill.confidence
                ),
            )

            db.add(student_skill)

        elif (
            existing_skill.source
            == "resume"
        ):
            # Keep the latest resume confidence.
            existing_skill.confidence_score = (
                resume_skill.confidence
            )

        # If source is manual or assessment,
        # preserve it instead of downgrading it to "resume".

        accepted_data.append(
            {
                "resume_skill_id":
                    resume_skill.id,
                "skill_id":
                    skill.id,
                "name":
                    skill.name,
                "confidence":
                    resume_skill.confidence,
            }
        )

    db.commit()

    return {
        "success": True,
        "resume_id": rid,
        "accepted": len(
            accepted_data
        ),
        "skill_ids": sorted(
            selected_skill_ids
        ),
        "skills": accepted_data,
        "message": (
            "Current resume skills confirmed successfully"
        ),
    }


# ======================================================
# GET CONFIRMED SKILLS FOR THIS RESUME
# Useful for career analysis and opportunity matching.
# ======================================================

@router.get("/{rid}/confirmed-skills")
def confirmed_skills(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(
        db,
        user.id,
    )

    get_owned_resume(
        db,
        student.id,
        rid,
    )

    rows = (
        db.query(
            ResumeSkill,
            Skill,
        )
        .join(
            Skill,
            ResumeSkill.skill_id
            == Skill.id,
        )
        .filter(
            ResumeSkill.resume_id
            == rid,
            ResumeSkill.is_accepted
            == True,
        )
        .all()
    )

    return {
        "success": True,
        "resume_id": rid,
        "skill_ids": [
            skill.id
            for _, skill
            in rows
        ],
        "data": [
            {
                "resume_skill_id":
                    resume_skill.id,
                "skill_id":
                    skill.id,
                "name":
                    skill.name,
                "confidence":
                    resume_skill.confidence,
            }
            for resume_skill, skill
            in rows
        ],
    }


# ======================================================
# DOWNLOAD ORIGINAL RESUME
# ======================================================

@router.get("/{rid}/download")
def download_resume(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(
        db,
        user.id,
    )

    resume = get_owned_resume(
        db,
        student.id,
        rid,
    )

    file_path = Path(
        resume.file_path
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Resume file not found "
                "on server"
            ),
        )

    return FileResponse(
        path=file_path,
        filename=(
            resume.original_filename
            or f"resume-{resume.id}.pdf"
        ),
        media_type="application/pdf",
    )
