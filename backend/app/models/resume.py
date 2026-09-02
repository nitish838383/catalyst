from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import require_roles

from app.models.user import User, UserRole
from app.models.company import Company
from app.models.college import College
from app.models.student import Student
from app.models.skill import Skill
from app.models.resume import Resume
from app.models.opportunity import Opportunity, OpportunitySkill
from app.models.application import Application, ApplicationStatus
from app.models.interview import Interview
from app.models.collaboration import Collaboration, CollaborationSkill

from app.schemas.company import CompanyCreate
from app.schemas.opportunity import OpportunityCreate, OpportunitySkillCreate
from app.schemas.application import (
    ApplicationStatusUpdate,
    InterviewScheduleRequest,
)
from app.schemas.collaboration import CollaborationCreate

from app.services.matching import calculate_match
from app.services.notifications import create_notification


router = APIRouter(
    prefix="/recruiters",
    tags=["Recruiters"]
)


# =========================================================
# HELPER - GET RECRUITER COMPANY
# =========================================================

def get_company(
    db: Session,
    user_id: int
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
            detail="Create company profile first"
        )

    return company


# =========================================================
# HELPER - CHECK STUDENT ACCESS
# =========================================================

def check_student_access(
    db: Session,
    company_id: int,
    student_id: int
):
    application = (
        db.query(Application)
        .join(
            Opportunity,
            Application.opportunity_id == Opportunity.id
        )
        .filter(
            Application.student_id == student_id,
            Opportunity.company_id == company_id
        )
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=403,
            detail="You cannot access this student"
        )

    return application


# =========================================================
# COMPANY
# =========================================================

