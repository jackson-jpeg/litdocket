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

class DeadlineServiceExtensions(BaseModel):
    """
    Per-deadline service extension overrides.

    When specified, these override the rule-level service_extensions for this
    specific deadline. Useful for deadlines that have different service rules
    than the default (e.g., statutory deadlines that don't allow extensions).
    """
    mail: Optional[int] = Field(None, description="Additional days for mail service (None = use rule default)")
    electronic: Optional[int] = Field(None, description="Additional days for electronic service (None = use rule default)")
    personal: Optional[int] = Field(None, description="Additional days for personal service (None = use rule default)")
    no_extensions: bool = Field(False, description="If true, no service extensions apply to this deadline")


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
    service_extensions: Optional[DeadlineServiceExtensions] = Field(
        None,
        description="Per-deadline service extension overrides. If None, uses rule-level defaults."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Response to Motion Due",
                "days_from_trigger": 14,
                "calculation_method": "calendar_days",
                "priority": "important",
                "party_responsible": "opposing",
                "conditions": {"motion_type": "dispositive"},
                "service_extensions": {"no_extensions": False, "mail": 5}
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
# BATCH OPERATION SCHEMAS
# =============================================================

class BatchApproveRequest(BaseModel):
    """Request to batch approve multiple proposals"""
    proposal_ids: List[str] = Field(..., min_length=1, description="List of proposal IDs to approve")
    notes: Optional[str] = Field(None, description="Optional notes for all approvals")


class BatchRejectRequest(BaseModel):
    """Request to batch reject multiple proposals"""
    proposal_ids: List[str] = Field(..., min_length=1, description="List of proposal IDs to reject")
    reason: str = Field(..., min_length=10, description="Reason for rejection")


class BatchOperationResult(BaseModel):
    """Result of a single operation in a batch"""
    proposal_id: str
    success: bool
    message: Optional[str] = None
    rule_id: Optional[str] = None  # For approvals, the created rule ID


class BatchOperationResponse(BaseModel):
    """Response for batch operations"""
    total_requested: int
    successful: int
    failed: int
    results: List[BatchOperationResult]


# =============================================================
# ANALYTICS SCHEMAS
# =============================================================

class RuleUsageStats(BaseModel):
    """Usage statistics for a single rule"""
    rule_id: str
    rule_name: str
    rule_code: str
    jurisdiction_name: Optional[str] = None
    usage_count: int
    deadlines_generated: int


class JurisdictionStats(BaseModel):
    """Statistics for a jurisdiction"""
    jurisdiction_id: str
    jurisdiction_name: str
    rule_count: int
    verified_count: int
    pending_proposals: int


class TierStats(BaseModel):
    """Statistics for an authority tier"""
    tier: str
    rule_count: int
    usage_count: int


class ProposalStats(BaseModel):
    """Proposal approval/rejection statistics"""
    total_proposals: int
    pending: int
    approved: int
    rejected: int
    needs_revision: int
    approval_rate: float  # Percentage


class ConflictStats(BaseModel):
    """Conflict resolution statistics"""
    total_conflicts: int
    pending: int
    auto_resolved: int
    manually_resolved: int
    ignored: int


class AnalyticsResponse(BaseModel):
    """Complete analytics response"""
    most_used_rules: List[RuleUsageStats]
    rules_by_jurisdiction: List[JurisdictionStats]
    rules_by_tier: List[TierStats]
    proposal_stats: ProposalStats
    conflict_stats: ConflictStats
    total_rules: int
    total_verified_rules: int


# =============================================================
# IMPORT/EXPORT SCHEMAS
# =============================================================

class RuleExportData(BaseModel):
    """Data format for exporting a rule"""
    rule_code: str
    rule_name: str
    trigger_type: str
    authority_tier: str
    citation: Optional[str] = None
    source_url: Optional[str] = None
    source_text: Optional[str] = None
    deadlines: List[Dict[str, Any]]
    conditions: Optional[Dict[str, Any]] = None
    service_extensions: Optional[Dict[str, int]] = None
    effective_date: Optional[str] = None


class RulesExportResponse(BaseModel):
    """Response for rules export"""
    export_version: str = "1.0"
    exported_at: datetime
    jurisdiction_id: Optional[str] = None
    jurisdiction_name: Optional[str] = None
    rule_count: int
    rules: List[RuleExportData]


class RulesImportRequest(BaseModel):
    """Request to import rules"""
    jurisdiction_id: str = Field(..., description="Target jurisdiction for imported rules")
    rules: List[RuleExportData] = Field(..., min_length=1, description="Rules to import")
    create_as_proposals: bool = Field(True, description="If true, create as proposals for review. If false, create as verified rules.")
    skip_duplicates: bool = Field(True, description="Skip rules with matching rule_code")


class ImportResult(BaseModel):
    """Result of importing a single rule"""
    rule_code: str
    success: bool
    message: str
    proposal_id: Optional[str] = None
    rule_id: Optional[str] = None


class RulesImportResponse(BaseModel):
    """Response for rules import"""
    total_requested: int
    imported: int
    skipped: int
    failed: int
    results: List[ImportResult]


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


# =============================================================
# RULEHARVESTER-2 ENHANCED SCHEMAS
# =============================================================

class ScrapeUrlRequest(BaseModel):
    """Request to scrape legal content from a URL"""
    url: str = Field(..., description="The URL to scrape (e.g., court rules page)")
    jurisdiction_id: str = Field(..., description="Jurisdiction this URL belongs to")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.flsd.uscourts.gov/local-rules",
                "jurisdiction_id": "sdfl-uuid"
            }
        }


