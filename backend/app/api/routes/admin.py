from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db

from app.models.user import User, UserRole
from app.models.student import Student
from app.models.college import College
from app.models.department import Department
from app.models.company import Company
from app.models.opportunity import Opportunity
from app.models.application import Application


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# ============================================================
# SCHEMAS
# ============================================================

class CollegeVerificationDecision(BaseModel):
    status: str = Field(pattern="^(verified|rejected|pending)$")
    note: str | None = Field(default=None, max_length=1000)


class RecruiterVerificationUpdate(BaseModel):
    is_verified: bool


# ============================================================
# HELPERS
# ============================================================

def role_text(value) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def college_is_verified(college: College) -> bool:
    return (
        getattr(college, "verification_status", None) == "verified"
        or bool(getattr(college, "is_verified", False))
    )


def serialize_college(row: College) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,

        "name": row.name,
        "college_public_id": getattr(row, "college_public_id", None),
        "college_logo_url": getattr(row, "college_logo_url", None),

        "affiliation_status": getattr(row, "affiliation_status", None),
        "university": getattr(row, "university", None),
        "college_code": getattr(row, "college_code", None),
        "aishe_code": getattr(row, "aishe_code", None),
        "institution_type": getattr(row, "institution_type", None),
        "established_year": getattr(row, "established_year", None),

        "website": getattr(row, "website", None),
        "official_email": getattr(row, "official_email", None),
        "official_phone": getattr(row, "official_phone", None),

        "address": getattr(row, "address", None),
        "city": getattr(row, "city", None),
        "state": getattr(row, "state", None),
        "pincode": getattr(row, "pincode", None),

        "principal_name": getattr(row, "principal_name", None),

        "authorized_person_name": getattr(
            row,
            "authorized_person_name",
            None,
        ),
        "authorized_designation": getattr(
            row,
            "authorized_designation",
            None,
        ),
        "authorized_email": getattr(
            row,
            "authorized_email",
            None,
        ),
        "authorized_phone": getattr(
            row,
            "authorized_phone",
            None,
        ),

        "affiliation_certificate_url": getattr(
            row,
            "affiliation_certificate_url",
            None,
        ),
        "authorization_letter_url": getattr(
            row,
            "authorization_letter_url",
            None,
        ),

        "email_verified": bool(
            getattr(row, "email_verified", False)
        ),
        "phone_verified": bool(
            getattr(row, "phone_verified", False)
        ),
        "website_verified": bool(
            getattr(row, "website_verified", False)
        ),
        "documents_verified": bool(
            getattr(row, "documents_verified", False)
        ),

        "verification_status": getattr(
            row,
            "verification_status",
            "pending",
        ),
        "verification_note": getattr(
            row,
            "verification_note",
            None,
        ),
        "verified_at": getattr(
            row,
            "verified_at",
            None,
        ),
        "verified_by": getattr(
            row,
            "verified_by",
            None,
        ),

        "is_verified": college_is_verified(row),
    }


# ============================================================
# DASHBOARD STATS
# ============================================================

@router.get("/dashboard/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    total_students = (
        db.query(func.count(Student.id))
        .scalar()
        or 0
    )

    verified_students = (
        db.query(func.count(Student.id))
        .filter(
            Student.college_verified.is_(True)
        )
        .scalar()
        or 0
    )

    total_colleges = (
        db.query(func.count(College.id))
        .scalar()
        or 0
    )

    pending_colleges = (
        db.query(func.count(College.id))
        .filter(
            College.verification_status == "pending"
        )
        .scalar()
        or 0
    )

    verified_colleges = (
        db.query(func.count(College.id))
        .filter(
            or_(
                College.verification_status == "verified",
                College.is_verified.is_(True),
            )
        )
        .scalar()
        or 0
    )

    total_recruiters = (
        db.query(func.count(User.id))
        .filter(
            User.role == UserRole.recruiter
        )
        .scalar()
        or 0
    )

    verified_companies = (
        db.query(func.count(Company.id))
        .filter(
            Company.is_verified.is_(True)
        )
        .scalar()
        or 0
    )

    total_opportunities = (
        db.query(func.count(Opportunity.id))
        .scalar()
        or 0
    )

    total_applications = (
        db.query(func.count(Application.id))
        .scalar()
        or 0
    )

    return {
        "success": True,
        "data": {
            "total_students": int(total_students),
            "verified_students": int(verified_students),

            "total_colleges": int(total_colleges),
            "pending_colleges": int(pending_colleges),
            "verified_colleges": int(verified_colleges),

            "total_recruiters": int(total_recruiters),
            "verified_companies": int(verified_companies),

            "total_opportunities": int(total_opportunities),
            "total_applications": int(total_applications),
        },
    }


# ============================================================
# COLLEGES
# ============================================================

