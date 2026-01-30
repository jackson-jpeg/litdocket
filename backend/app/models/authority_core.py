"""
Authority Core Models

Primary rules database that replaces hardcoded templates.
Supports AI-powered web scraping, attorney approval workflow, and conflict detection.
"""

from sqlalchemy import (
    Column, String, Date, DateTime, ForeignKey, Text, Boolean, Integer,
    Numeric, ARRAY, func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.enums import AuthorityTier, ProposalStatus, ScrapeStatus, ConflictResolution


class AuthorityRule(Base):
    """
    Primary rules database - single source of truth for deadline calculations.

    This table replaces hardcoded rule templates and becomes the definitive
    source for all deadline calculation rules across jurisdictions.
    """
    __tablename__ = "authority_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Ownership (NULL for system-generated rules)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Jurisdiction reference
    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="CASCADE"), index=True)

    # Authority level for precedence (federal > state > local > standing_order > firm)
    authority_tier = Column(
        SQLEnum(
            AuthorityTier,
            name='authority_tier',
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        default=AuthorityTier.STATE,
        index=True
    )

    # Rule identification
    rule_code = Column(String(100), nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)

    # What triggers this rule
    trigger_type = Column(String(100), nullable=False, index=True)

    # Source information
    citation = Column(Text)
    source_url = Column(Text)
    source_text = Column(Text)

    # Deadline specifications (JSONB array)
    # Structure: [{ title, days_from_trigger, calculation_method, priority, party_responsible, conditions }]
    deadlines = Column(JSONB, nullable=False, default=[])

    # Conditions when rule applies
    # Structure: { case_types: [], motion_types: [], service_methods: [], exclusions: {} }
    conditions = Column(JSONB, default={})

    # Service method extensions
    # Structure: { mail: 3, electronic: 0, personal: 0 }
    service_extensions = Column(JSONB, default={"mail": 3, "electronic": 0, "personal": 0})

    # AI extraction confidence (0.00 - 1.00)
    confidence_score = Column(Numeric(3, 2), default=0.00)

    # Verification status
    is_verified = Column(Boolean, default=False, index=True)
    verified_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    verified_at = Column(DateTime(timezone=True))

    # Active status
    is_active = Column(Boolean, default=True, index=True)

    # Effective dates
    effective_date = Column(Date)
    superseded_date = Column(Date)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    verified_by_user = relationship("User", foreign_keys=[verified_by])
    jurisdiction = relationship("Jurisdiction")
    proposals = relationship("RuleProposal", back_populates="approved_rule")
    usage_records = relationship("AuthorityRuleUsage", back_populates="rule", cascade="all, delete-orphan")
    conflicts_as_a = relationship("RuleConflict", foreign_keys="RuleConflict.rule_a_id", back_populates="rule_a", cascade="all, delete-orphan")
    conflicts_as_b = relationship("RuleConflict", foreign_keys="RuleConflict.rule_b_id", back_populates="rule_b", cascade="all, delete-orphan")


class ScrapeJob(Base):
    """
    Tracks AI-powered web scraping operations for rule extraction.

    Each job represents a search query against a jurisdiction's court rules,
    using Claude's web search capabilities to find and extract rules.
    """
    __tablename__ = "scrape_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Who initiated
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Target jurisdiction
    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="SET NULL"), index=True)

    # Search parameters
    search_query = Column(Text, nullable=False)

    # Status tracking
    status = Column(
        SQLEnum(
            ScrapeStatus,
            name='scrape_status',
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        default=ScrapeStatus.QUEUED,
        index=True
    )
    progress_pct = Column(Integer, default=0)

    # Results
    rules_found = Column(Integer, default=0)
    proposals_created = Column(Integer, default=0)
    urls_processed = Column(ARRAY(Text), default=[])

    # Error handling
    error_message = Column(Text)
    error_details = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User")
    jurisdiction = relationship("Jurisdiction")
    proposals = relationship("RuleProposal", back_populates="scrape_job", cascade="all, delete-orphan")


class RuleProposal(Base):
    """
    AI-extracted rules awaiting attorney review and approval.

    When the scraping pipeline extracts a rule, it creates a proposal
    that must be reviewed and approved before becoming an active rule.
    """
    __tablename__ = "rule_proposals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Who created (usually system via scrape)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Parent scrape job (NULL if manually created)
    scrape_job_id = Column(String(36), ForeignKey("scrape_jobs.id", ondelete="SET NULL"), index=True)

    # Target jurisdiction
    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="SET NULL"), index=True)

    # Proposed rule data (full structure matching AuthorityRule)
    proposed_rule_data = Column(JSONB, nullable=False)

    # Source information
    source_url = Column(Text)
    source_text = Column(Text)

    # AI extraction metadata
    confidence_score = Column(Numeric(3, 2), default=0.00)
    extraction_notes = Column(Text)

    # Review status
    status = Column(
        SQLEnum(
            ProposalStatus,
            name='proposal_status',
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        default=ProposalStatus.PENDING,
        index=True
    )

    # Review tracking
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    reviewer_notes = Column(Text)

    # If approved, link to created rule
    approved_rule_id = Column(String(36), ForeignKey("authority_rules.id", ondelete="SET NULL"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by])
    scrape_job = relationship("ScrapeJob", back_populates="proposals")
    jurisdiction = relationship("Jurisdiction")
    approved_rule = relationship("AuthorityRule", back_populates="proposals")


class RuleConflict(Base):
    """
    Detected conflicts between rules in the same jurisdiction.

    When rules have overlapping triggers or conflicting deadlines,
    the system creates a conflict record for attorney resolution.
    """
    __tablename__ = "rule_conflicts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # The two conflicting rules
    rule_a_id = Column(String(36), ForeignKey("authority_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_b_id = Column(String(36), ForeignKey("authority_rules.id", ondelete="CASCADE"), nullable=False, index=True)

    # Conflict details
    conflict_type = Column(String(50), nullable=False)  # days_mismatch, method_mismatch, priority_mismatch, condition_overlap
    severity = Column(String(20), nullable=False, default="warning")  # info, warning, error
    description = Column(Text, nullable=False)

    # Resolution
    resolution = Column(
        SQLEnum(
            ConflictResolution,
            name='conflict_resolution',
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        default=ConflictResolution.PENDING
    )
    resolution_notes = Column(Text)

    resolved_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    rule_a = relationship("AuthorityRule", foreign_keys=[rule_a_id], back_populates="conflicts_as_a")
    rule_b = relationship("AuthorityRule", foreign_keys=[rule_b_id], back_populates="conflicts_as_b")
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])


class AuthorityRuleUsage(Base):
    """
    Audit trail of when rules were applied to generate deadlines.

    Tracks every instance of a rule being used to calculate deadlines,
    supporting analytics and legal defensibility.
    """
    __tablename__ = "authority_rule_usage"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Which rule was used
    rule_id = Column(String(36), ForeignKey("authority_rules.id", ondelete="CASCADE"), nullable=False, index=True)

    # Where it was used
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="SET NULL"))

    # Who used it
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Context
    trigger_type = Column(String(100))
    trigger_date = Column(Date)

    # Result
    deadlines_generated = Column(Integer, default=0)

    # Timestamp
    used_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    rule = relationship("AuthorityRule", back_populates="usage_records")
    case = relationship("Case")
    deadline = relationship("Deadline")
    user = relationship("User")
