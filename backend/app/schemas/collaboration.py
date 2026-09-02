from datetime import datetime
from pydantic import BaseModel, Field
from app.models.collaboration import CollaborationType, CollaborationStatus

class CollaborationCreate(BaseModel):
    college_id: int
    collaboration_type: CollaborationType
    title: str
    description: str | None = None
    proposed_date: datetime | None = None
    location: str | None = None
    mode: str | None = None
    skills: list[str] = Field(default_factory=list)

class CollaborationStatusUpdate(BaseModel):
    status: CollaborationStatus
    college_note: str | None = None
