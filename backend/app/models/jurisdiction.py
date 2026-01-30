"""
Jurisdiction and Rule Set Models - CompuLaw-style hierarchical rule system

This implements a database-driven rule system with:
- Jurisdictions (Federal, Florida State, Local)
- Rule Sets (FL:RCP, FL:BRMD-7, FRCP, etc.)
- Rule Dependencies (concurrent rules that must be loaded together)
- Court Locations (for automatic rule selection)
"""
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Boolean, Integer,
    Enum as SQLEnum, JSON, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base

# Import centralized enums (SINGLE SOURCE OF TRUTH)
from app.models.enums import TriggerType, DeadlinePriority, CalculationMethod, JurisdictionType


class CourtType(enum.Enum):
    """Types of courts"""
    CIRCUIT = "circuit"           # Florida Circuit Court (general jurisdiction)
    COUNTY = "county"             # Florida County Court (limited jurisdiction)
    DISTRICT = "district"         # Federal District Court
    BANKRUPTCY = "bankruptcy"     # Federal Bankruptcy Court
    APPELLATE_STATE = "appellate_state"    # Florida DCA
    APPELLATE_FEDERAL = "appellate_federal" # Federal Circuit Court of Appeals
    SUPREME_STATE = "supreme_state"         # Florida Supreme Court
    SUPREME_FEDERAL = "supreme_federal"     # US Supreme Court


class DependencyType(enum.Enum):
    """Types of rule dependencies"""
    CONCURRENT = "concurrent"     # Must be loaded together (e.g., local + FRCP)
    INHERITS = "inherits"         # Child inherits from parent
    SUPPLEMENTS = "supplements"   # Adds to but doesn't replace
    OVERRIDES = "overrides"       # Local rule overrides parent on conflict


