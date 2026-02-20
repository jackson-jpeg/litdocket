"""
Inbox Models - Unified Approval Workflow

Provides a single inbox for all pending approvals:
- Jurisdiction approvals (from Cartographer discovery)
- Rule verifications (low confidence extractions)
- Watchtower changes (detected rule updates)
- Scraper failures (requiring manual intervention)
- Conflict resolutions (rule conflicts)
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Numeric, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import uuid

from app.database import Base
from app.models.enums import InboxItemType, InboxStatus


class InboxItem(Base):
    """
    Unified inbox for all approval workflows.

    This table consolidates multiple approval workflows into a single
    queue, making it easier for attorneys to review and act on pending items.
    """
    __tablename__ = "inbox_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Item classification
    type = Column(
        SQLEnum(
            InboxItemType,
            name='inbox_item_type',
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        index=True
    )

    status = Column(
        SQLEnum(
            InboxStatus,
            name='inbox_status',
            create_type=False,
            values_callable=lambda x: [e.value for e in x]
        ),
        nullable=False,
        default=InboxStatus.PENDING,
        index=True
    )

    # Display information
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # Polymorphic references (only one should be set based on type)
    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="CASCADE"), index=True)
    rule_id = Column(String(36), ForeignKey("authority_rules.id", ondelete="CASCADE"), index=True)
    conflict_id = Column(String(36), ForeignKey("rule_conflicts.id", ondelete="CASCADE"), index=True)
    scrape_job_id = Column(String(36), ForeignKey("scrape_jobs.id", ondelete="CASCADE"), index=True)

    # Metadata
    confidence = Column(Numeric(5, 2))  # AI confidence score (0-100)
    source_url = Column(Text)
    item_metadata = Column(JSONB, default={})  # Flexible metadata storage

    # Ownership — every inbox item belongs to a user
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Workflow tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    resolution = Column(String(50))  # 'approved', 'rejected', 'deferred'
    resolution_notes = Column(Text)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id])
    rule = relationship("AuthorityRule", foreign_keys=[rule_id])
    conflict = relationship("RuleConflict", foreign_keys=[conflict_id])
    scrape_job = relationship("ScrapeJob", foreign_keys=[scrape_job_id])
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by])

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type.value if self.type else None,
            "status": self.status.value if self.status else None,
            "title": self.title,
            "description": self.description,
            "jurisdiction_id": self.jurisdiction_id,
            "rule_id": self.rule_id,
            "conflict_id": self.conflict_id,
            "scrape_job_id": self.scrape_job_id,
            "confidence": float(self.confidence) if self.confidence else None,
            "source_url": self.source_url,
            "metadata": self.item_metadata,  # Map back to 'metadata' for API compatibility
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "resolution": self.resolution,
            "resolution_notes": self.resolution_notes
        }


class ScraperHealthLog(Base):
    """
    Audit trail for scraper health and self-healing operations.

    Tracks scraper failures, recoveries, config updates, and rediscoveries
    to provide visibility into the self-healing pipeline.
    """
    __tablename__ = "scraper_health_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event types: 'failure', 'recovery', 'config_update', 'rediscovery'
    event_type = Column(String(50), nullable=False, index=True)

    error_message = Column(Text)
    scraper_config_version = Column(Numeric, nullable=False)
    consecutive_failures = Column(Numeric, default=0)
    event_metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id])

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "jurisdiction_id": self.jurisdiction_id,
            "event_type": self.event_type,
            "error_message": self.error_message,
            "scraper_config_version": int(self.scraper_config_version) if self.scraper_config_version else None,
            "consecutive_failures": int(self.consecutive_failures) if self.consecutive_failures else 0,
            "metadata": self.event_metadata,  # Map back to 'metadata' for API compatibility
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
