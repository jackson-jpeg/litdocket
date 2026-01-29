"""
Rule Proposals API

Phase 2 endpoints for managing AI-proposed deadline rules.

These endpoints allow attorneys to:
1. View pending rule proposals
2. Approve proposals (converting them to active rules)
3. Reject proposals with reason
4. Modify and approve proposals
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from app.database import get_db
from app.models.user import User
from app.models.rule_proposal import RuleProposal
from app.models.jurisdiction import RuleTemplate, RuleTemplateDeadline, RuleSet
from app.models.enums import RuleProposalStatus
from app.utils.auth import get_current_user
from app.services.rule_discovery_service import get_rule_discovery_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ===================
# PYDANTIC MODELS
# ===================

class ProposalApproveRequest(BaseModel):
    """Request body for approving a proposal."""
    user_notes: Optional[str] = None
    # Optional overrides for the proposal
    override_days: Optional[int] = None
    override_priority: Optional[str] = None
    override_citation: Optional[str] = None


class ProposalRejectRequest(BaseModel):
    """Request body for rejecting a proposal."""
    reason: str


class ProposalModifyRequest(BaseModel):
    """Request body for modifying and approving a proposal."""
    proposed_days: int
    proposed_priority: Optional[str] = "standard"
    citation: Optional[str] = None
    user_notes: Optional[str] = None


class ResearchDeadlinesRequest(BaseModel):
    """Request body for triggering deadline research."""
    document_type: str
    jurisdiction: str = "florida_state"
    court: Optional[str] = None
    document_text: Optional[str] = None


# ===================
# LIST PROPOSALS
# ===================

@router.get("")
async def list_rule_proposals(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, modified"),
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List rule proposals for the current user.

    Returns proposals sorted by creation date (newest first).
    """
    query = db.query(RuleProposal).filter(
        RuleProposal.user_id == str(current_user.id)
    )

    # Apply filters
    if status:
        query = query.filter(RuleProposal.status == status)

    if case_id:
        query = query.filter(RuleProposal.case_id == case_id)

    # Get total count
    total = query.count()

    # Get paginated results
    proposals = query.order_by(desc(RuleProposal.created_at)).offset(skip).limit(limit).all()

    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "proposals": [p.to_dict() for p in proposals],
        "pending_count": db.query(RuleProposal).filter(
            RuleProposal.user_id == str(current_user.id),
            RuleProposal.status == "pending"
        ).count(),
    }


# ===================
# GET SINGLE PROPOSAL
# ===================