class Jurisdiction(Base):
    """
    Represents a legal jurisdiction (Federal, State, Local)

    Examples:
    - Federal (parent of all federal courts)
    - Florida State (parent of Florida state courts)
    - 11th Judicial Circuit (local, parent=Florida State)
    """
    __tablename__ = "jurisdictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, index=True)  # "FL", "FED", "FL-11CIR"
    name = Column(String(255), nullable=False)  # "Florida State Courts"
    description = Column(Text)
    jurisdiction_type = Column(
        SQLEnum(JurisdictionType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Hierarchy - for local courts under state/federal
    parent_jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id"), nullable=True)

    # Geographic info
    state = Column(String(50))  # "FL", "NY", etc.
    federal_circuit = Column(Integer)  # 11 for 11th Circuit

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship("Jurisdiction", remote_side=[id], backref="children")
    rule_sets = relationship("RuleSet", back_populates="jurisdiction", cascade="all, delete-orphan")
    court_locations = relationship("CourtLocation", back_populates="jurisdiction", cascade="all, delete-orphan")


class RuleSet(Base):
    """
    A collection of court rules that generate deadlines

    Examples:
    - FL:RCP (Florida Rules of Civil Procedure)
    - FL:BRMD-7 (Bankruptcy Court - Middle District - Chapter 7)
    - FRCP (Federal Rules of Civil Procedure)

    Rule sets can have dependencies - loading FL:BRMD-7 also loads FRCP and FRBP
    """
    __tablename__ = "rule_sets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), unique=True, nullable=False, index=True)  # "FL:RCP"
    name = Column(String(255), nullable=False)  # "Florida Rules of Civil Procedure"
    description = Column(Text)

    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id"), nullable=False, index=True)
    court_type = Column(
        SQLEnum(CourtType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # What rules/sources this set contains deadlines from
    contains_deadlines_from = Column(JSON)  # ["Florida Rules of Civil Procedure", "Florida Rules of Appellate Procedure"]

    # For versioning (rules change over time)
    version = Column(String(50), default="current")
    effective_date = Column(DateTime)

    is_active = Column(Boolean, default=True)
    is_local = Column(Boolean, default=False)  # True for local/district-specific rules

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="rule_sets")
    rule_templates = relationship("RuleTemplate", back_populates="rule_set", cascade="all, delete-orphan")

    # Dependencies - what other rule sets must be loaded with this one
    dependencies = relationship(
        "RuleSetDependency",
        foreign_keys="RuleSetDependency.rule_set_id",
        back_populates="rule_set",
        cascade="all, delete-orphan"
    )
    required_by = relationship(
        "RuleSetDependency",
        foreign_keys="RuleSetDependency.required_rule_set_id",
        back_populates="required_rule_set"
    )


class RuleSetDependency(Base):
    """
    Defines dependencies between rule sets

    Example: FL:BRMD-7 (Bankruptcy Middle District Chapter 7)
    requires: BK:FRCP-BK (Federal Rules of Bankruptcy Procedure)
    requires: FRBP (Federal Rules of Bankruptcy Procedure)

    When a user selects FL:BRMD-7, we automatically load all required rule sets
    """
    __tablename__ = "rule_set_dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # The rule set that has the dependency
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True)

    # The rule set that is required
    required_rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True)

    dependency_type = Column(
        SQLEnum(DependencyType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DependencyType.CONCURRENT
    )

    # Priority for conflict resolution (higher = takes precedence)
    priority = Column(Integer, default=0)

    notes = Column(Text)  # "Local rules supplement but do not override FRCP"

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    rule_set = relationship("RuleSet", foreign_keys=[rule_set_id], back_populates="dependencies")
    required_rule_set = relationship("RuleSet", foreign_keys=[required_rule_set_id], back_populates="required_by")

    __table_args__ = (
        UniqueConstraint('rule_set_id', 'required_rule_set_id', name='uq_rule_dependency'),
    )


class CourtLocation(Base):
    """
    Specific court locations for automatic rule selection

    When we detect "SOUTHERN DISTRICT OF FLORIDA" in a document,
    we can automatically select the appropriate rule sets
    """
    __tablename__ = "court_locations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)  # "U.S. District Court - Southern District of Florida"
    short_name = Column(String(100))  # "S.D. Fla."

    court_type = Column(
        SQLEnum(CourtType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Geographic identifiers
    district = Column(String(100))  # "Southern", "Middle", "Northern"
    circuit = Column(Integer)  # 11, 13, 17 for Florida circuits; 11 for 11th Circuit federal
    division = Column(String(100))  # "Miami", "Fort Lauderdale", "West Palm Beach"

    # Pattern matching for document detection
    detection_patterns = Column(JSON)  # ["SOUTHERN DISTRICT OF FLORIDA", "S.D. FLA", "S.D.FLA."]
    case_number_pattern = Column(String(255))  # Regex for case numbers: "^\d{1,2}:\d{2}-cv-\d+"

    # Default rule sets to load for this court
    default_rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=True)
    local_rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    jurisdiction = relationship("Jurisdiction", back_populates="court_locations")
    default_rule_set = relationship("RuleSet", foreign_keys=[default_rule_set_id])
    local_rule_set = relationship("RuleSet", foreign_keys=[local_rule_set_id])


class RuleTemplate(Base):
    """
    A template for generating deadlines from a trigger event

    Example: FL:RCP Answer Rule
    - Trigger: Complaint Served
    - Generates: Answer Due (20 days), Motion to Dismiss (20 days), etc.
    """
    __tablename__ = "rule_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True)

    rule_code = Column(String(100), nullable=False)  # "FL_CIV_ANSWER"
    name = Column(String(255), nullable=False)  # "Answer to Complaint"
    description = Column(Text)

    trigger_type = Column(
        SQLEnum(TriggerType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    citation = Column(String(255))  # "Fla. R. Civ. P. 1.140(a)"

    # Metadata
    court_type = Column(
        SQLEnum(CourtType, values_callable=lambda x: [e.value for e in x])
    )  # Can be null to apply to all
    case_types = Column(JSON)  # ["civil", "family"] or null for all

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    rule_set = relationship("RuleSet", back_populates="rule_templates")
    deadlines = relationship("RuleTemplateDeadline", back_populates="rule_template", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('rule_set_id', 'rule_code', name='uq_rule_template_code'),
    )


class RuleTemplateDeadline(Base):
    """
    A specific deadline generated from a rule template

    Example: Answer Due
    - Days from trigger: 20
    - Priority: FATAL
    - Party responsible: defendant
    - Add service days: True
    """
    __tablename__ = "rule_template_deadlines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    rule_template_id = Column(String(36), ForeignKey("rule_templates.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)  # "Answer Due"
    description = Column(Text)  # Full description

    days_from_trigger = Column(Integer, nullable=False)  # Can be negative (before trigger)
    priority = Column(
        SQLEnum(DeadlinePriority, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DeadlinePriority.STANDARD
    )

    party_responsible = Column(String(100))  # "defendant", "plaintiff", "both", "opposing", "movant"
    action_required = Column(Text)  # "File and serve Answer to Complaint"

    calculation_method = Column(
        SQLEnum(CalculationMethod, values_callable=lambda x: [e.value for e in x]),
        default=CalculationMethod.CALENDAR_DAYS
    )
    add_service_days = Column(Boolean, default=False)  # Add 3-5 days for mail service

    rule_citation = Column(String(255))  # Specific rule citation
    notes = Column(Text)  # Additional notes, warnings

    # For conditional deadlines
    conditions = Column(JSON)  # {"if_jury_trial": true, "if_service_by_mail": true}

    display_order = Column(Integer, default=0)  # For consistent ordering

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    rule_template = relationship("RuleTemplate", back_populates="deadlines")


class CaseRuleSet(Base):
    """
    Associates a case with its applicable rule sets

    When a case is created, we determine which rule sets apply
    based on jurisdiction detection and store them here
    """
    __tablename__ = "case_rule_sets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_set_id = Column(String(36), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True)

    # How this rule set was assigned
    assignment_method = Column(String(50))  # "auto_detected", "user_selected", "inherited"

    # Priority for conflict resolution
    priority = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('case_id', 'rule_set_id', name='uq_case_rule_set'),
    )
