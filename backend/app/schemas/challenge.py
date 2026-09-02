from datetime import datetime
from pydantic import BaseModel, Field
from app.models.challenge import ChallengeStatus, SubmissionStatus

class ChallengeCreate(BaseModel):
    title: str
    problem_statement: str
    expected_solution: str | None = None
    eligibility: str | None = None
    deadline: datetime | None = None
    status: ChallengeStatus = ChallengeStatus.draft

class ChallengeSubmissionCreate(BaseModel):
    title: str
    description: str
    github_url: str | None = None
    demo_url: str | None = None

class SubmissionEvaluation(BaseModel):
    status: SubmissionStatus
    score: int | None = Field(default=None, ge=0, le=100)
    feedback: str | None = None