class ScrapeUrlResponse(BaseModel):
    """Response from URL scraping"""
    raw_text: str = Field(..., description="Clean legal text with navigation filtered out")
    content_hash: str = Field(..., description="Hash of first 1000 chars for change detection")
    source_urls: List[str] = Field(..., description="Source URLs for the content")

    class Config:
        json_schema_extra = {
            "example": {
                "raw_text": "LOCAL RULE 7.1 MOTIONS GENERALLY\n(a) Time Periods...",
                "content_hash": "a1b2c3d4e5f6g7h8",
                "source_urls": ["https://www.flsd.uscourts.gov/local-rules"]
            }
        }


class RelatedRuleSpec(BaseModel):
    """A citation to another related rule"""
    citation: str = Field(..., description="The rule citation (e.g., FRCP 6(a))")
    purpose: str = Field(..., description="Why the rule is referenced")


class ExtractedDeadlineSpec(BaseModel):
    """Deadline specification from extraction"""
    title: str
    days_from_trigger: int
    calculation_method: str
    priority: str
    party_responsible: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class ExtractEnhancedRequest(BaseModel):
    """Request for enhanced extraction with extended thinking"""
    text: str = Field(..., description="The text content to extract rules from")
    jurisdiction_id: str = Field(..., description="Jurisdiction for context")
    source_url: Optional[str] = Field(None, description="Source URL of the content")
    use_extended_thinking: bool = Field(
        True,
        description="Whether to use extended thinking for complex extraction"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "LOCAL RULE 7.1 MOTIONS GENERALLY\n(a) Time Periods...",
                "jurisdiction_id": "sdfl-uuid",
                "source_url": "https://www.flsd.uscourts.gov/local-rules",
                "use_extended_thinking": True
            }
        }


class ExtractedRuleResponse(BaseModel):
    """Response for an extracted rule with RuleHarvester-2 enhancements"""
    rule_code: str
    rule_name: str
    trigger_type: str
    authority_tier: str
    citation: str
    source_url: Optional[str]
    source_text: str
    deadlines: List[ExtractedDeadlineSpec]
    conditions: Optional[Dict[str, Any]] = None
    service_extensions: Optional[Dict[str, int]] = None
    confidence_score: float
    extraction_notes: Optional[str] = None
    # RuleHarvester-2 enhancements
    related_rules: List[RelatedRuleSpec] = []
    extraction_reasoning: List[str] = []


class ExtractEnhancedResponse(BaseModel):
    """Response from enhanced extraction"""
    rules: List[ExtractedRuleResponse]
    total_rules_found: int
    used_extended_thinking: bool

    class Config:
        json_schema_extra = {
            "example": {
                "rules": [],
                "total_rules_found": 3,
                "used_extended_thinking": True
            }
        }


class DetectConflictsRequest(BaseModel):
    """Request to detect conflicts between a proposal and cited authority"""
    proposal_id: str = Field(..., description="The proposal ID to check for conflicts")
    authority_citation: str = Field(
        ...,
        description="The authority to check against (e.g., 'FRCP 6')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "proposal_id": "proposal-uuid",
                "authority_citation": "FRCP 6(a)"
            }
        }


class DetectedConflictResponse(BaseModel):
    """A detected conflict between rules"""
    rule_a: str = Field(..., description="Citation of the extracted/local rule")
    rule_b: str = Field(..., description="Citation of the authority being checked")
    discrepancy: str = Field(..., description="Description of the conflict")
    ai_resolution_recommendation: str = Field(
        ...,
        description="AI-generated recommendation for resolving the conflict"
    )