@router.get("/{proposal_id}")
async def get_rule_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single rule proposal by ID."""
    proposal = db.query(RuleProposal).filter(
        RuleProposal.id == proposal_id,
        RuleProposal.user_id == str(current_user.id)
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return {
        "success": True,
        "proposal": proposal.to_dict(),
    }


# ===================
# APPROVE PROPOSAL
# ===================

@router.post("/{proposal_id}/approve")
async def approve_rule_proposal(
    proposal_id: str,
    request: ProposalApproveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve a rule proposal.

    This converts the proposal into an active rule template that will be
    used for future documents of the same type.
    """
    proposal = db.query(RuleProposal).filter(
        RuleProposal.id == proposal_id,
        RuleProposal.user_id == str(current_user.id)
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Proposal cannot be approved - current status is '{proposal.status}'"
        )

    try:
        # Apply any overrides
        final_days = request.override_days or proposal.proposed_days
        final_priority = request.override_priority or proposal.proposed_priority
        final_citation = request.override_citation or proposal.citation

        # Create a user-level rule template from the proposal
        # Note: This creates a draft rule that could be promoted to firm-wide
        rule_template = _create_rule_from_proposal(
            db=db,
            proposal=proposal,
            days=final_days,
            priority=final_priority,
            citation=final_citation,
            created_by=str(current_user.id),
        )

        # Update proposal status
        proposal.status = RuleProposalStatus.APPROVED.value
        proposal.reviewed_by = str(current_user.id)
        proposal.reviewed_at = datetime.utcnow()
        proposal.user_notes = request.user_notes
        proposal.created_rule_template_id = rule_template.id if rule_template else None

        db.commit()
        db.refresh(proposal)

        logger.info(f"Approved proposal {proposal_id} - created rule template {rule_template.id if rule_template else 'N/A'}")

        return {
            "success": True,
            "message": "Proposal approved and rule created",
            "proposal": proposal.to_dict(),
            "created_rule_template_id": rule_template.id if rule_template else None,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to approve proposal {proposal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve proposal: {str(e)}")


# ===================
# REJECT PROPOSAL
# ===================

@router.post("/{proposal_id}/reject")
async def reject_rule_proposal(
    proposal_id: str,
    request: ProposalRejectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject a rule proposal.

    The proposal will be marked as rejected and can be reviewed later
    if needed. The rejection reason is stored for future reference.
    """
    proposal = db.query(RuleProposal).filter(
        RuleProposal.id == proposal_id,
        RuleProposal.user_id == str(current_user.id)
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Proposal cannot be rejected - current status is '{proposal.status}'"
        )

    try:
        proposal.status = RuleProposalStatus.REJECTED.value
        proposal.reviewed_by = str(current_user.id)
        proposal.reviewed_at = datetime.utcnow()
        proposal.user_notes = request.reason

        db.commit()
        db.refresh(proposal)

        logger.info(f"Rejected proposal {proposal_id}: {request.reason}")

        return {
            "success": True,
            "message": "Proposal rejected",
            "proposal": proposal.to_dict(),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reject proposal {proposal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reject proposal: {str(e)}")


# ===================
# MODIFY AND APPROVE
# ===================

@router.put("/{proposal_id}/modify")
async def modify_rule_proposal(
    proposal_id: str,
    request: ProposalModifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modify a proposal and approve it.

    Use this when the AI's proposal is close but needs adjustment
    (e.g., wrong number of days or priority).
    """
    proposal = db.query(RuleProposal).filter(
        RuleProposal.id == proposal_id,
        RuleProposal.user_id == str(current_user.id)
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Proposal cannot be modified - current status is '{proposal.status}'"
        )

    try:
        # Create rule with modified values
        rule_template = _create_rule_from_proposal(
            db=db,
            proposal=proposal,
            days=request.proposed_days,
            priority=request.proposed_priority or "standard",
            citation=request.citation,
            created_by=str(current_user.id),
        )

        # Update proposal status
        proposal.status = RuleProposalStatus.MODIFIED.value
        proposal.reviewed_by = str(current_user.id)
        proposal.reviewed_at = datetime.utcnow()
        proposal.user_notes = request.user_notes
        proposal.created_rule_template_id = rule_template.id if rule_template else None

        # Also update the proposal with the modified values
        proposal.proposed_days = request.proposed_days
        proposal.proposed_priority = request.proposed_priority
        proposal.citation = request.citation

        db.commit()
        db.refresh(proposal)

        logger.info(f"Modified and approved proposal {proposal_id}")

        return {
            "success": True,
            "message": "Proposal modified and approved",
            "proposal": proposal.to_dict(),
            "created_rule_template_id": rule_template.id if rule_template else None,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to modify proposal {proposal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to modify proposal: {str(e)}")


# ===================
# TRIGGER RESEARCH
# ===================

@router.post("/research")
async def research_deadlines(
    request: ResearchDeadlinesRequest,
    case_id: Optional[str] = Query(None),
    document_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger deadline research for a document type.

    This is called when a user clicks "Research Deadlines" for an
    unrecognized document. The system will:
    1. Search for applicable rules
    2. Synthesize a proposal using AI
    3. Check for conflicts
    4. Save the proposal for review
    """
    service = get_rule_discovery_service(db)

    result = await service.research_deadline_rule(
        document_type=request.document_type,
        jurisdiction=request.jurisdiction,
        court=request.court,
        document_text=request.document_text,
        case_id=case_id,
        document_id=document_id,
        user_id=str(current_user.id),
    )

    if not result.success:
        return {
            "success": False,
            "message": result.research_summary,
            "error": result.error,
        }

    return {
        "success": True,
        "proposal_id": result.proposal_id,
        "proposal": {
            "proposed_trigger": result.proposed_trigger,
            "proposed_days": result.proposed_days,
            "proposed_priority": result.proposed_priority,
            "citation": result.citation,
            "source_text": result.source_text,
            "confidence_score": result.confidence_score,
            "conflicts": result.conflicts,
        },
        "research_summary": result.research_summary,
    }


# ===================
# HELPER FUNCTIONS
# ===================

def _create_rule_from_proposal(
    db: Session,
    proposal: RuleProposal,
    days: int,
    priority: str,
    citation: Optional[str],
    created_by: str,
) -> Optional[RuleTemplate]:
    """
    Create a rule template from an approved proposal.

    The rule is created with:
    - status='draft' (not yet promoted to firm-wide)
    - is_official=False (AI-discovered, not official court rule)
    - created_by=user_id
    """
    import uuid

    try:
        # Create a unique rule code
        rule_code = f"AI-{uuid.uuid4().hex[:8].upper()}"

        # For now, create without linking to a RuleSet
        # In the future, this could be linked to a user-specific or firm-specific rule set
        rule_template = RuleTemplate(
            id=str(uuid.uuid4()),
            rule_code=rule_code,
            name=proposal.proposed_trigger,
            description=f"AI-discovered rule for {proposal.proposed_trigger}",
            trigger_type=proposal.proposed_trigger_type or "custom_trigger",
            citation=citation,
            court_type="civil",  # Default, could be enhanced
            case_types=["civil"],
            is_active=True,
            # Phase 2 fields
            status="draft",
            is_official=False,
            created_by=created_by,
            research_sources=proposal.research_sources or [],
            conflict_notes=str(proposal.conflicts) if proposal.conflicts else None,
        )

        db.add(rule_template)

        # Create the deadline definition
        deadline = RuleTemplateDeadline(
            id=str(uuid.uuid4()),
            rule_template_id=rule_template.id,
            name=f"Response to {proposal.proposed_trigger}",
            description=f"Response deadline for {proposal.proposed_trigger}",
            days_from_trigger=days,
            priority=priority,
            party_responsible="defendant",  # Default, could be enhanced
            action_required=f"File response to {proposal.proposed_trigger}",
            calculation_method=proposal.proposed_calculation_method or "calendar_days",
        )

        db.add(deadline)
        db.flush()

        logger.info(f"Created rule template {rule_template.id} from proposal")
        return rule_template

    except Exception as e:
        logger.error(f"Failed to create rule from proposal: {e}")
        return None
