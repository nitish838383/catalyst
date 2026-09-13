from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================
# College Profile Create
# ============================================================

class CollegeProfileCreate(BaseModel):
    name: str

    university: str | None = None
    city: str | None = None
    state: str | None = None
    website: str | None = None


# ============================================================
# College Profile Update
# ============================================================

class CollegeProfileUpdate(BaseModel):
    name: str | None = None

    university: str | None = None
    city: str | None = None
    state: str | None = None
    website: str | None = None


# ============================================================
# Department Create
# ============================================================

class DepartmentCreate(BaseModel):
    name: str
    code: str | None = None


# ============================================================
# College Student Registry Create
# College/TPO must add complete official student information.
# ============================================================

class CollegeStudentRegistryCreate(BaseModel):
    student_id_number: str
    student_name: str
    department_id: int
    year: int = Field(ge=1, le=10)

    @field_validator("student_id_number")
    @classmethod
    def normalize_student_id(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError(
                "Student ID / Enrollment Number is required"
            )

        return value

    @field_validator("student_name")
    @classmethod
    def validate_student_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Student name is required")

        return value


# ============================================================
# College Student Registry Update
# ============================================================

class CollegeStudentRegistryUpdate(BaseModel):
    student_name: str | None = None
    department_id: int | None = None
    year: int | None = Field(default=None, ge=1, le=10)
    is_active: bool | None = None

    @field_validator("student_name")
    @classmethod
    def validate_optional_student_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Student name cannot be empty")

        return value


# ============================================================
# College Student Registry Response
# ============================================================

class CollegeStudentRegistryResponse(BaseModel):
    id: int
    college_id: int
    department_id: int | None = None

    student_id_number: str
    student_name: str | None = None
    year: int | None = None

    is_active: bool
    claimed_student_id: int | None = None

    model_config = ConfigDict(
        from_attributes=True
    )
