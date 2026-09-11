from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import require_roles

from app.models.user import User, UserRole
from app.models.student import Student
from app.models.resume import Resume, ResumeSkill
from app.models.skill import Skill, StudentSkill
from app.models.project import Project
from app.models.certification import Certification
from app.models.opportunity import Opportunity
from app.models.company import Company
from app.models.application import Application, ApplicationStatus
from app.models.assessment import SkillAssessment
from app.models.collaboration import Collaboration, CollaborationStatus
from app.models.collaboration_participant import CollaborationParticipant

from app.schemas.student import (
    StudentProfileCreate,
    StudentProfileUpdate,
    StudentProfileResponse,
)
from app.schemas.skill import AddSkillRequest, AssessmentSubmit
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.certification import (
    CertificationCreate,
    CertificationResponse,
)

from app.services.matching import calculate_match


router = APIRouter(prefix="/students", tags=["Students"])


# ======================================================
# HELPER
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
            detail="Create student profile first",
        )

    return student


def get_confirmed_resume_skill_ids(
    db: Session,
    student_id: int,
    resume_id: int,
) -> list[int]:
    """
    Return only accepted skills from the selected resume.
    The resume must belong to the current student.
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
# STUDENT PROFILE
# ======================================================

@router.post("/profile", response_model=StudentProfileResponse)
def create_profile(
    data: StudentProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    existing = (
        db.query(Student)
        .filter(Student.user_id == user.id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Student profile already exists",
        )

    student = Student(
        user_id=user.id,
        **data.model_dump(),
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    return student


@router.get("/profile", response_model=StudentProfileResponse)
def profile(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    return get_student(db, user.id)


@router.patch("/profile", response_model=StudentProfileResponse)
def update_profile(
    data: StudentProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(student, key, value)

    db.commit()
    db.refresh(student)

    return student


# ======================================================
# STUDENT SKILLS
# ======================================================

@router.post("/skills")
def add_skill(
    data: AddSkillRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    name = data.name.strip().lower()

    skill = (
        db.query(Skill)
        .filter(Skill.name == name)
        .first()
    )

    if not skill:
        skill = Skill(
            name=name,
            category=data.category,
        )
        db.add(skill)
        db.flush()

    existing = (
        db.query(StudentSkill)
        .filter(
            StudentSkill.student_id == student.id,
            StudentSkill.skill_id == skill.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Skill already added",
        )

    student_skill = StudentSkill(
        student_id=student.id,
        skill_id=skill.id,
        level=data.level,
        source="manual",
    )

    db.add(student_skill)
    db.commit()
    db.refresh(student_skill)

    return {
        "success": True,
        "id": student_skill.id,
        "skill": skill.name,
    }


@router.get("/skills")
def skills(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    rows = (
        db.query(StudentSkill, Skill)
        .join(
            Skill,
            StudentSkill.skill_id == Skill.id,
        )
        .filter(
            StudentSkill.student_id == student.id
        )
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "id": student_skill.id,
                "name": skill.name,
                "level": student_skill.level,
                "source": student_skill.source,
                "verified": student_skill.is_verified,
            }
            for student_skill, skill in rows
        ],
    }


@router.delete("/skills/{sid}")
def delete_skill(
    sid: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    student_skill = (
        db.query(StudentSkill)
        .filter(
            StudentSkill.id == sid,
            StudentSkill.student_id == student.id,
        )
        .first()
    )

    if not student_skill:
        raise HTTPException(
            status_code=404,
            detail="Skill not found",
        )

    db.delete(student_skill)
    db.commit()

    return {"success": True}


# ======================================================
# PROJECTS
# ======================================================

@router.post("/projects", response_model=ProjectResponse)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    project = Project(
        student_id=student.id,
        **data.model_dump(),
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get("/projects", response_model=list[ProjectResponse])
def projects(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    return (
        db.query(Project)
        .filter(Project.student_id == student.id)
        .all()
    )


# ======================================================
# CERTIFICATIONS
# ======================================================

@router.post("/certifications", response_model=CertificationResponse)
def create_certification(
    data: CertificationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    certification = Certification(
        student_id=student.id,
        **data.model_dump(),
    )

    db.add(certification)
    db.commit()
    db.refresh(certification)

    return certification


@router.get("/certifications", response_model=list[CertificationResponse])
def certifications(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    return (
        db.query(Certification)
        .filter(
            Certification.student_id == student.id
        )
        .all()
    )


# ======================================================
# OPPORTUNITY MATCH
# ======================================================

@router.get("/opportunities/{oid}/match")
def match_opportunity(
    oid: int,
    resume_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    """
    Normal mode:
        GET /students/opportunities/{oid}/match

        Uses the student's complete StudentSkill profile.

    Resume AI mode:
        GET /students/opportunities/{oid}/match?resume_id=12

        Uses ONLY skills that the student confirmed for that resume.
    """

    student = get_student(db, user.id)

    opportunity = (
        db.query(Opportunity)
        .filter(
            Opportunity.id == oid,
            Opportunity.is_active == True,
        )
        .first()
    )

    if not opportunity:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    selected_skill_ids = None

    if resume_id is not None:
        selected_skill_ids = get_confirmed_resume_skill_ids(
            db,
            student.id,
            resume_id,
        )

    match_data = calculate_match(
        db,
        student.id,
        opportunity.id,
        selected_skill_ids=selected_skill_ids,
    )

    return {
        "success": True,
        "resume_id": resume_id,
        "analysis_source": (
            "confirmed_resume_skills"
            if resume_id is not None
            else "student_profile_skills"
        ),
        "match": match_data,
    }


# ======================================================
# APPLY OPPORTUNITY
# ======================================================

@router.post("/opportunities/{oid}/apply")
def apply_opportunity(
    oid: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    opportunity = (
        db.query(Opportunity)
        .filter(
            Opportunity.id == oid,
            Opportunity.is_active == True,
        )
        .first()
    )

    if not opportunity:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found",
        )

    existing = (
        db.query(Application)
        .filter(
            Application.student_id == student.id,
            Application.opportunity_id == oid,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Already applied",
        )

    application = Application(
        student_id=student.id,
        opportunity_id=oid,
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return {
        "success": True,
        "application_id": application.id,
        "status": application.status,
    }


# ======================================================
# STUDENT APPLICATIONS
# ======================================================

@router.get("/applications")
def applications(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    rows = (
        db.query(Application, Opportunity)
        .join(
            Opportunity,
            Application.opportunity_id == Opportunity.id,
        )
        .filter(
            Application.student_id == student.id
        )
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "application_id": application.id,
                "opportunity_id": opportunity.id,
                "title": opportunity.title,
                "status": application.status,
                "recruiter_note": application.recruiter_note,
                "applied_at": application.applied_at,
            }
            for application, opportunity in rows
        ],
    }


@router.patch("/applications/{aid}/withdraw")
def withdraw_application(
    aid: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    application = (
        db.query(Application)
        .filter(
            Application.id == aid,
            Application.student_id == student.id,
        )
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    if application.status in [
        ApplicationStatus.selected,
        ApplicationStatus.rejected,
        ApplicationStatus.withdrawn,
    ]:
        raise HTTPException(
            status_code=400,
            detail="Cannot withdraw",
        )

    application.status = ApplicationStatus.withdrawn

    db.commit()

    return {"success": True}


# ======================================================
# SKILL ASSESSMENT
# ======================================================

@router.post("/assessments")
def assessment(
    data: AssessmentSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    if (
        data.total_questions <= 0
        or data.correct_answers < 0
        or data.correct_answers > data.total_questions
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid assessment values",
        )

    score = (
        data.correct_answers
        / data.total_questions
        * 100
    )

    level = (
        "advanced"
        if score >= 80
        else "intermediate"
        if score >= 50
        else "beginner"
    )

    assessment_row = SkillAssessment(
        student_id=student.id,
        skill_id=data.skill_id,
        score=round(score, 2),
        level=level,
        total_questions=data.total_questions,
        correct_answers=data.correct_answers,
    )

    db.add(assessment_row)

    student_skill = (
        db.query(StudentSkill)
        .filter(
            StudentSkill.student_id == student.id,
            StudentSkill.skill_id == data.skill_id,
        )
        .first()
    )

    if student_skill:
        student_skill.level = level
        student_skill.is_verified = True
        student_skill.source = "assessment"
        student_skill.confidence_score = score / 100

    db.commit()

    return {
        "success": True,
        "score": round(score, 2),
        "level": level,
    }


# ======================================================
# COLLABORATION REGISTRATION
# ======================================================

@router.post("/collaborations/{cid}/register")
def register_collaboration(
    cid: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    student = get_student(db, user.id)

    collaboration = (
        db.query(Collaboration)
        .filter(
            Collaboration.id == cid,
            Collaboration.status.in_(
                [
                    CollaborationStatus.approved,
                    CollaborationStatus.ongoing,
                ]
            ),
        )
        .first()
    )

    if not collaboration:
        raise HTTPException(
            status_code=404,
            detail="Collaboration not available",
        )

    existing = (
        db.query(CollaborationParticipant)
        .filter(
            CollaborationParticipant.collaboration_id == cid,
            CollaborationParticipant.student_id == student.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Already registered",
        )

    participant = CollaborationParticipant(
        collaboration_id=cid,
        student_id=student.id,
    )

    db.add(participant)
    db.commit()
    db.refresh(participant)

    return {
        "success": True,
        "registration_id": participant.id,
    }


# ======================================================
# RECOMMENDED OPPORTUNITIES
# ======================================================

@router.get("/recommended-opportunities")
def recommended_opportunities(
    resume_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.student)),
):
    """
    Normal mode:
        GET /students/recommended-opportunities

        Uses the complete StudentSkill profile.

    Resume AI mode:
        GET /students/recommended-opportunities?resume_id=12

        Uses ONLY skills confirmed for the selected resume.
    """

    student = get_student(db, user.id)

    selected_skill_ids = None

    if resume_id is not None:
        selected_skill_ids = get_confirmed_resume_skill_ids(
            db,
            student.id,
            resume_id,
        )

    else:
        profile_skill_count = (
            db.query(StudentSkill)
            .filter(
                StudentSkill.student_id == student.id
            )
            .count()
        )

        if profile_skill_count == 0:
            return {
                "success": True,
                "analysis_source": "student_profile_skills",
                "message": (
                    "Add or accept skills before checking recommendations"
                ),
                "data": [],
            }

    opportunities = (
        db.query(Opportunity)
        .filter(
            Opportunity.is_active == True
        )
        .all()
    )

    results = []

    for opportunity in opportunities:
        try:
            match_data = calculate_match(
                db,
                student.id,
                opportunity.id,
                selected_skill_ids=selected_skill_ids,
            )
        except Exception as error:
            print(
                f"[recommended-opportunities] "
                f"match failed for opportunity "
                f"{opportunity.id}: {error}"
            )
            continue

        if not isinstance(match_data, dict):
            continue

        raw_score = (
            match_data.get("score")
            if match_data.get("score") is not None
            else match_data.get("match_score")
            if match_data.get("match_score") is not None
            else match_data.get("match_percentage")
            if match_data.get("match_percentage") is not None
            else match_data.get("percentage")
            if match_data.get("percentage") is not None
            else 0
        )

        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0

        # Ignore opportunities that have no required skills configured.
        if match_data.get("total_required_skills", 0) == 0:
            continue

        # Show only reasonably relevant recommendations.
        if score < 40:
            continue

        company = (
            db.query(Company)
            .filter(
                Company.id == opportunity.company_id
            )
            .first()
        )

        opportunity_type = getattr(
            opportunity,
            "opportunity_type",
            None,
        )

        if hasattr(opportunity_type, "value"):
            opportunity_type = opportunity_type.value
        elif opportunity_type is not None:
            opportunity_type = str(opportunity_type)

        results.append(
            {
                "opportunity_id": opportunity.id,
                "title": opportunity.title,

                "company": {
                    "id": company.id if company else None,
                    "name": (
                        company.name
                        if company
                        else "Unknown Company"
                    ),
                    "industry": (
                        getattr(company, "industry", None)
                        if company
                        else None
                    ),
                    "location": (
                        getattr(company, "location", None)
                        if company
                        else None
                    ),
                    "website": (
                        getattr(company, "website", None)
                        if company
                        else None
                    ),
                    "is_verified": (
                        getattr(company, "is_verified", False)
                        if company
                        else False
                    ),
                },

                "type": opportunity_type,
                "location": getattr(
                    opportunity,
                    "location",
                    None,
                ),
                "stipend": getattr(
                    opportunity,
                    "stipend",
                    None,
                ),
                "experience_required": getattr(
                    opportunity,
                    "experience_required",
                    None,
                ),

                "match_score": round(score, 2),

                "matched_skills": (
                    match_data.get("matched_skills")
                    or match_data.get("matches")
                    or []
                ),

                "missing_skills": (
                    match_data.get("missing_skills")
                    or match_data.get("missing")
                    or match_data.get("skill_gaps")
                    or []
                ),
            }
        )

    results.sort(
        key=lambda item: item["match_score"],
        reverse=True,
    )

    return {
        "success": True,
        "resume_id": resume_id,
        "analysis_source": (
            "confirmed_resume_skills"
            if resume_id is not None
            else "student_profile_skills"
        ),
        "message": "Recommended opportunities loaded",
        "data": results[:10],
    }

