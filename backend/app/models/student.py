from sqlalchemy import Boolean, ForeignKey, String, Text
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
        unique=True
    )

    # =====================================================
    # COLLEGE LINK
    # =====================================================

    college_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "colleges.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    department_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "departments.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    # Student/Enrollment/Roll number given by college
    student_id_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True
    )

    # True only after matching college registry
    college_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    # =====================================================
    # ACADEMIC PROFILE
    # =====================================================

    college_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True
    )

    branch: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    year: Mapped[int | None] = mapped_column(
        nullable=True
    )

    semester: Mapped[int | None] = mapped_column(
        nullable=True
    )

    # =====================================================
    # CAREER PROFILE
    # =====================================================

    career_goal: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    github_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    linkedin_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    portfolio_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )