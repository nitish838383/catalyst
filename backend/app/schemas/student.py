from pydantic import BaseModel, ConfigDict


# ============================================================
# Student Profile Create
# ============================================================

class StudentProfileCreate(BaseModel):

    college_id: int | None = None
    department_id: int | None = None

    # College-issued Student ID / Enrollment No.
    student_id_number: str | None = None

    college_name: str | None = None
    branch: str | None = None

    year: int | None = None
    semester: int | None = None

    career_goal: str | None = None
    bio: str | None = None

    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None


# ============================================================
# Student Profile Update
# ============================================================

class StudentProfileUpdate(StudentProfileCreate):
    pass


# ============================================================
# Student Profile Response
# ============================================================

class StudentProfileResponse(StudentProfileCreate):

    id: int
    user_id: int

    # Backend-controlled verification status
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
# Student College Verification Response
# ============================================================

class StudentCollegeVerifyResponse(BaseModel):

    success: bool

    verified: bool

    message: str

    college_id: int | None = None
    department_id: int | None = None

    student_id_number: str | None = None