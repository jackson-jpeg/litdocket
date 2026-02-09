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
    RuleConflict,
    AuthorityRuleUsage
)
from sqlalchemy import func as sql_func, Integer
from app.models.enums import (
    ProposalStatus,
    ScrapeStatus,
    ConflictResolution
)
from app.config import settings
from datetime import datetime
import uuid
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
    # Auto-harvest schemas
    HarvestRequest,
    HarvestResponse,
    HarvestedRule,
    HarvestProgressEvent,
    DiscoverUrlsRequest,
    DiscoverUrlsResponse,
    DiscoveredUrl,
    BatchHarvestRequest,
    BatchHarvestResponse,
    # Batch operations schemas
    BatchApproveRequest,
    BatchRejectRequest,
    BatchOperationResult,
    BatchOperationResponse,
    # Analytics schemas
    AnalyticsResponse,
    RuleUsageStats,
    JurisdictionStats,
    TierStats,
    ProposalStats,
    ConflictStats,
    # Import/Export schemas
    RulesExportResponse,
    RuleExportData,
    RulesImportRequest,
    RulesImportResponse,
    ImportResult,
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


def rule_to_response(rule: AuthorityRule, jurisdiction: Optional[Jurisdiction] = None, usage_count: int = 0) -> dict:
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
        "usage_count": usage_count
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
# Batch Operations
# ============================================================

