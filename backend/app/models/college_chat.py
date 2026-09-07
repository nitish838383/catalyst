from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base


class CollegeChatSession(Base):
    __tablename__ = "college_chat_sessions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    college_id: Mapped[int] = mapped_column(
        ForeignKey(
            "colleges.id",
            ondelete="CASCADE"
        ),
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(200),
        default="College AI Assistant"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    messages = relationship(
        "CollegeChatMessage",
        back_populates="session",
        cascade="all, delete-orphan"
    )


class CollegeChatMessage(Base):
    __tablename__ = "college_chat_messages"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey(
            "college_chat_sessions.id",
            ondelete="CASCADE"
        ),
        index=True
    )

    role: Mapped[str] = mapped_column(
        String(20)
    )

    content: Mapped[str] = mapped_column(
        Text
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    session = relationship(
        "CollegeChatSession",
        back_populates="messages"
    )