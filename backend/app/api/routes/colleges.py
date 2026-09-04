from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db

from app.models.user import User, UserRole
from app.models.college import College
from app.models.department import Department
from app.models.collaboration import Collaboration

from app.schemas.college import (
    CollegeProfileCreate,
    CollegeProfileUpdate,
    DepartmentCreate,
)

from app.schemas.collaboration import CollaborationStatusUpdate

from app.services.college_analytics import (
    get_college_summary,
    get_top_student_skills,
    get_industry_skill_demand,
    get_skill_gap_analysis,
)


# ============================================================
# Router
# ============================================================

router = APIRouter(
    prefix="/colleges",
    tags=["College / TPO"]
)


# ============================================================
# Helper - Get Logged-in College
# ============================================================

def get_college(
    db: Session,
    user_id: int
):
    row = (
        db.query(College)
        .filter(College.user_id == user_id)
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="College profile not found"
        )

    return row


# ============================================================
# CREATE COLLEGE PROFILE
#
# College ID manually send nahi karna hai.
# PostgreSQL / SQLAlchemy automatically row.id generate karega.
# ============================================================

@router.post("/profile")
def create_profile(
    data: CollegeProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    # Check whether profile already exists
    existing = (
        db.query(College)
        .filter(College.user_id == user.id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="College profile already exists"
        )

    # Create college
    row = College(
        user_id=user.id,
        **data.model_dump()
    )

    db.add(row)
    db.commit()

    # Gets auto-generated College ID
    db.refresh(row)

    return {
        "success": True,
        "message": "College profile created successfully",
        "data": {
            "id": row.id,
            "name": row.name,
            "university": row.university,
            "city": row.city,
            "state": row.state,
            "website": row.website,
            "is_verified": row.is_verified,
        },
    }


# ============================================================
# GET CURRENT COLLEGE PROFILE
#
# Frontend profile.html and dashboard.html use this.
# ============================================================

@router.get("/profile")
def read_profile(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    row = get_college(
        db,
        user.id
    )

    return {
        "success": True,
        "data": {
            "id": row.id,
            "name": row.name,
            "university": row.university,
            "city": row.city,
            "state": row.state,
            "website": row.website,
            "is_verified": row.is_verified,
        },
    }


# ============================================================
# UPDATE CURRENT COLLEGE PROFILE
#
# College ID change nahi hoga.
# Sirf profile information update hogi.
# ============================================================

@router.patch("/profile")
def update_profile(
    data: CollegeProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    row = get_college(
        db,
        user.id
    )

    update_data = data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(
            row,
            field,
            value
        )

    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": "College profile updated successfully",
        "data": {
            "id": row.id,
            "name": row.name,
            "university": row.university,
            "city": row.city,
            "state": row.state,
            "website": row.website,
            "is_verified": row.is_verified,
        },
    }


# ============================================================
# COLLEGE DIRECTORY
#
# Recruiter collaboration form me College ID manually
# enter karne ki jagah College dropdown ke liye.
# ============================================================

@router.get("/directory")
def college_directory(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.recruiter)
    ),
):
    rows = (
        db.query(College)
        .order_by(College.name.asc())
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "id": row.id,
                "name": row.name,
                "university": row.university,
                "city": row.city,
                "state": row.state,
                "is_verified": row.is_verified,
            }
            for row in rows
        ],
    }


# ============================================================
# CREATE DEPARTMENT
#
# Logged-in college ka College ID automatically attach hoga.
# ============================================================

@router.post("/departments")
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    row = Department(
        college_id=current_college.id,
        **data.model_dump()
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": "Department created successfully",
        "data": row,
    }


# ============================================================
# GET DEPARTMENTS
# ============================================================

@router.get("/departments")
def get_departments(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    rows = (
        db.query(Department)
        .filter(
            Department.college_id
            == current_college.id
        )
        .all()
    )

    return {
        "success": True,
        "data": rows,
    }


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

@router.get("/dashboard/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    return {
        "success": True,
        "data": get_college_summary(
            db,
            current_college.id
        ),
    }


# ============================================================
# STUDENT SKILL ANALYTICS
# ============================================================

@router.get("/analytics/student-skills")
def student_skills(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    return {
        "success": True,
        "data": get_top_student_skills(
            db,
            current_college.id
        ),
    }


# ============================================================
# INDUSTRY SKILL DEMAND
# ============================================================

@router.get("/analytics/industry-demand")
def industry_demand(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    # Make sure logged-in college has profile
    get_college(
        db,
        user.id
    )

    return {
        "success": True,
        "data": get_industry_skill_demand(db),
    }


# ============================================================
# SKILL GAP ANALYTICS
# ============================================================

@router.get("/analytics/skill-gap")
def skill_gap(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    return {
        "success": True,
        "data": get_skill_gap_analysis(
            db,
            current_college.id
        ),
    }


# ============================================================
# GET COLLABORATION REQUESTS
#
# Sirf logged-in college ko bheji gayi requests show hongi.
# ============================================================

@router.get("/collaborations")
def collaborations(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    rows = (
        db.query(Collaboration)
        .filter(
            Collaboration.college_id
            == current_college.id
        )
        .all()
    )

    return {
        "success": True,
        "data": rows,
    }


# ============================================================
# UPDATE COLLABORATION STATUS
# ============================================================

@router.patch(
    "/collaborations/{cid}/status"
)
def update_collaboration_status(
    cid: int,
    data: CollaborationStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    row = (
        db.query(Collaboration)
        .filter(
            Collaboration.id == cid,
            Collaboration.college_id
            == current_college.id,
        )
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Collaboration not found"
        )

    row.status = data.status
    row.college_note = data.college_note

    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": "Collaboration status updated",
        "data": {
            "id": row.id,
            "status": row.status,
            "college_note": row.college_note,
        },
    }