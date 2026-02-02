"""
Case Recommendation Model

Stores AI-generated actionable recommendations with full context
including rule citations, consequences, and suggested tools.
Part of the Enhanced Case Intelligence feature.
"""

from sqlalchemy import (
    Column, String, Text, Integer, DateTime, ForeignKey,
    func, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class CaseRecommendation(Base):
    """
    Model for storing enhanced case recommendations.

    Recommendations link to specific deadlines/documents that triggered them
    and include full legal context like rule citations and consequences.
    """
    __tablename__ = "case_recommendations"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign keys with ownership
    case_id = Column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Core recommendation fields
    priority = Column(Integer, nullable=False, default=10)  # Lower = more important
    action = Column(Text, nullable=False)
    reasoning = Column(Text)
    category = Column(String(50), nullable=False)  # deadlines, documents, discovery, risk, compliance

    # Context linking
    triggered_by_deadline_id = Column(
        String(36),
        ForeignKey("deadlines.id", ondelete="SET NULL"),
        index=True
    )
    triggered_by_document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="SET NULL")
    )

    # Legal context
    rule_citations = Column(JSONB, default=list)  # e.g., ["Fla. R. Civ. P. 1.140(a)(1)"]
    consequence_if_ignored = Column(Text)
    urgency_level = Column(String(20), default='medium')  # critical, high, medium, low
    days_until_consequence = Column(Integer)

    # Actionable tools
    suggested_tools = Column(JSONB, default=list)
    # e.g., [{"tool": "deadline-calculator", "action": "Verify calculation"}]
    suggested_document_types = Column(JSONB, default=list)
    # e.g., ["Answer", "Motion to Dismiss"]

    # Status tracking
    status = Column(String(20), default='pending')  # pending, in_progress, completed, dismissed, expired
    completed_at = Column(DateTime(timezone=True))
    dismissed_at = Column(DateTime(timezone=True))
    dismissed_reason = Column(Text)

    # Auto-expiration
    expires_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "urgency_level IN ('critical', 'high', 'medium', 'low')",
            name="check_urgency_level"
        ),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'dismissed', 'expired')",
            name="check_recommendation_status"
        ),
    )

    # Relationships
    case = relationship("Case", backref="recommendations")
    user = relationship("User", backref="case_recommendations")
    triggered_by_deadline = relationship("Deadline", foreign_keys=[triggered_by_deadline_id])
    triggered_by_document = relationship("Document", foreign_keys=[triggered_by_document_id])

    def __repr__(self) -> str:
        return f"<CaseRecommendation(id={self.id}, priority={self.priority}, urgency={self.urgency_level})>"

    def to_dict(self) -> dict:
        """Convert recommendation to dictionary for API responses."""
        result = {
            "id": self.id,
            "case_id": self.case_id,
            "priority": self.priority,
            "action": self.action,
            "reasoning": self.reasoning,
            "category": self.category,
            "triggered_by_deadline_id": self.triggered_by_deadline_id,
            "triggered_by_document_id": self.triggered_by_document_id,
            "rule_citations": self.rule_citations or [],
            "consequence_if_ignored": self.consequence_if_ignored,
            "urgency_level": self.urgency_level,
            "days_until_consequence": self.days_until_consequence,
            "suggested_tools": self.suggested_tools or [],
            "suggested_document_types": self.suggested_document_types or [],
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
            "dismissed_reason": self.dismissed_reason,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include deadline details if linked
        if self.triggered_by_deadline:
            result["triggered_by_deadline"] = {
                "id": self.triggered_by_deadline.id,
                "title": self.triggered_by_deadline.title,
                "deadline_date": self.triggered_by_deadline.deadline_date.isoformat() if self.triggered_by_deadline.deadline_date else None,
                "priority": self.triggered_by_deadline.priority,
            }

        return result
