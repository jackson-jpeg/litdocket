"""
Case Intelligence Models

AI-powered case analysis, predictions, and strategic recommendations.
"""

from sqlalchemy import (
    Column, String, Date, DateTime, ForeignKey, Text, Boolean, Integer,
    Numeric, func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class CaseHealthScore(Base):
    """
    AI-generated health scores and risk assessments for cases.

    Updated periodically based on:
    - Deadline compliance
    - Document completeness
    - Case stage vs timeline
    - Similar case outcomes
    - Discovery progress
    """
    __tablename__ = "case_health_scores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Overall health score (0-100)
    overall_score = Column(Integer, nullable=False)

    # Component scores (0-100)
    deadline_compliance_score = Column(Integer)  # Are deadlines being met?
    document_completeness_score = Column(Integer)  # Required docs present?
    discovery_progress_score = Column(Integer)  # Discovery on track?
    timeline_health_score = Column(Integer)  # Case progressing normally?
    risk_score = Column(Integer)  # Overall risk level (inverted)

    # Risk factors identified
    risk_factors = Column(JSONB, default=[])
    # Structure: [{ "type": "missed_deadline", "severity": "high", "description": "..." }]

    # Recommendations
    recommendations = Column(JSONB, default=[])
    # Structure: [{ "priority": 1, "action": "...", "reasoning": "...", "deadline": "..." }]

    # AI analysis metadata
    analysis_model = Column(String(100))
    analysis_confidence = Column(Numeric(3, 2))

    # Timestamps
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case")
    user = relationship("User")


class CasePrediction(Base):
    """
    AI predictions for case outcomes and milestones.
    """
    __tablename__ = "case_predictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Prediction type
    prediction_type = Column(String(50), nullable=False)
    # outcome, settlement_value, trial_date, disposition_type, duration

    # Prediction value
    predicted_value = Column(Text)  # JSON or string depending on type
    confidence = Column(Numeric(3, 2))

    # Prediction range (for numeric predictions)
    lower_bound = Column(Text)
    upper_bound = Column(Text)

    # Factors influencing prediction
    influencing_factors = Column(JSONB, default=[])
    # Structure: [{ "factor": "judge_history", "impact": "positive", "weight": 0.3 }]

    # Similar cases used for prediction
    similar_cases = Column(JSONB, default=[])
    # Structure: [{ "case_type": "...", "outcome": "...", "similarity": 0.85 }]

    # Model metadata
    model_version = Column(String(50))

    # Timestamps
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case")
    user = relationship("User")


class JudgeProfile(Base):
    """
    Judge analytics and ruling patterns.
    """
    __tablename__ = "judge_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Judge identification
    name = Column(String(255), nullable=False, index=True)
    court = Column(String(255))
    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="SET NULL"))

    # Contact/assignment info
    chambers_info = Column(JSONB, default={})
    # Structure: { "phone": "...", "clerk": "...", "courtroom": "..." }

    # Ruling statistics
    motion_stats = Column(JSONB, default={})
    # Structure: { "motion_to_dismiss": { "granted": 45, "denied": 55, "partial": 10 }, ... }

    # Timeline tendencies
    avg_ruling_time_days = Column(Integer)  # Average days to rule on motions
    avg_case_duration_months = Column(Integer)  # Average case duration

    # Procedural preferences
    preferences = Column(JSONB, default={})
    # Structure: { "prefers_oral_argument": true, "strict_on_deadlines": true, ... }

    # Notable rulings/tendencies
    notable_rulings = Column(JSONB, default=[])

    # Case type experience
    case_type_experience = Column(JSONB, default={})
    # Structure: { "contract": 150, "tort": 89, "employment": 45, ... }

    # Last updated
    data_sources = Column(ARRAY(Text), default=[])
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    jurisdiction = relationship("Jurisdiction")


