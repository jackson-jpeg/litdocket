"""
Case Template Model - Save and reuse case structures
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, func, Text
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class CaseTemplate(Base):
    """User-defined case templates for quick case creation"""
    __tablename__ = "case_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Template metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Case structure template
    case_type = Column(String(100))  # civil, criminal, appellate
    jurisdiction = Column(String(100))  # state, federal
    court = Column(String(255))  # Default court
    district = Column(String(100))  # Northern, Middle, Southern
    circuit = Column(String(50))  # 1st-20th for circuit courts

    # Party structure template (roles to fill in)
    party_roles = Column(JSON)  # e.g., [{"role": "Plaintiff", "name_placeholder": true}, {"role": "Defendant", "name_placeholder": true}]

    # Default deadlines to create
    default_deadlines = Column(JSON)  # e.g., [{"title": "File Answer", "days_from_filing": 20, "rule": "Fla. R. Civ. P. 1.140"}]

    # Default tags to apply to new cases
    default_tags = Column(JSON)

    # Usage stats
    times_used = Column(String(10), default="0")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="case_templates")
