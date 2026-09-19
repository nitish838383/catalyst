from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# ============================================================
# Student-editable profile fields
# ============================================================

class StudentEditableFields(BaseModel):
    """
    Fields the student is allowed to create/update manually.

    Official college identity fields are intentionally NOT included here.
    They are written only by the college verification flow after a
    successful match against CollegeStudentRegistry.
    """

    semester: int | None = Field(
        default=None,
        ge=1,
        le=12,
    )

    career_goal: str | None = None
    bio: str | None = None

    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    model_config = ConfigDict(
        extra="forbid"
    )


# ============================================================
# Student Profile Create
# ============================================================

class StudentProfileCreate(StudentEditableFields):
    pass


# ============================================================
# Student Profile Update
# ============================================================

class StudentProfileUpdate(StudentEditableFields):
    pass


# ============================================================
# Student Profile Response
# ============================================================

class StudentProfileResponse(StudentEditableFields):
    id: int
    user_id: int

    # --------------------------------------------------------
    # Official college identity
    # --------------------------------------------------------

    college_id: int | None = None
    department_id: int | None = None

    student_id_number: str | None = None

    college_name: str | None = None
    branch: str | None = None

    year: int | None = None

    # --------------------------------------------------------
    # Verification state
    # --------------------------------------------------------

    college_verified: bool = False

    college_verified_at: datetime | None = None

    college_verification_source: str | None = None

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# Student College Verification Request
#
# Student chooses a verified college and enters the official
# Enrollment / Student ID.
#
# Department is intentionally NOT trusted from the student.
# Backend derives the official department from the matching
# CollegeStudentRegistry record.
# ============================================================

class StudentCollegeVerifyRequest(BaseModel):
    college_id: int = Field(
        gt=0
    )

    student_id_number: str

    model_config = ConfigDict(
        extra="forbid"
    )

    @field_validator("student_id_number")
    @classmethod
    def normalize_student_id(
        cls,
        value: str,
    ) -> str:

        value = value.strip().upper()

        if not value:
            raise ValueError(
                "Student ID / Enrollment Number is required"
            )

        return value


# ============================================================
# Student College Verification Response Models
# ============================================================

class VerifiedCollegeInfo(BaseModel):
    # Internal database relation ID
    id: int

    # College-entered public ID, e.g. MGM095
    college_public_id: str | None = None

    # Official logo/profile image owned by the college.
    # Student never uploads or edits this value.
    college_logo_url: str | None = None

    name: str

    college_code: str | None = None
    aishe_code: str | None = None

    university: str | None = None

    city: str | None = None
    state: str | None = None

    verification_status: str = "verified"


class VerifiedStudentInfo(BaseModel):
    student_id_number: str

    official_name: str | None = None

    year: int | None = None

    # Link status is useful for UI / college registry.
    claimed: bool = False


class VerifiedDepartmentInfo(BaseModel):
    id: int | None = None

    name: str | None = None
    code: str | None = None
    program_type: str | None = None


class StudentCollegeVerificationData(BaseModel):
    college: VerifiedCollegeInfo
    student: VerifiedStudentInfo
    department: VerifiedDepartmentInfo

    verified_at: datetime | None = None
    verification_source: str | None = None


class StudentCollegeVerifyResponse(BaseModel):
    success: bool
    verified: bool
    message: str

    data: StudentCollegeVerificationData | None = None


# ============================================================
# Student College Verification Status Response
# ============================================================

class StudentCollegeVerificationStatusCollege(BaseModel):
    id: int | None = None

    college_public_id: str | None = None

    # Official college logo returned with verification status so
    # student dashboard does not need a second directory request.
    college_logo_url: str | None = None

    name: str | None = None

    college_code: str | None = None
    aishe_code: str | None = None

    city: str | None = None
    state: str | None = None


class StudentCollegeVerificationStatusDepartment(BaseModel):
    id: int | None = None

    name: str | None = None
    code: str | None = None

    program_type: str | None = None


class StudentCollegeVerificationStatusData(BaseModel):
    verified: bool

    student_id_number: str | None = None
    student_name: str | None = None

    year: int | None = None

    verified_at: datetime | None = None
    verification_source: str | None = None

    college: StudentCollegeVerificationStatusCollege | None = None

    department: StudentCollegeVerificationStatusDepartment | None = None


class StudentCollegeVerificationStatusResponse(BaseModel):
    success: bool
    data: StudentCollegeVerificationStatusData
