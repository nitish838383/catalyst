from pydantic import BaseModel, ConfigDict


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
# College admin will add these students.
# ============================================================

class CollegeStudentRegistryCreate(BaseModel):

    student_id_number: str

    student_name: str | None = None

    department_id: int | None = None

    year: int | None = None


# ============================================================
# College Student Registry Update
# ============================================================

class CollegeStudentRegistryUpdate(BaseModel):

    student_name: str | None = None

    department_id: int | None = None

    year: int | None = None

    is_active: bool | None = None


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