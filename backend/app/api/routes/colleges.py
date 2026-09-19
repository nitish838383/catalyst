from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
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
    DepartmentUpdate,
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
# Helper - Verification / Serialization
# ============================================================

def is_college_verified(college: College) -> bool:
    """
    New verification_status is authoritative.
    is_verified is kept as a legacy fallback during migration.
    """
    return (
        getattr(college, "verification_status", None) == "verified"
        or bool(getattr(college, "is_verified", False))
    )


def require_verified_college_profile(college: College):
    if not is_college_verified(college):
        raise HTTPException(
            status_code=403,
            detail=(
                "College verification is required for this action. "
                "Complete institution verification and admin approval first."
            ),
        )


def serialize_college(row: College):
    return {
        "id": row.id,
        "user_id": row.user_id,
        "name": row.name,
        "college_public_id": getattr(row, "college_public_id", None),
        "college_logo_url": getattr(row, "college_logo_url", None),
        "affiliation_status": getattr(row, "affiliation_status", None),
        "university": row.university,
        "college_code": getattr(row, "college_code", None),
        "aishe_code": getattr(row, "aishe_code", None),
        "institution_type": getattr(row, "institution_type", None),
        "established_year": getattr(row, "established_year", None),
        "website": row.website,
        "official_email": getattr(row, "official_email", None),
        "official_phone": getattr(row, "official_phone", None),
        "address": getattr(row, "address", None),
        "city": row.city,
        "state": row.state,
        "pincode": getattr(row, "pincode", None),
        "principal_name": getattr(row, "principal_name", None),
        "authorized_person_name": getattr(
            row, "authorized_person_name", None
        ),
        "authorized_designation": getattr(
            row, "authorized_designation", None
        ),
        "authorized_email": getattr(row, "authorized_email", None),
        "authorized_phone": getattr(row, "authorized_phone", None),
        "affiliation_certificate_url": getattr(
            row, "affiliation_certificate_url", None
        ),
        "authorization_letter_url": getattr(
            row, "authorization_letter_url", None
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
            row, "verification_status", "pending"
        ),
        "verification_note": getattr(
            row, "verification_note", None
        ),
        "is_verified": is_college_verified(row),
    }


