from pydantic import BaseModel, Field


class CollegeChatSessionCreate(BaseModel):
    title: str | None = Field(
        default="College AI Assistant",
        max_length=200
    )


class CollegeChatMessageCreate(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000
    )