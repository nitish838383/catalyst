from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
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
from app.services.section_detector import detect_sections
from app.services.ats_analyzer import calculate_ats_score
from app.services.matching import calculate_match
from app.services.resume_ai import generate_resume_guidance


router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"],
)


# ======================================================
# HELPERS
# ======================================================

def get_student(
    db: Session,
    user_id: int,
) -> Student:

    student = (
        db.query(Student)
        .filter(
            Student.user_id == user_id
        )
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
    student = get_student(
        db,
        user.id,
    )

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

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded resume is empty",
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
        "filename": resume.original_filename,
        "message": "Resume uploaded successfully",
    }


# ======================================================
# ANALYZE RESUME
#
# Deterministic analysis:
#
# PDF
# ↓
# Text Extraction
# ↓
# Skill Detection
# ↓
# Section Detection
# ↓
# ATS Readiness Analysis
#
# IMPORTANT:
# Detected skills are NOT automatically confirmed.
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

    # -----------------------------------------
    # Extract text
    # -----------------------------------------

    try:
        text = extract_pdf_text(
            resume.file_path
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Resume file not found on server",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unable to read resume PDF: "
                f"{str(exc)}"
            ),
        )

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "No readable text could be extracted "
                "from this PDF. Scanned/image-only PDFs "
                "are not currently supported."
            ),
        )

    # -----------------------------------------
    # Skill extraction
    # -----------------------------------------

    detected = extract_skills(
        text
    )

    # -----------------------------------------
    # Section detection
    # -----------------------------------------

    sections = detect_sections(
        text
    )

    # -----------------------------------------
    # ATS readiness analysis
    # -----------------------------------------

    ats_result = calculate_ats_score(
        text=text,
        sections=sections,
        skills=detected,
    )

    # -----------------------------------------
    # Save analysis
    # -----------------------------------------

    resume.extracted_text = text
    resume.is_processed = True

    resume.section_analysis = sections

    resume.ats_analysis = ats_result

    resume.ats_score = float(
        ats_result.get(
            "score",
            0,
        )
    )

    resume.analyzed_at = (
        datetime.utcnow()
    )

    # Previous AI guidance may no longer match
    # the newly analyzed resume.
    resume.ai_guidance = None

    # -----------------------------------------
    # Remove old detections
    # -----------------------------------------

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

    # -----------------------------------------
    # Save newly detected skills
    # -----------------------------------------

    for item in detected:

        skill_name = (
            str(
                item.get(
                    "name",
                    "",
                )
            )
            .strip()
            .lower()
        )

        if not skill_name:
            continue

        skill = (
            db.query(Skill)
            .filter(
                Skill.name == skill_name
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

            confidence=float(
                item.get(
                    "confidence",
                    1.0,
                )
            ),

            is_accepted=False,
        )

        db.add(
            resume_skill
        )

    db.commit()
    db.refresh(resume)

    return {
        "success": True,

        "resume_id": resume.id,

        "message": (
            "Resume analyzed successfully. "
            "Review and confirm the skills "
            "you actually know."
        ),

        "detected_skills": detected,

        "sections": sections,

        "ats": ats_result,
    }


# ======================================================
# GET RESUME ANALYSIS
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

    resume = get_owned_resume(
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

    detected_skills = [
        {
            "resume_skill_id":
                resume_skill.id,

            "skill_id":
                skill.id,

            "name":
                skill.name,

            "confidence":
                resume_skill.confidence,

            "accepted":
                resume_skill.is_accepted,
        }

        for resume_skill, skill
        in rows
    ]

    return {
        "success": True,

        "resume_id": resume.id,

        "processed":
            resume.is_processed,

        "analyzed_at":
            resume.analyzed_at,

        "ats_score":
            resume.ats_score,

        "sections":
            resume.section_analysis
            or {},

        "ats":
            resume.ats_analysis
            or {},

        "detected_skills":
            detected_skills,

        "ai_guidance":
            resume.ai_guidance,
    }


# ======================================================
# CONFIRM CURRENT RESUME SKILLS
# ======================================================

@router.post("/{rid}/accept-skills")
def accept(
    rid: int,

    resume_skill_ids: list[int] = Body(...),

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

    # Remove duplicate submitted IDs
    selected_resume_skill_ids = list(
        dict.fromkeys(
            int(value)
            for value
            in resume_skill_ids
        )
    )

    # -----------------------------------------
    # Ensure all selected rows belong
    # to the current resume
    # -----------------------------------------

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

    # -----------------------------------------
    # Reset current resume detections
    # -----------------------------------------

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

    # -----------------------------------------
    # Remove OLD resume-sourced profile skills
    # not confirmed in current resume
    #
    # Manual and assessment skills stay safe.
    # -----------------------------------------

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

    # -----------------------------------------
    # Add selected skills
    # -----------------------------------------

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

                skill_id=
                    resume_skill.skill_id,

                level="beginner",

                source="resume",

                confidence_score=
                    resume_skill.confidence,
            )

            db.add(
                student_skill
            )

        elif (
            existing_skill.source
            == "resume"
        ):
            existing_skill.confidence_score = (
                resume_skill.confidence
            )

        # If skill came from manual / assessment,
        # do NOT downgrade its source.

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

        "skills":
            accepted_data,

        "message": (
            "Current resume skills "
            "confirmed successfully"
        ),
    }


# ======================================================
# GET CONFIRMED SKILLS
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
# AI RESUME GUIDANCE
#
# LLM DOES NOT:
# - calculate ATS score
# - calculate opportunity score
# - verify skills
#
# It ONLY gives improvement guidance.
# ======================================================

@router.post("/{rid}/ai-guidance")
def create_ai_guidance(
    rid: int,

    payload: dict | None = Body(
        default=None
    ),

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

    if (
        not resume.is_processed
        or not resume.extracted_text
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Analyze the resume before "
                "requesting AI guidance"
            ),
        )

    payload = payload or {}

    target_role = payload.get(
        "target_role"
    )

    opportunity_id = payload.get(
        "opportunity_id"
    )

    # -----------------------------------------
    # Detected skills
    # -----------------------------------------

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

    detected_skills = [
        {
            "name": skill.name,

            "confidence":
                resume_skill.confidence,

            "accepted":
                resume_skill.is_accepted,
        }

        for resume_skill, skill
        in rows
    ]

    # -----------------------------------------
    # Optional opportunity matching
    # -----------------------------------------

    match_result = None

    if opportunity_id is not None:

        try:
            opportunity_id = int(
                opportunity_id
            )

        except (
            TypeError,
            ValueError,
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid opportunity_id"
                ),
            )

        selected_skill_ids = [
            resume_skill.skill_id

            for resume_skill, _
            in rows

            if resume_skill.is_accepted
        ]

        match_result = calculate_match(
            db=db,

            student_id=student.id,

            opportunity_id=
                opportunity_id,

            selected_skill_ids=
                selected_skill_ids,
        )

    # -----------------------------------------
    # Generate AI guidance
    # -----------------------------------------

    try:
        guidance = (
            generate_resume_guidance(
                resume_text=
                    resume.extracted_text,

                ats_result=
                    resume.ats_analysis
                    or {},

                detected_skills=
                    detected_skills,

                target_role=
                    target_role,

                match_result=
                    match_result,
            )
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail=(
                "AI resume guidance "
                "is temporarily unavailable"
            ),
        )

    # -----------------------------------------
    # Store latest guidance
    # -----------------------------------------

    stored_guidance = {
        "target_role":
            target_role,

        "opportunity_id":
            opportunity_id,

        "generated_at":
            datetime.utcnow().isoformat(),

        "guidance":
            guidance,
    }

    resume.ai_guidance = (
        stored_guidance
    )

    db.commit()

    return {
        "success": True,

        "resume_id": rid,

        "ats_score":
            resume.ats_score,

        "match":
            match_result,

        "data":
            stored_guidance,
    }


# ======================================================
# GET LAST SAVED AI GUIDANCE
# ======================================================

@router.get("/{rid}/ai-guidance")
def get_ai_guidance(
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

    return {
        "success": True,
        "resume_id": rid,
        "data": resume.ai_guidance,
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