def normalize_code(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip().upper()
    return value or None


def ensure_unique_college_identity(
    db: Session,
    *,
    college_public_id: str | None,
    college_code: str | None,
    aishe_code: str | None,
    official_email: str | None,
    exclude_college_id: int | None = None,
):
    filters = []

    if college_public_id:
        filters.append(
            College.college_public_id == college_public_id
        )

    if college_code:
        filters.append(College.college_code == college_code)

    if aishe_code:
        filters.append(College.aishe_code == aishe_code)

    if official_email:
        filters.append(
            College.official_email == official_email.lower()
        )

    if not filters:
        return

    query = db.query(College).filter(or_(*filters))

    if exclude_college_id is not None:
        query = query.filter(College.id != exclude_college_id)

    existing = query.first()

    if not existing:
        return

    if (
        college_public_id
        and existing.college_public_id == college_public_id
    ):
        detail = "This Public College ID is already registered."

    elif college_code and existing.college_code == college_code:
        detail = "This College / University Code is already registered."

    elif aishe_code and existing.aishe_code == aishe_code:
        detail = "This AISHE Code is already registered."

    else:
        detail = "This official college email is already registered."

    raise HTTPException(status_code=409, detail=detail)


def get_website_domain(url: str | None) -> str:
    if not url:
        return ""

    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return ""

    host = host.lower().strip()

    if host.startswith("www."):
        host = host[4:]

    return host


def get_email_domain(email: str | None) -> str:
    if not email or "@" not in email:
        return ""

    return email.rsplit("@", 1)[-1].lower().strip()


def domain_matches(website: str | None, email: str | None) -> bool:
    website_domain = get_website_domain(website)
    email_domain = get_email_domain(email)

    if not website_domain or not email_domain:
        return False

    return (
        website_domain == email_domain
        or website_domain.endswith("." + email_domain)
        or email_domain.endswith("." + website_domain)
    )


# ============================================================
# CREATE COLLEGE PROFILE
# ============================================================

@router.post("/profile")
def create_profile(
    data: CollegeProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    existing = (
        db.query(College)
        .filter(College.user_id == user.id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="College profile already exists",
        )

    create_data = data.model_dump()

    create_data["college_public_id"] = normalize_code(
        create_data.get("college_public_id")
    )

    create_data["college_code"] = normalize_code(
        create_data.get("college_code")
    )
    create_data["aishe_code"] = normalize_code(
        create_data.get("aishe_code")
    )

    if create_data.get("official_email"):
        create_data["official_email"] = (
            create_data["official_email"].strip().lower()
        )

    if create_data.get("affiliation_status") == "affiliated":
        if not create_data.get("university"):
            raise HTTPException(
                status_code=400,
                detail="Affiliated university is required.",
            )

    if create_data.get("affiliation_status") == "self_university":
        create_data["university"] = None

    ensure_unique_college_identity(
        db,
        college_public_id=create_data.get("college_public_id"),
        college_code=create_data.get("college_code"),
        aishe_code=create_data.get("aishe_code"),
        official_email=create_data.get("official_email"),
    )

    row = College(
        user_id=user.id,
        **create_data,
    )

    # College cannot verify itself.
    row.is_verified = False
    row.verification_status = "pending"
    row.email_verified = False
    row.phone_verified = False
    row.website_verified = False
    row.documents_verified = False
    row.verification_note = None
    row.verified_at = None
    row.verified_by = None

    db.add(row)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "College identity already exists. "
                "Check Public College ID, College Code, AISHE Code and official email."
            ),
        )

    db.refresh(row)

    return {
        "success": True,
        "message": (
            "College profile created successfully. "
            "Verification is pending."
        ),
        "data": serialize_college(row),
    }


# ============================================================
# GET CURRENT COLLEGE PROFILE
# ============================================================

@router.get("/profile")
def read_profile(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    row = get_college(db, user.id)

    return {
        "success": True,
        "data": serialize_college(row),
    }


# ============================================================
# UPDATE CURRENT COLLEGE PROFILE
# ============================================================

@router.patch("/profile")
def update_profile(
    data: CollegeProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    row = get_college(db, user.id)

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        return {
            "success": True,
            "message": "No profile changes supplied.",
            "data": serialize_college(row),
        }

    if "college_public_id" in update_data:
        update_data["college_public_id"] = normalize_code(
            update_data["college_public_id"]
        )

        if not update_data["college_public_id"]:
            raise HTTPException(
                status_code=400,
                detail="Public College ID cannot be empty.",
            )

    if "college_code" in update_data:
        update_data["college_code"] = normalize_code(
            update_data["college_code"]
        )

    if "aishe_code" in update_data:
        update_data["aishe_code"] = normalize_code(
            update_data["aishe_code"]
        )

    if (
        "official_email" in update_data
        and update_data["official_email"] is not None
    ):
        update_data["official_email"] = (
            update_data["official_email"].strip().lower()
        )

    future_affiliation_status = update_data.get(
        "affiliation_status",
        row.affiliation_status,
    )
    future_university = update_data.get(
        "university",
        row.university,
    )

    if future_affiliation_status == "affiliated":
        if (
            future_university is None
            or not str(future_university).strip()
        ):
            raise HTTPException(
                status_code=400,
                detail="Affiliated university is required.",
            )

    elif future_affiliation_status == "self_university":
        update_data["university"] = None

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid affiliation status.",
        )

    final_college_public_id = update_data.get(
        "college_public_id",
        row.college_public_id,
    )

    final_college_code = update_data.get(
        "college_code",
        row.college_code,
    )
    final_aishe_code = update_data.get(
        "aishe_code",
        row.aishe_code,
    )
    final_official_email = update_data.get(
        "official_email",
        row.official_email,
    )

    ensure_unique_college_identity(
        db,
        college_public_id=final_college_public_id,
        college_code=final_college_code,
        aishe_code=final_aishe_code,
        official_email=final_official_email,
        exclude_college_id=row.id,
    )

    # College logo is intentionally NOT verification-sensitive.
    # A logo change should not revoke an otherwise verified institution.
    verification_sensitive_fields = {
        "name",
        "college_public_id",
        "affiliation_status",
        "university",
        "college_code",
        "aishe_code",
        "institution_type",
        "website",
        "official_email",
        "official_phone",
        "address",
        "city",
        "state",
        "pincode",
        "principal_name",
        "authorized_person_name",
        "authorized_designation",
        "authorized_email",
        "authorized_phone",
    }

    changed_sensitive_fields = {
        field
        for field in verification_sensitive_fields
        if field in update_data
        and getattr(row, field, None) != update_data[field]
    }

    if changed_sensitive_fields:
        row.verification_status = "pending"
        row.is_verified = False
        row.verification_note = (
            "Institution profile changed; re-verification required."
        )
        row.verified_at = None
        row.verified_by = None

    if "official_email" in changed_sensitive_fields:
        row.email_verified = False

    if "official_phone" in changed_sensitive_fields:
        row.phone_verified = False

    if (
        "website" in changed_sensitive_fields
        or "official_email" in changed_sensitive_fields
    ):
        row.website_verified = False

    for field, value in update_data.items():
        setattr(row, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "College identity already exists. "
                "Check Public College ID, College Code, AISHE Code and official email."
            ),
        )

    db.refresh(row)

    return {
        "success": True,
        "message": (
            "College profile updated successfully. "
            "Re-verification may be required if trusted details changed."
        ),
        "data": serialize_college(row),
    }


# ============================================================
# WEBSITE / OFFICIAL EMAIL DOMAIN CHECK
# ============================================================

@router.post("/verification/website")
def verify_website_domain(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    row = get_college(db, user.id)

    if not row.website or not row.official_email:
        raise HTTPException(
            status_code=400,
            detail=(
                "Official website and official email are required "
                "before domain verification."
            ),
        )

    if not domain_matches(row.website, row.official_email):
        row.website_verified = False
        db.commit()

        raise HTTPException(
            status_code=400,
            detail=(
                "Official email domain does not match the "
                "college website domain. Manual review is required."
            ),
        )

    row.website_verified = True
    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": "Official website/email domain matched successfully.",
        "data": {
            "website_verified": True,
            "website_domain": get_website_domain(row.website),
        },
    }


# ============================================================
# COLLEGE DIRECTORY
#
# Recruiters should only see trusted institutions.
# Legacy is_verified=True is also accepted during migration.
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
        .filter(
            or_(
                College.verification_status == "verified",
                College.is_verified.is_(True),
            )
        )
        .order_by(College.name.asc())
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "id": row.id,
                "name": row.name,
                "college_public_id": row.college_public_id,
                "college_logo_url": getattr(row, "college_logo_url", None),
                "affiliation_status": row.affiliation_status,
                "university": row.university,
                "college_code": row.college_code,
                "aishe_code": row.aishe_code,
                "city": row.city,
                "state": row.state,
                "website": row.website,
                "verification_status": (
                    "verified"
                    if is_college_verified(row)
                    else row.verification_status
                ),
                "is_verified": is_college_verified(row),
            }
            for row in rows
        ],
    }