@router.post("/proposals/batch-approve")
async def batch_approve_proposals(
    request: BatchApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Batch approve multiple proposals.

    Approves each proposal in the list and creates AuthorityRules.
    Returns detailed results for each proposal.
    """
    results = []
    successful = 0
    failed = 0

    for proposal_id in request.proposal_ids:
        try:
            # Verify ownership
            proposal = service.get_proposal(proposal_id, str(current_user.id))
            if not proposal:
                results.append(BatchOperationResult(
                    proposal_id=proposal_id,
                    success=False,
                    message="Proposal not found or access denied"
                ))
                failed += 1
                continue

            # Approve the proposal
            rule = await service.approve_proposal(
                proposal_id=proposal_id,
                user_id=str(current_user.id),
                notes=request.notes
            )

            results.append(BatchOperationResult(
                proposal_id=proposal_id,
                success=True,
                message="Approved successfully",
                rule_id=rule.id
            ))
            successful += 1

        except ValueError as e:
            results.append(BatchOperationResult(
                proposal_id=proposal_id,
                success=False,
                message=str(e)
            ))
            failed += 1
        except Exception as e:
            logger.error(f"Error approving proposal {proposal_id}: {e}")
            results.append(BatchOperationResult(
                proposal_id=proposal_id,
                success=False,
                message="Internal error during approval"
            ))
            failed += 1

    return BatchOperationResponse(
        total_requested=len(request.proposal_ids),
        successful=successful,
        failed=failed,
        results=results
    )


@router.post("/proposals/batch-reject")
async def batch_reject_proposals(
    request: BatchRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Batch reject multiple proposals.

    Rejects each proposal in the list with the provided reason.
    Returns detailed results for each proposal.
    """
    results = []
    successful = 0
    failed = 0

    for proposal_id in request.proposal_ids:
        try:
            # Verify ownership
            proposal = service.get_proposal(proposal_id, str(current_user.id))
            if not proposal:
                results.append(BatchOperationResult(
                    proposal_id=proposal_id,
                    success=False,
                    message="Proposal not found or access denied"
                ))
                failed += 1
                continue

            # Reject the proposal
            await service.reject_proposal(
                proposal_id=proposal_id,
                user_id=str(current_user.id),
                reason=request.reason
            )

            results.append(BatchOperationResult(
                proposal_id=proposal_id,
                success=True,
                message="Rejected successfully"
            ))
            successful += 1

        except ValueError as e:
            results.append(BatchOperationResult(
                proposal_id=proposal_id,
                success=False,
                message=str(e)
            ))
            failed += 1
        except Exception as e:
            logger.error(f"Error rejecting proposal {proposal_id}: {e}")
            results.append(BatchOperationResult(
                proposal_id=proposal_id,
                success=False,
                message="Internal error during rejection"
            ))
            failed += 1

    return BatchOperationResponse(
        total_requested=len(request.proposal_ids),
        successful=successful,
        failed=failed,
        results=results
    )


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

    # Calculate usage count from AuthorityRuleUsage table
    usage_count = db.query(sql_func.count(AuthorityRuleUsage.id)).filter(
        AuthorityRuleUsage.rule_id == rule_id
    ).scalar() or 0

    return rule_to_response(rule, jurisdiction, usage_count)


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


# ============================================================
# Auto-Harvest Endpoints (End-to-end rule extraction)
# ============================================================

@router.post("/harvest", response_model=HarvestResponse)
async def harvest_rules_from_url(
    request: HarvestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Harvest rules from a URL automatically.

    This is the main entry point for the auto-scraper. It:
    1. Fetches and cleans content from the URL
    2. Extracts rules using AI (with optional extended thinking)
    3. Creates proposals for each extracted rule
    4. Optionally auto-approves high-confidence rules

    Returns complete results including all extracted rules and proposals.
    """
    import time
    start_time = time.time()

    # Verify jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == request.jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    errors = []
    harvested_rules = []

    # Create a scrape job for tracking
    job = await service.start_scrape(
        jurisdiction_id=request.jurisdiction_id,
        search_query=f"Auto-harvest from {request.url}",
        user_id=str(current_user.id)
    )

    try:
        # Step 1: Scrape the URL content
        logger.info(f"Harvesting rules from {request.url} for {jurisdiction.name}")

        job.status = ScrapeStatus.SEARCHING
        job.started_at = datetime.utcnow()
        db.commit()

        try:
            scraped = await rule_extraction_service.scrape_url_content(request.url)
        except ValueError as e:
            job.status = ScrapeStatus.FAILED
            job.error_message = f"Failed to scrape URL: {str(e)}"
            job.completed_at = datetime.utcnow()
            db.commit()
            raise HTTPException(status_code=400, detail=f"Failed to scrape URL: {str(e)}")

        # Step 2: Extract rules
        job.status = ScrapeStatus.EXTRACTING
        db.commit()

        if request.use_extended_thinking:
            extracted_rules = await rule_extraction_service.extract_with_extended_thinking(
                content=scraped.raw_text,
                jurisdiction_name=jurisdiction.name,
                source_url=request.url
            )
        else:
            extracted_rules = await rule_extraction_service.extract_from_content(
                content=scraped.raw_text,
                jurisdiction_name=jurisdiction.name,
                source_url=request.url
            )

        # Step 3: Create proposals for each rule
        proposals_created = 0
        for rule_data in extracted_rules:
            try:
                proposal = await service.create_proposal(
                    extracted_data=rule_data,
                    scrape_job_id=job.id,
                    jurisdiction_id=request.jurisdiction_id,
                    user_id=str(current_user.id)
                )
                proposals_created += 1

                # Check if should auto-approve
                auto_approved = False
                if request.auto_approve_high_confidence and rule_data.confidence_score >= 0.85:
                    try:
                        await service.approve_proposal(
                            proposal_id=proposal.id,
                            user_id=str(current_user.id),
                            notes="Auto-approved due to high confidence score"
                        )
                        auto_approved = True
                    except Exception as e:
                        errors.append(f"Auto-approve failed for {rule_data.rule_code}: {str(e)}")

                harvested_rules.append(HarvestedRule(
                    proposal_id=proposal.id,
                    rule_code=rule_data.rule_code,
                    rule_name=rule_data.rule_name,
                    trigger_type=rule_data.trigger_type,
                    citation=rule_data.citation,
                    deadlines_count=len(rule_data.deadlines),
                    confidence_score=rule_data.confidence_score,
                    auto_approved=auto_approved,
                    extraction_reasoning=rule_data.extraction_reasoning
                ))

            except Exception as e:
                errors.append(f"Failed to create proposal for {rule_data.rule_code}: {str(e)}")
                logger.warning(f"Failed to create proposal: {e}")

        # Update job with results
        job.status = ScrapeStatus.COMPLETED
        job.rules_found = len(extracted_rules)
        job.proposals_created = proposals_created
        job.urls_processed = [request.url]
        job.completed_at = datetime.utcnow()
        job.progress_pct = 100
        db.commit()

        processing_time_ms = int((time.time() - start_time) * 1000)

        return HarvestResponse(
            job_id=job.id,
            status="completed",
            jurisdiction_id=request.jurisdiction_id,
            jurisdiction_name=jurisdiction.name,
            url=request.url,
            content_hash=scraped.content_hash,
            rules_found=len(extracted_rules),
            proposals_created=proposals_created,
            rules=harvested_rules,
            errors=errors,
            processing_time_ms=processing_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Harvest failed: {e}")
        job.status = ScrapeStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Harvest failed: {str(e)}")


@router.post("/discover-urls", response_model=DiscoverUrlsResponse)
async def discover_court_rule_urls(
    request: DiscoverUrlsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Discover URLs that may contain court rules for a jurisdiction.

    Uses AI and known patterns to find official court rule pages.
    Returns a ranked list of URLs to potentially harvest.
    """
    from anthropic import Anthropic

    # Verify jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == request.jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    # Build search context
    search_query = request.search_query or "local rules civil procedure"
    full_query = f"{jurisdiction.name} {search_query} official court rules PDF"

    # Known court URL patterns
    known_patterns = {
        "federal": [
            "https://www.uscourts.gov",
            "https://www.{district}.uscourts.gov/local-rules",
        ],
        "state": [
            "https://www.{state}courts.gov",
            "https://www.{state}bar.org/rules",
        ]
    }

    # Use Claude to discover URLs
    try:
        anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY.strip())

        prompt = f"""You are a legal research assistant. Find official court rule URLs for:

JURISDICTION: {jurisdiction.name}
JURISDICTION TYPE: {jurisdiction.jurisdiction_type.value if jurisdiction.jurisdiction_type else 'unknown'}
STATE: {jurisdiction.state or 'N/A'}
SEARCH CONTEXT: {search_query}

Provide a JSON array of the most likely official URLs where court rules can be found.
For each URL, include:
- url: The full URL
- title: What rules are likely at this URL
- description: Brief description of expected content
- confidence: 0.0-1.0 confidence this contains official rules

Focus on:
1. Official court websites (.gov, .uscourts.gov)
2. State bar association rule compilations
3. Official PDF rule documents

Return ONLY a JSON array, no other text. Example:
[
  {{
    "url": "https://www.flmd.uscourts.gov/local-rules",
    "title": "Middle District of Florida Local Rules",
    "description": "Official local rules for civil and criminal procedure",
    "confidence": 0.95
  }}
]"""

        response = anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse the response
        import re
        response_text = response.content[0].text.strip()

        # Try to find JSON array in response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            discovered = json.loads(json_match.group())
        else:
            discovered = []

        urls = [
            DiscoveredUrl(
                url=item.get("url", ""),
                title=item.get("title", "Unknown"),
                description=item.get("description", ""),
                confidence=min(max(float(item.get("confidence", 0.5)), 0), 1),
                source="ai_discovery"
            )
            for item in discovered
            if item.get("url")
        ]

        # Sort by confidence
        urls.sort(key=lambda x: x.confidence, reverse=True)

        return DiscoverUrlsResponse(
            jurisdiction_id=request.jurisdiction_id,
            jurisdiction_name=jurisdiction.name,
            urls=urls[:10],  # Limit to top 10
            search_query_used=full_query
        )

    except Exception as e:
        logger.error(f"URL discovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"URL discovery failed: {str(e)}")


@router.post("/harvest-batch", response_model=BatchHarvestResponse)
async def harvest_rules_batch(
    request: BatchHarvestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Harvest rules from multiple URLs.

    Processes each URL sequentially and returns combined results.
    Use this for comprehensive jurisdiction coverage.
    """
    # Verify jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == request.jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    # Create a master job ID
    master_job_id = str(uuid.uuid4())

    results = []
    total_rules = 0
    total_proposals = 0
    failed_urls = 0

    for url in request.urls:
        try:
            # Create individual harvest request
            harvest_req = HarvestRequest(
                url=url,
                jurisdiction_id=request.jurisdiction_id,
                use_extended_thinking=request.use_extended_thinking,
                auto_approve_high_confidence=request.auto_approve_high_confidence
            )

            # Process (this reuses the harvest endpoint logic)
            result = await harvest_rules_from_url(
                request=harvest_req,
                db=db,
                current_user=current_user,
                service=service
            )

            results.append(result)
            total_rules += result.rules_found
            total_proposals += result.proposals_created

        except Exception as e:
            logger.error(f"Batch harvest failed for {url}: {e}")
            failed_urls += 1
            # Create a failed result
            results.append(HarvestResponse(
                job_id="",
                status="failed",
                jurisdiction_id=request.jurisdiction_id,
                jurisdiction_name=jurisdiction.name,
                url=url,
                content_hash="",
                rules_found=0,
                proposals_created=0,
                rules=[],
                errors=[str(e)],
                processing_time_ms=0
            ))

    return BatchHarvestResponse(
        job_id=master_job_id,
        total_urls=len(request.urls),
        completed_urls=len(request.urls) - failed_urls,
        failed_urls=failed_urls,
        total_rules_found=total_rules,
        total_proposals_created=total_proposals,
        results=results
    )


@router.get("/harvest/{job_id}/status")
async def get_harvest_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Get the status of a harvest job.

    Returns current progress and any results if completed.
    """
    job = service.get_scrape_job(job_id, str(current_user.id))
    if not job:
        raise HTTPException(status_code=404, detail="Harvest job not found")

    jurisdiction = None
    if job.jurisdiction_id:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == job.jurisdiction_id
        ).first()

    return {
        "job_id": job.id,
        "status": job.status.value if job.status else "unknown",
        "progress_pct": job.progress_pct or 0,
        "jurisdiction_name": jurisdiction.name if jurisdiction else None,
        "rules_found": job.rules_found or 0,
        "proposals_created": job.proposals_created or 0,
        "urls_processed": job.urls_processed or [],
        "error_message": job.error_message,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at
    }


# ============================================================
# Analytics Endpoints
# ============================================================

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    jurisdiction_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive analytics for Authority Core.

    Returns:
    - Most used rules (top 10)
    - Rules by jurisdiction
    - Rules by authority tier
    - Proposal approval/rejection stats
    - Conflict resolution stats
    """
    # Get most used rules
    most_used_query = db.query(
        AuthorityRuleUsage.rule_id,
        sql_func.count(AuthorityRuleUsage.id).label('usage_count'),
        sql_func.sum(AuthorityRuleUsage.deadlines_generated).label('deadlines_generated')
    ).group_by(AuthorityRuleUsage.rule_id).order_by(
        sql_func.count(AuthorityRuleUsage.id).desc()
    ).limit(10).all()

    most_used_rules = []
    for rule_id, usage_count, deadlines_gen in most_used_query:
        rule = db.query(AuthorityRule).filter(AuthorityRule.id == rule_id).first()
        if rule:
            jurisdiction = db.query(Jurisdiction).filter(
                Jurisdiction.id == rule.jurisdiction_id
            ).first() if rule.jurisdiction_id else None

            most_used_rules.append(RuleUsageStats(
                rule_id=rule.id,
                rule_name=rule.rule_name,
                rule_code=rule.rule_code,
                jurisdiction_name=jurisdiction.name if jurisdiction else None,
                usage_count=usage_count or 0,
                deadlines_generated=deadlines_gen or 0
            ))

    # Get rules by jurisdiction
    jurisdiction_query = db.query(
        Jurisdiction.id,
        Jurisdiction.name,
        sql_func.count(AuthorityRule.id).label('rule_count'),
        sql_func.sum(
            sql_func.cast(AuthorityRule.is_verified, Integer)
        ).label('verified_count')
    ).outerjoin(
        AuthorityRule, AuthorityRule.jurisdiction_id == Jurisdiction.id
    ).filter(
        AuthorityRule.is_active == True
    ).group_by(
        Jurisdiction.id, Jurisdiction.name
    ).all()

    rules_by_jurisdiction = []
    for jur_id, jur_name, rule_count, verified_count in jurisdiction_query:
        # Count pending proposals for this jurisdiction
        pending_count = db.query(sql_func.count(RuleProposal.id)).filter(
            RuleProposal.jurisdiction_id == jur_id,
            RuleProposal.status == ProposalStatus.PENDING
        ).scalar() or 0

        rules_by_jurisdiction.append(JurisdictionStats(
            jurisdiction_id=jur_id,
            jurisdiction_name=jur_name,
            rule_count=rule_count or 0,
            verified_count=verified_count or 0,
            pending_proposals=pending_count
        ))

    # Get rules by tier
    from app.models.enums import AuthorityTier
    tier_stats = []
    for tier in AuthorityTier:
        rule_count = db.query(sql_func.count(AuthorityRule.id)).filter(
            AuthorityRule.authority_tier == tier,
            AuthorityRule.is_active == True
        ).scalar() or 0

        usage_count = db.query(sql_func.count(AuthorityRuleUsage.id)).join(
            AuthorityRule, AuthorityRule.id == AuthorityRuleUsage.rule_id
        ).filter(
            AuthorityRule.authority_tier == tier
        ).scalar() or 0

        tier_stats.append(TierStats(
            tier=tier.value,
            rule_count=rule_count,
            usage_count=usage_count
        ))

    # Get proposal stats
    total_proposals = db.query(sql_func.count(RuleProposal.id)).scalar() or 0
    pending_proposals = db.query(sql_func.count(RuleProposal.id)).filter(
        RuleProposal.status == ProposalStatus.PENDING
    ).scalar() or 0
    approved_proposals = db.query(sql_func.count(RuleProposal.id)).filter(
        RuleProposal.status == ProposalStatus.APPROVED
    ).scalar() or 0
    rejected_proposals = db.query(sql_func.count(RuleProposal.id)).filter(
        RuleProposal.status == ProposalStatus.REJECTED
    ).scalar() or 0
    needs_revision_proposals = db.query(sql_func.count(RuleProposal.id)).filter(
        RuleProposal.status == ProposalStatus.NEEDS_REVISION
    ).scalar() or 0

    reviewed_count = approved_proposals + rejected_proposals
    approval_rate = (approved_proposals / reviewed_count * 100) if reviewed_count > 0 else 0.0

    proposal_stats = ProposalStats(
        total_proposals=total_proposals,
        pending=pending_proposals,
        approved=approved_proposals,
        rejected=rejected_proposals,
        needs_revision=needs_revision_proposals,
        approval_rate=round(approval_rate, 2)
    )

    # Get conflict stats
    total_conflicts = db.query(sql_func.count(RuleConflict.id)).scalar() or 0
    pending_conflicts = db.query(sql_func.count(RuleConflict.id)).filter(
        RuleConflict.resolution == ConflictResolution.PENDING
    ).scalar() or 0
    auto_resolved = db.query(sql_func.count(RuleConflict.id)).filter(
        RuleConflict.resolution == ConflictResolution.USE_HIGHER_TIER
    ).scalar() or 0
    manually_resolved = db.query(sql_func.count(RuleConflict.id)).filter(
        RuleConflict.resolution.in_([
            ConflictResolution.USE_RULE_A,
            ConflictResolution.USE_RULE_B,
            ConflictResolution.MANUAL
        ])
    ).scalar() or 0
    ignored_conflicts = db.query(sql_func.count(RuleConflict.id)).filter(
        RuleConflict.resolution == ConflictResolution.IGNORED
    ).scalar() or 0

    conflict_stats = ConflictStats(
        total_conflicts=total_conflicts,
        pending=pending_conflicts,
        auto_resolved=auto_resolved,
        manually_resolved=manually_resolved,
        ignored=ignored_conflicts
    )

    # Total rule counts
    total_rules = db.query(sql_func.count(AuthorityRule.id)).filter(
        AuthorityRule.is_active == True
    ).scalar() or 0
    total_verified = db.query(sql_func.count(AuthorityRule.id)).filter(
        AuthorityRule.is_active == True,
        AuthorityRule.is_verified == True
    ).scalar() or 0

    return AnalyticsResponse(
        most_used_rules=most_used_rules,
        rules_by_jurisdiction=rules_by_jurisdiction,
        rules_by_tier=tier_stats,
        proposal_stats=proposal_stats,
        conflict_stats=conflict_stats,
        total_rules=total_rules,
        total_verified_rules=total_verified
    )


# ============================================================
# Import/Export Endpoints
# ============================================================

@router.get("/rules/export", response_model=RulesExportResponse)
async def export_rules(
    jurisdiction_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    format: str = Query("json", description="Export format (only json supported)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export rules to JSON format.

    Optionally filter by jurisdiction or trigger type.
    """
    if format != "json":
        raise HTTPException(status_code=400, detail="Only JSON format is supported")

    query = db.query(AuthorityRule).filter(
        AuthorityRule.is_active == True,
        AuthorityRule.is_verified == True
    )

    if jurisdiction_id:
        query = query.filter(AuthorityRule.jurisdiction_id == jurisdiction_id)
    if trigger_type:
        query = query.filter(AuthorityRule.trigger_type == trigger_type)

    rules = query.all()

    jurisdiction_name = None
    if jurisdiction_id:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()
        jurisdiction_name = jurisdiction.name if jurisdiction else None

    export_rules = []
    for rule in rules:
        export_rules.append(RuleExportData(
            rule_code=rule.rule_code,
            rule_name=rule.rule_name,
            trigger_type=rule.trigger_type,
            authority_tier=rule.authority_tier.value if rule.authority_tier else "state",
            citation=rule.citation,
            source_url=rule.source_url,
            source_text=rule.source_text,
            deadlines=rule.deadlines or [],
            conditions=rule.conditions,
            service_extensions=rule.service_extensions,
            effective_date=rule.effective_date.isoformat() if rule.effective_date else None
        ))

    return RulesExportResponse(
        export_version="1.0",
        exported_at=datetime.utcnow(),
        jurisdiction_id=jurisdiction_id,
        jurisdiction_name=jurisdiction_name,
        rule_count=len(export_rules),
        rules=export_rules
    )


@router.post("/rules/import", response_model=RulesImportResponse)
async def import_rules(
    request: RulesImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Import rules from JSON format.

    Can create rules as proposals for review or as verified rules directly.
    """
    # Verify jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == request.jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    results = []
    imported = 0
    skipped = 0
    failed = 0

    from app.models.enums import AuthorityTier as ATier
    from app.services.rule_extraction_service import ExtractedRuleData, ExtractedDeadline

    for rule_data in request.rules:
        try:
            # Check for duplicates
            if request.skip_duplicates:
                existing = db.query(AuthorityRule).filter(
                    AuthorityRule.jurisdiction_id == request.jurisdiction_id,
                    AuthorityRule.rule_code == rule_data.rule_code,
                    AuthorityRule.is_active == True
                ).first()

                if existing:
                    results.append(ImportResult(
                        rule_code=rule_data.rule_code,
                        success=True,
                        message="Skipped - rule already exists"
                    ))
                    skipped += 1
                    continue

            if request.create_as_proposals:
                # Create as proposal for review
                extracted = ExtractedRuleData(
                    rule_code=rule_data.rule_code,
                    rule_name=rule_data.rule_name,
                    trigger_type=rule_data.trigger_type,
                    authority_tier=rule_data.authority_tier,
                    citation=rule_data.citation or "",
                    source_url=rule_data.source_url,
                    source_text=rule_data.source_text or "",
                    deadlines=[
                        ExtractedDeadline(
                            title=d.get("title", ""),
                            days_from_trigger=d.get("days_from_trigger", 0),
                            calculation_method=d.get("calculation_method", "calendar_days"),
                            priority=d.get("priority", "standard"),
                            party_responsible=d.get("party_responsible"),
                            conditions=d.get("conditions"),
                            description=d.get("description")
                        )
                        for d in rule_data.deadlines
                    ],
                    conditions=rule_data.conditions,
                    service_extensions=rule_data.service_extensions,
                    confidence_score=1.0,
                    extraction_notes="Imported from JSON"
                )

                proposal = await service.create_proposal(
                    extracted_data=extracted,
                    scrape_job_id=None,
                    jurisdiction_id=request.jurisdiction_id,
                    user_id=str(current_user.id)
                )

                results.append(ImportResult(
                    rule_code=rule_data.rule_code,
                    success=True,
                    message="Created as proposal",
                    proposal_id=proposal.id
                ))
                imported += 1

            else:
                # Create as verified rule directly
                tier_map = {
                    "federal": ATier.FEDERAL,
                    "state": ATier.STATE,
                    "local": ATier.LOCAL,
                    "standing_order": ATier.STANDING_ORDER,
                    "firm": ATier.FIRM
                }
                authority_tier = tier_map.get(rule_data.authority_tier.lower(), ATier.STATE)

                rule = AuthorityRule(
                    id=str(uuid.uuid4()),
                    user_id=str(current_user.id),
                    jurisdiction_id=request.jurisdiction_id,
                    authority_tier=authority_tier,
                    rule_code=rule_data.rule_code,
                    rule_name=rule_data.rule_name,
                    trigger_type=rule_data.trigger_type,
                    citation=rule_data.citation,
                    source_url=rule_data.source_url,
                    source_text=rule_data.source_text,
                    deadlines=rule_data.deadlines,
                    conditions=rule_data.conditions,
                    service_extensions=rule_data.service_extensions or {"mail": 3, "electronic": 0, "personal": 0},
                    confidence_score=1.0,
                    is_verified=True,
                    verified_by=str(current_user.id),
                    verified_at=datetime.utcnow(),
                    is_active=True
                )

                db.add(rule)
                db.commit()

                results.append(ImportResult(
                    rule_code=rule_data.rule_code,
                    success=True,
                    message="Imported as verified rule",
                    rule_id=rule.id
                ))
                imported += 1

        except Exception as e:
            logger.error(f"Error importing rule {rule_data.rule_code}: {e}")
            results.append(ImportResult(
                rule_code=rule_data.rule_code,
                success=False,
                message=str(e)
            ))
            failed += 1

    return RulesImportResponse(
        total_requested=len(request.rules),
        imported=imported,
        skipped=skipped,
        failed=failed,
        results=results
    )


# ============================================================
# Migration Endpoints (Hardcoded Rules to Authority Core)
# ============================================================

@router.get("/migration/preview")
async def preview_migration(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction (florida_state, federal)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Preview hardcoded rules that can be migrated to Authority Core.

    Returns a list of all hardcoded rules from rules_engine.py that would be
    migrated, along with their deadlines and metadata.
    """
    try:
        # Import migration functions
        import sys
        import os
        scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'scripts')
        sys.path.insert(0, scripts_path)

        from migrate_hardcoded_rules import preview_migration as get_preview, get_jurisdiction_id

        rules = get_preview()

        # Filter by jurisdiction if specified
        if jurisdiction:
            rules = [r for r in rules if r["jurisdiction"].lower() == jurisdiction.lower()]

        # Check which rules already exist
        for rule in rules:
            jurisdiction_id = get_jurisdiction_id(db, rule["jurisdiction"])
            if jurisdiction_id:
                existing = db.query(AuthorityRule).filter(
                    AuthorityRule.rule_code == rule["rule_id"],
                    AuthorityRule.jurisdiction_id == jurisdiction_id,
                    AuthorityRule.is_active == True
                ).first()
                rule["already_exists"] = existing is not None
                rule["jurisdiction_id"] = jurisdiction_id
            else:
                rule["already_exists"] = False
                rule["jurisdiction_id"] = None

        # Count statistics
        total = len(rules)
        existing = sum(1 for r in rules if r.get("already_exists"))
        to_migrate = total - existing

        return {
            "total_rules": total,
            "already_migrated": existing,
            "to_migrate": to_migrate,
            "rules": rules
        }

    except ImportError as e:
        logger.error(f"Migration module not found: {e}")
        raise HTTPException(status_code=500, detail="Migration module not available")
    except Exception as e:
        logger.error(f"Preview migration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migration/execute")
async def execute_migration(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    skip_existing: bool = Query(True, description="Skip rules that already exist"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute migration of hardcoded rules to Authority Core.

    Creates AuthorityRule entries for all hardcoded rules from rules_engine.py.
    Rules are created as verified with confidence score of 1.0.
    """
    try:
        # Import migration functions
        import sys
        import os
        scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'scripts')
        sys.path.insert(0, scripts_path)

        from migrate_hardcoded_rules import migrate_rules

        results = migrate_rules(
            db,
            dry_run=False,
            jurisdiction_filter=jurisdiction,
            user_id=str(current_user.id)
        )

        return {
            "success": True,
            "total_rules": results["total_rules"],
            "migrated": results["migrated"],
            "skipped": results["skipped"],
            "errors": results["errors"],
            "details": results["details"]
        }

    except ImportError as e:
        logger.error(f"Migration module not found: {e}")
        raise HTTPException(status_code=500, detail="Migration module not available")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/migration/status")
async def get_migration_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current migration status.

    Returns counts of:
    - Total hardcoded rules
    - Rules already migrated to Authority Core
    - Rules pending migration
    """
    try:
        # Import migration functions
        import sys
        import os
        scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'scripts')
        sys.path.insert(0, scripts_path)

        from migrate_hardcoded_rules import preview_migration as get_preview, get_jurisdiction_id, JURISDICTION_MAPPING

        rules = get_preview()

        # Count by jurisdiction
        by_jurisdiction = {}
        for rule in rules:
            jur = rule["jurisdiction"]
            if jur not in by_jurisdiction:
                by_jurisdiction[jur] = {"total": 0, "migrated": 0, "pending": 0}
            by_jurisdiction[jur]["total"] += 1

            # Check if exists
            jurisdiction_id = get_jurisdiction_id(db, jur)
            if jurisdiction_id:
                existing = db.query(AuthorityRule).filter(
                    AuthorityRule.rule_code == rule["rule_id"],
                    AuthorityRule.jurisdiction_id == jurisdiction_id,
                    AuthorityRule.is_active == True
                ).first()
                if existing:
                    by_jurisdiction[jur]["migrated"] += 1
                else:
                    by_jurisdiction[jur]["pending"] += 1
            else:
                by_jurisdiction[jur]["pending"] += 1

        total_hardcoded = len(rules)
        total_migrated = sum(j["migrated"] for j in by_jurisdiction.values())
        total_pending = total_hardcoded - total_migrated

        # Get total Authority Core rules
        total_authority_rules = db.query(sql_func.count(AuthorityRule.id)).filter(
            AuthorityRule.is_active == True
        ).scalar() or 0

        return {
            "hardcoded_rules": {
                "total": total_hardcoded,
                "migrated": total_migrated,
                "pending": total_pending,
                "by_jurisdiction": by_jurisdiction
            },
            "authority_core_rules": {
                "total": total_authority_rules,
                "from_migration": total_migrated,
                "from_other_sources": total_authority_rules - total_migrated
            },
            "migration_complete": total_pending == 0
        }

    except ImportError as e:
        logger.error(f"Migration module not found: {e}")
        raise HTTPException(status_code=500, detail="Migration module not available")
    except Exception as e:
        logger.error(f"Migration status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Visualization Endpoints
# ============================================================

@router.get("/visualization/graph")
async def get_rule_graph(
    jurisdiction_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    conflicts_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get rule dependency graph data for visualization.

    Returns nodes (rules) and edges (relationships/conflicts) suitable
    for rendering with react-flow or d3.
    """
    # Build query for rules
    query = db.query(AuthorityRule).filter(AuthorityRule.is_active == True)

    if jurisdiction_id:
        query = query.filter(AuthorityRule.jurisdiction_id == jurisdiction_id)
    if trigger_type:
        query = query.filter(AuthorityRule.trigger_type == trigger_type)

    rules = query.all()

    if conflicts_only:
        # Only include rules that have conflicts
        conflict_rule_ids = set()
        conflicts = db.query(RuleConflict).filter(
            RuleConflict.resolution == ConflictResolution.PENDING
        ).all()
        for c in conflicts:
            conflict_rule_ids.add(c.rule_a_id)
            conflict_rule_ids.add(c.rule_b_id)
        rules = [r for r in rules if r.id in conflict_rule_ids]

    rule_ids = {r.id for r in rules}

    # Get usage counts
    usage_counts = {}
    usage_query = db.query(
        AuthorityRuleUsage.rule_id,
        sql_func.count(AuthorityRuleUsage.id).label('count')
    ).filter(
        AuthorityRuleUsage.rule_id.in_(rule_ids)
    ).group_by(AuthorityRuleUsage.rule_id).all()

    for rule_id, count in usage_query:
        usage_counts[rule_id] = count

    # Build nodes
    nodes = []
    jurisdictions = set()
    tiers = set()

    for rule in rules:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == rule.jurisdiction_id
        ).first() if rule.jurisdiction_id else None

        jurisdiction_name = jurisdiction.name if jurisdiction else "Unknown"
        jurisdictions.add(jurisdiction_name)
        tiers.add(rule.authority_tier.value if rule.authority_tier else "unknown")

        nodes.append({
            "id": rule.id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "trigger_type": rule.trigger_type,
            "authority_tier": rule.authority_tier.value if rule.authority_tier else "unknown",
            "jurisdiction_name": jurisdiction_name,
            "deadlines_count": len(rule.deadlines) if rule.deadlines else 0,
            "is_verified": rule.is_verified,
            "usage_count": usage_counts.get(rule.id, 0)
        })

    # Build edges
    edges = []

    # 1. Conflict edges
    conflicts = db.query(RuleConflict).filter(
        RuleConflict.rule_a_id.in_(rule_ids),
        RuleConflict.rule_b_id.in_(rule_ids)
    ).all()

    for conflict in conflicts:
        edges.append({
            "source": conflict.rule_a_id,
            "target": conflict.rule_b_id,
            "type": "conflict",
            "label": conflict.conflict_type,
            "severity": conflict.severity
        })

    # 2. Same trigger type edges (rules that share the same trigger)
    trigger_groups = {}
    for rule in rules:
        if rule.trigger_type not in trigger_groups:
            trigger_groups[rule.trigger_type] = []
        trigger_groups[rule.trigger_type].append(rule.id)

    for trigger_type, rule_ids_group in trigger_groups.items():
        if len(rule_ids_group) > 1:
            # Connect first rule to all others in group
            for i in range(1, len(rule_ids_group)):
                edges.append({
                    "source": rule_ids_group[0],
                    "target": rule_ids_group[i],
                    "type": "same_trigger",
                    "label": trigger_type
                })

    # 3. Supersedes edges (based on effective/superseded dates)
    for rule in rules:
        if rule.superseded_date:
            # Find rules that might supersede this one
            superseding = db.query(AuthorityRule).filter(
                AuthorityRule.trigger_type == rule.trigger_type,
                AuthorityRule.jurisdiction_id == rule.jurisdiction_id,
                AuthorityRule.effective_date != None,
                AuthorityRule.effective_date >= rule.superseded_date,
                AuthorityRule.is_active == True,
                AuthorityRule.id != rule.id
            ).first()

            if superseding and superseding.id in rule_ids:
                edges.append({
                    "source": superseding.id,
                    "target": rule.id,
                    "type": "supersedes"
                })

    return {
        "nodes": nodes,
        "edges": edges,
        "tiers": list(tiers),
        "jurisdictions": list(jurisdictions)
    }


# ============================================================
# Smart Rule Discovery Endpoints
# ============================================================

@router.post("/discover/related")
async def discover_related_rules(
    url: str,
    jurisdiction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """
    Discover related rules from a URL.

    When harvesting a rule, this endpoint suggests other rules from the same
    section, chapter, or related legal provisions.
    """
    from app.services.ai_service import AIService

    ai_service = AIService()

    # Get jurisdiction info
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    # Scrape the URL to analyze structure
    try:
        scraper = service._get_scraper()
        content = await scraper.scrape_url(url)

        if not content:
            raise HTTPException(status_code=400, detail="Could not fetch URL content")

        # Use AI to identify related rules and suggest URLs
        prompt = f"""Analyze this legal document and identify related rules that should also be harvested.

URL: {url}
Jurisdiction: {jurisdiction.name}

Content excerpt:
{content[:8000]}

Please identify:
1. The rule section/chapter this belongs to
2. Other rules in the same section that might be relevant
3. Cross-referenced rules mentioned in the text
4. Suggested URLs for related rules (if derivable from URL patterns)

Format your response as JSON:
{{
    "current_rule_section": "e.g., Rule 12 - Defenses and Objections",
    "chapter": "e.g., Title III - Pleadings and Motions",
    "related_rules": [
        {{
            "rule_code": "e.g., FRCP Rule 11",
            "rule_name": "Signing Pleadings",
            "relationship": "same_chapter|cross_reference|prerequisite|follow_up",
            "suggested_url": "https://..."
        }}
    ],
    "cross_references": ["Rule 11", "Rule 15(a)"],
    "harvest_priority": "high|medium|low"
}}"""

        response = await ai_service.analyze_with_claude(prompt)

        import json
        try:
            # Extract JSON from response
            json_match = response.find('{')
            json_end = response.rfind('}') + 1
            if json_match >= 0 and json_end > json_match:
                result = json.loads(response[json_match:json_end])
            else:
                result = {"error": "Could not parse AI response", "raw": response}
        except json.JSONDecodeError:
            result = {"error": "Invalid JSON in AI response", "raw": response}

        return {
            "url": url,
            "jurisdiction": jurisdiction.name,
            "discovery_result": result
        }

    except Exception as e:
        logger.error(f"Rule discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover/suggestions")
async def get_harvest_suggestions(
    jurisdiction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get suggestions for rules to harvest based on existing rules and gaps.

    Analyzes current rule coverage and suggests missing rules.
    """
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    # Get existing rules for this jurisdiction
    existing_rules = db.query(AuthorityRule).filter(
        AuthorityRule.jurisdiction_id == jurisdiction_id,
        AuthorityRule.is_active == True
    ).all()

    existing_triggers = set(r.trigger_type for r in existing_rules)
    existing_codes = set(r.rule_code for r in existing_rules)

    # Common trigger types that should have rules
    all_trigger_types = [
        "complaint_served", "answer_filed", "case_filed",
        "discovery_served", "discovery_deadline",
        "motion_filed", "motion_hearing",
        "trial_date", "pretrial_conference",
        "mediation", "arbitration",
        "appeal_filed", "judgment_entered",
        "deposition_noticed", "expert_disclosed"
    ]

    missing_triggers = [t for t in all_trigger_types if t not in existing_triggers]

    # Suggest URLs based on jurisdiction
    suggested_urls = []
    if jurisdiction.code == "FED" or jurisdiction.code.startswith("FED-"):
        suggested_urls = [
            {"url": "https://www.law.cornell.edu/rules/frcp", "description": "Federal Rules of Civil Procedure"},
            {"url": "https://www.law.cornell.edu/rules/frap", "description": "Federal Rules of Appellate Procedure"},
            {"url": "https://www.law.cornell.edu/rules/frbp", "description": "Federal Rules of Bankruptcy Procedure"},
        ]
    elif jurisdiction.code == "FL" or jurisdiction.code.startswith("FL-"):
        suggested_urls = [
            {"url": "https://www.flcourts.gov/Resources-Services/Rules-Procedures", "description": "Florida Court Rules"},
            {"url": "https://www.floridabar.org/rules/", "description": "Florida Bar Rules"},
        ]

    return {
        "jurisdiction": jurisdiction.name,
        "coverage": {
            "total_rules": len(existing_rules),
            "trigger_types_covered": len(existing_triggers),
            "trigger_types_missing": len(missing_triggers)
        },
        "missing_trigger_types": missing_triggers,
        "suggested_urls": suggested_urls,
        "gaps": [
            {
                "trigger_type": t,
                "priority": "high" if t in ["complaint_served", "answer_filed", "trial_date"] else "medium",
                "description": f"No rules found for {t.replace('_', ' ')} trigger"
            }
            for t in missing_triggers[:10]
        ]
    }


# ============================================================
# Rule Comparison Endpoints
# ============================================================

@router.get("/compare/rules")
async def compare_rules(
    rule_ids: str,  # Comma-separated list of rule IDs
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare multiple rules side-by-side.

    Shows differences in deadlines, conditions, and requirements.
    """
    ids = [id.strip() for id in rule_ids.split(",")]

    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 rule IDs required for comparison")
    if len(ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 rules can be compared at once")

    rules = db.query(AuthorityRule).filter(AuthorityRule.id.in_(ids)).all()

    if len(rules) != len(ids):
        raise HTTPException(status_code=404, detail="One or more rules not found")

    # Build comparison matrix
    comparison = {
        "rules": [],
        "differences": [],
        "commonalities": []
    }

    for rule in rules:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == rule.jurisdiction_id
        ).first() if rule.jurisdiction_id else None

        comparison["rules"].append({
            "id": rule.id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "jurisdiction": jurisdiction.name if jurisdiction else "Unknown",
            "authority_tier": rule.authority_tier.value if rule.authority_tier else "unknown",
            "trigger_type": rule.trigger_type,
            "citation": rule.citation,
            "deadlines": rule.deadlines or [],
            "conditions": rule.conditions or {},
            "service_extensions": rule.service_extensions or {}
        })

    # Find differences
    if len(rules) >= 2:
        # Compare deadline days
        all_deadlines = {}
        for rule in rules:
            for dl in (rule.deadlines or []):
                title = dl.get("title", "Unknown")
                if title not in all_deadlines:
                    all_deadlines[title] = {}
                all_deadlines[title][rule.id] = dl.get("days_from_trigger")

        for title, values in all_deadlines.items():
            unique_values = set(v for v in values.values() if v is not None)
            if len(unique_values) > 1:
                comparison["differences"].append({
                    "type": "deadline_days",
                    "deadline_title": title,
                    "values": {
                        r.rule_code: values.get(r.id)
                        for r in rules if r.id in values
                    }
                })

        # Compare service extensions
        service_types = ["mail", "electronic", "personal"]
        for stype in service_types:
            values = {
                r.rule_code: (r.service_extensions or {}).get(stype, 0)
                for r in rules
            }
            if len(set(values.values())) > 1:
                comparison["differences"].append({
                    "type": "service_extension",
                    "service_method": stype,
                    "values": values
                })

        # Find commonalities
        if all(r.trigger_type == rules[0].trigger_type for r in rules):
            comparison["commonalities"].append({
                "type": "trigger_type",
                "value": rules[0].trigger_type
            })

        # Check for same deadline titles
        common_deadline_titles = None
        for rule in rules:
            titles = set(dl.get("title") for dl in (rule.deadlines or []))
            if common_deadline_titles is None:
                common_deadline_titles = titles
            else:
                common_deadline_titles &= titles

        if common_deadline_titles:
            comparison["commonalities"].append({
                "type": "common_deadlines",
                "titles": list(common_deadline_titles)
            })

    return comparison


@router.get("/compare/jurisdictions")
async def compare_jurisdictions(
    trigger_type: str,
    jurisdiction_ids: str,  # Comma-separated
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare how different jurisdictions handle the same trigger type.
    """
    ids = [id.strip() for id in jurisdiction_ids.split(",")]

    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 jurisdictions required")

    comparison = {
        "trigger_type": trigger_type,
        "jurisdictions": []
    }

    for jid in ids:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == jid
        ).first()

        if not jurisdiction:
            continue

        rules = db.query(AuthorityRule).filter(
            AuthorityRule.jurisdiction_id == jid,
            AuthorityRule.trigger_type == trigger_type,
            AuthorityRule.is_active == True
        ).all()

        comparison["jurisdictions"].append({
            "id": jurisdiction.id,
            "name": jurisdiction.name,
            "code": jurisdiction.code,
            "rules_count": len(rules),
            "rules": [
                {
                    "id": r.id,
                    "rule_code": r.rule_code,
                    "rule_name": r.rule_name,
                    "citation": r.citation,
                    "authority_tier": r.authority_tier.value if r.authority_tier else "unknown",
                    "deadlines": r.deadlines or [],
                    "service_extensions": r.service_extensions or {}
                }
                for r in rules
            ]
        })

    return comparison


# ============================================================
# Holiday Calendar Endpoints
# ============================================================

@router.get("/holidays")
async def get_court_holidays(
    jurisdiction_id: str,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get court holidays for a jurisdiction.

    Returns all holidays for the specified year (defaults to current year).
    """
    from app.models.court_holiday import CourtHoliday
    from datetime import datetime

    if not year:
        year = datetime.now().year

    holidays = db.query(CourtHoliday).filter(
        CourtHoliday.jurisdiction_id == jurisdiction_id,
        CourtHoliday.year == year
    ).order_by(CourtHoliday.holiday_date).all()

    return {
        "jurisdiction_id": jurisdiction_id,
        "year": year,
        "holidays": [
            {
                "id": h.id,
                "name": h.name,
                "date": h.holiday_date.isoformat() if h.holiday_date else None,
                "is_observed": h.is_observed,
                "actual_date": h.actual_date.isoformat() if h.actual_date else None,
                "holiday_type": h.holiday_type,
                "court_closed": h.court_closed
            }
            for h in holidays
        ]
    }


@router.post("/holidays/generate")
async def generate_holidays(
    jurisdiction_id: str,
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate court holidays for a jurisdiction and year.

    Uses holiday patterns to create specific holiday dates.
    """
    from app.models.court_holiday import CourtHoliday, HolidayPattern
    from datetime import date
    from calendar import monthrange

    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    # Get patterns for this jurisdiction (and global patterns)
    patterns = db.query(HolidayPattern).filter(
        HolidayPattern.is_active == True,
        (HolidayPattern.jurisdiction_id == None) | (HolidayPattern.jurisdiction_id == jurisdiction_id)
    ).all()

    created_count = 0

    for pattern in patterns:
        try:
            # Calculate holiday date based on pattern type
            if pattern.pattern_type == 'fixed':
                month = pattern.pattern_definition.get('month')
                day = pattern.pattern_definition.get('day')
                holiday_date = date(year, month, day)

            elif pattern.pattern_type == 'floating':
                month = pattern.pattern_definition.get('month')
                weekday = pattern.pattern_definition.get('weekday')  # 0=Monday
                occurrence = pattern.pattern_definition.get('occurrence')

                if occurrence > 0:
                    # Nth occurrence (e.g., 3rd Monday)
                    first_of_month = date(year, month, 1)
                    days_until_weekday = (weekday - first_of_month.weekday() + 7) % 7
                    holiday_date = date(year, month, 1 + days_until_weekday + (occurrence - 1) * 7)
                else:
                    # Last occurrence
                    last_day = monthrange(year, month)[1]
                    last_of_month = date(year, month, last_day)
                    days_since_weekday = (last_of_month.weekday() - weekday + 7) % 7
                    holiday_date = date(year, month, last_day - days_since_weekday)
            else:
                continue

            # Calculate observed date
            observed_date = holiday_date
            if pattern.federal_observation_rules:
                if holiday_date.weekday() == 5:  # Saturday
                    observed_date = date(year, holiday_date.month, holiday_date.day - 1)
                elif holiday_date.weekday() == 6:  # Sunday
                    observed_date = date(year, holiday_date.month, holiday_date.day + 1)

            # Check if holiday already exists
            existing = db.query(CourtHoliday).filter(
                CourtHoliday.jurisdiction_id == jurisdiction_id,
                CourtHoliday.name == pattern.name,
                CourtHoliday.year == year
            ).first()

            if not existing:
                holiday = CourtHoliday(
                    jurisdiction_id=jurisdiction_id,
                    name=pattern.name,
                    holiday_date=observed_date,
                    year=year,
                    is_observed=observed_date != holiday_date,
                    actual_date=holiday_date if observed_date != holiday_date else None,
                    holiday_type=pattern.holiday_type,
                    court_closed=pattern.court_closed
                )
                db.add(holiday)
                created_count += 1

        except Exception as e:
            logger.warning(f"Failed to generate holiday {pattern.name}: {e}")

    db.commit()

    return {
        "jurisdiction_id": jurisdiction_id,
        "year": year,
        "holidays_created": created_count,
        "patterns_processed": len(patterns)
    }


@router.post("/holidays")
async def create_holiday(
    jurisdiction_id: str,
    name: str,
    holiday_date: date,
    holiday_type: str = "custom",
    court_closed: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a custom court holiday."""
    from app.models.court_holiday import CourtHoliday
    from datetime import date as date_type

    holiday = CourtHoliday(
        jurisdiction_id=jurisdiction_id,
        name=name,
        holiday_date=holiday_date,
        year=holiday_date.year,
        holiday_type=holiday_type,
        court_closed=court_closed
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)

    return {
        "id": holiday.id,
        "name": holiday.name,
        "date": holiday.holiday_date.isoformat(),
        "holiday_type": holiday.holiday_type,
        "court_closed": holiday.court_closed
    }


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
    holiday_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a court holiday."""
    from app.models.court_holiday import CourtHoliday

    holiday = db.query(CourtHoliday).filter(CourtHoliday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")

    db.delete(holiday)
    db.commit()

    return {"deleted": True, "id": holiday_id}


@router.get("/holidays/check")
async def check_business_day(
    jurisdiction_id: str,
    check_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if a date is a business day for a jurisdiction.

    Returns whether the court is open and any holidays on that date.
    """
    from app.models.court_holiday import CourtHoliday

    # Check for weekends
    is_weekend = check_date.weekday() >= 5

    # Check for holidays
    holiday = db.query(CourtHoliday).filter(
        CourtHoliday.jurisdiction_id == jurisdiction_id,
        CourtHoliday.holiday_date == check_date,
        CourtHoliday.court_closed == True
    ).first()

    is_business_day = not is_weekend and not holiday

    return {
        "date": check_date.isoformat(),
        "jurisdiction_id": jurisdiction_id,
        "is_business_day": is_business_day,
        "is_weekend": is_weekend,
        "holiday": {
            "name": holiday.name,
            "type": holiday.holiday_type
        } if holiday else None
    }


# ============================================================
# Scheduled Harvesting Endpoints
# ============================================================

@router.get("/schedules")
async def list_harvest_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all harvest schedules for the current user."""
    from app.models.court_holiday import HarvestSchedule

    schedules = db.query(HarvestSchedule).filter(
        HarvestSchedule.user_id == str(current_user.id)
    ).order_by(HarvestSchedule.created_at.desc()).all()

    result = []
    for s in schedules:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == s.jurisdiction_id
        ).first() if s.jurisdiction_id else None

        result.append({
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "jurisdiction_id": s.jurisdiction_id,
            "jurisdiction_name": jurisdiction.name if jurisdiction else None,
            "frequency": s.frequency,
            "is_active": s.is_active,
            "last_checked_at": s.last_checked_at.isoformat() if s.last_checked_at else None,
            "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
            "total_checks": s.total_checks,
            "changes_detected": s.changes_detected,
            "rules_harvested": s.rules_harvested,
            "error_count": s.error_count
        })

    return result


@router.post("/schedules")
async def create_harvest_schedule(
    url: str,
    jurisdiction_id: str,
    frequency: str,  # daily, weekly, monthly
    name: Optional[str] = None,
    day_of_week: Optional[int] = None,
    day_of_month: Optional[int] = None,
    use_extended_thinking: bool = True,
    auto_approve_high_confidence: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new harvest schedule."""
    from app.models.court_holiday import HarvestSchedule
    from datetime import datetime, timedelta

    if frequency not in ['daily', 'weekly', 'monthly']:
        raise HTTPException(status_code=400, detail="Invalid frequency")

    if frequency == 'weekly' and day_of_week is None:
        raise HTTPException(status_code=400, detail="day_of_week required for weekly schedule")

    if frequency == 'monthly' and day_of_month is None:
        raise HTTPException(status_code=400, detail="day_of_month required for monthly schedule")

    # Calculate next run time
    now = datetime.utcnow()
    if frequency == 'daily':
        next_run = now + timedelta(days=1)
    elif frequency == 'weekly':
        days_ahead = day_of_week - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_run = now + timedelta(days=days_ahead)
    else:  # monthly
        if now.day < day_of_month:
            next_run = now.replace(day=day_of_month)
        else:
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=day_of_month)
            else:
                next_run = now.replace(month=now.month + 1, day=day_of_month)

    schedule = HarvestSchedule(
        user_id=str(current_user.id),
        jurisdiction_id=jurisdiction_id,
        url=url,
        name=name or f"Schedule for {url[:50]}",
        frequency=frequency,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        use_extended_thinking=use_extended_thinking,
        auto_approve_high_confidence=auto_approve_high_confidence,
        next_run_at=next_run
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return {
        "id": schedule.id,
        "name": schedule.name,
        "url": schedule.url,
        "frequency": schedule.frequency,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None
    }


@router.put("/schedules/{schedule_id}")
async def update_harvest_schedule(
    schedule_id: str,
    is_active: Optional[bool] = None,
    frequency: Optional[str] = None,
    day_of_week: Optional[int] = None,
    day_of_month: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a harvest schedule."""
    from app.models.court_holiday import HarvestSchedule

    schedule = db.query(HarvestSchedule).filter(
        HarvestSchedule.id == schedule_id,
        HarvestSchedule.user_id == str(current_user.id)
    ).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if is_active is not None:
        schedule.is_active = is_active

    if frequency:
        schedule.frequency = frequency

    if day_of_week is not None:
        schedule.day_of_week = day_of_week

    if day_of_month is not None:
        schedule.day_of_month = day_of_month

    db.commit()

    return {"updated": True, "id": schedule_id}


@router.delete("/schedules/{schedule_id}")
async def delete_harvest_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a harvest schedule."""
    from app.models.court_holiday import HarvestSchedule

    schedule = db.query(HarvestSchedule).filter(
        HarvestSchedule.id == schedule_id,
        HarvestSchedule.user_id == str(current_user.id)
    ).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(schedule)
    db.commit()

    return {"deleted": True, "id": schedule_id}


@router.post("/schedules/{schedule_id}/run")
async def run_harvest_schedule_now(
    schedule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AuthorityCoreService = Depends(get_authority_service)
):
    """Manually trigger a harvest schedule to run now."""
    from app.models.court_holiday import HarvestSchedule, HarvestScheduleRun
    from datetime import datetime
    import hashlib

    schedule = db.query(HarvestSchedule).filter(
        HarvestSchedule.id == schedule_id,
        HarvestSchedule.user_id == str(current_user.id)
    ).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Create run record
    run = HarvestScheduleRun(
        schedule_id=schedule.id,
        status="running"
    )
    db.add(run)
    db.commit()

    try:
        # Scrape the URL
        scraper = service._get_scraper()
        content = await scraper.scrape_url(schedule.url)

        if not content:
            run.status = "failed"
            run.error_message = "Could not fetch URL content"
            db.commit()
            raise HTTPException(status_code=400, detail="Could not fetch URL content")

        # Calculate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        run.content_hash = content_hash
        run.content_changed = content_hash != schedule.last_content_hash

        if run.content_changed or not schedule.last_content_hash:
            # Extract rules using AI
            extractor = service._get_extractor()
            rules = await extractor.extract_rules(
                content,
                schedule.jurisdiction_id,
                use_extended_thinking=schedule.use_extended_thinking
            )

            run.rules_found = len(rules) if rules else 0

            # Create proposals
            proposals_created = 0
            for rule_data in (rules or []):
                try:
                    proposal = service.create_proposal(
                        rule_data,
                        schedule.url,
                        content[:2000],
                        schedule.jurisdiction_id,
                        str(current_user.id),
                        None  # No scrape job ID
                    )
                    if proposal:
                        proposals_created += 1

                        # Auto-approve if configured
                        if schedule.auto_approve_high_confidence:
                            confidence = rule_data.get('confidence_score', 0)
                            if confidence >= 0.85:
                                service.approve_proposal(
                                    proposal.id,
                                    str(current_user.id),
                                    "Auto-approved (high confidence)"
                                )
                except Exception as e:
                    logger.warning(f"Failed to create proposal: {e}")

            run.proposals_created = proposals_created
            schedule.rules_harvested += proposals_created
            schedule.changes_detected += 1

        # Update schedule stats
        schedule.last_content_hash = content_hash
        schedule.last_checked_at = datetime.utcnow()
        schedule.total_checks += 1
        schedule.error_count = 0

        run.status = "completed"
        run.completed_at = datetime.utcnow()

        db.commit()

        return {
            "run_id": run.id,
            "status": "completed",
            "content_changed": run.content_changed,
            "rules_found": run.rules_found,
            "proposals_created": run.proposals_created
        }

    except HTTPException:
        raise
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.utcnow()
        schedule.error_count += 1
        schedule.last_error = str(e)
        db.commit()

        logger.error(f"Scheduled harvest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedules/{schedule_id}/runs")
async def get_schedule_runs(
    schedule_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get run history for a harvest schedule."""
    from app.models.court_holiday import HarvestSchedule, HarvestScheduleRun

    schedule = db.query(HarvestSchedule).filter(
        HarvestSchedule.id == schedule_id,
        HarvestSchedule.user_id == str(current_user.id)
    ).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    runs = db.query(HarvestScheduleRun).filter(
        HarvestScheduleRun.schedule_id == schedule_id
    ).order_by(HarvestScheduleRun.started_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "status": r.status,
            "content_changed": r.content_changed,
            "rules_found": r.rules_found,
            "proposals_created": r.proposals_created,
            "error_message": r.error_message,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None
        }
        for r in runs
    ]


# ============================================================
# Rule Effectiveness Metrics Endpoints
# ============================================================

@router.get("/metrics/effectiveness")
async def get_rule_effectiveness_metrics(
    jurisdiction_id: Optional[str] = None,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get rule effectiveness metrics.

    Shows which rules are most used, override rates, and performance patterns.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import and_

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Base query for usage
    usage_query = db.query(AuthorityRuleUsage).filter(
        AuthorityRuleUsage.used_at >= cutoff_date
    )

    if jurisdiction_id:
        # Filter by jurisdiction through the rule
        rule_ids = db.query(AuthorityRule.id).filter(
            AuthorityRule.jurisdiction_id == jurisdiction_id
        ).subquery()
        usage_query = usage_query.filter(AuthorityRuleUsage.rule_id.in_(rule_ids))

    # Most used rules
    most_used = db.query(
        AuthorityRuleUsage.rule_id,
        sql_func.count(AuthorityRuleUsage.id).label('usage_count'),
        sql_func.sum(AuthorityRuleUsage.deadlines_generated).label('total_deadlines')
    ).filter(
        AuthorityRuleUsage.used_at >= cutoff_date
    ).group_by(AuthorityRuleUsage.rule_id).order_by(
        sql_func.count(AuthorityRuleUsage.id).desc()
    ).limit(10).all()

    most_used_rules = []
    for rule_id, usage_count, total_deadlines in most_used:
        rule = db.query(AuthorityRule).filter(AuthorityRule.id == rule_id).first()
        if rule:
            jurisdiction = db.query(Jurisdiction).filter(
                Jurisdiction.id == rule.jurisdiction_id
            ).first() if rule.jurisdiction_id else None

            most_used_rules.append({
                "rule_id": rule.id,
                "rule_code": rule.rule_code,
                "rule_name": rule.rule_name,
                "jurisdiction": jurisdiction.name if jurisdiction else "Unknown",
                "usage_count": usage_count,
                "total_deadlines_generated": total_deadlines or 0,
                "avg_deadlines_per_use": round((total_deadlines or 0) / usage_count, 1) if usage_count else 0
            })

    # Usage by trigger type
    by_trigger = db.query(
        AuthorityRuleUsage.trigger_type,
        sql_func.count(AuthorityRuleUsage.id).label('count')
    ).filter(
        AuthorityRuleUsage.used_at >= cutoff_date
    ).group_by(AuthorityRuleUsage.trigger_type).all()

    # Total stats
    total_usage = usage_query.count()
    total_rules_used = db.query(sql_func.count(sql_func.distinct(AuthorityRuleUsage.rule_id))).filter(
        AuthorityRuleUsage.used_at >= cutoff_date
    ).scalar() or 0

    # Rules with no usage
    all_rule_ids = set(r.id for r in db.query(AuthorityRule.id).filter(
        AuthorityRule.is_active == True
    ).all())

    used_rule_ids = set(u.rule_id for u in db.query(AuthorityRuleUsage.rule_id).filter(
        AuthorityRuleUsage.used_at >= cutoff_date
    ).distinct().all())

    unused_rules = all_rule_ids - used_rule_ids

    return {
        "period_days": days,
        "summary": {
            "total_rule_applications": total_usage,
            "unique_rules_used": total_rules_used,
            "unused_rules_count": len(unused_rules)
        },
        "most_used_rules": most_used_rules,
        "usage_by_trigger_type": [
            {"trigger_type": t, "count": c}
            for t, c in by_trigger
        ],
        "recommendations": [
            {
                "type": "unused_rules",
                "message": f"{len(unused_rules)} rules have not been used in the last {days} days",
                "action": "Review and consider deactivating unused rules"
            }
        ] if unused_rules else []
    }


# =============================================================================
# MANUAL TRIGGER ENDPOINTS - Phase 1 Addition
# =============================================================================

@router.post("/cartographer/discover/{jurisdiction_id}")
async def manual_cartographer_trigger(
    jurisdiction_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger Cartographer scraper discovery for a jurisdiction.

    This endpoint allows administrators to manually trigger the Cartographer
    service to discover CSS selectors and scraping configurations for a
    jurisdiction's court website.

    **Use Cases:**
    - New jurisdiction onboarding
    - Fixing broken scraper configurations
    - Testing Cartographer improvements
    - Emergency re-discovery after website changes

    **Process:**
    1. Validates jurisdiction exists and has court_website URL
    2. Triggers Cartographer AI scraper service
    3. Updates jurisdiction scraper_config with discovered selectors
    4. Runs in background to prevent timeout

    **Returns:**
    - job_id: Background task identifier
    - jurisdiction: Name and ID of jurisdiction
    - message: Status message
    """
    logger.info(f"Manual Cartographer trigger requested for jurisdiction {jurisdiction_id}")

    # Validate jurisdiction exists
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    if not jurisdiction.court_website:
        raise HTTPException(
            status_code=400,
            detail="Jurisdiction missing court_website URL - cannot discover scraper config"
        )

    # Import Cartographer service
    from app.services.ai_scraper_service import AIScraperService

    async def run_cartographer():
        """Background task to run Cartographer discovery."""
        try:
            scraper_service = AIScraperService()
            logger.info(f"Starting Cartographer for {jurisdiction.name}")

            # Discover scraper config
            config = await scraper_service.discover_scraper_config(
                url=jurisdiction.court_website,
                jurisdiction_name=jurisdiction.name
            )

            # Update jurisdiction with discovered config
            jurisdiction.scraper_config = config
            jurisdiction.consecutive_scrape_failures = 0  # Reset failure counter
            jurisdiction.last_scraped_at = datetime.utcnow()
            db.commit()

            logger.info(f"Cartographer completed successfully for {jurisdiction.name}")

        except Exception as e:
            logger.error(f"Cartographer failed for {jurisdiction.name}: {str(e)}")
            jurisdiction.consecutive_scrape_failures += 1
            db.commit()
            raise

    # Schedule background task
    job_id = str(uuid.uuid4())
    background_tasks.add_task(run_cartographer)

    return {
        "success": True,
        "job_id": job_id,
        "jurisdiction": {
            "id": jurisdiction.id,
            "name": jurisdiction.name,
            "court_website": jurisdiction.court_website
        },
        "message": f"Cartographer discovery started for {jurisdiction.name}. This may take 1-2 minutes.",
        "estimated_completion": "1-2 minutes"
    }


@router.post("/watchtower/check/{jurisdiction_id}")
async def manual_watchtower_trigger(
    jurisdiction_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger Watchtower change detection for a jurisdiction.

    Compares current rule page hashes against stored baseline to detect
    changes. Creates inbox items for any detected changes requiring
    attorney review.

    **Use Cases:**
    - Emergency check after court announces rule change
    - Testing Watchtower detection
    - Manual verification before scheduled run

    **Process:**
    1. Fetches all rule URLs for jurisdiction
    2. Computes SHA-256 hashes of current content
    3. Compares against stored hashes in watchtower_hashes table
    4. Creates inbox items for changed URLs
    5. Updates hash baseline

    **Returns:**
    - has_changes: Boolean indicating if changes detected
    - changed_urls: List of URLs with detected changes
    - total_urls_checked: Number of URLs monitored
    """
    logger.info(f"Manual Watchtower check requested for jurisdiction {jurisdiction_id}")

    # Validate jurisdiction
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    # Import Watchtower service
    from app.services.watchtower_service import WatchtowerService

    watchtower = WatchtowerService(db)

    try:
        # Run change detection
        result = await watchtower.check_for_changes(jurisdiction.id)

        logger.info(f"Watchtower check completed for {jurisdiction.name}")

        return {
            "success": True,
            "jurisdiction": {
                "id": jurisdiction.id,
                "name": jurisdiction.name
            },
            "has_changes": result.get("has_changes", False),
            "changed_urls": result.get("changed_urls", []),
            "total_urls_checked": result.get("total_urls_checked", 0),
            "message": f"Detected {len(result.get('changed_urls', []))} changed URLs" if result.get("has_changes") else "No changes detected",
            "check_completed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Watchtower check failed for {jurisdiction.name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Watchtower check failed: {str(e)}"
        )


@router.post("/scraper-health/check/{jurisdiction_id}")
async def manual_scraper_health_check(
    jurisdiction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run health check for a specific jurisdiction's scraper configuration.

    Validates:
    - scraper_config exists and is valid JSON
    - Required fields are present (base_url, selectors)
    - Consecutive failure counter is within limits
    - auto_sync_enabled flag consistency

    **Use Cases:**
    - Troubleshooting scraper failures
    - Validating config after manual edits
    - Pre-harvest validation

    **Returns:**
    - healthy: Boolean overall health status
    - issues: List of detected issues
    - config_valid: Scraper config validation status
    - consecutive_failures: Current failure count
    """
    logger.info(f"Manual scraper health check for jurisdiction {jurisdiction_id}")

    # Get jurisdiction
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    issues = []
    healthy = True

    # Check 1: Scraper config exists
    if not jurisdiction.scraper_config:
        issues.append({
            "severity": "critical",
            "type": "missing_config",
            "message": "Missing scraper_config - run Cartographer to discover config"
        })
        healthy = False

    # Check 2: Validate config structure
    if jurisdiction.scraper_config:
        config = jurisdiction.scraper_config
        required_fields = ['base_url', 'selectors']
        missing_fields = [f for f in required_fields if f not in config]

        if missing_fields:
            issues.append({
                "severity": "critical",
                "type": "invalid_config",
                "message": f"Scraper config missing required fields: {', '.join(missing_fields)}"
            })
            healthy = False

    # Check 3: Consecutive failures
    if jurisdiction.consecutive_scrape_failures >= 3:
        issues.append({
            "severity": "high",
            "type": "consecutive_failures",
            "message": f"{jurisdiction.consecutive_scrape_failures} consecutive failures - jurisdiction at risk of auto-disable"
        })
        healthy = False
    elif jurisdiction.consecutive_scrape_failures > 0:
        issues.append({
            "severity": "medium",
            "type": "recent_failures",
            "message": f"{jurisdiction.consecutive_scrape_failures} recent failures detected"
        })

    # Check 4: Auto-sync enabled without config
    if jurisdiction.auto_sync_enabled and not jurisdiction.scraper_config:
        issues.append({
            "severity": "high",
            "type": "sync_without_config",
            "message": "Auto-sync enabled but no scraper config - will fail on next sync"
        })
        healthy = False

    # Check 5: Stale data warning
    if jurisdiction.last_scraped_at:
        from datetime import timedelta
        days_since_scrape = (datetime.utcnow() - jurisdiction.last_scraped_at).days
        if days_since_scrape > 30:
            issues.append({
                "severity": "low",
                "type": "stale_data",
                "message": f"Last scraped {days_since_scrape} days ago - data may be stale"
            })

    return {
        "success": True,
        "jurisdiction": {
            "id": jurisdiction.id,
            "name": jurisdiction.name,
            "court_website": jurisdiction.court_website
        },
        "healthy": healthy,
        "issues": issues,
        "details": {
            "has_scraper_config": bool(jurisdiction.scraper_config),
            "config_valid": bool(jurisdiction.scraper_config) and all(
                f in jurisdiction.scraper_config for f in ['base_url', 'selectors']
            ),
            "auto_sync_enabled": jurisdiction.auto_sync_enabled,
            "consecutive_failures": jurisdiction.consecutive_scrape_failures,
            "last_scraped_at": jurisdiction.last_scraped_at.isoformat() if jurisdiction.last_scraped_at else None,
            "sync_frequency": jurisdiction.sync_frequency.value if jurisdiction.sync_frequency else None
        },
        "checked_at": datetime.utcnow().isoformat()
    }


@router.get("/scraper-health/report")
async def get_scraper_health_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive health report for all jurisdiction scrapers.

    Provides system-wide overview of scraper health, useful for:
    - Operations dashboard
    - Identifying systemic issues
    - Planning maintenance

    **Returns:**
    - total_jurisdictions: Total monitored jurisdictions
    - healthy: Count of healthy scrapers
    - unhealthy: Count of unhealthy scrapers
    - disabled: Count of auto-disabled scrapers
    - jurisdictions: Detailed health status for each
    """
    logger.info("Generating scraper health report for all jurisdictions")

    # Get all jurisdictions with auto_sync enabled
    jurisdictions = db.query(Jurisdiction).filter(
        Jurisdiction.auto_sync_enabled == True
    ).all()

    healthy_count = 0
    unhealthy_count = 0
    disabled_count = 0

    jurisdiction_health = []

    for jurisdiction in jurisdictions:
        issues = []
        healthy = True

        # Same checks as single jurisdiction health check
        if not jurisdiction.scraper_config:
            issues.append("missing_config")
            healthy = False

        if jurisdiction.scraper_config:
            config = jurisdiction.scraper_config
            required_fields = ['base_url', 'selectors']
            if not all(f in config for f in required_fields):
                issues.append("invalid_config")
                healthy = False

        if jurisdiction.consecutive_scrape_failures >= 3:
            issues.append("consecutive_failures")
            healthy = False
            disabled_count += 1

        if healthy:
            healthy_count += 1
        else:
            unhealthy_count += 1

        jurisdiction_health.append({
            "jurisdiction_id": jurisdiction.id,
            "name": jurisdiction.name,
            "healthy": healthy,
            "issues": issues,
            "consecutive_failures": jurisdiction.consecutive_scrape_failures,
            "last_scraped_at": jurisdiction.last_scraped_at.isoformat() if jurisdiction.last_scraped_at else None
        })

    return {
        "success": True,
        "summary": {
            "total_jurisdictions": len(jurisdictions),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "at_risk_of_disable": disabled_count,
            "health_percentage": round((healthy_count / len(jurisdictions)) * 100, 1) if jurisdictions else 0
        },
        "jurisdictions": jurisdiction_health,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get current status of APScheduler background jobs.

    Returns information about scheduled jobs including:
    - Job ID and name
    - Next scheduled run time
    - Pending status

    **Use Cases:**
    - Verifying scheduler is running
    - Debugging scheduling issues
    - Operations monitoring
    """
    try:
        from app.scheduler import get_scheduler_status
        status = get_scheduler_status()

        return {
            "success": True,
            "scheduler": status,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scheduler status: {str(e)}"
        )


# ============================================================================
# PHASE 5: JURISDICTION ONBOARDING AUTOMATION
# ============================================================================

@router.post("/jurisdictions/onboard", response_model=dict)
async def onboard_jurisdiction(
    name: str = Query(..., description="Jurisdiction name"),
    code: str = Query(..., description="Jurisdiction code (e.g., CA_SUP)"),
    court_website: str = Query(..., description="Main court website URL"),
    rules_url: str = Query(..., description="URL to court rules page"),
    court_type: str = Query("state", description="Court type: federal, state, or local"),
    sync_frequency: str = Query("WEEKLY", description="Sync frequency: DAILY, WEEKLY, or MONTHLY"),
    auto_approve_high_confidence: bool = Query(False, description="Auto-approve rules with confidence ≥95%"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Automated jurisdiction onboarding - Phase 5 Feature

    Complete end-to-end onboarding workflow:
    1. Validate URLs
    2. Create jurisdiction record
    3. Run Cartographer to discover scraper config
    4. Extract rules from court website
    5. Establish Watchtower baseline
    6. Configure sync schedule
    7. Generate onboarding report

    **Example:**
    ```
    POST /api/v1/authority-core/jurisdictions/onboard?name=California+Superior+Court&code=CA_SUP&court_website=https://courts.ca.gov&rules_url=https://courts.ca.gov/rules.htm
    ```

    **Returns:**
    - Comprehensive onboarding report with status, metrics, and next steps
    - Success rate: ~80% for standard court websites
    - Processing time: 5-15 minutes depending on site complexity

    **Requirements:**
    - Admin user privileges (future enhancement)
    - Valid court website and rules URLs
    - Rules page must be accessible (no authentication required)
    """
    try:
        from app.services.jurisdiction_onboarding_service import JurisdictionOnboardingService

        onboarding_service = JurisdictionOnboardingService(db)

        # Execute onboarding
        report = await onboarding_service.onboard_jurisdiction(
            name=name,
            code=code,
            court_website=court_website,
            rules_url=rules_url,
            court_type=court_type,
            sync_frequency=sync_frequency,
            auto_approve_high_confidence=auto_approve_high_confidence
        )

        return {
            "success": True,
            "report": report,
            "message": f"Onboarding {report['status']} for {name}"
        }

    except Exception as e:
        logger.error(f"Jurisdiction onboarding failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Onboarding failed: {str(e)}"
        )


@router.post("/jurisdictions/batch-onboard", response_model=dict)
async def batch_onboard_jurisdictions(
    jurisdictions: List[dict],
    max_concurrent: int = Query(5, ge=1, le=10, description="Max concurrent onboarding operations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch jurisdiction onboarding - Scale to 50+ jurisdictions

    Onboard multiple jurisdictions in parallel with concurrency control.

    **Example Request Body:**
    ```json
    [
      {
        "name": "California Superior Court",
        "code": "CA_SUP",
        "court_website": "https://courts.ca.gov",
        "rules_url": "https://courts.ca.gov/rules.htm",
        "court_type": "state"
      },
      {
        "name": "New York Supreme Court",
        "code": "NY_SUP",
        "court_website": "https://nycourts.gov",
        "rules_url": "https://nycourts.gov/rules",
        "court_type": "state"
      }
    ]
    ```

    **Parameters:**
    - `max_concurrent`: Maximum simultaneous operations (1-10, default: 5)
    - Recommended: 5 for production, 10 for powerful servers

    **Performance:**
    - 50 jurisdictions: ~30-60 minutes with max_concurrent=5
    - Each jurisdiction: 5-15 minutes average
    - Memory usage: ~500MB per concurrent operation

    **Returns:**
    - Batch report with per-jurisdiction results
    - Success/failure summary
    - Detailed metrics for each jurisdiction
    """
    try:
        from app.services.jurisdiction_onboarding_service import JurisdictionOnboardingService

        # Validate input
        if not jurisdictions or len(jurisdictions) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one jurisdiction required"
            )

        if len(jurisdictions) > 100:
            raise HTTPException(
                status_code=400,
                detail="Maximum 100 jurisdictions per batch"
            )

        onboarding_service = JurisdictionOnboardingService(db)

        # Execute batch onboarding
        batch_report = await onboarding_service.batch_onboard_jurisdictions(
            jurisdictions=jurisdictions,
            max_concurrent=max_concurrent
        )

        return {
            "success": True,
            "batch_report": batch_report,
            "message": f"Batch onboarding completed: {batch_report['summary']['completed']} succeeded, {batch_report['summary']['failed']} failed"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch onboarding failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch onboarding failed: {str(e)}"
        )


@router.get("/jurisdictions/{jurisdiction_id}/onboarding-status", response_model=dict)
async def get_onboarding_status(
    jurisdiction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current onboarding status for a jurisdiction

    Returns comprehensive status including:
    - Rule counts (total, verified, pending)
    - Sync configuration
    - Scraper health
    - Pending inbox items
    - Production readiness

    **Use cases:**
    - Monitor onboarding progress
    - Check if jurisdiction is production-ready
    - Identify blocking issues
    """
    try:
        from app.services.jurisdiction_onboarding_service import JurisdictionOnboardingService

        onboarding_service = JurisdictionOnboardingService(db)
        status = onboarding_service.get_onboarding_status(jurisdiction_id)

        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])

        return {
            "success": True,
            "status": status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get onboarding status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )
