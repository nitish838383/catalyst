from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "students.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    stored_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Extracted PDF text
    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Resume processing status
    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # -----------------------------------------
    # Deterministic Resume Analysis
    # -----------------------------------------

    ats_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    section_analysis: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    ats_analysis: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # -----------------------------------------
    # LLM Resume Guidance
    # -----------------------------------------

    ai_guidance: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    resume_id: Mapped[int] = mapped_column(
        ForeignKey(
            "resumes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    skill_id: Mapped[int] = mapped_column(
        ForeignKey(
            "skills.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )

    is_accepted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "resume_id",
            "skill_id",
            name="uq_resume_skill",
        ),
    )