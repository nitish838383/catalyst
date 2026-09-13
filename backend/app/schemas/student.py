from pydantic import BaseModel, ConfigDict


# ============================================================
# Student-editable profile fields
# ============================================================

class StudentEditableFields(BaseModel):
    """
    Fields the student is allowed to create/update manually.

    Official college identity fields are intentionally NOT included here.
    They are written only by /students/verify-college after a successful
    match against the college/TPO registry.
    """

    semester: int | None = None

    career_goal: str | None = None
    bio: str | None = None

    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None


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
    # Official college fields.
    # These are backend-controlled and are populated only after
    # successful verification against CollegeStudentRegistry.
    # --------------------------------------------------------
    college_id: int | None = None
    department_id: int | None = None
    student_id_number: str | None = None

    college_name: str | None = None
    branch: str | None = None

    year: int | None = None

    college_verified: bool = False

    model_config = ConfigDict(
        from_attributes=True
    )


# ============================================================
# Student College Verification Request
# ============================================================

class StudentCollegeVerifyRequest(BaseModel):
    college_id: int
    student_id_number: str


# ============================================================
# Student College Verification Response Models
# ============================================================

class VerifiedCollegeInfo(BaseModel):
    id: int
    name: str
    university: str | None = None


class VerifiedStudentInfo(BaseModel):
    student_id_number: str
    official_name: str | None = None
    year: int | None = None


class VerifiedDepartmentInfo(BaseModel):
    id: int | None = None
    name: str | None = None
    code: str | None = None


class StudentCollegeVerificationData(BaseModel):
    college: VerifiedCollegeInfo
    student: VerifiedStudentInfo
    department: VerifiedDepartmentInfo


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
    name: str | None = None


class StudentCollegeVerificationStatusDepartment(BaseModel):
    id: int | None = None
    name: str | None = None
    code: str | None = None


class StudentCollegeVerificationStatusData(BaseModel):
    verified: bool
    student_id_number: str | None = None
    student_name: str | None = None
    year: int | None = None
    college: StudentCollegeVerificationStatusCollege | None = None
    department: StudentCollegeVerificationStatusDepartment | None = None


class StudentCollegeVerificationStatusResponse(BaseModel):
    success: bool
    data: StudentCollegeVerificationStatusData
