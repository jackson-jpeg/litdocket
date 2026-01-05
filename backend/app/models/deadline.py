from sqlalchemy import Column, String, Date, Time, DateTime, ForeignKey, Text, Boolean, func
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
    service_method = Column(String(100))  # email, mail, personal

    # Rule citations
    applicable_rule = Column(String(255))  # e.g., "FRCP 12(a)(1)(A)(i)"
    rule_citation = Column(Text)  # Full rule text
    calculation_basis = Column(Text)  # How deadline was calculated

    # Status and priority (CompuLaw-inspired)
    priority = Column(String(20), default="standard")  # informational, standard, important, critical, fatal
    status = Column(String(50), default="pending")  # pending, completed, cancelled
    reminder_sent = Column(Boolean, default=False)
    created_via_chat = Column(Boolean, default=False)  # Was this created via chatbot?

    # Trigger-based architecture (CompuLaw-inspired)
    is_calculated = Column(Boolean, default=False)  # Auto-calculated from rules engine
    is_dependent = Column(Boolean, default=False)  # Depends on another deadline (trigger)
    parent_deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"))  # Trigger deadline
    auto_recalculate = Column(Boolean, default=True)  # Recalculate if trigger changes

    # Audit trail
    modified_by = Column(String(255))  # User who last modified
    modification_reason = Column(Text)  # Why was this changed?
    original_deadline_date = Column(Date)  # Original calculated date (for audit)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case", back_populates="deadlines")
    document = relationship("Document", back_populates="deadlines")
    user = relationship("User", back_populates="deadlines")
    calendar_events = relationship("CalendarEvent", back_populates="deadline")
