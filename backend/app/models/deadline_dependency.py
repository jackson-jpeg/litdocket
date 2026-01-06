"""
Deadline Dependency Model - Tracks parent-child relationships between deadlines
Enables automatic recalculation when parent deadlines change
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class DeadlineDependency(Base):
    """
    Defines dependency between two deadlines
    Example: "Pretrial Stipulation" depends on "Trial Date" (15 days before)
    """
    __tablename__ = "deadline_dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chain_id = Column(String(36), ForeignKey("deadline_chains.id", ondelete="CASCADE"), nullable=True, index=True)

    # The dependent (child) deadline
    deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"), nullable=False, index=True)

    # What it depends on (parent)
    depends_on_deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"), nullable=False, index=True)

    # Offset calculation
    offset_days = Column(Integer, nullable=False)  # Number of days
    offset_direction = Column(String(10), nullable=False)  # 'before' or 'after'

    # Whether to apply service method days
    add_service_days = Column(Boolean, default=False)

    # Auto-recalculation settings
    auto_recalculate = Column(Boolean, default=True)  # Recalc when parent changes
    last_recalculated = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chain = relationship("DeadlineChain", back_populates="dependencies")
    deadline = relationship("Deadline", foreign_keys=[deadline_id], back_populates="dependencies_as_child")
    depends_on_deadline = relationship("Deadline", foreign_keys=[depends_on_deadline_id], back_populates="dependencies_as_parent")