# ============================================================
# DEPARTMENT HELPERS
# ============================================================

def get_department_for_college(
    db: Session,
    college_id: int,
    department_id: int,
) -> Department:
    row = (
        db.query(Department)
        .filter(
            Department.id == department_id,
            Department.college_id == college_id,
        )
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Department not found",
        )

    return row


def normalize_department_code(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip().upper()

    return value or None


def ensure_unique_department(
    db: Session,
    *,
    college_id: int,
    name: str,
    code: str | None,
    exclude_department_id: int | None = None,
):
    query = (
        db.query(Department)
        .filter(
            Department.college_id == college_id
        )
    )

    if exclude_department_id is not None:
        query = query.filter(
            Department.id != exclude_department_id
        )

    duplicate_name = (
        query.filter(
            func.lower(Department.name)
            == name.strip().lower()
        )
        .first()
    )

    if duplicate_name:
        raise HTTPException(
            status_code=409,
            detail=(
                "A department with this name already "
                "exists in your college."
            ),
        )

    if code:
        duplicate_code = (
            query.filter(
                Department.code == code
            )
            .first()
        )

        if duplicate_code:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A department with this code already "
                    "exists in your college."
                ),
            )


def get_department_registry_stats(
    db: Session,
    department_id: int,
) -> dict:
    registered_students = (
        db.query(func.count(CollegeStudentRegistry.id))
        .filter(
            CollegeStudentRegistry.department_id
            == department_id,
            CollegeStudentRegistry.is_active.is_(True),
        )
        .scalar()
        or 0
    )

    verified_students = (
        db.query(func.count(CollegeStudentRegistry.id))
        .filter(
            CollegeStudentRegistry.department_id
            == department_id,
            CollegeStudentRegistry.is_active.is_(True),
            CollegeStudentRegistry.claimed_student_id.isnot(None),
        )
        .scalar()
        or 0
    )

    return {
        "registered_students": int(registered_students),
        "verified_students": int(verified_students),
    }


