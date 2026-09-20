"""sync current database schema safely

Revision ID: 960446968520
Revises:
Create Date: 2026-09-20 12:51:22.188047

This first Alembic migration is intended for the CURRENT EXISTING database.
It avoids unnecessary destructive changes detected by autogenerate.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "960446968520"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # College student registry
    # ---------------------------------------------------------
    op.create_index(
        "ix_college_student_registry_is_active",
        "college_student_registry",
        ["is_active"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Colleges
    #
    # Keep existing UNIQUE constraints on user_id.
    # Keep existing DB server defaults.
    # Only add missing indexes / FK that match current models.
    # ---------------------------------------------------------
    op.create_index(
        "ix_colleges_aishe_code",
        "colleges",
        ["aishe_code"],
        unique=True,
    )

    op.create_index(
        "ix_colleges_college_code",
        "colleges",
        ["college_code"],
        unique=True,
    )

    op.create_index(
        "ix_colleges_official_email",
        "colleges",
        ["official_email"],
        unique=True,
    )

    op.create_index(
        "ix_colleges_verification_status",
        "colleges",
        ["verification_status"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_colleges_verified_by_users",
        "colleges",
        "users",
        ["verified_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # ---------------------------------------------------------
    # Departments
    #
    # is_active is added with a temporary server default so
    # existing rows receive TRUE and the NOT NULL addition is safe.
    # The server default is then removed to match the SQLAlchemy model.
    # ---------------------------------------------------------
    op.add_column(
        "departments",
        sa.Column(
            "program_type",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.add_column(
        "departments",
        sa.Column(
            "established_year",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "departments",
        sa.Column(
            "intake_capacity",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "departments",
        sa.Column(
            "hod_name",
            sa.String(length=150),
            nullable=True,
        ),
    )

    op.add_column(
        "departments",
        sa.Column(
            "coordinator_name",
            sa.String(length=150),
            nullable=True,
        ),
    )

    op.add_column(
        "departments",
        sa.Column(
            "official_email",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "departments",
        sa.Column(
            "contact_number",
            sa.String(length=30),
            nullable=True,
        ),
    )

    op.add_column(
        "departments",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.alter_column(
        "departments",
        "is_active",
        server_default=None,
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )

    op.create_unique_constraint(
        "uq_college_department_code",
        "departments",
        ["college_id", "code"],
    )

    # ---------------------------------------------------------
    # Students
    #
    # Existing UNIQUE constraint on user_id is preserved.
    # Existing DB default on college_verified is preserved.
    # ---------------------------------------------------------
    op.create_index(
        "ix_students_college_verified",
        "students",
        ["college_verified"],
        unique=False,
    )

    op.create_index(
        "ix_students_student_id_number",
        "students",
        ["student_id_number"],
        unique=False,
    )


def downgrade() -> None:
    # NOTE:
    # Downgrading removes fields added by this migration and can
    # destroy department metadata. Do not run this on production
    # unless you intentionally want to roll back these changes.

    op.drop_index(
        "ix_students_student_id_number",
        table_name="students",
    )

    op.drop_index(
        "ix_students_college_verified",
        table_name="students",
    )

    op.drop_constraint(
        "uq_college_department_code",
        "departments",
        type_="unique",
    )

    op.drop_column("departments", "is_active")
    op.drop_column("departments", "contact_number")
    op.drop_column("departments", "official_email")
    op.drop_column("departments", "coordinator_name")
    op.drop_column("departments", "hod_name")
    op.drop_column("departments", "intake_capacity")
    op.drop_column("departments", "established_year")
    op.drop_column("departments", "program_type")

    op.drop_constraint(
        "fk_colleges_verified_by_users",
        "colleges",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_colleges_verification_status",
        table_name="colleges",
    )

    op.drop_index(
        "ix_colleges_official_email",
        table_name="colleges",
    )

    op.drop_index(
        "ix_colleges_college_code",
        table_name="colleges",
    )

    op.drop_index(
        "ix_colleges_aishe_code",
        table_name="colleges",
    )

    op.drop_index(
        "ix_college_student_registry_is_active",
        table_name="college_student_registry",
    )
