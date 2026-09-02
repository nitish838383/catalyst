from datetime import date
from pydantic import BaseModel, ConfigDict

class CertificationCreate(BaseModel):
    name: str
    organization: str | None = None
    issue_date: date | None = None
    credential_url: str | None = None
    credential_id: str | None = None

class CertificationResponse(CertificationCreate):
    id: int
    student_id: int
    model_config = ConfigDict(from_attributes=True)
