from pydantic import BaseModel, Field

class CreateChatRequest(BaseModel):
    title: str | None = None

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
    opportunity_id: int | None = None
