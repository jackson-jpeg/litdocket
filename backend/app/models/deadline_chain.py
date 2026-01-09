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

    # Minimal schema - only columns that exist in actual DB
    # Removed: trigger_code, trigger_type, template_id, children_count
    # All other metadata should be retrieved through relationships

    # Relationships
    case = relationship("Case", back_populates="deadline_chains")
    parent_deadline = relationship("Deadline", foreign_keys=[parent_deadline_id], back_populates="chains_as_parent")
    # template relationship removed - template_id column doesn't exist in DB
    dependencies = relationship("DeadlineDependency", back_populates="chain", cascade="all, delete-orphan")
