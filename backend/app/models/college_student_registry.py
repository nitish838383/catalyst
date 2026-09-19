from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.db.session import Base


class CollegeStudentRegistry(Base):

    __tablename__ = "college_student_registry"

    __table_args__ = (
        UniqueConstraint(
            "college_id",
            "student_id_number",
            name="uq_college_student_registry_student",
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
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =====================================================
    # DEPARTMENT
    # =====================================================

    # Official department selected by College / TPO.
    # Program/Course should be derived from Department.program_type
    # instead of duplicating it in this registry table.
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "departments.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # =====================================================
    # STUDENT DETAILS ADDED BY COLLEGE
    # =====================================================

    # Official Enrollment / Student / Roll number.
    student_id_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Official student name maintained by College / TPO.
    student_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Current academic year, e.g. 1, 2, 3, 4.
    year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Admission / graduating batch.
    # Example: 2026-2030
    batch: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # College section / class group.
    # Example: F2, A, CSE-A
    section: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Active registry records can be claimed by students.
    # Deactivating a claimed record revokes college verification.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # =====================================================
    # CLAIMED BY SKILLBRIDGE STUDENT
    # =====================================================

    # unique=True guarantees one SkillBridge student account
    # cannot claim multiple official registry identities.
    claimed_student_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "students.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        unique=True,
        index=True,
    )
