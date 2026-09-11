from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db

from app.models.user import User, UserRole
from app.models.student import Student
from app.models.resume import Resume, ResumeSkill
from app.models.roadmap import LearningRoadmap, RoadmapStep

from app.services.readiness import calculate_readiness
from app.services.roadmap_generator import generate_roadmap_steps


router = APIRouter(
    prefix="/career",
    tags=["Career Intelligence"],
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


def get_confirmed_resume_skill_ids(
    db: Session,
    student_id: int,
    resume_id: int,
) -> list[int]:
    """
    Return ONLY accepted skills from a resume owned by this student.
    """

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

    rows = (
        db.query(ResumeSkill)
        .filter(
            ResumeSkill.resume_id == resume_id,
            ResumeSkill.is_accepted == True,
        )
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=400,
            detail=(
                "No confirmed skills found for this resume. "
                "Confirm your detected skills first."
            ),
        )

    return list({
        row.skill_id
        for row in rows
    })


# ======================================================
# CAREER READINESS
#
# Resume AI:
# GET /career/readiness?role=full%20stack%20developer&resume_id=12
#
# Normal profile mode:
# GET /career/readiness?role=backend%20developer
# ======================================================

@router.get("/readiness")
def readiness(
    role: str,
    resume_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(
        db,
        user.id,
    )

    selected_skill_ids = None

    if resume_id is not None:
        selected_skill_ids = (
            get_confirmed_resume_skill_ids(
                db,
                student.id,
                resume_id,
            )
        )

    result = calculate_readiness(
        db,
        student,
        role,
        selected_skill_ids=selected_skill_ids,
    )

    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result["error"],
        )

    return {
        "success": True,
        "resume_id": resume_id,
        "data": result,
    }


# ======================================================
# CREATE ROADMAP
#
# Resume AI:
# POST /career/roadmap?role=full%20stack%20developer&resume_id=12
#
# Normal profile mode:
# POST /career/roadmap?role=backend%20developer
# ======================================================

@router.post("/roadmap")
def create_roadmap(
    role: str,
    resume_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(
        db,
        user.id,
    )

    selected_skill_ids = None

    if resume_id is not None:
        selected_skill_ids = (
            get_confirmed_resume_skill_ids(
                db,
                student.id,
                resume_id,
            )
        )

    readiness_result = calculate_readiness(
        db,
        student,
        role,
        selected_skill_ids=selected_skill_ids,
    )

    if "error" in readiness_result:
        raise HTTPException(
            status_code=400,
            detail=readiness_result["error"],
        )

    road = LearningRoadmap(
        student_id=student.id,
        target_role=role.strip().lower(),
        title=f"{role.title()} Roadmap",
    )

    db.add(road)
    db.flush()

    steps = generate_roadmap_steps(
        readiness_result["missing_skills"]
    )

    for step_data in steps:
        db.add(
            RoadmapStep(
                roadmap_id=road.id,
                **step_data,
            )
        )

    db.commit()

    return {
        "success": True,
        "resume_id": resume_id,
        "roadmap_id": road.id,
        "current_readiness": (
            readiness_result["readiness_score"]
        ),
        "analysis_source": (
            readiness_result["analysis_source"]
        ),
        "matched_skills": (
            readiness_result["matched_skills"]
        ),
        "missing_skills": (
            readiness_result["missing_skills"]
        ),
        "roadmap": steps,
    }


# ======================================================
# COMPLETE ROADMAP STEP
# ======================================================

@router.patch("/roadmap/steps/{sid}/complete")
def complete(
    sid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    student = get_student(
        db,
        user.id,
    )

    step = (
        db.query(RoadmapStep)
        .join(
            LearningRoadmap,
            RoadmapStep.roadmap_id
            == LearningRoadmap.id,
        )
        .filter(
            RoadmapStep.id == sid,
            LearningRoadmap.student_id
            == student.id,
        )
        .first()
    )

    if not step:
        raise HTTPException(
            status_code=404,
            detail="Roadmap step not found",
        )

    step.completed = True
    db.commit()

    return {
        "success": True
    }


# ======================================================
# ROADMAP PROGRESS
# ======================================================

@router.get("/roadmap/{rid}/progress")
def progress(
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

    road = (
        db.query(LearningRoadmap)
        .filter(
            LearningRoadmap.id == rid,
            LearningRoadmap.student_id
            == student.id,
        )
        .first()
    )

    if not road:
        raise HTTPException(
            status_code=404,
            detail="Roadmap not found",
        )

    total = (
        db.query(RoadmapStep)
        .filter(
            RoadmapStep.roadmap_id
            == rid
        )
        .count()
    )

    done = (
        db.query(RoadmapStep)
        .filter(
            RoadmapStep.roadmap_id
            == rid,
            RoadmapStep.completed
            == True,
        )
        .count()
    )

    return {
        "success": True,
        "total_steps": total,
        "completed_steps": done,
        "progress": (
            round(
                done / total * 100,
                2,
            )
            if total
            else 0
        ),
    }
