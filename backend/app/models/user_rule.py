"""
User-Created Rule Models

These models support user-created deadline calculation rules that can be:
- Saved as drafts
- Activated for use
- Shared publicly in the marketplace
- Versioned for history tracking
- Executed to generate deadlines

NOTE: These models map to tables created in migration 009_dynamic_rules_engine.sql:
- rule_templates
- rule_versions
- rule_executions

The table names differ from the class names for compatibility with existing schema.
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

    Maps to 'rule_templates' table from migration 009.
    """
    __tablename__ = "rule_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic info
    rule_name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)

    # Classification
    jurisdiction = Column(String(100), nullable=False, index=True)
    trigger_type = Column(String(100), nullable=False, index=True)
    tags = Column(ARRAY(Text))  # PostgreSQL array type

    # Ownership - maps to 'created_by' in the database
    user_id = Column('created_by', String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

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
        "RuleExecution",
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

    Maps to 'rule_versions' table from migration 009.
    """
    __tablename__ = "rule_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    rule_template_id = Column(
        String(36),
        ForeignKey("rule_templates.id", ondelete="CASCADE"),
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
    change_notes = Column('change_summary', Text)

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


class RuleExecution(Base):
    """
    Audit trail of rule executions

    Records every time a rule is executed to generate deadlines,
    including the trigger data used and results produced.

    Maps to 'rule_executions' table from migration 009.
    """
    __tablename__ = "rule_executions"
    __table_args__ = {'extend_existing': True}  # Allow extending if table already mapped

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # What was executed
    rule_template_id = Column(
        String(36),
        ForeignKey("rule_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    rule_version_id = Column(
        String(36),
        ForeignKey("rule_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Who executed and where
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    trigger_deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="SET NULL"), nullable=True)

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
