"""
AI Extraction Feedback Model - Learning system for AI improvements
Tracks user corrections to AI extractions to improve future accuracy
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class AIExtractionFeedback(Base):
    """
    User feedback on AI deadline extractions
    Used to improve AI prompts and accuracy over time
    """
    __tablename__ = "ai_extraction_feedback"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"), nullable=True, index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # What AI suggested vs what user corrected to
    ai_suggestion = Column(Text, nullable=False)  # Original AI extraction (JSON)
    user_correction = Column(Text, nullable=False)  # What user changed it to (JSON)

    # Feedback classification
    feedback_type = Column(String(50), nullable=False)  # 'date_wrong', 'party_wrong', 'rule_wrong', 'missing', 'extra', etc.
    severity = Column(String(20))  # 'minor', 'major', 'critical'

    # AI confidence at time of extraction
    original_confidence = Column(Float)  # 0.0-1.0

    # Context
    document_type = Column(String(100))
    jurisdiction = Column(String(50))
    court_type = Column(String(50))

    # Learning metadata
    pattern_identified = Column(Text)  # Pattern that caused the error (for future improvements)
    correction_applied = Column(Text)  # How the prompt was adjusted

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    deadline = relationship("Deadline", back_populates="ai_feedback")
    case = relationship("Case", back_populates="ai_feedback")
    user = relationship("User", back_populates="ai_feedback")
