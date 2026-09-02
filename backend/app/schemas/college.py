from pydantic import BaseModel

class CollegeProfileCreate(BaseModel):
    name: str
    university: str | None = None
    city: str | None = None
    state: str | None = None
    website: str | None = None

class DepartmentCreate(BaseModel):
    name: str
    code: str | None = None
