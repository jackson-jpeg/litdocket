"""
User-Created Rule Models

These models support user-created deadline calculation rules that can be:
- Saved as drafts
- Activated for use
- Shared publicly in the marketplace
- Versioned for history tracking
- Executed to generate deadlines

Tables (created in migration 010_user_rules_additions.sql):
- user_rule_templates
- user_rule_template_versions
- user_rule_executions

These are separate from the CompuLaw-style RuleTemplate in jurisdiction.py.
"""
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Boolean, Integer,
    JSON, UniqueConstraint, func, ARRAY
)
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


class UserRuleStatus(enum.Enum):
    """Status of a user-created rule"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class UserRuleTemplate(Base):
    """
    User-created deadline calculation rule template

    Users can create custom rules for their specific jurisdictions/needs,
    optionally share them publicly, and execute them to generate deadlines.

    Uses a separate table 'user_rule_templates' to avoid conflict with the
    CompuLaw-style RuleTemplate in jurisdiction.py which uses 'rule_templates'.
    """
    __tablename__ = "user_rule_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic info
    rule_name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)  # Unique per user via index
    description = Column(Text)

    # Classification
    jurisdiction = Column(String(100), nullable=False, index=True)
    trigger_type = Column(String(100), nullable=False, index=True)
    tags = Column(ARRAY(Text))  # PostgreSQL array type

    # Ownership
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Sharing
    is_public = Column(Boolean, default=False)
    is_official = Column(Boolean, default=False)

    # Current version tracking
    current_version_id = Column(String(36))

    # Statistics
    version_count = Column(Integer, default=1)
    usage_count = Column(Integer, default=0)
    user_count = Column(Integer, default=0)

    # Status (stored as string in DB)
    status = Column(String(50), default='draft')

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime(timezone=True))
    deprecated_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", backref="user_rule_templates")
    versions = relationship(
        "UserRuleTemplateVersion",
        back_populates="rule_template",
        cascade="all, delete-orphan",
        order_by="desc(UserRuleTemplateVersion.version_number)"
    )
    executions = relationship(
        "UserRuleExecution",
        back_populates="rule_template",
        cascade="all, delete-orphan"
    )

    @property
    def current_version(self):
        """Get the latest active version"""
        for v in self.versions:
            if v.status == 'active':
                return v
        return self.versions[0] if self.versions else None


class UserRuleTemplateVersion(Base):
    """
    Versioned content of a user rule template

    Each version stores a complete rule_schema so users can:
    - Roll back to previous versions
    - Compare changes between versions
    - Maintain audit trail
    """
    __tablename__ = "user_rule_template_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    rule_template_id = Column(
        String(36),
        ForeignKey("user_rule_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    version_number = Column(Integer, nullable=False)
    version_name = Column(String(255))

    # The complete rule schema (JSONB in PostgreSQL)
    rule_schema = Column(JSON, nullable=False)

    # Creator - maps to 'created_by' in the database
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Change tracking
    change_summary = Column(Text)

    # Validation
    is_validated = Column(Boolean, default=False)
    validation_errors = Column(JSON)

    # Testing stats
    test_cases_passed = Column(Integer, default=0)
    test_cases_failed = Column(Integer, default=0)

    # Version status
    status = Column(String(50), default='draft')

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    activated_at = Column(DateTime(timezone=True))
    deprecated_at = Column(DateTime(timezone=True))

    # Relationships
    rule_template = relationship("UserRuleTemplate", back_populates="versions")


class UserRuleExecution(Base):
    """
    Audit trail of user rule executions

    Records every time a user rule is executed to generate deadlines,
    including the trigger data used and results produced.
    """
    __tablename__ = "user_rule_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # What was executed
    rule_template_id = Column(
        String(36),
        ForeignKey("user_rule_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    rule_version_id = Column(
        String(36),
        ForeignKey("user_rule_template_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Who executed and where
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)

    # Input data
    trigger_data = Column(JSON)

    # Results
    deadlines_created = Column(Integer, default=0)
    deadline_ids = Column(ARRAY(Text))  # PostgreSQL array type

    # Performance tracking
    execution_time_ms = Column(Integer)

    # Status
    status = Column(String(50), default='success')
    error_message = Column(Text)
    errors = Column(JSON)

    # Was this a dry run (preview without creating)?
    dry_run = Column(Boolean, default=False)

    # Timestamps
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    rule_template = relationship("UserRuleTemplate", back_populates="executions")
    user = relationship("User", backref="rule_executions")
    case = relationship("Case", backref="rule_executions")
