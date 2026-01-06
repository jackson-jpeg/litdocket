"""
Deadline History Model - Version control for deadline changes
Tracks all modifications to deadlines for audit trail
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class DeadlineHistory(Base):
    """
    Audit trail for deadline modifications
    Tracks who changed what and when
    """
    __tablename__ = "deadline_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"), nullable=False, index=True)
    changed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # What changed
    field_changed = Column(String(50), nullable=False)  # 'deadline_date', 'status', 'priority', etc.
    old_value = Column(Text)
    new_value = Column(Text)

    # Why it changed
    change_reason = Column(Text)  # "User manually updated" or "Auto-recalculated due to parent change"
    change_type = Column(String(20))  # 'manual', 'auto_recalc', 'ai_correction', 'system'

    # When it changed
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    deadline = relationship("Deadline", back_populates="history")
    user = relationship("User", back_populates="deadline_history_entries")
