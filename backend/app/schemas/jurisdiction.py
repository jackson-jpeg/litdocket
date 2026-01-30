"""
Pydantic schemas for Jurisdiction and Rule System

These schemas handle API request/response validation for:
- Jurisdictions
- Rule Sets
- Rule Dependencies
- Court Locations
- Rule Templates and Deadlines
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ============================================================
# Enums (mirror the SQLAlchemy enums for Pydantic)
# ============================================================

class JurisdictionTypeEnum(str, Enum):
    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"
    BANKRUPTCY = "bankruptcy"
    APPELLATE = "appellate"


class CourtTypeEnum(str, Enum):
    CIRCUIT = "circuit"
    COUNTY = "county"
    DISTRICT = "district"
    BANKRUPTCY = "bankruptcy"
    APPELLATE_STATE = "appellate_state"
    APPELLATE_FEDERAL = "appellate_federal"
    SUPREME_STATE = "supreme_state"
    SUPREME_FEDERAL = "supreme_federal"


class DependencyTypeEnum(str, Enum):
    CONCURRENT = "concurrent"
    INHERITS = "inherits"
    SUPPLEMENTS = "supplements"
    OVERRIDES = "overrides"


class TriggerTypeEnum(str, Enum):
    CASE_FILED = "case_filed"
    SERVICE_COMPLETED = "service_completed"
    COMPLAINT_SERVED = "complaint_served"
    ANSWER_DUE = "answer_due"
    DISCOVERY_COMMENCED = "discovery_commenced"
    DISCOVERY_DEADLINE = "discovery_deadline"
    DISPOSITIVE_MOTIONS_DUE = "dispositive_motions_due"
    PRETRIAL_CONFERENCE = "pretrial_conference"
    TRIAL_DATE = "trial_date"
    HEARING_SCHEDULED = "hearing_scheduled"
    MOTION_FILED = "motion_filed"
    ORDER_ENTERED = "order_entered"
    APPEAL_FILED = "appeal_filed"
    MEDIATION_SCHEDULED = "mediation_scheduled"
    CUSTOM_TRIGGER = "custom_trigger"


class DeadlinePriorityEnum(str, Enum):
    INFORMATIONAL = "informational"
    STANDARD = "standard"
    IMPORTANT = "important"
    CRITICAL = "critical"
    FATAL = "fatal"


class CalculationMethodEnum(str, Enum):
    CALENDAR_DAYS = "calendar_days"
    COURT_DAYS = "court_days"
    BUSINESS_DAYS = "business_days"


# ============================================================
# Jurisdiction Schemas
# ============================================================

class JurisdictionBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, description="Unique code like 'FL', 'FED', 'FL-11CIR'")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    jurisdiction_type: JurisdictionTypeEnum
    parent_jurisdiction_id: Optional[str] = None
    state: Optional[str] = Field(None, max_length=50)
    federal_circuit: Optional[int] = Field(None, ge=1, le=13)


class JurisdictionCreate(JurisdictionBase):
    pass


class JurisdictionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class JurisdictionResponse(JurisdictionBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JurisdictionWithChildren(JurisdictionResponse):
    children: List['JurisdictionResponse'] = []
    rule_sets: List['RuleSetResponse'] = []


# ============================================================
# Rule Set Schemas
# ============================================================

class RuleSetBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50, description="Code like 'FL:RCP', 'FRCP'")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    jurisdiction_id: str
    court_type: CourtTypeEnum
    contains_deadlines_from: Optional[List[str]] = None
    version: Optional[str] = "current"
    is_local: bool = False


class RuleSetCreate(RuleSetBase):
    pass


class RuleSetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    contains_deadlines_from: Optional[List[str]] = None
    is_active: Optional[bool] = None


class RuleSetResponse(RuleSetBase):
    id: str
    is_active: bool
    effective_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RuleSetWithDependencies(RuleSetResponse):
    """Rule set with its dependencies resolved"""
    dependencies: List['RuleSetDependencyResponse'] = []
    rule_templates: List['RuleTemplateResponse'] = []


# ============================================================
# Rule Set Dependency Schemas
# ============================================================

class RuleSetDependencyBase(BaseModel):
    rule_set_id: str
    required_rule_set_id: str
    dependency_type: DependencyTypeEnum = DependencyTypeEnum.CONCURRENT
    priority: int = 0
    notes: Optional[str] = None


class RuleSetDependencyCreate(RuleSetDependencyBase):
    pass


class RuleSetDependencyResponse(RuleSetDependencyBase):
    id: str
    created_at: datetime
    required_rule_set: Optional[RuleSetResponse] = None

    class Config:
        from_attributes = True


# ============================================================
# Court Location Schemas
# ============================================================

class CourtLocationBase(BaseModel):
    jurisdiction_id: str
    name: str = Field(..., min_length=1, max_length=255)
    short_name: Optional[str] = Field(None, max_length=100)
    court_type: CourtTypeEnum
    district: Optional[str] = None
    circuit: Optional[int] = None
    division: Optional[str] = None
    detection_patterns: Optional[List[str]] = None
    case_number_pattern: Optional[str] = None
    default_rule_set_id: Optional[str] = None
    local_rule_set_id: Optional[str] = None


class CourtLocationCreate(CourtLocationBase):
    pass


class CourtLocationUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    detection_patterns: Optional[List[str]] = None
    case_number_pattern: Optional[str] = None
    default_rule_set_id: Optional[str] = None
    local_rule_set_id: Optional[str] = None
    is_active: Optional[bool] = None


class CourtLocationResponse(CourtLocationBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourtLocationWithRules(CourtLocationResponse):
    """Court location with resolved rule sets"""
    default_rule_set: Optional[RuleSetResponse] = None
    local_rule_set: Optional[RuleSetResponse] = None
    all_applicable_rule_sets: List[RuleSetResponse] = []


# ============================================================
# Rule Template Schemas
# ============================================================

class RuleTemplateDeadlineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    days_from_trigger: int = Field(..., description="Days from trigger (negative = before)")
    priority: DeadlinePriorityEnum = DeadlinePriorityEnum.STANDARD
    party_responsible: Optional[str] = None
    action_required: Optional[str] = None
    calculation_method: CalculationMethodEnum = CalculationMethodEnum.CALENDAR_DAYS
    add_service_days: bool = False
    rule_citation: Optional[str] = None
    notes: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    display_order: int = 0


class RuleTemplateDeadlineCreate(RuleTemplateDeadlineBase):
    rule_template_id: str


class RuleTemplateDeadlineResponse(RuleTemplateDeadlineBase):
    id: str
    rule_template_id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RuleTemplateBase(BaseModel):
    rule_set_id: str
    rule_code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: TriggerTypeEnum
    citation: Optional[str] = None
    court_type: Optional[CourtTypeEnum] = None
    case_types: Optional[List[str]] = None


class RuleTemplateCreate(RuleTemplateBase):
    deadlines: Optional[List[RuleTemplateDeadlineBase]] = None


class RuleTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    citation: Optional[str] = None
    is_active: Optional[bool] = None


class RuleTemplateResponse(RuleTemplateBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RuleTemplateWithDeadlines(RuleTemplateResponse):
    """Rule template with all its deadline definitions"""
    deadlines: List[RuleTemplateDeadlineResponse] = []


# ============================================================
# Case Rule Set Association
# ============================================================

class CaseRuleSetCreate(BaseModel):
    case_id: str
    rule_set_id: str
    assignment_method: str = "user_selected"
    priority: int = 0


class CaseRuleSetResponse(BaseModel):
    id: str
    case_id: str
    rule_set_id: str
    assignment_method: str
    priority: int
    is_active: bool
    created_at: datetime
    rule_set: Optional[RuleSetResponse] = None

    class Config:
        from_attributes = True


# ============================================================
# Jurisdiction Detection Schemas
# ============================================================

class JurisdictionDetectionRequest(BaseModel):
    """Request to detect jurisdiction from text"""
    text: str = Field(..., min_length=10, description="Document text to analyze")
    case_number: Optional[str] = None
    court_name: Optional[str] = None


class JurisdictionDetectionResult(BaseModel):
    """Result of jurisdiction detection"""
    detected: bool
    confidence: float = Field(..., ge=0, le=1)

    jurisdiction: Optional[JurisdictionResponse] = None
    court_location: Optional[CourtLocationResponse] = None

    # All applicable rule sets (including dependencies)
    applicable_rule_sets: List[RuleSetResponse] = []

    # Detection details
    detected_court_name: Optional[str] = None
    detected_district: Optional[str] = None
    detected_case_number: Optional[str] = None

    # Patterns that matched
    matched_patterns: List[str] = []


# ============================================================
# Calculated Deadline Schemas (for trigger calculations)
# ============================================================

class TriggerEventRequest(BaseModel):
    """Request to calculate deadlines from a trigger event"""
    case_id: str
    trigger_type: TriggerTypeEnum
    trigger_date: date
    service_method: str = "electronic"  # electronic, mail, personal
    notes: Optional[str] = None


class CalculatedDeadline(BaseModel):
    """A calculated deadline from a trigger event"""
    title: str
    description: str
    deadline_date: date
    priority: DeadlinePriorityEnum
    party_role: Optional[str] = None
    action_required: Optional[str] = None
    rule_citation: Optional[str] = None
    calculation_basis: str
    trigger_event: str
    trigger_date: date
    is_calculated: bool = True
    is_dependent: bool = True
    notes: Optional[str] = None

    # CompuLaw-style extras
    trigger_code: Optional[str] = None
    trigger_formula: Optional[str] = None
    party_string: Optional[str] = None
    short_explanation: Optional[str] = None


class TriggerEventResponse(BaseModel):
    """Response after calculating deadlines from a trigger"""
    trigger_id: str
    trigger_type: TriggerTypeEnum
    trigger_date: date
    case_id: str

    # Deadlines that were created
    deadlines_created: int
    deadlines: List[CalculatedDeadline]

    # Rule sets that were used
    rule_sets_applied: List[str]


# ============================================================
# Hierarchy Schemas (CompuLaw-style cascading dropdowns)
# ============================================================

class HierarchyNode(BaseModel):
    """A node in the jurisdiction hierarchy tree"""
    id: str
    code: str
    name: str
    level: int  # 1=System, 2=Jurisdiction, 3=Court, 4=Judge
    level_name: str  # "system", "jurisdiction", "court", "judge"
    parent_id: Optional[str] = None
    children: List['HierarchyNode'] = []
    metadata: Optional[Dict[str, Any]] = None
    rule_set_codes: List[str] = []  # Applicable rule sets at this level


class JurisdictionHierarchyResponse(BaseModel):
    """Full jurisdiction hierarchy for cascading dropdowns"""
    systems: List[HierarchyNode]
    last_updated: datetime


class CaseJurisdictionUpdate(BaseModel):
    """Request to update a case's jurisdiction (triggers Retroactive Ripple)"""
    jurisdiction_id: Optional[str] = None
    court_location_id: Optional[str] = None
    judge: Optional[str] = None
    # If true, recalculate all deadlines with new jurisdiction's rules
    recalculate_deadlines: bool = True


