from pydantic import BaseModel


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
# All fields optional because PATCH supports partial updates
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