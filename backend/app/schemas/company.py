from pydantic import BaseModel, ConfigDict

class CompanyCreate(BaseModel):
    name: str
    industry: str | None = None
    website: str | None = None
    description: str | None = None
    location: str | None = None

class CompanyResponse(CompanyCreate):
    id: int
    user_id: int
    is_verified: bool
    model_config = ConfigDict(from_attributes=True)
