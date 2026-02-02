"""
Document Deadline Suggestion Model

Stores AI-extracted deadline suggestions from documents for user review.
Part of the Document → Deadline Auto-Generation Pipeline.
"""

from sqlalchemy import (
    Column, String, Text, Date, DateTime, Integer, ForeignKey,
    func, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class DocumentDeadlineSuggestion(Base):
    """
    Model for storing AI-extracted deadline suggestions.

    These are created when documents are uploaded and analyzed.
    Users can approve/reject suggestions, and approved suggestions
    are converted to actual Deadline records.
    """
    __tablename__ = "document_deadline_suggestions"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign keys with ownership
    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
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

    # Suggestion content
    title = Column(String(500), nullable=False)
    description = Column(Text)
    suggested_date = Column(Date)
    deadline_type = Column(String(100))

    # Extraction metadata
    extraction_method = Column(String(50), nullable=False)  # ai_key_dates, ai_deadlines_mentioned, trigger_detected
    source_text = Column(Text)  # Original text that led to this suggestion

    # Rule matching
    matched_trigger_type = Column(String(100))  # Maps to TriggerType if detected
    rule_citation = Column(String(255))

    # Confidence scoring
    confidence_score = Column(Integer, default=50)
    confidence_factors = Column(JSONB, default=dict)

    # Status tracking
    status = Column(String(20), default='pending')  # pending, approved, rejected, expired
    reviewed_at = Column(DateTime(timezone=True))
    created_deadline_id = Column(
        String(36),
        ForeignKey("deadlines.id", ondelete="SET NULL")
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 100",
            name="check_confidence_score_range"
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired')",
            name="check_suggestion_status"
        ),
    )

    # Relationships
    document = relationship("Document", backref="deadline_suggestions")
    case = relationship("Case", backref="deadline_suggestions")
    user = relationship("User", backref="deadline_suggestions")
    created_deadline = relationship("Deadline", foreign_keys=[created_deadline_id])

    def __repr__(self) -> str:
        return f"<DocumentDeadlineSuggestion(id={self.id}, title='{self.title[:30]}...', status={self.status})>"

    def to_dict(self) -> dict:
        """Convert suggestion to dictionary for API responses."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "case_id": self.case_id,
            "title": self.title,
            "description": self.description,
            "suggested_date": self.suggested_date.isoformat() if self.suggested_date else None,
            "deadline_type": self.deadline_type,
            "extraction_method": self.extraction_method,
            "source_text": self.source_text,
            "matched_trigger_type": self.matched_trigger_type,
            "rule_citation": self.rule_citation,
            "confidence_score": self.confidence_score,
            "confidence_factors": self.confidence_factors,
            "status": self.status,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_deadline_id": self.created_deadline_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
