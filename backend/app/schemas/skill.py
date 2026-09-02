from typing import Literal
from pydantic import BaseModel

class AddSkillRequest(BaseModel):
    name: str
    category: str | None = None
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"

class AssessmentSubmit(BaseModel):
    skill_id: int
    total_questions: int
    correct_answers: int
