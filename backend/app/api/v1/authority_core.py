"""
Authority Core API Endpoints

Provides endpoints for:
- Web scraping pipeline for rule extraction
- Rule proposal management (review, approve, reject)
- Rules database queries for deadline calculation
- Conflict detection and resolution
"""
import logging
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio

from app.database import get_db
from app.utils.auth import get_current_user
from app.models.user import User
from app.models.jurisdiction import Jurisdiction
from app.models.authority_core import (
    AuthorityRule,
    ScrapeJob,
    RuleProposal,
    RuleConflict
)
from app.models.enums import (
    ProposalStatus,
    ScrapeStatus,
    ConflictResolution
)
from app.schemas.authority_core import (
    AuthorityRuleCreate,
    AuthorityRuleUpdate,
    AuthorityRuleResponse,
    AuthorityRuleSearchResult,
    ScrapeRequest,
    ScrapeProgress,
    ScrapeJobResponse,
    RuleProposalCreate,
    RuleProposalResponse,
    ProposalApprovalRequest,
    ProposalRejectionRequest,
    ProposalRevisionRequest,
    RuleConflictResponse,
    ConflictResolutionRequest,
    RuleUsageResponse,
    DeadlineCalculationRequest,
    DeadlineCalculationResponse,
    ProposalStatusEnum,
    ScrapeStatusEnum,
    ConflictResolutionEnum,
    # RuleHarvester-2 enhanced schemas
    ScrapeUrlRequest,
    ScrapeUrlResponse,
    ExtractEnhancedRequest,
    ExtractEnhancedResponse,
    ExtractedRuleResponse,
    ExtractedDeadlineSpec,
    RelatedRuleSpec,
    DetectConflictsRequest,
    DetectConflictsResponse,
    DetectedConflictResponse,
)
from app.services.authority_core_service import AuthorityCoreService
from app.services.rule_extraction_service import (
    ExtractedRuleData,
    ExtractedDeadline,
    rule_extraction_service,
    ScrapedContent,
    DetectedConflict,
    RelatedRule
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/authority-core", tags=["Authority Core"])


# ============================================================
# Helper Functions
# ============================================================

def get_authority_service(db: Session = Depends(get_db)) -> AuthorityCoreService:
    """Dependency to get AuthorityCoreService instance"""
    return AuthorityCoreService(db)


def rule_to_response(rule: AuthorityRule, jurisdiction: Optional[Jurisdiction] = None) -> dict:
    """Convert AuthorityRule model to response dict"""
    return {
        "id": rule.id,
        "jurisdiction_id": rule.jurisdiction_id,
        "jurisdiction_name": jurisdiction.name if jurisdiction else None,
        "user_id": rule.user_id,
        "rule_code": rule.rule_code,
        "rule_name": rule.rule_name,
        "trigger_type": rule.trigger_type,
        "authority_tier": rule.authority_tier.value if rule.authority_tier else "state",
        "citation": rule.citation,
        "source_url": rule.source_url,
        "source_text": rule.source_text,
        "deadlines": rule.deadlines or [],
        "conditions": rule.conditions,
        "service_extensions": rule.service_extensions,
        "confidence_score": float(rule.confidence_score) if rule.confidence_score else 0.0,
        "is_verified": rule.is_verified,
        "verified_by": rule.verified_by,
        "verified_at": rule.verified_at,
        "is_active": rule.is_active,
        "effective_date": rule.effective_date,
        "superseded_date": rule.superseded_date,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
        "usage_count": 0  # TODO: Calculate from usage table
    }


def proposal_to_response(proposal: RuleProposal, jurisdiction: Optional[Jurisdiction] = None) -> dict:
    """Convert RuleProposal model to response dict"""
    return {
        "id": proposal.id,
        "user_id": proposal.user_id,
        "scrape_job_id": proposal.scrape_job_id,
        "jurisdiction_id": proposal.jurisdiction_id,
        "jurisdiction_name": jurisdiction.name if jurisdiction else None,
        "proposed_rule_data": proposal.proposed_rule_data,
        "source_url": proposal.source_url,
        "source_text": proposal.source_text,
        "confidence_score": float(proposal.confidence_score) if proposal.confidence_score else 0.0,
        "extraction_notes": proposal.extraction_notes,
        "status": proposal.status.value if proposal.status else "pending",
        "reviewed_by": proposal.reviewed_by,
        "reviewer_notes": proposal.reviewer_notes,
        "approved_rule_id": proposal.approved_rule_id,
        "created_at": proposal.created_at,
        "reviewed_at": proposal.reviewed_at
    }


def job_to_response(job: ScrapeJob, jurisdiction: Optional[Jurisdiction] = None) -> dict:
    """Convert ScrapeJob model to response dict"""
    return {
        "id": job.id,
        "user_id": job.user_id,
        "jurisdiction_id": job.jurisdiction_id,
        "jurisdiction_name": jurisdiction.name if jurisdiction else None,
        "search_query": job.search_query,
        "status": job.status.value if job.status else "queued",
        "progress_pct": job.progress_pct or 0,
        "rules_found": job.rules_found or 0,
        "proposals_created": job.proposals_created or 0,
        "urls_processed": job.urls_processed or [],
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }


def conflict_to_response(conflict: RuleConflict, db: Session) -> dict:
    """Convert RuleConflict model to response dict"""
    rule_a = db.query(AuthorityRule).filter(AuthorityRule.id == conflict.rule_a_id).first()
    rule_b = db.query(AuthorityRule).filter(AuthorityRule.id == conflict.rule_b_id).first()

    return {
        "id": conflict.id,
        "rule_a_id": conflict.rule_a_id,
        "rule_a_name": rule_a.rule_name if rule_a else None,
        "rule_a_citation": rule_a.citation if rule_a else None,
        "rule_b_id": conflict.rule_b_id,
        "rule_b_name": rule_b.rule_name if rule_b else None,
        "rule_b_citation": rule_b.citation if rule_b else None,
        "conflict_type": conflict.conflict_type,
        "severity": conflict.severity,
        "description": conflict.description,
        "resolution": conflict.resolution.value if conflict.resolution else "pending",
        "resolution_notes": conflict.resolution_notes,
        "resolved_by": conflict.resolved_by,
        "resolved_at": conflict.resolved_at,
        "created_at": conflict.created_at
    }


# ============================================================
# Scraping Endpoints
# ============================================================

@router.post("/scrape", response_model=ScrapeJobResponse)
async def start_scrape(
    request: ScrapeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Start a new scraping job for rule extraction.

    This creates a job record. Use the /scrape/{job_id}/process endpoint
    to actually process content and extract rules.
    """
    # Verify jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == request.jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    job = await service.start_scrape(
        jurisdiction_id=request.jurisdiction_id,
        search_query=request.search_query,
        user_id=str(current_user.id)
    )

    return job_to_response(job, jurisdiction)


@router.post("/scrape/{job_id}/process")
async def process_scrape_job(
    job_id: str,
    content: str = Query(..., description="The content to extract rules from"),
    source_url: Optional[str] = Query(None, description="Source URL of the content"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Process a scrape job with provided content.

    Returns a streaming response with progress updates.
    """
    job = service.get_scrape_job(job_id, str(current_user.id))
    if not job:
        raise HTTPException(status_code=404, detail="Scrape job not found")

    async def event_generator():
        async for progress in service.process_scrape_job(job_id, content, source_url):
            yield f"data: {json.dumps({
                'job_id': progress.job_id,
                'status': progress.status.value,
                'progress_pct': progress.progress_pct,
                'message': progress.message,
                'urls_processed': progress.urls_processed,
                'rules_found': progress.rules_found,
                'current_action': progress.current_action
            })}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.get("/scrape/{job_id}", response_model=ScrapeJobResponse)