class JurisdictionChangeResult(BaseModel):
    """Result of a jurisdiction change with Retroactive Ripple"""
    case_id: str
    previous_jurisdiction: Optional[str]
    new_jurisdiction: Optional[str]
    deadlines_updated: int
    deadlines_removed: int
    deadlines_added: int
    audit_message: str
    warnings: List[str] = []


# ============================================================
# Jurisdiction Tree Schemas (for frontend tree selector)
# ============================================================

class RuleSetDependencySimple(BaseModel):
    """Simplified dependency for tree view"""
    required_rule_set_id: str
    dependency_type: str
    priority: int


class JurisdictionTreeItem(BaseModel):
    """Jurisdiction item for tree"""
    id: str
    code: str
    name: str
    jurisdiction_type: str
    parent_jurisdiction_id: Optional[str] = None


class RuleSetTreeItem(BaseModel):
    """Rule set item for tree with dependencies"""
    id: str
    code: str
    name: str
    jurisdiction_id: str
    court_type: Optional[str] = None
    is_local: bool = False
    dependencies: List[RuleSetDependencySimple] = []


class JurisdictionTreeResponse(BaseModel):
    """Complete data for jurisdiction tree selector"""
    jurisdictions: List[JurisdictionTreeItem]
    rule_sets: List[RuleSetTreeItem]


# Fix forward references
HierarchyNode.model_rebuild()
JurisdictionWithChildren.model_rebuild()
RuleSetWithDependencies.model_rebuild()
