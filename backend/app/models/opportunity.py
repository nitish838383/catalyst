import enum
from sqlalchemy import Boolean, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class OpportunityType(str, enum.Enum):
    internship = "internship"
    job = "job"

class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    opportunity_type: Mapped[OpportunityType] = mapped_column(Enum(OpportunityType), default=OpportunityType.internship)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stipend: Mapped[float | None] = mapped_column(Float, nullable=True)
    experience_required: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class OpportunitySkill(Base):
    __tablename__ = "opportunity_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    __table_args__ = (UniqueConstraint("opportunity_id", "skill_id", name="uq_opportunity_skill"),)