class CaseEvent(Base):
    """
    Unified case events for timeline visualization.

    Consolidates all case activities: filings, deadlines, hearings,
    discovery, communications, etc.
    """
    __tablename__ = "case_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event classification
    event_type = Column(String(50), nullable=False, index=True)
    # filing, deadline, hearing, discovery, deposition, mediation,
    # trial, ruling, communication, milestone, custom

    event_subtype = Column(String(50))
    # For filing: complaint, answer, motion, brief, etc.
    # For discovery: interrogatory, document_request, deposition_notice, etc.

    # Event details
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Timing
    event_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True))  # For multi-day events
    is_all_day = Column(Boolean, default=True)

    # Status
    status = Column(String(50), default="scheduled")
    # scheduled, completed, cancelled, pending, overdue

    # Priority/importance
    priority = Column(String(20), default="standard")
    # critical, high, standard, low

    # Related entities
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))
    deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="SET NULL"))

    # Participants
    participants = Column(JSONB, default=[])
    # Structure: [{ "name": "...", "role": "attorney|witness|expert|judge" }]

    # Location (for hearings, depositions)
    location = Column(Text)
    virtual_link = Column(Text)

    # Additional metadata
    metadata = Column(JSONB, default={})

    # AI-generated flag
    is_ai_generated = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case")
    user = relationship("User")
    document = relationship("Document")
    deadline = relationship("Deadline")


class DiscoveryRequest(Base):
    """
    Discovery request tracking.
    """
    __tablename__ = "discovery_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Request identification
    request_type = Column(String(50), nullable=False)
    # interrogatory, document_request, admission_request, deposition_notice

    request_number = Column(Integer)  # Set number (e.g., First Set, Second Set)

    # Direction
    direction = Column(String(20), nullable=False)  # outgoing, incoming

    # Parties
    from_party = Column(String(255))
    to_party = Column(String(255))

    # Content
    title = Column(String(500))
    description = Column(Text)
    items = Column(JSONB, default=[])
    # Structure: [{ "number": 1, "text": "...", "response": "...", "objections": [...] }]

    # Dates
    served_date = Column(Date)
    response_due_date = Column(Date, index=True)
    response_received_date = Column(Date)

    # Status
    status = Column(String(50), default="pending")
    # pending, responded, objected, motion_to_compel, resolved

    # Related deadline
    deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="SET NULL"))

    # Document references
    request_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))
    response_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case")
    user = relationship("User")
    deadline = relationship("Deadline")


class CaseFact(Base):
    """
    Extracted facts from case documents.

    AI-extracted key facts that form the knowledge graph of the case.
    """
    __tablename__ = "case_facts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Fact classification
    fact_type = Column(String(50), nullable=False, index=True)
    # party, date, amount, claim, defense, evidence, witness, location, contract_term

    # Fact content
    fact_text = Column(Text, nullable=False)
    normalized_value = Column(Text)  # Standardized value (e.g., date in ISO format)

    # Importance
    importance = Column(String(20), default="standard")
    # critical, high, standard, low

    # Disputed status
    is_disputed = Column(Boolean, default=False)
    dispute_details = Column(Text)

    # Source
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))
    source_page = Column(Integer)
    source_excerpt = Column(Text)

    # AI extraction metadata
    extraction_confidence = Column(Numeric(3, 2))
    verified = Column(Boolean, default=False)
    verified_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))

    # Related facts (for building knowledge graph)
    related_fact_ids = Column(ARRAY(String(36)), default=[])

    # Timestamps
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", foreign_keys=[case_id])
    user = relationship("User", foreign_keys=[user_id])
    source_document = relationship("Document")


class BriefDraft(Base):
    """
    AI-assisted brief and motion drafts.
    """
    __tablename__ = "brief_drafts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Document type
    document_type = Column(String(100), nullable=False)
    # motion_to_dismiss, motion_for_summary_judgment, response_brief,
    # reply_brief, trial_brief, discovery_motion, etc.

    title = Column(String(500), nullable=False)

    # Content sections
    sections = Column(JSONB, default=[])
    # Structure: [{ "heading": "INTRODUCTION", "content": "...", "citations": [...] }]

    # Full draft content
    content = Column(Text)

    # AI generation metadata
    generation_prompt = Column(Text)
    generation_context = Column(JSONB, default={})
    # What case facts, documents, rules were used

    # Citations used
    citations = Column(JSONB, default=[])
    # Structure: [{ "citation": "...", "quote": "...", "page": "..." }]

    # Similar successful filings referenced
    similar_filings = Column(JSONB, default=[])

    # Status
    status = Column(String(50), default="draft")
    # draft, review, approved, filed

    # Version tracking
    version = Column(Integer, default=1)
    parent_draft_id = Column(String(36), ForeignKey("brief_drafts.id", ondelete="SET NULL"))

    # Final document (if filed)
    final_document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case")
    user = relationship("User")
    parent_draft = relationship("BriefDraft", remote_side=[id])
    final_document = relationship("Document")
