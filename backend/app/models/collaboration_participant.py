from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class CollaborationParticipant(Base):
    __tablename__ = "collaboration_participants"
    id: Mapped[int] = mapped_column(primary_key=True)
    collaboration_id: Mapped[int] = mapped_column(ForeignKey("collaborations.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("collaboration_id", "student_id", name="uq_collaboration_student"),)
