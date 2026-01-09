"""
Deadline Chain Model - Tracks trigger-based deadline chains
Architecture for auto-generated deadline dependencies
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class DeadlineChain(Base):
    """
    Represents a chain of deadlines triggered by a parent event
    Example: Trial date set → generates 15+ dependent deadlines
    """
    __tablename__ = "deadline_chains"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)

    # Parent deadline that triggered this chain
    parent_deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"), nullable=False, index=True)

    # Trigger information
    trigger_code = Column(String(10))  # $TR (trial), $MC (mediation), $PC (pretrial conf), etc.
    trigger_type = Column(String(50))  # trial_date, service_completed, etc.

    # Template used to generate this chain
    template_id = Column(String(36), ForeignKey("deadline_templates.id", ondelete="SET NULL"), nullable=True)

    # Chain metadata
    children_count = Column(Integer, default=0)  # Number of dependent deadlines
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="deadline_chains")
    parent_deadline = relationship("Deadline", foreign_keys=[parent_deadline_id], back_populates="chains_as_parent")
    template = relationship("DeadlineTemplate", back_populates="chains")
    dependencies = relationship("DeadlineDependency", back_populates="chain", cascade="all, delete-orphan")
