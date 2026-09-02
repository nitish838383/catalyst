from datetime import datetime
from pydantic import BaseModel
from app.models.application import ApplicationStatus

class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    recruiter_note: str | None = None

class InterviewScheduleRequest(BaseModel):
    scheduled_at: datetime
    mode: str = "online"
    meeting_link: str | None = None
    location: str | None = None
    instructions: str | None = None