@router.post("/company")
def create_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    existing = (
        db.query(Company)
        .filter(
            Company.user_id == user.id
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Company profile already exists"
        )

    company = Company(
        user_id=user.id,
        **data.model_dump()
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return company


@router.get("/company")
def get_recruiter_company(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    return get_company(
        db,
        user.id
    )


# =========================================================
# CREATE OPPORTUNITY
# =========================================================

@router.post("/opportunities")
def create_opportunity(
    data: OpportunityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    opportunity = Opportunity(
        company_id=company.id,
        **data.model_dump()
    )

    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)

    return {
        "success": True,
        "data": {
            "id": opportunity.id,
            "title": opportunity.title,
            "description": opportunity.description,
            "opportunity_type": opportunity.opportunity_type,
            "location": opportunity.location,
            "stipend": opportunity.stipend,
            "experience_required": opportunity.experience_required,
            "is_active": opportunity.is_active
        }
    }


# =========================================================
# GET MY OPPORTUNITIES
# =========================================================

@router.get("/opportunities")
def get_my_opportunities(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    opportunities = (
        db.query(Opportunity)
        .filter(
            Opportunity.company_id == company.id
        )
        .order_by(
            Opportunity.id.desc()
        )
        .all()
    )

    data = []

    for opportunity in opportunities:

        application_count = (
            db.query(Application)
            .filter(
                Application.opportunity_id == opportunity.id
            )
            .count()
        )

        data.append({
            "id": opportunity.id,
            "title": opportunity.title,
            "description": opportunity.description,
            "opportunity_type": opportunity.opportunity_type,
            "location": opportunity.location,
            "stipend": opportunity.stipend,
            "experience_required": opportunity.experience_required,
            "is_active": opportunity.is_active,
            "application_count": application_count
        })

    return {
        "success": True,
        "data": data
    }


# =========================================================
# ADD OPPORTUNITY SKILL
# =========================================================

@router.post("/opportunities/{oid}/skills")
def add_opportunity_skill(
    oid: int,
    data: OpportunitySkillCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    opportunity = (
        db.query(Opportunity)
        .filter(
            Opportunity.id == oid,
            Opportunity.company_id == company.id
        )
        .first()
    )

    if not opportunity:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found"
        )

    skill_name = (
        data.skill_name
        .strip()
        .lower()
    )

    skill = (
        db.query(Skill)
        .filter(
            Skill.name == skill_name
        )
        .first()
    )

    if not skill:
        skill = Skill(
            name=skill_name,
            category=data.category
        )

        db.add(skill)
        db.flush()

    existing = (
        db.query(OpportunitySkill)
        .filter(
            OpportunitySkill.opportunity_id == oid,
            OpportunitySkill.skill_id == skill.id
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Skill already added"
        )

    row = OpportunitySkill(
        opportunity_id=oid,
        skill_id=skill.id,
        is_required=data.is_required,
        weight=data.weight
    )

    db.add(row)
    db.commit()

    return {
        "success": True,
        "message": "Skill added successfully"
    }


# =========================================================
# RANKED APPLICANTS
# =========================================================

@router.get("/opportunities/{oid}/applications")
def ranked_applicants(
    oid: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    opportunity = (
        db.query(Opportunity)
        .filter(
            Opportunity.id == oid,
            Opportunity.company_id == company.id
        )
        .first()
    )

    if not opportunity:
        raise HTTPException(
            status_code=404,
            detail="Opportunity not found"
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
            Application.opportunity_id == oid
        )
        .all()
    )

    candidates = []

    for application, student, student_user in rows:

        match = calculate_match(
            db,
            student.id,
            oid
        )

        latest_resume = (
            db.query(Resume)
            .filter(
                Resume.student_id == student.id
            )
            .order_by(
                Resume.created_at.desc()
            )
            .first()
        )

        candidates.append({
            "application_id": application.id,

            "student_id": student.id,

            "name": student_user.full_name,

            "email": student_user.email,

            "college_id": student.college_id,

            "college_name": student.college_name,

            "department_id": student.department_id,

            "branch": student.branch,

            "year": student.year,

            "semester": student.semester,

            "career_goal": student.career_goal,

            "match_score": match["score"],

            "matched_skills": match["matched_skills"],

            "missing_skills": match["missing_skills"],

            "status": application.status,

            "recruiter_note": application.recruiter_note,

            "has_resume": latest_resume is not None,

            "resume_id": (
                latest_resume.id
                if latest_resume
                else None
            )
        })

    candidates.sort(
        key=lambda item: item["match_score"],
        reverse=True
    )

    return {
        "success": True,

        "opportunity": {
            "id": opportunity.id,
            "title": opportunity.title,
            "type": opportunity.opportunity_type,
            "location": opportunity.location
        },

        "total_candidates": len(candidates),

        "candidates": candidates
    }


# =========================================================
# VIEW STUDENT PROFILE
# =========================================================

@router.get("/students/{student_id}")
def recruiter_student_profile(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    check_student_access(
        db,
        company.id,
        student_id
    )

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
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    student, student_user = row

    college_name = student.college_name

    if student.college_id:

        college = (
            db.query(College)
            .filter(
                College.id == student.college_id
            )
            .first()
        )

        if college:
            college_name = college.name

    resume = (
        db.query(Resume)
        .filter(
            Resume.student_id == student.id
        )
        .order_by(
            Resume.created_at.desc()
        )
        .first()
    )

    return {
        "success": True,

        "data": {
            "student_id": student.id,

            "name": student_user.full_name,

            "email": student_user.email,

            "college_id": student.college_id,

            "college_name": college_name,

            "department_id": student.department_id,

            "branch": student.branch,

            "year": student.year,

            "semester": student.semester,

            "career_goal": student.career_goal,

            "bio": student.bio,

            "github_url": student.github_url,

            "linkedin_url": student.linkedin_url,

            "portfolio_url": student.portfolio_url,

            "has_resume": resume is not None,

            "resume_id": (
                resume.id
                if resume
                else None
            ),

            "resume_filename": (
                resume.original_filename
                if resume
                else None
            )
        }
    }


# =========================================================
# GET STUDENT RESUME INFO
# =========================================================

@router.get("/students/{student_id}/resume")
def recruiter_student_resume(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    check_student_access(
        db,
        company.id,
        student_id
    )

    resume = (
        db.query(Resume)
        .filter(
            Resume.student_id == student_id
        )
        .order_by(
            Resume.created_at.desc()
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Student has not uploaded a resume"
        )

    return {
        "success": True,

        "data": {
            "resume_id": resume.id,
            "student_id": resume.student_id,
            "filename": resume.original_filename,
            "is_processed": resume.is_processed,
            "created_at": resume.created_at
        }
    }


# =========================================================
# VIEW RESUME
# =========================================================

@router.get("/students/{student_id}/resume/view")
def recruiter_view_resume(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    check_student_access(
        db,
        company.id,
        student_id
    )

    resume = (
        db.query(Resume)
        .filter(
            Resume.student_id == student_id
        )
        .order_by(
            Resume.created_at.desc()
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    path = Path(
        resume.file_path
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Resume file is no longer available"
        )

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=resume.original_filename,
        content_disposition_type="inline"
    )


# =========================================================
# DOWNLOAD RESUME
# =========================================================

@router.get("/students/{student_id}/resume/download")
def recruiter_download_resume(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    check_student_access(
        db,
        company.id,
        student_id
    )

    resume = (
        db.query(Resume)
        .filter(
            Resume.student_id == student_id
        )
        .order_by(
            Resume.created_at.desc()
        )
        .first()
    )

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    path = Path(
        resume.file_path
    )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Resume file is no longer available"
        )

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=resume.original_filename
    )


# =========================================================
# UPDATE APPLICATION STATUS
# =========================================================

@router.patch("/applications/{aid}/status")
def update_application_status(
    aid: int,
    data: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    row = (
        db.query(
            Application,
            Opportunity,
            Student
        )
        .join(
            Opportunity,
            Application.opportunity_id == Opportunity.id
        )
        .join(
            Student,
            Application.student_id == Student.id
        )
        .filter(
            Application.id == aid,
            Opportunity.company_id == company.id
        )
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    application, opportunity, student = row

    application.status = data.status

    application.recruiter_note = (
        data.recruiter_note
    )

    create_notification(
        db,
        student.user_id,

        f"Application Update: {opportunity.title}",

        f"Status changed to {data.status.value}.",

        "application_update",

        application.id
    )

    db.commit()

    return {
        "success": True,
        "status": application.status
    }


# =========================================================
# SCHEDULE INTERVIEW
# =========================================================

@router.post("/applications/{aid}/interview")
def schedule_interview(
    aid: int,
    data: InterviewScheduleRequest,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

    row = (
        db.query(
            Application,
            Opportunity,
            Student
        )
        .join(
            Opportunity,
            Application.opportunity_id == Opportunity.id
        )
        .join(
            Student,
            Application.student_id == Student.id
        )
        .filter(
            Application.id == aid,
            Opportunity.company_id == company.id
        )
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    application, opportunity, student = row

    interview = (
        db.query(Interview)
        .filter(
            Interview.application_id == aid
        )
        .first()
    )

    if interview:

        for key, value in data.model_dump().items():
            setattr(
                interview,
                key,
                value
            )

    else:

        interview = Interview(
            application_id=aid,
            **data.model_dump()
        )

        db.add(interview)

    application.status = (
        ApplicationStatus.interview
    )

    create_notification(
        db,
        student.user_id,

        "Interview Scheduled",

        f"Interview scheduled for {opportunity.title}.",

        "interview",

        aid
    )

    db.commit()

    return {
        "success": True,
        "message": "Interview scheduled successfully"
    }


# =========================================================
# CREATE COLLABORATION
# =========================================================

@router.post("/collaborations")
def create_collaboration(
    data: CollaborationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    )
):
    company = get_company(
        db,
        user.id
    )

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
            detail="College not found"
        )

    collaboration = Collaboration(
        company_id=company.id,
        college_id=college.id,
        collaboration_type=data.collaboration_type,
        title=data.title,
        description=data.description,
        proposed_date=data.proposed_date,
        location=data.location,
        mode=data.mode
    )

    db.add(collaboration)
    db.flush()

    for skill_name in data.skills:

        name = (
            skill_name
            .strip()
            .lower()
        )

        skill = (
            db.query(Skill)
            .filter(
                Skill.name == name
            )
            .first()
        )

        if not skill:
            skill = Skill(
                name=name
            )

            db.add(skill)
            db.flush()

        db.add(
            CollaborationSkill(
                collaboration_id=collaboration.id,
                skill_id=skill.id
            )
        )

    create_notification(
        db,
        college.user_id,

        "New Industry Collaboration Proposal",

        f"{company.name} proposed {collaboration.title}",

        "collaboration",

        collaboration.id
    )

    db.commit()

    return {
        "success": True,
        "id": collaboration.id
    }