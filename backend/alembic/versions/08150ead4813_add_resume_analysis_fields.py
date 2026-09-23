"""add resume analysis fields

Revision ID: 08150ead4813
Revises: 960446968520
Create Date: 2026-09-23 20:36:45.125816
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "08150ead4813"
down_revision: Union[str, None] = "960446968520"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ResumeSkill lookup indexes
    op.create_index(
        op.f("ix_resume_skills_resume_id"),
        "resume_skills",
        ["resume_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_resume_skills_skill_id"),
        "resume_skills",
        ["skill_id"],
        unique=False,
    )

    # Advanced resume analysis fields
    op.add_column(
        "resumes",
        sa.Column(
            "analyzed_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    op.add_column(
        "resumes",
        sa.Column(
            "ats_score",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "resumes",
        sa.Column(
            "section_analysis",
            sa.JSON(),
            nullable=True,
        ),
    )

    op.add_column(
        "resumes",
        sa.Column(
            "ats_analysis",
            sa.JSON(),
            nullable=True,
        ),
    )

    op.add_column(
        "resumes",
        sa.Column(
            "ai_guidance",
            sa.JSON(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Remove resume analysis fields
    op.drop_column(
        "resumes",
        "ai_guidance",
    )

    op.drop_column(
        "resumes",
        "ats_analysis",
    )

    op.drop_column(
        "resumes",
        "section_analysis",
    )

    op.drop_column(
        "resumes",
        "ats_score",
    )

    op.drop_column(
        "resumes",
        "analyzed_at",
    )

    # Remove ResumeSkill indexes
    op.drop_index(
        op.f("ix_resume_skills_skill_id"),
        table_name="resume_skills",
    )

    op.drop_index(
        op.f("ix_resume_skills_resume_id"),
        table_name="resume_skills",
    )