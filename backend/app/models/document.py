from sqlalchemy import Column, String, BigInteger, Date, DateTime, ForeignKey, Text, func, JSON, Boolean, Integer, Numeric
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(50))  # pdf, jpg, png
    file_size_bytes = Column(BigInteger)
    storage_path = Column(String(1000), nullable=False)  # S3 path
    storage_url = Column(String(1000))  # Presigned URL
    document_type = Column(String(100))  # motion, order, notice, etc.
    filing_date = Column(Date)
    received_date = Column(Date)
    analysis_status = Column(String(50), default="pending")  # pending, processing, completed, failed, needs_ocr
    needs_ocr = Column(Boolean, default=False)  # True if PDF appears to be scanned/unreadable
    extracted_text = Column(Text)
    ai_summary = Column(Text)
    extracted_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # =========================================================================
    # Phase 1: Document Classification Fields
    # These fields support "soft ingestion" - rich classification for all
    # documents, including those that don't match known trigger patterns.
    # =========================================================================

    # Classification pipeline status: pending, matched, unrecognized, needs_research, researched, manual
    classification_status = Column(String(50), default="pending", index=True)

    # If matched, what trigger type was matched (TriggerType enum value)
    matched_trigger_type = Column(String(100))

    # What pattern matched (for debugging/transparency)
    matched_pattern = Column(String(255))

    # Classification confidence score (0.0 - 1.0)
    classification_confidence = Column(Numeric(3, 2))

    # For unrecognized documents: AI's best guess at the trigger event
    # e.g., "Receipt of Rule 11 Motion", "Service of Subpoena"
    potential_trigger_event = Column(String(255))

    # Whether this document requires a response from another party
    response_required = Column(Boolean, default=False)

    # Who must respond: plaintiff, defendant, both, third_party, null
    response_party = Column(String(50))

    # Estimated response deadline in days (from AI analysis)
    response_deadline_days = Column(Integer)

    # What stage the case is in: Pre-Answer, Discovery Phase, Post-Discovery/Pre-Trial, etc.
    procedural_posture = Column(String(100))

    # What the filing party is asking for
    relief_sought = Column(Text)

    # Urgency indicators found in the document (JSON array of strings)
    # e.g., ["emergency", "expedited", "ex parte"]
    urgency_indicators = Column(JSON, default=list)

    # Rule citations found in the document (JSON array of strings)
    # e.g., ["Fla. R. Civ. P. 1.380", "FRCP 37"]
    rule_references = Column(JSON, default=list)

    # Suggested next action: apply_rules, research_deadlines, manual_review, none
    suggested_action = Column(String(50))

    # Document category: motion, order, notice, pleading, discovery, subpoena, correspondence, other
    document_category = Column(String(50))

    # Relationships
    case = relationship("Case", back_populates="documents")
    user = relationship("User", back_populates="documents")
    deadlines = relationship("Deadline", back_populates="document")

    # V3.0 Enhancements - RAG
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")

    # Document tagging
    tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")
