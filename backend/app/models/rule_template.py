"""
Rule Template Model - Database-Driven Rules System

Stores rule definitions as JSON schemas, enabling unlimited jurisdictions
without code changes.
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ARRAY, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class RuleTemplate(Base):
    """
    Master rule definition for a jurisdiction/trigger combination

    Example: "Florida Civil - Trial Date Chain"

    A rule template can have multiple versions over time (for updates/changes).
    The current_version_id points to the active version.
    """
    __tablename__ = "rule_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Metadata
    rule_name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)  # "florida-civil-trial-date"
    jurisdiction = Column(String(100), nullable=False, index=True)  # "florida_civil"
    trigger_type = Column(String(100), nullable=False, index=True)  # "TRIAL_DATE"

    # Ownership
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    is_public = Column(Boolean, default=False, index=True)  # Shareable in marketplace
    is_official = Column(Boolean, default=False)  # Verified by LitDocket

    # Versioning
    current_version_id = Column(String(36), ForeignKey('rule_versions.id', use_alter=True, name='fk_current_version'))
    version_count = Column(Integer, default=1)

    # Status
    status = Column(String(50), default='draft', index=True)  # draft, active, deprecated, archived

    # Usage tracking
    usage_count = Column(Integer, default=0)  # How many times executed
    user_count = Column(Integer, default=0)   # How many unique users

    # Metadata
    description = Column(Text)
    tags = Column(ARRAY(String))  # ["florida", "civil", "trial"]

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    published_at = Column(DateTime)
    deprecated_at = Column(DateTime)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_rules")
    versions = relationship("RuleVersion", foreign_keys="RuleVersion.rule_template_id", back_populates="rule_template", cascade="all, delete-orphan")
    current_version = relationship("RuleVersion", foreign_keys=[current_version_id], post_update=True)
    executions = relationship("RuleExecution", back_populates="rule_template", cascade="all, delete-orphan")
    test_cases = relationship("RuleTestCase", back_populates="rule_template", cascade="all, delete-orphan")

    # Table args
    __table_args__ = (
        Index('idx_jurisdiction_trigger', 'jurisdiction', 'trigger_type'),
    )

    def __repr__(self):
        return f"<RuleTemplate {self.rule_name} ({self.jurisdiction}/{self.trigger_type})>"


class RuleVersion(Base):
    """
    Specific version of a rule template

    Rules are immutable once published - changes create new versions.
    This enables rollback and audit trail.
    """
    __tablename__ = "rule_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_template_id = Column(String(36), ForeignKey('rule_templates.id', ondelete='CASCADE'), nullable=False, index=True)

    # Version info
    version_number = Column(Integer, nullable=False)
    version_name = Column(String(255))  # "2025 Update", "Post-Reform Changes"

    # The actual rule definition (JSON)
    rule_schema = Column(JSONB, nullable=False)
    # Structure: {
    #   "metadata": {...},
    #   "trigger": {...},
    #   "deadlines": [...],
    #   "validation": {...},
    #   "settings": {...}
    # }

    # Change tracking
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    change_summary = Column(Text)  # "Added service method extensions for mail service"

    # Validation
    is_validated = Column(Boolean, default=False)
    validation_errors = Column(JSONB)  # Array of validation issues

    # Testing
    test_cases_passed = Column(Integer, default=0)
    test_cases_failed = Column(Integer, default=0)

    # Status
    status = Column(String(50), default='draft')  # draft, active, deprecated

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    activated_at = Column(DateTime)
    deprecated_at = Column(DateTime)

    # Relationships
    rule_template = relationship("RuleTemplate", foreign_keys=[rule_template_id], back_populates="versions")
    creator = relationship("User", foreign_keys=[created_by])
    conditions = relationship("RuleCondition", back_populates="rule_version", cascade="all, delete-orphan")
    dependencies = relationship("RuleDependency", back_populates="rule_version", cascade="all, delete-orphan")

    # Unique constraint: one version number per template
    __table_args__ = (
        Index('idx_unique_version', 'rule_template_id', 'version_number', unique=True),
    )

    def __repr__(self):
        return f"<RuleVersion v{self.version_number} of {self.rule_template_id}>"


class RuleCondition(Base):
    """
    Conditional logic for deadlines (if-then rules)

    Example: If case_type == "personal_injury", then offset_days = -120
    """
    __tablename__ = "rule_conditions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_version_id = Column(String(36), ForeignKey('rule_versions.id', ondelete='CASCADE'), nullable=False, index=True)
    deadline_id = Column(String(100), nullable=False)  # Which deadline this affects

    # Condition definition (JSON)
    condition_schema = Column(JSONB, nullable=False)
    # Example: {"if": {"case_type": "personal_injury"}, "then": {"offset_days": -120}}

    # Priority (conditions evaluated in order)
    priority = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rule_version = relationship("RuleVersion", back_populates="conditions")

    def __repr__(self):
        return f"<RuleCondition for deadline {self.deadline_id}>"


class RuleExecution(Base):
    """
    Audit trail of rule executions

    Every time a rule runs, we log it for legal defensibility and analytics.
    """
    __tablename__ = "rule_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # What was executed
    rule_template_id = Column(String(36), ForeignKey('rule_templates.id'), nullable=False, index=True)
    rule_version_id = Column(String(36), ForeignKey('rule_versions.id'), nullable=False, index=True)

    # Where it was executed
    case_id = Column(String(36), ForeignKey('cases.id'), nullable=False, index=True)
    trigger_deadline_id = Column(String(36), ForeignKey('deadlines.id'))

    # Who executed it
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)

    # Input data
    trigger_data = Column(JSONB)  # {"trial_date": "2026-03-01", "trial_type": "jury"}

    # Output results
    deadlines_created = Column(Integer, default=0)
    deadline_ids = Column(ARRAY(String))  # UUIDs of created deadlines

    # Performance
    execution_time_ms = Column(Integer)

    # Status
    status = Column(String(50))  # success, failed, partial
    error_message = Column(Text)

    # Timestamps
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    rule_template = relationship("RuleTemplate", back_populates="executions")
    rule_version = relationship("RuleVersion")
    case = relationship("Case")
    trigger_deadline = relationship("Deadline")
    user = relationship("User")

    def __repr__(self):
        return f"<RuleExecution {self.id} - {self.status}>"


class RuleTestCase(Base):
    """
    Test cases for validating rules

    Each rule should have test cases proving it generates correct deadlines.
    """
    __tablename__ = "rule_test_cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_template_id = Column(String(36), ForeignKey('rule_templates.id', ondelete='CASCADE'), nullable=False, index=True)

    # Test case definition
    test_name = Column(String(255), nullable=False)
    test_description = Column(Text)

    # Input data
    input_data = Column(JSONB, nullable=False)
    # Example: {"trial_date": "2026-06-01", "case_type": "civil", "service_method": "mail"}

    # Expected output
    expected_deadlines = Column(JSONB, nullable=False)
    # Array of expected deadline objects with dates, priorities, etc.

    # Validation rules
    validation_rules = Column(JSONB)
    # {"min_deadlines": 10, "max_deadlines": 60, "require_citations": true}

    # Test results
    last_run_at = Column(DateTime)
    last_run_status = Column(String(50))  # passed, failed
    last_run_errors = Column(JSONB)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rule_template = relationship("RuleTemplate", back_populates="test_cases")

    def __repr__(self):
        return f"<RuleTestCase {self.test_name}>"


class RuleDependency(Base):
    """
    Models deadline dependencies (deadline A must come before/after deadline B)
    """
    __tablename__ = "rule_dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_version_id = Column(String(36), ForeignKey('rule_versions.id', ondelete='CASCADE'), nullable=False, index=True)

    # Dependency relationship
    deadline_id = Column(String(100), nullable=False)
    depends_on_deadline_id = Column(String(100), nullable=False)

    # Dependency type
    dependency_type = Column(String(50))  # must_come_after, must_come_before, same_day

    # Offset if sequential
    offset_days = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rule_version = relationship("RuleVersion", back_populates="dependencies")

    # Check constraint: prevent self-dependency
    __table_args__ = (
        # Note: Actual CHECK constraint would be added in migration
    )

    def __repr__(self):
        return f"<RuleDependency {self.deadline_id} depends on {self.depends_on_deadline_id}>"