async def get_scrape_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """Get a specific scrape job"""
    job = service.get_scrape_job(job_id, str(current_user.id))
    if not job:
        raise HTTPException(status_code=404, detail="Scrape job not found")

    jurisdiction = None
    if job.jurisdiction_id:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == job.jurisdiction_id
        ).first()

    return job_to_response(job, jurisdiction)


@router.get("/jobs", response_model=List[ScrapeJobResponse])
async def list_scrape_jobs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """List scrape jobs for the current user"""
    jobs = service.list_scrape_jobs(str(current_user.id), limit, offset)

    # Get jurisdictions for all jobs
    jurisdiction_ids = [j.jurisdiction_id for j in jobs if j.jurisdiction_id]
    jurisdictions = {
        j.id: j for j in db.query(Jurisdiction).filter(
            Jurisdiction.id.in_(jurisdiction_ids)
        ).all()
    } if jurisdiction_ids else {}

    return [
        job_to_response(job, jurisdictions.get(job.jurisdiction_id))
        for job in jobs
    ]


# ============================================================
# Proposal Endpoints
# ============================================================

@router.get("/proposals", response_model=List[RuleProposalResponse])
async def list_proposals(
    status: Optional[ProposalStatusEnum] = None,
    jurisdiction_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """List rule proposals for the current user"""
    # Convert enum if provided
    status_filter = None
    if status:
        status_map = {
            ProposalStatusEnum.PENDING: ProposalStatus.PENDING,
            ProposalStatusEnum.APPROVED: ProposalStatus.APPROVED,
            ProposalStatusEnum.REJECTED: ProposalStatus.REJECTED,
            ProposalStatusEnum.NEEDS_REVISION: ProposalStatus.NEEDS_REVISION
        }
        status_filter = status_map.get(status)

    proposals = service.list_proposals(
        user_id=str(current_user.id),
        status=status_filter,
        jurisdiction_id=jurisdiction_id,
        limit=limit,
        offset=offset
    )

    # Get jurisdictions
    jurisdiction_ids = [p.jurisdiction_id for p in proposals if p.jurisdiction_id]
    jurisdictions = {
        j.id: j for j in db.query(Jurisdiction).filter(
            Jurisdiction.id.in_(jurisdiction_ids)
        ).all()
    } if jurisdiction_ids else {}

    return [
        proposal_to_response(p, jurisdictions.get(p.jurisdiction_id))
        for p in proposals
    ]


@router.get("/proposals/{proposal_id}", response_model=RuleProposalResponse)
async def get_proposal(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """Get a specific proposal"""
    proposal = service.get_proposal(proposal_id, str(current_user.id))
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    jurisdiction = None
    if proposal.jurisdiction_id:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == proposal.jurisdiction_id
        ).first()

    return proposal_to_response(proposal, jurisdiction)


@router.post("/proposals/{proposal_id}/approve", response_model=AuthorityRuleResponse)
async def approve_proposal(
    proposal_id: str,
    request: Optional[ProposalApprovalRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Approve a proposal and create an AuthorityRule.

    Optionally provide modifications to the proposed rule data.
    """
    try:
        modifications = None
        notes = None
        if request:
            if request.modifications:
                modifications = request.modifications.model_dump()
            notes = request.notes

        rule = await service.approve_proposal(
            proposal_id=proposal_id,
            user_id=str(current_user.id),
            modifications=modifications,
            notes=notes
        )

        jurisdiction = None
        if rule.jurisdiction_id:
            jurisdiction = db.query(Jurisdiction).filter(
                Jurisdiction.id == rule.jurisdiction_id
            ).first()

        return rule_to_response(rule, jurisdiction)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    request: ProposalRejectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """Reject a proposal"""
    try:
        await service.reject_proposal(
            proposal_id=proposal_id,
            user_id=str(current_user.id),
            reason=request.reason
        )
        return {"success": True, "message": "Proposal rejected"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/proposals/{proposal_id}/request-revision")
async def request_revision(
    proposal_id: str,
    request: ProposalRevisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """Mark a proposal as needing revision"""
    try:
        await service.request_revision(
            proposal_id=proposal_id,
            user_id=str(current_user.id),
            notes=request.notes
        )
        return {"success": True, "message": "Revision requested"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Rules Database Endpoints
# ============================================================

@router.get("/rules", response_model=List[AuthorityRuleResponse])
async def list_rules(
    jurisdiction_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    verified_only: bool = True,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """List rules from the Authority Core database"""
    rules = service.list_rules(
        jurisdiction_id=jurisdiction_id,
        trigger_type=trigger_type,
        verified_only=verified_only,
        limit=limit,
        offset=offset
    )

    # Get jurisdictions
    jurisdiction_ids = [r.jurisdiction_id for r in rules if r.jurisdiction_id]
    jurisdictions = {
        j.id: j for j in db.query(Jurisdiction).filter(
            Jurisdiction.id.in_(jurisdiction_ids)
        ).all()
    } if jurisdiction_ids else {}

    return [
        rule_to_response(r, jurisdictions.get(r.jurisdiction_id))
        for r in rules
    ]


@router.get("/rules/search", response_model=List[AuthorityRuleResponse])
async def search_rules(
    q: str = Query(..., min_length=2, description="Search query"),
    jurisdiction_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """Search rules by keyword"""
    rules = await service.search_rules(
        query=q,
        jurisdiction_id=jurisdiction_id,
        trigger_type=trigger_type,
        limit=limit
    )

    # Get jurisdictions
    jurisdiction_ids = [r.jurisdiction_id for r in rules if r.jurisdiction_id]
    jurisdictions = {
        j.id: j for j in db.query(Jurisdiction).filter(
            Jurisdiction.id.in_(jurisdiction_ids)
        ).all()
    } if jurisdiction_ids else {}

    return [
        rule_to_response(r, jurisdictions.get(r.jurisdiction_id))
        for r in rules
    ]


@router.get("/rules/{rule_id}", response_model=AuthorityRuleResponse)
async def get_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """Get a specific rule by ID"""
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    jurisdiction = None
    if rule.jurisdiction_id:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == rule.jurisdiction_id
        ).first()

    return rule_to_response(rule, jurisdiction)


@router.patch("/rules/{rule_id}", response_model=AuthorityRuleResponse)
async def update_rule(
    rule_id: str,
    request: AuthorityRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a rule (requires ownership)"""
    # SECURITY: Always filter by user_id to prevent IDOR
    rule = db.query(AuthorityRule).filter(
        AuthorityRule.id == rule_id,
        AuthorityRule.user_id == str(current_user.id)
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Update fields if provided
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "deadlines" and value is not None:
            # Convert DeadlineSpec objects to dicts
            value = [d.model_dump() if hasattr(d, 'model_dump') else d for d in value]
        if field == "conditions" and value is not None:
            value = value.model_dump() if hasattr(value, 'model_dump') else value
        if field == "service_extensions" and value is not None:
            value = value.model_dump() if hasattr(value, 'model_dump') else value
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)

    jurisdiction = None
    if rule.jurisdiction_id:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == rule.jurisdiction_id
        ).first()

    return rule_to_response(rule, jurisdiction)


@router.delete("/rules/{rule_id}")
async def deactivate_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate a rule (soft delete, requires ownership)"""
    # SECURITY: Always filter by user_id to prevent IDOR
    rule = db.query(AuthorityRule).filter(
        AuthorityRule.id == rule_id,
        AuthorityRule.user_id == str(current_user.id)
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.is_active = False
    db.commit()

    return {"success": True, "message": "Rule deactivated"}


# ============================================================
# Deadline Calculation Endpoints
# ============================================================

@router.post("/calculate-deadlines", response_model=DeadlineCalculationResponse)
async def calculate_deadlines(
    request: DeadlineCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Calculate deadlines using Authority Core rules.

    This endpoint queries the Authority Core database for matching rules
    and calculates deadlines based on the trigger type and date.
    """
    # Verify jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == request.jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    deadlines = await service.calculate_deadlines(
        jurisdiction_id=request.jurisdiction_id,
        trigger_type=request.trigger_type,
        trigger_date=request.trigger_date,
        case_context=request.case_context
    )

    return DeadlineCalculationResponse(
        trigger_type=request.trigger_type,
        trigger_date=request.trigger_date,
        jurisdiction_id=request.jurisdiction_id,
        rules_applied=len(set(d.source_rule_id for d in deadlines)),
        deadlines=deadlines,
        warnings=None
    )


# ============================================================
# Conflict Endpoints
# ============================================================

@router.get("/conflicts", response_model=List[RuleConflictResponse])
async def list_conflicts(
    resolution: Optional[ConflictResolutionEnum] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """List rule conflicts"""
    # Convert enum if provided
    resolution_filter = None
    if resolution:
        resolution_map = {
            ConflictResolutionEnum.PENDING: ConflictResolution.PENDING,
            ConflictResolutionEnum.USE_HIGHER_TIER: ConflictResolution.USE_HIGHER_TIER,
            ConflictResolutionEnum.USE_RULE_A: ConflictResolution.USE_RULE_A,
            ConflictResolutionEnum.USE_RULE_B: ConflictResolution.USE_RULE_B,
            ConflictResolutionEnum.MANUAL: ConflictResolution.MANUAL,
            ConflictResolutionEnum.IGNORED: ConflictResolution.IGNORED
        }
        resolution_filter = resolution_map.get(resolution)

    conflicts = service.list_conflicts(
        resolution=resolution_filter,
        limit=limit,
        offset=offset
    )

    return [conflict_to_response(c, db) for c in conflicts]


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    request: ConflictResolutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """Resolve a conflict between rules"""
    # Convert enum
    resolution_map = {
        ConflictResolutionEnum.PENDING: ConflictResolution.PENDING,
        ConflictResolutionEnum.USE_HIGHER_TIER: ConflictResolution.USE_HIGHER_TIER,
        ConflictResolutionEnum.USE_RULE_A: ConflictResolution.USE_RULE_A,
        ConflictResolutionEnum.USE_RULE_B: ConflictResolution.USE_RULE_B,
        ConflictResolutionEnum.MANUAL: ConflictResolution.MANUAL,
        ConflictResolutionEnum.IGNORED: ConflictResolution.IGNORED
    }
    resolution = resolution_map.get(request.resolution, ConflictResolution.MANUAL)

    try:
        await service.resolve_conflict(
            conflict_id=conflict_id,
            resolution=resolution,
            user_id=str(current_user.id),
            notes=request.notes
        )
        return {"success": True, "message": "Conflict resolved"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Manual Rule Creation
# ============================================================

@router.post("/rules", response_model=AuthorityRuleResponse)
async def create_rule(
    request: AuthorityRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually create a new AuthorityRule.

    This bypasses the proposal workflow for direct rule creation.
    """
    # Verify jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == request.jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    # Map authority tier
    from app.models.enums import AuthorityTier
    tier_map = {
        "federal": AuthorityTier.FEDERAL,
        "state": AuthorityTier.STATE,
        "local": AuthorityTier.LOCAL,
        "standing_order": AuthorityTier.STANDING_ORDER,
        "firm": AuthorityTier.FIRM
    }
    authority_tier = tier_map.get(request.authority_tier.value, AuthorityTier.STATE)

    import uuid
    from datetime import datetime

    rule = AuthorityRule(
        id=str(uuid.uuid4()),
        user_id=str(current_user.id),
        jurisdiction_id=request.jurisdiction_id,
        authority_tier=authority_tier,
        rule_code=request.rule_code,
        rule_name=request.rule_name,
        trigger_type=request.trigger_type,
        citation=request.citation,
        source_url=request.source_url,
        source_text=request.source_text,
        deadlines=[d.model_dump() for d in request.deadlines],
        conditions=request.conditions.model_dump() if request.conditions else None,
        service_extensions=request.service_extensions.model_dump() if request.service_extensions else {
            "mail": 3, "electronic": 0, "personal": 0
        },
        confidence_score=1.0,  # Manual creation = high confidence
        is_verified=True,
        verified_by=str(current_user.id),
        verified_at=datetime.utcnow(),
        is_active=True,
        effective_date=request.effective_date
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return rule_to_response(rule, jurisdiction)


# ============================================================
# RuleHarvester-2 Enhanced Endpoints
# ============================================================

@router.post("/scrape-url", response_model=ScrapeUrlResponse)
async def scrape_url_content(
    request: ScrapeUrlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Scrape and clean legal content from a court URL.

    Uses Claude to extract clean legal text from the URL, filtering out
    navigation, sidebars, footers, and other UI noise. Returns the cleaned
    text along with a content hash for change detection.

    This is the first step in the RuleHarvester-2 pipeline:
    1. scrape-url → Get clean legal text
    2. extract-enhanced → Extract rules with extended thinking
    3. detect-conflicts → Check for conflicts with cited authorities
    """
    # Verify jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == request.jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    try:
        scraped = await rule_extraction_service.scrape_url_content(request.url)
        return ScrapeUrlResponse(
            raw_text=scraped.raw_text,
            content_hash=scraped.content_hash,
            source_urls=scraped.source_urls
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"URL scraping failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to scrape URL content")


@router.post("/extract-enhanced", response_model=ExtractEnhancedResponse)
async def extract_with_extended_thinking(
    request: ExtractEnhancedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Extract rules from text using Claude's extended thinking.

    Uses extended thinking (chain-of-thought) for complex rule extraction,
    providing transparency into the extraction reasoning. This improves
    accuracy for complex rules with multiple conditions or references.

    Returns extracted rules with:
    - extraction_reasoning: Chain-of-thought from extended thinking
    - related_rules: Citations to other rules referenced
    - confidence_score: Calculated confidence in the extraction
    """
    # Verify jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == request.jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    try:
        if request.use_extended_thinking:
            extracted_rules = await rule_extraction_service.extract_with_extended_thinking(
                content=request.text,
                jurisdiction_name=jurisdiction.name,
                source_url=request.source_url
            )
        else:
            extracted_rules = await rule_extraction_service.extract_from_content(
                content=request.text,
                jurisdiction_name=jurisdiction.name,
                source_url=request.source_url
            )

        # Convert to response format
        rules_response = []
        for rule in extracted_rules:
            rules_response.append(ExtractedRuleResponse(
                rule_code=rule.rule_code,
                rule_name=rule.rule_name,
                trigger_type=rule.trigger_type,
                authority_tier=rule.authority_tier,
                citation=rule.citation,
                source_url=rule.source_url,
                source_text=rule.source_text,
                deadlines=[
                    ExtractedDeadlineSpec(
                        title=d.title,
                        days_from_trigger=d.days_from_trigger,
                        calculation_method=d.calculation_method,
                        priority=d.priority,
                        party_responsible=d.party_responsible,
                        conditions=d.conditions,
                        description=d.description
                    )
                    for d in rule.deadlines
                ],
                conditions=rule.conditions,
                service_extensions=rule.service_extensions,
                confidence_score=rule.confidence_score,
                extraction_notes=rule.extraction_notes,
                related_rules=[
                    RelatedRuleSpec(citation=r.citation, purpose=r.purpose)
                    for r in rule.related_rules
                ],
                extraction_reasoning=rule.extraction_reasoning
            ))

        return ExtractEnhancedResponse(
            rules=rules_response,
            total_rules_found=len(rules_response),
            used_extended_thinking=request.use_extended_thinking
        )

    except Exception as e:
        logger.error(f"Enhanced extraction failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract rules")


@router.post("/detect-conflicts", response_model=DetectConflictsResponse)
async def detect_authority_conflicts(
    request: DetectConflictsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Detect conflicts between a proposal and cited authority.

    Cross-references the extracted rule in a proposal against the cited
    authority (e.g., FRCP 6) to identify any contradictions or discrepancies.
    Returns AI-generated resolution recommendations.

    Use this after extraction to verify the rule doesn't conflict with
    higher-tier authorities before approval.
    """
    # Get the proposal
    proposal = service.get_proposal(request.proposal_id, str(current_user.id))
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Extract rule data from proposal
    rule_data = proposal.proposed_rule_data
    if not rule_data:
        raise HTTPException(status_code=400, detail="Proposal has no rule data")

    # Convert proposal data to ExtractedRuleData for conflict detection
    try:
        deadlines = [
            ExtractedDeadline(
                title=d.get("title", ""),
                days_from_trigger=d.get("days_from_trigger", 0),
                calculation_method=d.get("calculation_method", "calendar_days"),
                priority=d.get("priority", "standard"),
                party_responsible=d.get("party_responsible"),
                conditions=d.get("conditions"),
                description=d.get("description")
            )
            for d in rule_data.get("deadlines", [])
        ]

        extracted_rule = ExtractedRuleData(
            rule_code=rule_data.get("rule_code", "UNKNOWN"),
            rule_name=rule_data.get("rule_name", "Unknown Rule"),
            trigger_type=rule_data.get("trigger_type", "custom_trigger"),
            authority_tier=rule_data.get("authority_tier", "state"),
            citation=rule_data.get("citation", ""),
            source_url=proposal.source_url,
            source_text=proposal.source_text or "",
            deadlines=deadlines,
            conditions=rule_data.get("conditions"),
            service_extensions=rule_data.get("service_extensions")
        )

        # Run conflict detection
        conflicts = await rule_extraction_service.detect_authority_conflicts(
            rule=extracted_rule,
            authority_citation=request.authority_citation
        )

        return DetectConflictsResponse(
            proposal_id=request.proposal_id,
            authority_citation=request.authority_citation,
            conflicts_found=len(conflicts),
            conflicts=[
                DetectedConflictResponse(
                    rule_a=c.rule_a,
                    rule_b=c.rule_b,
                    discrepancy=c.discrepancy,
                    ai_resolution_recommendation=c.ai_resolution_recommendation
                )
                for c in conflicts
            ]
        )

    except Exception as e:
        logger.error(f"Conflict detection failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect conflicts")
