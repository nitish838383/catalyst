from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db

from app.models.user import User, UserRole
from app.models.college import College
from app.models.department import Department
from app.models.collaboration import Collaboration
from app.models.college_student_registry import CollegeStudentRegistry
from app.models.student import Student

from app.schemas.college import (
    CollegeProfileCreate,
    CollegeProfileUpdate,
    DepartmentCreate,
    CollegeStudentRegistryCreate,
    CollegeStudentRegistryUpdate,
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
# COLLEGE STUDENT REGISTRY
#
# College/TPO apne registered students ke official
# Student ID / Enrollment Number yahan maintain karega.
# Student verification isi registry ke against hogi.
# ============================================================

def normalize_student_id(value: str) -> str:
    return value.strip().upper()


def validate_department_for_college(
    db: Session,
    college_id: int,
    department_id: int | None,
):
    if department_id is None:
        return None

    department = (
        db.query(Department)
        .filter(
            Department.id == department_id,
            Department.college_id == college_id,
        )
        .first()
    )

    if not department:
        raise HTTPException(
            status_code=400,
            detail="Department does not belong to this college"
        )

    return department


@router.post("/student-registry")
def create_student_registry(
    data: CollegeStudentRegistryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    # Department is mandatory in the create schema and must
    # belong to the logged-in college.
    validate_department_for_college(
        db,
        current_college.id,
        data.department_id,
    )

    normalized_id = normalize_student_id(
        data.student_id_number
    )

    existing = (
        db.query(CollegeStudentRegistry)
        .filter(
            CollegeStudentRegistry.college_id
            == current_college.id,
            CollegeStudentRegistry.student_id_number
            == normalized_id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="This Student ID already exists in your registry"
        )

    row = CollegeStudentRegistry(
        college_id=current_college.id,
        department_id=data.department_id,
        student_id_number=normalized_id,
        student_name=data.student_name.strip(),
        year=data.year,
        is_active=True,
    )

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": "Student added to college registry",
        "data": {
            "id": row.id,
            "college_id": row.college_id,
            "department_id": row.department_id,
            "student_id_number": row.student_id_number,
            "student_name": row.student_name,
            "year": row.year,
            "is_active": row.is_active,
            "claimed_student_id": row.claimed_student_id,
            "is_claimed": row.claimed_student_id is not None,
        },
    }


@router.get("/student-registry")
def get_student_registry(
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
        db.query(CollegeStudentRegistry)
        .filter(
            CollegeStudentRegistry.college_id
            == current_college.id
        )
        .order_by(
            CollegeStudentRegistry.id.desc()
        )
        .all()
    )

    department_ids = {
        row.department_id
        for row in rows
        if row.department_id is not None
    }

    department_map = {}

    if department_ids:
        departments = (
            db.query(Department)
            .filter(
                Department.id.in_(department_ids),
                Department.college_id
                == current_college.id,
            )
            .all()
        )

        department_map = {
            department.id: {
                "name": department.name,
                "code": department.code,
            }
            for department in departments
        }

    return {
        "success": True,
        "data": [
            {
                "id": row.id,
                "college_id": row.college_id,
                "department_id": row.department_id,
                "department_name": (
                    department_map.get(
                        row.department_id,
                        {}
                    ).get("name")
                ),
                "department_code": (
                    department_map.get(
                        row.department_id,
                        {}
                    ).get("code")
                ),
                "student_id_number":
                    row.student_id_number,
                "student_name":
                    row.student_name,
                "year":
                    row.year,
                "is_active":
                    row.is_active,
                "claimed_student_id":
                    row.claimed_student_id,
                "is_claimed":
                    row.claimed_student_id
                    is not None,
            }
            for row in rows
        ],
    }


@router.patch("/student-registry/{registry_id}")
def update_student_registry(
    registry_id: int,
    data: CollegeStudentRegistryUpdate,
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
        db.query(CollegeStudentRegistry)
        .filter(
            CollegeStudentRegistry.id
            == registry_id,
            CollegeStudentRegistry.college_id
            == current_college.id,
        )
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Student registry record not found"
        )

    update_data = data.model_dump(
        exclude_unset=True
    )

    if "department_id" in update_data:
        # update schema allows None, but for an official active
        # registry record we do not allow removing the department.
        if update_data["department_id"] is None:
            raise HTTPException(
                status_code=400,
                detail="Department is required for a student registry record"
            )

        validate_department_for_college(
            db,
            current_college.id,
            update_data["department_id"],
        )

    if "student_name" in update_data:
        if update_data["student_name"] is None:
            raise HTTPException(
                status_code=400,
                detail="Student name is required"
            )

        update_data["student_name"] = (
            update_data["student_name"].strip()
        )

    if "year" in update_data and update_data["year"] is None:
        raise HTTPException(
            status_code=400,
            detail="Year is required"
        )

    for field, value in update_data.items():
        setattr(
            row,
            field,
            value
        )

    # If this registry row is already claimed, keep the linked
    # SkillBridge student profile synchronized with the official
    # college/TPO registry.
    linked_student = None

    if row.claimed_student_id is not None:
        linked_student = (
            db.query(Student)
            .filter(
                Student.id == row.claimed_student_id
            )
            .first()
        )

    if linked_student:
        linked_student.college_id = current_college.id
        linked_student.college_name = current_college.name
        linked_student.department_id = row.department_id
        linked_student.student_id_number = row.student_id_number
        linked_student.year = row.year
        linked_student.college_verified = bool(row.is_active)

        if row.department_id is not None:
            department = (
                db.query(Department)
                .filter(
                    Department.id == row.department_id,
                    Department.college_id == current_college.id,
                )
                .first()
            )

            if department:
                linked_student.branch = department.name

    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": "Student registry updated successfully",
        "data": {
            "id": row.id,
            "college_id": row.college_id,
            "department_id": row.department_id,
            "student_id_number": row.student_id_number,
            "student_name": row.student_name,
            "year": row.year,
            "is_active": row.is_active,
            "claimed_student_id": row.claimed_student_id,
            "is_claimed": row.claimed_student_id is not None,
        },
    }


@router.delete("/student-registry/{registry_id}")
def delete_student_registry(
    registry_id: int,
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
        db.query(CollegeStudentRegistry)
        .filter(
            CollegeStudentRegistry.id
            == registry_id,
            CollegeStudentRegistry.college_id
            == current_college.id,
        )
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Student registry record not found"
        )

    # Claimed records are kept for audit/history.
    # Deactivate the official record and revoke verification
    # on the linked SkillBridge student profile.
    if row.claimed_student_id is not None:
        row.is_active = False

        linked_student = (
            db.query(Student)
            .filter(
                Student.id == row.claimed_student_id
            )
            .first()
        )

        if linked_student:
            linked_student.college_verified = False

        db.commit()

        return {
            "success": True,
            "message": (
                "Verified student record deactivated and "
                "college verification revoked successfully"
            ),
        }

    db.delete(row)
    db.commit()

    return {
        "success": True,
        "message": "Student removed from registry"
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

# ============================================================
# STUDENT COLLEGE DIRECTORY
# ============================================================

@router.get("/student-directory")
def student_college_directory(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
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
# STUDENT DEPARTMENTS BY COLLEGE
# ============================================================

@router.get("/{college_id}/student-departments")
def student_college_departments(
    college_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    college_row = (
        db.query(College)
        .filter(College.id == college_id)
        .first()
    )

    if not college_row:
        raise HTTPException(
            status_code=404,
            detail="College not found"
        )

    rows = (
        db.query(Department)
        .filter(
            Department.college_id == college_id
        )
        .order_by(Department.name.asc())
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "id": row.id,
                "name": row.name,
                "code": row.code,
                "college_id": row.college_id,
            }
            for row in rows
        ],
    }