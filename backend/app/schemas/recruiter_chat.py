from pydantic import (
    BaseModel,
    Field,
)


# =========================================================
# CREATE CHAT SESSION
# =========================================================

class CreateRecruiterChatRequest(BaseModel):

    title: str | None = Field(
        default=None,
        max_length=200
    )


# =========================================================
# SEND MESSAGE
# =========================================================

class RecruiterChatRequest(BaseModel):

    message: str = Field(
        min_length=1,
        max_length=4000
    )

    opportunity_id: int | None = None