



from sqlalchemy import (
    Boolean,
    ForeignKey,
    String,
    UniqueConstraint
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from app.db.session import Base


class CollegeStudentRegistry(Base):

    __tablename__ = "college_student_registry"

    __table_args__ = (
        UniqueConstraint(
            "college_id",
            "student_id_number",
            name="uq_college_student_registry_student"
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # =====================================================
    # COLLEGE
    # =====================================================

    college_id: Mapped[int] = mapped_column(
        ForeignKey(
            "colleges.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    # =====================================================
    # DEPARTMENT
    # =====================================================

    department_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "departments.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    # =====================================================
    # STUDENT DETAILS ADDED BY COLLEGE
    # =====================================================

    student_id_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    student_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    year: Mapped[int | None] = mapped_column(
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    # =====================================================
    # CLAIMED BY SKILLBRIDGE STUDENT
    # =====================================================

    claimed_student_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "students.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        unique=True,
        index=True
    )