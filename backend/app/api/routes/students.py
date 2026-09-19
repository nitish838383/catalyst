from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.college_student_registry import CollegeStudentRegistry
from app.models.college import College
from app.models.department import Department

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
    StudentCollegeVerifyRequest,
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

# ======================================================
# COLLEGE IDENTITY VERIFICATION
#
# Canonical APIs:
#   POST /students/college-verification/claim
#   GET  /students/college-verification/status
#
# Old endpoints are kept as hidden aliases so existing
# frontend code does not break immediately.
# ======================================================

def is_verified_college(college: College) -> bool:
    return (
        getattr(college, "verification_status", None) == "verified"
        or bool(getattr(college, "is_verified", False))
    )


def serialize_verified_college(
    college: College,
) -> dict:
    return {
        # Internal database relation ID
        "id": college.id,

        # College-entered public ID
        "college_public_id": getattr(
            college,
            "college_public_id",
            None,
        ),

        # Official college logo/profile image.
        # This belongs to College, not Student.
        "college_logo_url": getattr(
            college,
            "college_logo_url",
            None,
        ),

        "name": college.name,

        "college_code": getattr(
            college,
            "college_code",
            None,
        ),

        "aishe_code": getattr(
            college,
            "aishe_code",
            None,
        ),

        "university": getattr(
            college,
            "university",
            None,
        ),

        "city": getattr(
            college,
            "city",
            None,
        ),

        "state": getattr(
            college,
            "state",
            None,
        ),

        "verification_status": "verified",
    }


@router.post("/college-verification/claim")
@router.post(
    "/verify-college",
    include_in_schema=False,
)
def verify_college(
    data: StudentCollegeVerifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    """
    Claim an official college/TPO registry record.

    Student sends only:
        - selected verified college_id
        - Student ID / Enrollment Number

    Department, year and official student identity are taken
    from CollegeStudentRegistry, not trusted from the student.
    """

    student = get_student(
        db,
        user.id,
    )

    # ------------------------------------------------------
    # 1) Selected college must exist
    # ------------------------------------------------------

    college = (
        db.query(College)
        .filter(
            College.id == data.college_id
        )
        .first()
    )

    if not college:
        raise HTTPException(
            status_code=404,
            detail="Selected college not found",
        )

    # ------------------------------------------------------
    # 2) Students can claim only a VERIFIED institution
    # ------------------------------------------------------

    if not is_verified_college(college):
        raise HTTPException(
            status_code=403,
            detail=(
                "This institution is not verified yet. "
                "Select a verified college."
            ),
        )

    # Schema already normalizes this, but normalize again at
    # the trust boundary for safety / legacy callers.
    entered_id = (
        data.student_id_number
        .strip()
        .upper()
    )

    # ------------------------------------------------------
    # 3) Match selected college + official enrollment ID
    # ------------------------------------------------------

    registry = (
        db.query(CollegeStudentRegistry)
        .filter(
            CollegeStudentRegistry.college_id
            == college.id,

            CollegeStudentRegistry.student_id_number
            == entered_id,

            CollegeStudentRegistry.is_active.is_(
                True
            ),
        )
        .first()
    )

    if not registry:
        raise HTTPException(
            status_code=404,
            detail=(
                "Student ID / Enrollment Number was not found "
                "in the selected college's active registry."
            ),
        )

    # ------------------------------------------------------
    # 4) One official registry identity -> one account
    # ------------------------------------------------------

    if (
        registry.claimed_student_id is not None
        and registry.claimed_student_id
        != student.id
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This Student ID is already linked "
                "to another SkillBridge account."
            ),
        )

    # ------------------------------------------------------
    # 5) One SkillBridge account -> one registry identity
    # ------------------------------------------------------

    another_claim = (
        db.query(CollegeStudentRegistry)
        .filter(
            CollegeStudentRegistry.claimed_student_id
            == student.id,

            CollegeStudentRegistry.id
            != registry.id,
        )
        .first()
    )

    if another_claim:
        raise HTTPException(
            status_code=409,
            detail=(
                "Your SkillBridge account is already verified "
                "with another college registry record."
            ),
        )

    # ------------------------------------------------------
    # 6) Registry department is official
    # ------------------------------------------------------

    department = None

    if registry.department_id is not None:

        department = (
            db.query(Department)
            .filter(
                Department.id
                == registry.department_id,

                Department.college_id
                == college.id,
            )
            .first()
        )

        if not department:
            raise HTTPException(
                status_code=409,
                detail=(
                    "The official registry record references "
                    "an invalid department. Contact your college."
                ),
            )

        if not getattr(
            department,
            "is_active",
            True,
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Your registered department is currently "
                    "inactive. Contact your college/TPO."
                ),
            )

    # ------------------------------------------------------
    # 7) Claim official record + synchronize student profile
    # ------------------------------------------------------

    verified_at = datetime.utcnow()

    registry.claimed_student_id = student.id

    student.college_id = college.id
    student.college_name = college.name

    student.department_id = (
        registry.department_id
    )

    student.student_id_number = (
        registry.student_id_number
    )

    student.year = registry.year

    student.college_verified = True
    student.college_verified_at = verified_at
    student.college_verification_source = (
        "college_registry"
    )

    student.branch = (
        department.name
        if department
        else None
    )

    db.commit()

    db.refresh(student)
    db.refresh(registry)

    # ------------------------------------------------------
    # 8) Return official trusted identity
    # ------------------------------------------------------

    return {
        "success": True,
        "verified": True,
        "message": (
            "College student identity verified successfully."
        ),
        "data": {
            "college": serialize_verified_college(
                college
            ),

            "student": {
                "student_id_number":
                    registry.student_id_number,

                "official_name":
                    registry.student_name,

                "year":
                    registry.year,

                "claimed":
                    True,
            },

            "department": {
                "id":
                    department.id
                    if department
                    else None,

                "name":
                    department.name
                    if department
                    else None,

                "code":
                    department.code
                    if department
                    else None,

                "program_type":
                    getattr(
                        department,
                        "program_type",
                        None,
                    )
                    if department
                    else None,
            },

            "verified_at":
                student.college_verified_at,

            "verification_source":
                student.college_verification_source,
        },
    }


@router.get("/college-verification/status")
@router.get(
    "/college-verification",
    include_in_schema=False,
)
def get_college_verification(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    """
    Return the logged-in student's official college
    verification state.
    """

    student = get_student(
        db,
        user.id,
    )

    registry = (
        db.query(CollegeStudentRegistry)
        .filter(
            CollegeStudentRegistry.claimed_student_id
            == student.id
        )
        .first()
    )

    # If student says verified but the official claim is missing,
    # do not expose a false verified state.
    if not registry:
        return {
            "success": True,
            "data": {
                "verified": False,

                "student_id_number":
                    student.student_id_number,

                "verified_at":
                    None,

                "verification_source":
                    None,

                "college":
                    None,

                "department":
                    None,
            },
        }

    college = (
        db.query(College)
        .filter(
            College.id
            == registry.college_id
        )
        .first()
    )

    department = None

    if registry.department_id is not None:
        department = (
            db.query(Department)
            .filter(
                Department.id
                == registry.department_id,

                Department.college_id
                == registry.college_id,
            )
            .first()
        )

    # Verification remains valid only while:
    # - official registry record is active
    # - institution itself remains verified
    registry_active = bool(
        registry.is_active
    )

    institution_verified = bool(
        college
        and is_verified_college(college)
    )

    verified = bool(
        student.college_verified
        and registry_active
        and institution_verified
    )

    return {
        "success": True,
        "data": {
            "verified":
                verified,

            "student_id_number":
                registry.student_id_number,

            "student_name":
                registry.student_name,

            "year":
                registry.year,

            "verified_at":
                student.college_verified_at
                if verified
                else None,

            "verification_source":
                student.college_verification_source
                if verified
                else None,

            "college":
                (
                    {
                        "id":
                            college.id,

                        "college_public_id":
                            getattr(
                                college,
                                "college_public_id",
                                None,
                            ),

                        "college_logo_url":
                            getattr(
                                college,
                                "college_logo_url",
                                None,
                            ),

                        "name":
                            college.name,

                        "college_code":
                            getattr(
                                college,
                                "college_code",
                                None,
                            ),

                        "aishe_code":
                            getattr(
                                college,
                                "aishe_code",
                                None,
                            ),

                        "city":
                            getattr(
                                college,
                                "city",
                                None,
                            ),

                        "state":
                            getattr(
                                college,
                                "state",
                                None,
                            ),
                    }
                    if college
                    else None
                ),

            "department":
                {
                    "id":
                        department.id
                        if department
                        else None,

                    "name":
                        department.name
                        if department
                        else None,

                    "code":
                        department.code
                        if department
                        else None,

                    "program_type":
                        getattr(
                            department,
                            "program_type",
                            None,
                        )
                        if department
                        else None,
                },
        },
    }

