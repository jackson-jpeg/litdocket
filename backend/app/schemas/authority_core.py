"""
Pydantic schemas for Authority Core API endpoints.

Authority Core is the AI-powered rules database that serves as the
single source of truth for deadline calculations across LitDocket.
"""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum


# =============================================================
# ENUMS FOR API
# =============================================================

class AuthorityTierEnum(str, Enum):
    """Authority level for rule precedence"""
    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"
    STANDING_ORDER = "standing_order"
    FIRM = "firm"


class ProposalStatusEnum(str, Enum):
    """Status of rule proposals"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ScrapeStatusEnum(str, Enum):
    """Status of scrape jobs"""
    QUEUED = "queued"
    SEARCHING = "searching"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    FAILED = "failed"


class ConflictResolutionEnum(str, Enum):
    """How a conflict was resolved"""
    PENDING = "pending"
    USE_HIGHER_TIER = "use_higher_tier"
    USE_RULE_A = "use_rule_a"
    USE_RULE_B = "use_rule_b"
    MANUAL = "manual"
    IGNORED = "ignored"


# =============================================================
# DEADLINE SPEC SCHEMAS
# =============================================================

class DeadlineSpec(BaseModel):
    """Specification for a single deadline within a rule"""
    title: str = Field(..., description="Deadline title")
    days_from_trigger: int = Field(..., description="Days from trigger event (negative = before)")
    calculation_method: str = Field(
        "calendar_days",
        description="Calculation method: calendar_days, business_days, court_days"
    )
    priority: str = Field(
        "standard",
        description="Priority: informational, standard, important, critical, fatal"
    )
    party_responsible: Optional[str] = Field(
        None,
        description="Who is responsible: plaintiff, defendant, both, court"
    )
    conditions: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional conditions for this specific deadline"
    )
    description: Optional[str] = Field(None, description="Additional description")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Response to Motion Due",
                "days_from_trigger": 14,
                "calculation_method": "calendar_days",
                "priority": "important",
                "party_responsible": "opposing",
                "conditions": {"motion_type": "dispositive"}
            }
        }


class ServiceExtensions(BaseModel):
    """Additional days based on service method"""
    mail: int = Field(3, description="Additional days for mail service")
    electronic: int = Field(0, description="Additional days for electronic service")
    personal: int = Field(0, description="Additional days for personal service")


class RuleConditions(BaseModel):
    """Conditions when a rule applies"""
    case_types: Optional[List[str]] = Field(None, description="Applicable case types")
    motion_types: Optional[List[str]] = Field(None, description="Applicable motion types")
    service_methods: Optional[List[str]] = Field(None, description="Applicable service methods")
    exclusions: Optional[Dict[str, Any]] = Field(None, description="Exclusion conditions")


# =============================================================
# AUTHORITY RULE SCHEMAS
# =============================================================

class AuthorityRuleBase(BaseModel):
    """Base schema for Authority Rules"""
    rule_code: str = Field(..., max_length=100, description="Unique rule code (e.g., SDFL_LR_7.1)")
    rule_name: str = Field(..., max_length=255, description="Human-readable rule name")
    trigger_type: str = Field(..., description="What triggers this rule")
    authority_tier: AuthorityTierEnum = Field(
        AuthorityTierEnum.STATE,
        description="Authority level for precedence"
    )
    citation: Optional[str] = Field(None, description="Official citation")
    source_url: Optional[str] = Field(None, description="URL where rule was found")
    source_text: Optional[str] = Field(None, description="Original rule text")
    deadlines: List[DeadlineSpec] = Field(default_factory=list, description="Deadline specifications")
    conditions: Optional[RuleConditions] = Field(None, description="When rule applies")
    service_extensions: Optional[ServiceExtensions] = Field(None, description="Service method extensions")
    effective_date: Optional[date] = Field(None, description="When rule takes effect")


class AuthorityRuleCreate(AuthorityRuleBase):
    """Schema for creating an Authority Rule"""
    jurisdiction_id: str = Field(..., description="Jurisdiction this rule applies to")

    class Config:
        json_schema_extra = {
            "example": {
                "rule_code": "SDFL_LR_7.1_a_2",
                "rule_name": "Motion Response Time - S.D. Florida Local Rule 7.1(a)(2)",
                "trigger_type": "motion_filed",
                "authority_tier": "local",
                "jurisdiction_id": "sdfl-uuid",
                "citation": "S.D. Fla. L.R. 7.1(a)(2)",
                "source_url": "https://www.flsd.uscourts.gov/local-rules",
                "deadlines": [
                    {
                        "title": "Response to Motion Due",
                        "days_from_trigger": 14,
                        "calculation_method": "calendar_days",
                        "priority": "important",
                        "party_responsible": "opposing"
                    }
                ],
                "service_extensions": {"mail": 3, "electronic": 0, "personal": 0}
            }
        }


class AuthorityRuleUpdate(BaseModel):
    """Schema for updating an Authority Rule"""
    rule_name: Optional[str] = Field(None, max_length=255)
    citation: Optional[str] = None
    source_text: Optional[str] = None
    deadlines: Optional[List[DeadlineSpec]] = None
    conditions: Optional[RuleConditions] = None
    service_extensions: Optional[ServiceExtensions] = None
    is_active: Optional[bool] = None
    effective_date: Optional[date] = None
    superseded_date: Optional[date] = None


class AuthorityRuleResponse(AuthorityRuleBase):
    """Schema for Authority Rule response"""
    id: str
    jurisdiction_id: Optional[str]
    jurisdiction_name: Optional[str] = None
    user_id: Optional[str]
    confidence_score: float = 0.0
    is_verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    is_active: bool = True
    superseded_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    usage_count: Optional[int] = 0

    class Config:
        from_attributes = True


class AuthorityRuleSearchResult(BaseModel):
    """Search result with relevance score"""
    rule: AuthorityRuleResponse
    relevance_score: float = Field(..., description="Search relevance score 0-1")
    match_highlights: Optional[List[str]] = Field(None, description="Text highlights from matches")


# =============================================================
# SCRAPE JOB SCHEMAS
# =============================================================

class ScrapeRequest(BaseModel):
    """Request to start a scraping job"""
    jurisdiction_id: str = Field(..., description="Jurisdiction to search rules for")
    search_query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Search query for finding rules"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "jurisdiction_id": "sdfl-uuid",
                "search_query": "motion response deadline local rules"
            }
        }


class ScrapeProgress(BaseModel):
    """Progress update for a scrape job (SSE event)"""
    job_id: str
    status: ScrapeStatusEnum
    progress_pct: int = Field(..., ge=0, le=100)
    message: str
    urls_processed: List[str] = []
    rules_found: int = 0
    current_action: Optional[str] = None


class ScrapeJobResponse(BaseModel):
    """Response for a scrape job"""
    id: str
    user_id: str
    jurisdiction_id: Optional[str]
    jurisdiction_name: Optional[str] = None
    search_query: str
    status: ScrapeStatusEnum
    progress_pct: int
    rules_found: int
    proposals_created: int
    urls_processed: List[str]
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================
# RULE PROPOSAL SCHEMAS
# =============================================================

class ProposedRuleData(BaseModel):
    """The proposed rule data structure"""
    rule_code: str
    rule_name: str
    trigger_type: str
    authority_tier: AuthorityTierEnum
    citation: Optional[str] = None
    deadlines: List[DeadlineSpec]
    conditions: Optional[RuleConditions] = None
    service_extensions: Optional[ServiceExtensions] = None


class RuleProposalCreate(BaseModel):
    """Manually create a rule proposal"""
    jurisdiction_id: str
    proposed_rule_data: ProposedRuleData
    source_url: Optional[str] = None
    source_text: Optional[str] = None


class RuleProposalResponse(BaseModel):
    """Response for a rule proposal"""
    id: str
    user_id: str
    scrape_job_id: Optional[str]
    jurisdiction_id: Optional[str]
    jurisdiction_name: Optional[str] = None
    proposed_rule_data: Dict[str, Any]
    source_url: Optional[str]
    source_text: Optional[str]
    confidence_score: float
    extraction_notes: Optional[str]
    status: ProposalStatusEnum
    reviewed_by: Optional[str] = None
    reviewer_notes: Optional[str] = None
    approved_rule_id: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProposalApprovalRequest(BaseModel):
    """Request to approve a proposal with optional modifications"""
    modifications: Optional[ProposedRuleData] = Field(
        None,
        description="Modified rule data (if empty, uses original proposal)"
    )
    notes: Optional[str] = Field(None, description="Reviewer notes")


class ProposalRejectionRequest(BaseModel):
    """Request to reject a proposal"""
    reason: str = Field(..., min_length=10, description="Reason for rejection")


class ProposalRevisionRequest(BaseModel):
    """Request to mark proposal as needing revision"""
    notes: str = Field(..., min_length=10, description="What needs to be revised")


# =============================================================
# RULE CONFLICT SCHEMAS
# =============================================================

class RuleConflictResponse(BaseModel):
    """Response for a rule conflict"""
    id: str
    rule_a_id: str
    rule_a_name: Optional[str] = None
    rule_a_citation: Optional[str] = None
    rule_b_id: str
    rule_b_name: Optional[str] = None
    rule_b_citation: Optional[str] = None
    conflict_type: str
    severity: str
    description: str
    resolution: ConflictResolutionEnum
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConflictResolutionRequest(BaseModel):
    """Request to resolve a conflict"""
    resolution: ConflictResolutionEnum = Field(..., description="How to resolve the conflict")
    notes: Optional[str] = Field(None, description="Resolution notes")


# =============================================================
# RULE USAGE SCHEMAS
# =============================================================

class RuleUsageResponse(BaseModel):
    """Response for rule usage record"""
    id: str
    rule_id: str
    rule_name: Optional[str] = None
    case_id: Optional[str]
    case_number: Optional[str] = None
    deadline_id: Optional[str]
    user_id: str
    trigger_type: Optional[str]
    trigger_date: Optional[date]
    deadlines_generated: int
    used_at: datetime

    class Config:
        from_attributes = True


# =============================================================
# CALCULATED DEADLINE SCHEMA
# =============================================================

class CalculatedDeadline(BaseModel):
    """A deadline calculated from an Authority Rule"""
    title: str
    deadline_date: date
    days_from_trigger: int
    calculation_method: str
    priority: str
    party_responsible: Optional[str] = None
    source_rule_id: str
    citation: Optional[str] = None
    rule_name: str
    conditions_met: Dict[str, Any] = {}


class DeadlineCalculationRequest(BaseModel):
    """Request to calculate deadlines from a trigger"""
    jurisdiction_id: str = Field(..., description="Jurisdiction for rule lookup")
    trigger_type: str = Field(..., description="Type of trigger event")
    trigger_date: date = Field(..., description="Date of trigger event")
    case_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context (case_type, motion_type, etc.)"
    )


class DeadlineCalculationResponse(BaseModel):
    """Response with calculated deadlines"""
    trigger_type: str
    trigger_date: date
    jurisdiction_id: str
    rules_applied: int
    deadlines: List[CalculatedDeadline]
    warnings: Optional[List[str]] = None