class DetectConflictsResponse(BaseModel):
    """Response from conflict detection"""
    proposal_id: str
    authority_citation: str
    conflicts_found: int
    conflicts: List[DetectedConflictResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "proposal_id": "proposal-uuid",
                "authority_citation": "FRCP 6(a)",
                "conflicts_found": 1,
                "conflicts": [{
                    "rule_a": "S.D. Fla. L.R. 7.1(a)",
                    "rule_b": "FRCP 6(a)",
                    "discrepancy": "Local rule specifies 14 calendar days but does not account for FRCP 6(a) weekend/holiday extension",
                    "ai_resolution_recommendation": "Apply FRCP 6(a) extension rules when deadline falls on weekend/holiday"
                }]
            }
        }


# =============================================================
# AUTO-HARVEST SCHEMAS (End-to-end rule extraction)
# =============================================================

class HarvestRequest(BaseModel):
    """Request to harvest rules from a URL automatically"""
    url: str = Field(..., description="URL to scrape for court rules")
    jurisdiction_id: str = Field(..., description="Target jurisdiction")
    use_extended_thinking: bool = Field(
        True,
        description="Use extended thinking for complex rule extraction"
    )
    auto_approve_high_confidence: bool = Field(
        False,
        description="Auto-approve rules with confidence >= 0.85"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.flmd.uscourts.gov/local-rules",
                "jurisdiction_id": "jurisdiction-uuid",
                "use_extended_thinking": True,
                "auto_approve_high_confidence": False
            }
        }


class DiscoverUrlsRequest(BaseModel):
    """Request to discover court rule URLs for a jurisdiction"""
    jurisdiction_id: str = Field(..., description="Jurisdiction to find rules for")
    search_query: Optional[str] = Field(
        None,
        description="Optional specific search query (e.g., 'motion deadlines')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "jurisdiction_id": "jurisdiction-uuid",
                "search_query": "local rules civil procedure"
            }
        }


class DiscoveredUrl(BaseModel):
    """A discovered URL that may contain court rules"""
    url: str
    title: str
    description: str
    confidence: float = Field(..., ge=0, le=1, description="Confidence this URL contains rules")
    source: str = Field(..., description="How URL was discovered (web_search, known_pattern)")


class DiscoverUrlsResponse(BaseModel):
    """Response with discovered URLs"""
    jurisdiction_id: str
    jurisdiction_name: str
    urls: List[DiscoveredUrl]
    search_query_used: str


class HarvestProgressEvent(BaseModel):
    """Progress event during harvesting"""
    job_id: str
    status: str
    progress_pct: int
    phase: str  # "scraping", "extracting", "creating_proposals", "completed", "failed"
    message: str
    url: Optional[str] = None
    rules_found: int = 0
    proposals_created: int = 0
    errors: List[str] = []


class HarvestedRule(BaseModel):
    """A rule that was harvested"""
    proposal_id: str
    rule_code: str
    rule_name: str
    trigger_type: str
    citation: Optional[str]
    deadlines_count: int
    confidence_score: float
    auto_approved: bool = False
    extraction_reasoning: List[str] = []


class HarvestResponse(BaseModel):
    """Complete response from a harvest operation"""
    job_id: str
    status: str
    jurisdiction_id: str
    jurisdiction_name: str
    url: str
    content_hash: str
    rules_found: int
    proposals_created: int
    rules: List[HarvestedRule]
    errors: List[str] = []
    processing_time_ms: int

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job-uuid",
                "status": "completed",
                "jurisdiction_id": "jurisdiction-uuid",
                "jurisdiction_name": "U.S. District Court - Middle District of Florida",
                "url": "https://www.flmd.uscourts.gov/local-rules",
                "content_hash": "a1b2c3d4",
                "rules_found": 15,
                "proposals_created": 15,
                "rules": [],
                "errors": [],
                "processing_time_ms": 45000
            }
        }


class BatchHarvestRequest(BaseModel):
    """Request to harvest rules from multiple URLs"""
    urls: List[str] = Field(..., min_length=1, max_length=10, description="URLs to harvest")
    jurisdiction_id: str = Field(..., description="Target jurisdiction")
    use_extended_thinking: bool = True
    auto_approve_high_confidence: bool = False


class BatchHarvestResponse(BaseModel):
    """Response from batch harvesting"""
    job_id: str
    total_urls: int
    completed_urls: int
    failed_urls: int
    total_rules_found: int
    total_proposals_created: int
    results: List[HarvestResponse]
