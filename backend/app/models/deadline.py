from sqlalchemy import Column, String, Date, Time, DateTime, ForeignKey, Text, Boolean, Integer, JSON, func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Core deadline information
    title = Column(String(500), nullable=False)
    description = Column(Text)
    deadline_date = Column(Date, index=True)  # Made nullable for TBD deadlines
    deadline_time = Column(Time)
    deadline_type = Column(String(100))  # response, hearing, filing, etc.

    # Jackson's methodology fields
    party_role = Column(String(255))  # Who must take action (Plaintiff, Defendant, etc.)
    action_required = Column(Text)  # What action is required
    trigger_event = Column(String(500))  # What triggered this deadline
    trigger_date = Column(Date)  # Date of triggering event
    is_estimated = Column(Boolean, default=False)  # Is this deadline estimated/TBD?
    source_document = Column(String(500))  # Source document reference
    service_method = Column(String(100))  # electronic, mail, hand_delivery (affects +3 day rule)

    # Phase 3: Advanced deadline calculation
    calculation_type = Column(String(50), default="calendar_days")  # "court_days" or "calendar_days"
    days_count = Column(Integer)  # Original number of days in calculation (e.g., 30)

    # Case OS: Confidence Scoring & Source Attribution
    source_page = Column(Integer)  # PDF page number where deadline was found
    source_text = Column(Text)  # Exact text snippet from PDF
    source_coordinates = Column(JSON)  # PDF coordinates for text highlighting
    confidence_score = Column(Integer)  # 0-100 confidence score
    confidence_level = Column(String(20))  # high, medium, low
    confidence_factors = Column(JSON)  # Detailed breakdown of confidence calculation

    # Case OS: Verification Gate
    verification_status = Column(String(20), default="pending")  # pending, approved, rejected, modified
    verified_by = Column(String(36), ForeignKey("users.id"))  # User who verified
    verified_at = Column(DateTime(timezone=True))  # When was it verified
    verification_notes = Column(Text)  # User notes during verification

    # Case OS: AI Extraction Quality
    extraction_method = Column(String(50))  # ai, manual, rule-based, hybrid
    extraction_quality_score = Column(Integer)  # How well did AI extract this (1-10)

    # Rule citations
    applicable_rule = Column(String(255))  # e.g., "FRCP 12(a)(1)(A)(i)"
    rule_citation = Column(Text)  # Full rule text
    calculation_basis = Column(Text)  # How deadline was calculated

    # Authority Core integration - links to the authoritative rule that generated this deadline
    source_rule_id = Column(String(36), ForeignKey("authority_rules.id", ondelete="SET NULL"), index=True)

    # Status and priority
    priority = Column(String(20), default="standard")  # informational, standard, important, critical, fatal
    status = Column(String(50), default="pending")  # pending, completed, cancelled
    reminder_sent = Column(Boolean, default=False)
    created_via_chat = Column(Boolean, default=False)  # Was this created via chatbot?

    # Trigger-based architecture
    is_calculated = Column(Boolean, default=False)  # Auto-calculated from rules engine
    is_dependent = Column(Boolean, default=False)  # Depends on another deadline (trigger)
    parent_deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"))  # Trigger deadline
    auto_recalculate = Column(Boolean, default=True)  # Recalculate if trigger changes

    # Audit trail
    modified_by = Column(String(255))  # User who last modified
    modification_reason = Column(Text)  # Why was this changed?
    original_deadline_date = Column(Date)  # Original calculated date (for audit)

    # Manual override tracking
    is_manually_overridden = Column(Boolean, default=False)  # User manually changed a calculated deadline
    override_timestamp = Column(DateTime(timezone=True))  # When was it overridden?
    override_user_id = Column(String(36), ForeignKey("users.id"))  # Who overrode it?
    override_reason = Column(Text)  # Why was it manually changed?

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case", back_populates="deadlines")
    document = relationship("Document", back_populates="deadlines")
    # Specify foreign_keys to resolve ambiguity (user_id vs override_user_id vs verified_by)
    user = relationship("User", foreign_keys=[user_id], back_populates="deadlines")
    override_user = relationship("User", foreign_keys=[override_user_id])  # Who manually overrode this deadline
    verified_by_user = relationship("User", foreign_keys=[verified_by])  # Who verified this deadline (Case OS)
    calendar_events = relationship("CalendarEvent", back_populates="deadline")

    # Authority Core - link to the authoritative rule that generated this deadline
    authority_rule = relationship("AuthorityRule", foreign_keys=[source_rule_id])

    # V3.0 Enhancements - Dependency tracking and audit trail
    chains_as_parent = relationship("DeadlineChain", foreign_keys="DeadlineChain.parent_deadline_id", back_populates="parent_deadline", cascade="all, delete-orphan")
    dependencies_as_child = relationship("DeadlineDependency", foreign_keys="DeadlineDependency.deadline_id", back_populates="deadline", cascade="all, delete-orphan")
    dependencies_as_parent = relationship("DeadlineDependency", foreign_keys="DeadlineDependency.depends_on_deadline_id", back_populates="depends_on_deadline", cascade="all, delete-orphan")
    history = relationship("DeadlineHistory", back_populates="deadline", cascade="all, delete-orphan")
    ai_feedback = relationship("AIExtractionFeedback", back_populates="deadline", cascade="all, delete-orphan")