def serialize_department(
    db: Session,
    row: Department,
) -> dict:
    stats = get_department_registry_stats(
        db,
        row.id,
    )

    return {
        "id": row.id,
        "college_id": row.college_id,

        "name": row.name,
        "code": row.code,

        "program_type": row.program_type,

        "hod_name": row.hod_name,
        "coordinator_name": row.coordinator_name,

        "official_email": row.official_email,
        "contact_number": row.contact_number,

        "intake_capacity": row.intake_capacity,
        "established_year": row.established_year,

        "is_active": row.is_active,

        # Dynamic values - database columns nahi hain.
        "registered_students": stats[
            "registered_students"
        ],
        "verified_students": stats[
            "verified_students"
        ],
    }


# ============================================================
# CREATE DEPARTMENT
#
# Pending college profile ko departments prepare karne dete hain.
# Sensitive student verification separately verified-college
# restriction ke under hi rahega.
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

    create_data = data.model_dump()

    create_data["name"] = (
        create_data["name"].strip()
    )

    create_data["code"] = normalize_department_code(
        create_data.get("code")
    )

    ensure_unique_department(
        db,
        college_id=current_college.id,
        name=create_data["name"],
        code=create_data.get("code"),
    )

    row = Department(
        college_id=current_college.id,
        **create_data,
    )

    db.add(row)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Department already exists. "
                "Check department name and code."
            ),
        )

    db.refresh(row)

    return {
        "success": True,
        "message": "Department created successfully",
        "data": serialize_department(
            db,
            row,
        ),
    }


# ============================================================
# GET ALL DEPARTMENTS
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
        .order_by(
            Department.is_active.desc(),
            Department.name.asc(),
        )
        .all()
    )

    return {
        "success": True,
        "data": [
            serialize_department(
                db,
                row,
            )
            for row in rows
        ],
    }


# ============================================================
# GET ONE DEPARTMENT
# ============================================================

@router.get("/departments/{department_id}")
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    row = get_department_for_college(
        db,
        current_college.id,
        department_id,
    )

    return {
        "success": True,
        "data": serialize_department(
            db,
            row,
        ),
    }


# ============================================================
# UPDATE DEPARTMENT
# ============================================================

@router.patch("/departments/{department_id}")
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    row = get_department_for_college(
        db,
        current_college.id,
        department_id,
    )

    update_data = data.model_dump(
        exclude_unset=True
    )

    if not update_data:
        return {
            "success": True,
            "message": "No department changes supplied.",
            "data": serialize_department(
                db,
                row,
            ),
        }

    if "name" in update_data:
        if update_data["name"] is None:
            raise HTTPException(
                status_code=400,
                detail="Department name is required",
            )

        update_data["name"] = (
            update_data["name"].strip()
        )

    if "code" in update_data:
        update_data["code"] = (
            normalize_department_code(
                update_data["code"]
            )
        )

    final_name = update_data.get(
        "name",
        row.name,
    )

    final_code = update_data.get(
        "code",
        row.code,
    )

    ensure_unique_department(
        db,
        college_id=current_college.id,
        name=final_name,
        code=final_code,
        exclude_department_id=row.id,
    )

    for field, value in update_data.items():
        setattr(
            row,
            field,
            value,
        )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Department update conflicts with "
                "an existing department."
            ),
        )

    db.refresh(row)

    return {
        "success": True,
        "message": "Department updated successfully",
        "data": serialize_department(
            db,
            row,
        ),
    }


# ============================================================
# DELETE / DEACTIVATE DEPARTMENT
#
# No linked students  -> hard delete allowed.
# Linked students     -> deactivate to preserve history.
# ============================================================

