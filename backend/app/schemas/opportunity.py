from pydantic import BaseModel
from app.models.opportunity import OpportunityType

class OpportunityCreate(BaseModel):
    title: str
    description: str
    opportunity_type: OpportunityType = OpportunityType.internship
    location: str | None = None
    stipend: float | None = None
    experience_required: str | None = None

class OpportunitySkillCreate(BaseModel):
    skill_name: str
    category: str | None = None
    is_required: bool = True
    weight: float = 1.0
