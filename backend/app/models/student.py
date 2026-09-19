from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        unique=True,
        nullable=False,
        index=True,
    )

    # =====================================================
    # VERIFIED COLLEGE IDENTITY
    # =====================================================

    # Internal College primary key.
    # Student frontend me verified college select karega,
    # lekin successful registry verification ke baad hi
    # is field ko official college identity maana jayega.
    college_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "colleges.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True,
    )

    # Official department linked to the selected college.
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "departments.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True,
    )

    # Student / Enrollment / Roll number issued by college.
    # Normalized to uppercase in API layer.
    student_id_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # True only after matching an ACTIVE official
    # CollegeStudentRegistry record.
    college_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # When the student's college identity was last verified.
    college_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Source of verification.
    # Current supported value:
    # "college_registry"
    college_verification_source: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # =====================================================
    # ACADEMIC PROFILE
    # =====================================================

    # Kept for display / legacy compatibility.
    # After successful college verification this should be
    # synchronized from the verified College record.
    college_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    # Kept for display / legacy compatibility.
    # After verification this should be synchronized from
    # the official Department record.
    branch: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    # Official academic year can be synchronized from
    # CollegeStudentRegistry after successful verification.
    year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    semester: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # =====================================================
    # CAREER PROFILE
    # =====================================================

    career_goal: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    github_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    linkedin_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    portfolio_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