@router.get("/colleges")
def admin_colleges(
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    rows = (
        db.query(College)
        .order_by(College.id.desc())
        .all()
    )

    return {
        "success": True,
        "data": [
            serialize_college(row)
            for row in rows
        ],
    }


@router.get("/colleges/{college_id}")
def admin_college_detail(
    college_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    row = (
        db.query(College)
        .filter(College.id == college_id)
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="College not found",
        )

    return {
        "success": True,
        "data": serialize_college(row),
    }


@router.patch("/colleges/{college_id}/verification")
def update_college_verification(
    college_id: int,
    data: CollegeVerificationDecision,
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    row = (
        db.query(College)
        .filter(College.id == college_id)
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="College not found",
        )

    status = data.status.strip().lower()
    note = (
        data.note.strip()
        if data.note
        else None
    )

    if status == "rejected" and not note:
        raise HTTPException(
            status_code=400,
            detail="Rejection reason is required.",
        )

    now = datetime.now(timezone.utc)

    if status == "verified":
        row.verification_status = "verified"
        row.is_verified = True
        row.verification_note = note
        row.verified_by = admin.id
        row.verified_at = now

    elif status == "rejected":
        row.verification_status = "rejected"
        row.is_verified = False
        row.verification_note = note
        row.verified_by = admin.id
        row.verified_at = now

    else:
        row.verification_status = "pending"
        row.is_verified = False
        row.verification_note = note
        row.verified_by = None
        row.verified_at = None

    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": (
            "College verification updated successfully."
        ),
        "data": serialize_college(row),
    }


# ============================================================
# STUDENTS
# ============================================================

@router.get("/students")
def admin_students(
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    rows = (
        db.query(
            Student,
            User,
            College,
            Department,
        )
        .join(
            User,
            Student.user_id == User.id,
        )
        .outerjoin(
            College,
            Student.college_id == College.id,
        )
        .outerjoin(
            Department,
            Student.department_id == Department.id,
        )
        .order_by(Student.id.desc())
        .all()
    )

    data = []

    for student, user, college, department in rows:
        data.append(
            {
                "id": student.id,
                "user_id": student.user_id,

                "name": getattr(
                    user,
                    "full_name",
                    None,
                ),
                "email": getattr(
                    user,
                    "email",
                    None,
                ),

                "college_id": student.college_id,
                "college_name": (
                    college.name
                    if college
                    else getattr(
                        student,
                        "college_name",
                        None,
                    )
                ),
                "college_public_id": (
                    getattr(
                        college,
                        "college_public_id",
                        None,
                    )
                    if college
                    else None
                ),

                "department_id": student.department_id,
                "department_name": (
                    department.name
                    if department
                    else getattr(
                        student,
                        "branch",
                        None,
                    )
                ),

                "branch": getattr(
                    student,
                    "branch",
                    None,
                ),
                "student_id_number": getattr(
                    student,
                    "student_id_number",
                    None,
                ),

                "year": getattr(
                    student,
                    "year",
                    None,
                ),
                "semester": getattr(
                    student,
                    "semester",
                    None,
                ),

                "career_goal": getattr(
                    student,
                    "career_goal",
                    None,
                ),

                "college_verified": bool(
                    getattr(
                        student,
                        "college_verified",
                        False,
                    )
                ),
                "college_verified_at": getattr(
                    student,
                    "college_verified_at",
                    None,
                ),
                "college_verification_source": getattr(
                    student,
                    "college_verification_source",
                    None,
                ),
            }
        )

    return {
        "success": True,
        "data": data,
    }


# ============================================================
# RECRUITERS / COMPANIES
# ============================================================

@router.get("/recruiters")
def admin_recruiters(
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    recruiter_users = (
        db.query(User)
        .filter(
            User.role == UserRole.recruiter
        )
        .order_by(User.id.desc())
        .all()
    )

    company_rows = (
        db.query(Company)
        .all()
    )

    company_by_user = {
        company.user_id: company
        for company in company_rows
    }

    opportunity_counts = dict(
        db.query(
            Opportunity.company_id,
            func.count(Opportunity.id),
        )
        .group_by(
            Opportunity.company_id
        )
        .all()
    )

    data = []

    for user in recruiter_users:
        company = company_by_user.get(
            user.id
        )

        data.append(
            {
                "user_id": user.id,

                "recruiter_name": getattr(
                    user,
                    "full_name",
                    None,
                ),
                "email": getattr(
                    user,
                    "email",
                    None,
                ),

                "company_id": (
                    company.id
                    if company
                    else None
                ),
                "company_name": (
                    getattr(
                        company,
                        "name",
                        None,
                    )
                    if company
                    else None
                ),
                "industry": (
                    getattr(
                        company,
                        "industry",
                        None,
                    )
                    if company
                    else None
                ),
                "location": (
                    getattr(
                        company,
                        "location",
                        None,
                    )
                    if company
                    else None
                ),
                "website": (
                    getattr(
                        company,
                        "website",
                        None,
                    )
                    if company
                    else None
                ),
                "is_verified": (
                    bool(
                        getattr(
                            company,
                            "is_verified",
                            False,
                        )
                    )
                    if company
                    else False
                ),
                "opportunity_count": (
                    int(
                        opportunity_counts.get(
                            company.id,
                            0,
                        )
                    )
                    if company
                    else 0
                ),
            }
        )

    return {
        "success": True,
        "data": data,
    }


@router.patch(
    "/recruiters/{company_id}/verification"
)
def update_recruiter_verification(
    company_id: int,
    data: RecruiterVerificationUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(
        require_roles(UserRole.admin)
    ),
):
    company = (
        db.query(Company)
        .filter(
            Company.id == company_id
        )
        .first()
    )

    if not company:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    company.is_verified = (
        data.is_verified
    )

    db.commit()
    db.refresh(company)

    return {
        "success": True,
        "message": (
            "Company verified successfully."
            if company.is_verified
            else "Company verification removed."
        ),
        "data": {
            "company_id": company.id,
            "is_verified": bool(
                company.is_verified
            ),
        },
    }
