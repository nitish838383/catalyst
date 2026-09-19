from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Department(Base):
    __tablename__ = "departments"

    # Same college ke andar duplicate department name/code nahi hona chahiye
    __table_args__ = (
        UniqueConstraint(
            "college_id",
            "name",
            name="uq_college_department",
        ),
        UniqueConstraint(
            "college_id",
            "code",
            name="uq_college_department_code",
        ),
    )

    # =========================================================
    # Basic Identity
    # =========================================================

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    college_id: Mapped[int] = mapped_column(
        ForeignKey(
            "colleges.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # =========================================================
    # Academic Information
    # =========================================================

    program_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Examples:
    # B.Tech
    # M.Tech
    # BCA
    # MCA
    # MBA

    established_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    intake_capacity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # =========================================================
    # Department Administration
    # =========================================================

    hod_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    coordinator_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    official_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    contact_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # =========================================================
    # Status
    # =========================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )