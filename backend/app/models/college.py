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


class College(Base):
    __tablename__ = "colleges"

    # =========================================================
    # Basic Identity
    # =========================================================

    # Internal database ID.
    # PostgreSQL / SQLAlchemy automatically generates this.
    # College user cannot choose or edit this value.
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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Public / official SkillBridge College ID.
    #
    # Example:
    # MGM095
    #
    # This is entered by the college during profile registration.
    # It is different from the internal database primary key `id`.
    #
    # nullable=True is intentionally kept during migration so that
    # existing college rows do not break. The create schema/API can
    # make this field mandatory for all new college profiles.
    college_public_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )

    # Official college logo / profile image.
    #
    # Store only the persistent public/object-storage URL here.
    # Do NOT store image binary/base64 in this column.
    #
    # Student dashboard should read this through student.college_id
    # -> College.college_logo_url instead of duplicating the image
    # URL into every Student row.
    college_logo_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # =========================================================
    # Affiliation / Institution Identity
    # =========================================================

    # affiliated / self_university
    affiliation_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    university: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    college_code: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )

    aishe_code: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )

    institution_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    established_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # =========================================================
    # Official Contact Details
    # =========================================================

    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    official_email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    official_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    pincode: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # =========================================================
    # College Authority
    # =========================================================

    principal_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    authorized_person_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    authorized_designation: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    authorized_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    authorized_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # =========================================================
    # Verification Documents
    # =========================================================

    affiliation_certificate_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    authorization_letter_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # =========================================================
    # Verification
    # =========================================================

    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    phone_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    website_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    documents_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # pending / verified / rejected
    verification_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )

    verification_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    verified_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL"
        ),
        nullable=True,
    )

    # =========================================================
    # Legacy field
    # =========================================================

    # Abhi remove mat karna.
    # Existing frontend/backend routes me use ho sakta hai.
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
