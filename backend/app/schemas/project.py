from datetime import date
from pydantic import BaseModel, ConfigDict

class ProjectCreate(BaseModel):
    title: str
    description: str | None = None
    technologies: str | None = None
    github_url: str | None = None
    live_url: str | None = None
    start_date: date | None = None
    end_date: date | None = None

class ProjectResponse(ProjectCreate):
    id: int
    student_id: int
    model_config = ConfigDict(from_attributes=True)
