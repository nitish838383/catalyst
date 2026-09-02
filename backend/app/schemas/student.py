from pydantic import BaseModel, ConfigDict

class StudentProfileCreate(BaseModel):
    college_id: int | None = None
    department_id: int | None = None
    college_name: str | None = None
    branch: str | None = None
    year: int | None = None
    semester: int | None = None
    career_goal: str | None = None
    bio: str | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

class StudentProfileUpdate(StudentProfileCreate):
    pass

class StudentProfileResponse(StudentProfileCreate):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)
