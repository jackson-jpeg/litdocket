"""
Scraped Rule Models - Database persistence for rules scraping pipeline

These models track:
1. ScrapedRule: Individual rules extracted by Haiku, validated by Opus
2. JurisdictionCoverage: Progress tracking for 50 states + federal courts
3. ScrapingJob: Background job tracking for batch scraping

Architecture:
- Haiku extracts raw rules → ScrapedRule (status=SCRAPED)
- Opus validates rules → ScrapedRule (status=VALIDATED/REJECTED)
- Admin approves → ScrapedRule (status=APPROVED)
- Deploy to production → Creates RuleTemplate, ScrapedRule (status=DEPLOYED)
"""

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, Float,
    Enum as SQLEnum, JSON, ForeignKey, func
)
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.enums import ScrapedRuleStatus, ScraperCourtType


class ScrapedRule(Base):
    """
    A court rule extracted by the rules scraper.

    Lifecycle:
    1. SCRAPED: Haiku extracts from source
    2. QUEUED: Waiting for Opus validation
    3. VALIDATING: Opus is validating
    4. VALIDATED/REJECTED: Validation complete
    5. PENDING_APPROVAL: Awaiting admin review
    6. APPROVED: Ready for deployment
    7. DEPLOYED: Live in RuleTemplate
    """
    __tablename__ = "scraped_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Jurisdiction info
    jurisdiction_code = Column(String(50), nullable=False, index=True)  # "FL", "USDC-SDFL"
    jurisdiction_name = Column(String(255))  # "Florida State Courts"
    court_type = Column(SQLEnum(ScraperCourtType), nullable=False)

    # Rule identification
    rule_number = Column(String(100), nullable=False)  # "1.140", "12(b)(6)"
    rule_title = Column(String(500), nullable=False)
    rule_text = Column(Text, nullable=False)
    rule_citation = Column(String(255))  # "Fla. R. Civ. P. 1.140(a)"

    # Source tracking
    source_url = Column(String(1000))
    source_document = Column(Text)  # First 500 chars for reference
    effective_date = Column(DateTime(timezone=True))

    # Extracted trigger/deadline data (JSON)
    triggers = Column(JSON, default=list)  # Events that activate this rule
    deadlines = Column(JSON, default=list)  # Deadline templates

    # Pipeline status
    status = Column(SQLEnum(ScrapedRuleStatus), default=ScrapedRuleStatus.SCRAPED, index=True)
    confidence_score = Column(Float, default=0.0)  # 0.0 - 1.0

    # Validation tracking
    validation_notes = Column(Text)
    validation_issues = Column(JSON, default=list)  # Issues found during validation
    validated_at = Column(DateTime(timezone=True))
    validated_by_model = Column(String(100))  # "claude-opus-4-5-20251101"

    # Approval tracking
    approved_by = Column(String(36))  # User ID
    approved_at = Column(DateTime(timezone=True))
    approval_notes = Column(Text)

    # Deployment tracking
    deployed_rule_template_id = Column(String(36), ForeignKey("rule_templates.id", ondelete="SET NULL"))
    deployed_at = Column(DateTime(timezone=True))

    # Scraping job reference
    scraping_job_id = Column(String(36), ForeignKey("scraping_jobs.id", ondelete="SET NULL"), index=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    scraping_job = relationship("ScrapingJob", back_populates="scraped_rules")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "jurisdiction_code": self.jurisdiction_code,
            "jurisdiction_name": self.jurisdiction_name,
            "court_type": self.court_type.value if self.court_type else None,
            "rule_number": self.rule_number,
            "rule_title": self.rule_title,
            "rule_text": self.rule_text[:500] + "..." if len(self.rule_text or "") > 500 else self.rule_text,
            "rule_citation": self.rule_citation,
            "source_url": self.source_url,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "triggers": self.triggers or [],
            "deadlines": self.deadlines or [],
            "status": self.status.value if self.status else None,
            "confidence_score": self.confidence_score,
            "validation_notes": self.validation_notes,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JurisdictionCoverage(Base):
    """
    Tracks scraping coverage for each jurisdiction.

    Used to monitor progress toward "all courts captured" goal.
    """
    __tablename__ = "jurisdiction_coverage"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Jurisdiction identification
    jurisdiction_code = Column(String(50), unique=True, nullable=False, index=True)
    jurisdiction_name = Column(String(255), nullable=False)
    jurisdiction_type = Column(String(50))  # "state", "federal", "local"

    # Coverage statistics
    total_rules_expected = Column(Integer, default=0)  # Estimated total rules
    rules_scraped = Column(Integer, default=0)
    rules_validated = Column(Integer, default=0)
    rules_rejected = Column(Integer, default=0)
    rules_approved = Column(Integer, default=0)
    rules_deployed = Column(Integer, default=0)

    # Coverage percentage (computed)
    coverage_percentage = Column(Float, default=0.0)

    # Last activity
    last_scrape_at = Column(DateTime(timezone=True))
    last_validation_at = Column(DateTime(timezone=True))
    last_deployment_at = Column(DateTime(timezone=True))

    # Sources tracked
    sources_discovered = Column(JSON, default=list)  # URLs/documents found
    sources_processed = Column(JSON, default=list)   # URLs/documents scraped

    # Status flags
    is_priority = Column(Boolean, default=False)  # High-priority jurisdiction
    is_complete = Column(Boolean, default=False)  # All rules captured
    needs_review = Column(Boolean, default=False)  # Has pending approvals

    # Notes
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def update_coverage(self):
        """Recalculate coverage percentage."""
        if self.total_rules_expected > 0:
            self.coverage_percentage = (self.rules_deployed / self.total_rules_expected) * 100
        else:
            self.coverage_percentage = 0.0

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "jurisdiction_code": self.jurisdiction_code,
            "jurisdiction_name": self.jurisdiction_name,
            "jurisdiction_type": self.jurisdiction_type,
            "total_rules_expected": self.total_rules_expected,
            "rules_scraped": self.rules_scraped,
            "rules_validated": self.rules_validated,
            "rules_rejected": self.rules_rejected,
            "rules_approved": self.rules_approved,
            "rules_deployed": self.rules_deployed,
            "coverage_percentage": round(self.coverage_percentage, 2),
            "last_scrape_at": self.last_scrape_at.isoformat() if self.last_scrape_at else None,
            "is_priority": self.is_priority,
            "is_complete": self.is_complete,
            "needs_review": self.needs_review,
        }


class ScrapingJob(Base):
    """
    Tracks background scraping jobs for batch processing.
    """
    __tablename__ = "scraping_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Job identification
    job_type = Column(String(50), nullable=False)  # "jurisdiction_scrape", "url_scrape", "batch_validate"
    jurisdiction_code = Column(String(50), index=True)

    # Status
    status = Column(String(20), default="pending", index=True)  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 0.0 - 100.0

    # Statistics
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    successful_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Configuration
    config = Column(JSON, default=dict)  # Job-specific configuration

    # Error tracking
    errors = Column(JSON, default=list)  # List of errors encountered
    last_error = Column(Text)

    # Who initiated
    initiated_by = Column(String(36))  # User ID or "SYSTEM"

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    scraped_rules = relationship("ScrapedRule", back_populates="scraping_job")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "jurisdiction_code": self.jurisdiction_code,
            "status": self.status,
            "progress": round(self.progress, 2),
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "errors": self.errors or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
