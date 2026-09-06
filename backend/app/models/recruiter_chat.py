from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.session import Base


# =========================================================
# RECRUITER CHAT SESSION
# =========================================================

class RecruiterChatSession(Base):

    __tablename__ = "recruiter_chat_sessions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="Hiring Conversation"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# =========================================================
# RECRUITER CHAT MESSAGE
# =========================================================

class RecruiterChatMessage(Base):

    __tablename__ = "recruiter_chat_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey(
            "recruiter_chat_sessions.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )