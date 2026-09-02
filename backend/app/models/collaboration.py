import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class CollaborationType(str, enum.Enum):
    workshop = "workshop"
    guest_lecture = "guest_lecture"
    hackathon = "hackathon"
    mentorship = "mentorship"
    industry_project = "industry_project"
    internship_drive = "internship_drive"
    placement_drive = "placement_drive"

class CollaborationStatus(str, enum.Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"

class Collaboration(Base):
    __tablename__ = "collaborations"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    collaboration_type: Mapped[CollaborationType] = mapped_column(Enum(CollaborationType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[CollaborationStatus] = mapped_column(Enum(CollaborationStatus), default=CollaborationStatus.proposed)
    college_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CollaborationSkill(Base):
    __tablename__ = "collaboration_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    collaboration_id: Mapped[int] = mapped_column(ForeignKey("collaborations.id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint("collaboration_id", "skill_id", name="uq_collaboration_skill"),)
