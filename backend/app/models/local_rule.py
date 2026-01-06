"""
Local Rules Model - Florida jurisdiction-specific rules database
Stores all 20 Florida judicial circuits' local rules
"""
from sqlalchemy import Column, String, Text, Boolean, JSON, Index
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class LocalRule(Base):
    """
    Florida local court rules database
    Covers all 20 judicial circuits + 3 federal districts
    """
    __tablename__ = "local_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Jurisdiction identification
    jurisdiction_type = Column(String(20), nullable=False, index=True)  # 'circuit', 'district', 'county'
    jurisdiction_id = Column(String(50), nullable=False, index=True)  # '11th Circuit', 'S.D. Fla', 'Miami-Dade', etc.

    # Rule details
    rule_number = Column(String(50), nullable=False, index=True)  # '1.200', '3.1(a)', etc.
    rule_title = Column(String(200))
    rule_text = Column(Text, nullable=False)

    # Classification
    category = Column(String(100))  # 'pretrial', 'discovery', 'trial', 'motion_practice', etc.
    affects_deadlines = Column(Boolean, default=False)  # Does this rule affect deadline calculations?
    deadline_days = Column(String(50))  # e.g., "30 days", "15 business days"

    # Metadata
    rule_metadata = Column(JSON)  # {effective_date, supersedes, related_rules, notes}

    # Search and indexing
    __table_args__ = (
        Index('idx_jurisdiction', 'jurisdiction_type', 'jurisdiction_id'),
        Index('idx_rule_lookup', 'jurisdiction_id', 'rule_number'),
    )