@router.delete("/departments/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    row = get_department_for_college(
        db,
        current_college.id,
        department_id,
    )

    registry_link = (
        db.query(CollegeStudentRegistry.id)
        .filter(
            CollegeStudentRegistry.department_id
            == row.id
        )
        .first()
    )

    student_link = (
        db.query(Student.id)
        .filter(
            Student.department_id == row.id
        )
        .first()
    )

    # Existing student/history ko break nahi karna.
    if registry_link or student_link:
        row.is_active = False

        db.commit()
        db.refresh(row)

        return {
            "success": True,
            "action": "deactivated",
            "message": (
                "Department has linked students, so it was "
                "deactivated instead of permanently deleted."
            ),
            "data": serialize_department(
                db,
                row,
            ),
        }

    db.delete(row)
    db.commit()

    return {
        "success": True,
        "action": "deleted",
        "message": "Department deleted successfully",
    }


# ============================================================
# REACTIVATE DEPARTMENT
# ============================================================

@router.patch("/departments/{department_id}/activate")
def activate_department(
    department_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.college)
    ),
):
    current_college = get_college(
        db,
        user.id
    )

    row = get_department_for_college(
        db,
        current_college.id,
        department_id,
    )

    row.is_active = True

    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": "Department activated successfully",
        "data": serialize_department(
            db,
            row,
        ),
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

    if not department.is_active:
        raise HTTPException(
            status_code=400,
            detail=(
                "This department is inactive. "
                "Activate it before assigning students."
            ),
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

    require_verified_college_profile(current_college)

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

    normalized_batch = (
        data.batch.strip()
        if data.batch
        else None
    )

    normalized_section = (
        data.section.strip().upper()
        if data.section
        else None
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
        batch=normalized_batch,
        section=normalized_section,
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
            "batch": row.batch,
            "section": row.section,
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
                "program_type": department.program_type,
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
                "program_type": (
                    department_map.get(
                        row.department_id,
                        {}
                    ).get("program_type")
                ),
                "student_id_number":
                    row.student_id_number,
                "student_name":
                    row.student_name,
                "year":
                    row.year,
                "batch":
                    row.batch,
                "section":
                    row.section,
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

    require_verified_college_profile(current_college)

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

    if "batch" in update_data:
        update_data["batch"] = (
            update_data["batch"].strip()
            if update_data["batch"]
            else None
        )

    if "section" in update_data:
        update_data["section"] = (
            update_data["section"].strip().upper()
            if update_data["section"]
            else None
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
            "batch": row.batch,
            "section": row.section,
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

    require_verified_college_profile(current_college)

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

    require_verified_college_profile(current_college)

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
#
# Students should only select a verified institution.
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
        .filter(
            or_(
                College.verification_status == "verified",
                College.is_verified.is_(True),
            )
        )
        .order_by(College.name.asc())
        .all()
    )

    return {
        "success": True,
        "data": [
            {
                "id": row.id,
                "name": row.name,
                "college_public_id": row.college_public_id,
                "college_logo_url": getattr(row, "college_logo_url", None),
                "affiliation_status": row.affiliation_status,
                "university": row.university,
                "college_code": row.college_code,
                "aishe_code": row.aishe_code,
                "city": row.city,
                "state": row.state,
                "verification_status": "verified",
                "is_verified": True,
            }
            for row in rows
        ],
    }


# ============================================================
# STUDENT LOOKUP - VERIFIED COLLEGE BY PUBLIC ID
#
# Useful for student college selection / verification flow.
# Only verified institutions can be resolved here.
# ============================================================

@router.get("/student-directory/by-public-id/{college_public_id}")
def student_college_by_public_id(
    college_public_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.student)
    ),
):
    normalized_public_id = normalize_code(
        college_public_id
    )

    row = (
        db.query(College)
        .filter(
            College.college_public_id
            == normalized_public_id,
            or_(
                College.verification_status == "verified",
                College.is_verified.is_(True),
            ),
        )
        .first()
    )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Verified college not found",
        )

    return {
        "success": True,
        "data": {
            "id": row.id,
            "college_public_id": row.college_public_id,
            "college_logo_url": getattr(row, "college_logo_url", None),
            "name": row.name,
            "college_code": row.college_code,
            "aishe_code": row.aishe_code,
            "university": row.university,
            "city": row.city,
            "state": row.state,
            "verification_status": "verified",
            "is_verified": True,
        },
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

    if not is_college_verified(college_row):
        raise HTTPException(
            status_code=403,
            detail="This college is not verified yet"
        )

    rows = (
        db.query(Department)
        .filter(
            Department.college_id == college_id,
            Department.is_active.is_(True),
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
                "program_type": row.program_type,
                "college_id": row.college_id,
            }
            for row in rows
        ],
    }