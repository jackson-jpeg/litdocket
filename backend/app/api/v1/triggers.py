"""
Trigger API - Trigger-based deadline generation

This module handles trigger-based deadline generation with Authority Core integration.
The Authority Core rules database is queried first, with fallback to hardcoded rules.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from datetime import date as date_type, datetime, timedelta
from pydantic import BaseModel
import os

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.deadline import Deadline
from app.models.jurisdiction import Jurisdiction
from app.utils.auth import get_current_user
from app.services.rules_engine import rules_engine, TriggerType
from app.services.calendar_service import calendar_service
from app.services.case_summary_service import CaseSummaryService
from app.services.authority_integrated_deadline_service import (
    AuthorityIntegratedDeadlineService,
    USE_AUTHORITY_CORE
)
import logging

logger = logging.getLogger(__name__)


def get_jurisdiction_id(db: Session, jurisdiction_name: str) -> Optional[str]:
    """
    Look up jurisdiction_id from jurisdiction name.

    Maps common jurisdiction strings (e.g., "florida_state", "federal") to
    the actual Jurisdiction table UUID.

    Args:
        db: Database session
        jurisdiction_name: Jurisdiction name string (e.g., "florida_state")

    Returns:
        Jurisdiction UUID or None if not found
    """
    if not jurisdiction_name:
        return None

    # Try exact match first
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.name.ilike(jurisdiction_name)
    ).first()

    if jurisdiction:
        return jurisdiction.id

    # Try matching by code or common names
    name_mappings = {
        "florida_state": ["Florida State", "Florida", "FL"],
        "federal": ["Federal", "US Federal"],
        "us_district": ["US District Court", "Federal District"],
    }

    search_terms = name_mappings.get(jurisdiction_name.lower(), [jurisdiction_name])
    for term in search_terms:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.name.ilike(f"%{term}%")
        ).first()
        if jurisdiction:
            return jurisdiction.id

    return None

router = APIRouter()


# ============================================================================
# TRIGGER TYPE DEFINITIONS
# Friendly names + metadata for the TriggerType enum
# Used by SmartEventEntry command bar for autocomplete
# ============================================================================

TRIGGER_TYPE_METADATA = {
    TriggerType.TRIAL_DATE: {
        "name": "Trial Date",
        "friendly_name": "Start of Jury Trial",
        "description": "Set trial date to generate all pretrial deadlines (expert disclosures, motions in limine, witness lists, etc.)",
        "category": "trial",
        "icon": "gavel",
        "example": "June 15, 2025",
        "generates_approx": 47,
    },
    TriggerType.COMPLAINT_SERVED: {
        "name": "Complaint Served",
        "friendly_name": "Service of Complaint on Defendant",
        "description": "Date complaint was served on defendant - triggers answer deadline and discovery timeline",
        "category": "pleading",
        "icon": "file-text",
        "example": "Defendant served on March 1",
        "generates_approx": 23,
    },
    TriggerType.SERVICE_COMPLETED: {
        "name": "Service Completed",
        "friendly_name": "Service of Process Completed",
        "description": "Service of process completed on all defendants",
        "category": "pleading",
        "icon": "check-circle",
        "example": "All defendants served",
        "generates_approx": 15,
    },
    TriggerType.CASE_FILED: {
        "name": "Case Filed",
        "friendly_name": "Case Filing Date",
        "description": "Date case was filed with the court - starts statute of limitations calculations",
        "category": "pleading",
        "icon": "folder-plus",
        "example": "Complaint filed January 15",
        "generates_approx": 8,
    },
    TriggerType.ANSWER_DUE: {
        "name": "Answer Due",
        "friendly_name": "Answer Deadline",
        "description": "Defendant's answer due date - triggers discovery and responsive pleading deadlines",
        "category": "pleading",
        "icon": "file-edit",
        "example": "Answer due in 20 days",
        "generates_approx": 12,
    },
    TriggerType.DISCOVERY_COMMENCED: {
        "name": "Discovery Commenced",
        "friendly_name": "Start of Discovery Period",
        "description": "Discovery period begins - triggers interrogatories, RFPs, deposition deadlines",
        "category": "discovery",
        "icon": "search",
        "example": "Discovery opens after initial disclosures",
        "generates_approx": 18,
    },
    TriggerType.DISCOVERY_DEADLINE: {
        "name": "Discovery Deadline",
        "friendly_name": "Discovery Cutoff Date",
        "description": "Last day to complete discovery - triggers expert disclosure and deposition deadlines",
        "category": "discovery",
        "icon": "calendar-clock",
        "example": "Discovery closes 60 days before trial",
        "generates_approx": 15,
    },
    TriggerType.DISPOSITIVE_MOTIONS_DUE: {
        "name": "Dispositive Motions Due",
        "friendly_name": "Summary Judgment Deadline",
        "description": "Deadline for filing dispositive motions (MSJ, MTD) - triggers response and reply deadlines",
        "category": "motion",
        "icon": "scale",
        "example": "MSJ due 90 days before trial",
        "generates_approx": 8,
    },
    TriggerType.MOTION_FILED: {
        "name": "Motion Filed",
        "friendly_name": "Motion Filing Date",
        "description": "Date motion was filed - triggers response deadline (typically 14-21 days)",
        "category": "motion",
        "icon": "file-signature",
        "example": "Motion to Compel filed",
        "generates_approx": 5,
    },
    TriggerType.HEARING_SCHEDULED: {
        "name": "Hearing Scheduled",
        "friendly_name": "Motion Hearing Date",
        "description": "Hearing date set - triggers exhibit exchange, witness disclosure, trial prep deadlines",
        "category": "motion",
        "icon": "calendar",
        "example": "Hearing on May 10 at 9:00 AM",
        "generates_approx": 6,
    },
    TriggerType.PRETRIAL_CONFERENCE: {
        "name": "Pretrial Conference",
        "friendly_name": "Pretrial Conference Date",
        "description": "Pretrial/calendar call date - triggers joint pretrial statement deadlines",
        "category": "trial",
        "icon": "users",
        "example": "Final pretrial conference 2 weeks before trial",
        "generates_approx": 10,
    },
    TriggerType.ORDER_ENTERED: {
        "name": "Order Entered",
        "friendly_name": "Court Order Entry Date",
        "description": "Date court order was entered - triggers compliance deadlines and appeal windows",
        "category": "other",
        "icon": "stamp",
        "example": "Order granting MSJ entered",
        "generates_approx": 4,
    },
    TriggerType.APPEAL_FILED: {
        "name": "Appeal Filed",
        "friendly_name": "Notice of Appeal Filed",
        "description": "Notice of appeal filed - triggers appellate briefing schedule",
        "category": "appellate",
        "icon": "arrow-up-circle",
        "example": "Appeal to 11th Circuit filed",
        "generates_approx": 12,
    },
    TriggerType.MEDIATION_SCHEDULED: {
        "name": "Mediation Scheduled",
        "friendly_name": "Mediation Conference Date",
        "description": "Mediation date set - triggers mediation statement and document exchange deadlines",
        "category": "other",
        "icon": "handshake",
        "example": "Mediation scheduled for April 20",
        "generates_approx": 5,
    },
    TriggerType.CUSTOM_TRIGGER: {
        "name": "Custom Event",
        "friendly_name": "Custom Trigger Event",
        "description": "User-defined trigger event with custom deadline rules",
        "category": "other",
        "icon": "plus-circle",
        "example": "Any custom event",
        "generates_approx": 0,
    },
}


class CreateTriggerRequest(BaseModel):
    case_id: str
    trigger_type: str
    trigger_date: str  # ISO format YYYY-MM-DD
    jurisdiction: str  # "federal", "florida_state"
    court_type: str  # "civil", "criminal", "appellate"
    service_method: Optional[str] = "email"
    rule_template_id: Optional[str] = None  # If specific template desired
    notes: Optional[str] = None
    # SmartEventEntry overrides - allows user to customize dates before saving
    overrides: Optional[dict[str, str]] = None  # { "deadline_title": "2025-01-15" }
    exclusions: Optional[List[str]] = None  # ["deadline_title_1", "deadline_title_2"]
    # CONVERSATIONAL INTAKE: User-provided context for conditional deadline filtering
    context: Optional[dict[str, Any]] = None  # { "jury_status": true, "trial_duration_days": 3 }


class UpdateTriggerRequest(BaseModel):
    new_trigger_date: str  # ISO format YYYY-MM-DD
    modification_reason: str


class RuleTemplateResponse(BaseModel):
    rule_id: str
    name: str
    description: str
    jurisdiction: str
    court_type: str
    trigger_type: str
    citation: str
    num_dependent_deadlines: int


class PreviewTriggerRequest(BaseModel):
    """Request schema for previewing trigger deadlines before creation"""
    trigger_type: str
    trigger_date: str  # ISO format YYYY-MM-DD
    jurisdiction: str  # "federal", "florida_state"
    court_type: str  # "civil", "criminal", "appellate"
    service_method: Optional[str] = "email"


@router.get("/types")
def get_trigger_types(
    q: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    GET /api/v1/triggers/types - Command bar autocomplete endpoint

    Returns all trigger types with friendly names mapped to TriggerType enum.
    Used by SmartEventEntry cmdk-style command bar.

    Performance: Single dict lookup, no database queries - instant response (<10ms)

    Query params:
        q: Optional search query to filter by name/description
        category: Optional category filter (trial, pleading, discovery, motion, appellate, other)

    Returns: List of trigger types with metadata for UI rendering
    """
    results = []

    for trigger_type, metadata in TRIGGER_TYPE_METADATA.items():
        # Apply category filter
        if category and metadata["category"] != category:
            continue

        # Apply search filter (fuzzy match on name, friendly_name, description)
        if q:
            q_lower = q.lower()
            searchable = f"{metadata['name']} {metadata['friendly_name']} {metadata['description']}".lower()
            if q_lower not in searchable:
                continue

        results.append({
            "id": trigger_type.value,
            "trigger_type": trigger_type.value,
            "name": metadata["name"],
            "friendly_name": metadata["friendly_name"],
            "description": metadata["description"],
            "category": metadata["category"],
            "icon": metadata["icon"],
            "example": metadata["example"],
            "generates_approx": metadata["generates_approx"],
        })

    # Sort by category priority, then by name
    category_order = {"trial": 0, "pleading": 1, "discovery": 2, "motion": 3, "appellate": 4, "other": 5}
    results.sort(key=lambda x: (category_order.get(x["category"], 99), x["name"]))

    return {
        "success": True,
        "count": len(results),
        "types": results
    }


# ============================================================================
# SIMULATE ENDPOINT - Pre-Flight Audit for Deadline Calculation
# Returns calculated deadlines WITHOUT saving to database
# ============================================================================

class SimulateTriggerRequest(BaseModel):
    """Request schema for simulating trigger deadlines (Pre-Flight Audit)"""
    trigger_type: str
    trigger_date: str  # ISO format YYYY-MM-DD
    case_id: str
    service_method: Optional[str] = "email"


class SimulatedDeadline(BaseModel):
    """A simulated deadline returned by the simulate endpoint"""
    title: str
    description: str
    deadline_date: str  # ISO format
    priority: str
    party_role: str
    action_required: str
    rule_citation: str
    calculation_basis: str
    trigger_formula: str
    days_count: int
    calculation_type: str
    short_explanation: str


@router.post("/simulate")
async def simulate_trigger_deadlines(
    request: SimulateTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/triggers/simulate - Pre-Flight Audit endpoint

    Simulates deadline calculation for a trigger event WITHOUT saving to database.
    Powers the Pre-Flight Audit UI where users can preview 50+ deadlines before committing.

    **Authority Core Integration**: Queries Authority Core rules first, with fallback
    to hardcoded rules if no Authority rules exist for this jurisdiction/trigger.

    Request:
        trigger_type: One of TriggerType enum values (e.g., "trial_date")
        trigger_date: ISO format date (e.g., "2025-06-15")
        case_id: UUID of the case
        service_method: Optional service method ("email", "mail", "personal")

    Returns:
        List of calculated deadlines with:
        - title: CompuLaw-style title
        - description: Full description with trigger formula
        - deadline_date: Calculated date
        - priority: FATAL, CRITICAL, IMPORTANT, STANDARD, INFORMATIONAL
        - party_role: Who is responsible
        - action_required: What needs to be done
        - rule_citation: Legal rule citation
        - calculation_basis: Full calculation explanation
        - trigger_formula: CompuLaw-style formula (e.g., "triggered 90 Days before $TR")
        - days_count: Number of days from trigger
        - calculation_type: calendar_days or court_days
        - short_explanation: Brief explanation for UI
        - source_rule_id: Authority Core rule ID (if from Authority Core)
        - source: "authority_core" or "system_rules"

    Constraint: Does NOT save to database - this is a preview/simulation only.
    """
    # Validate trigger_type
    try:
        trigger_type_enum = TriggerType(request.trigger_type)
    except ValueError:
        valid_types = [t.value for t in TriggerType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger_type. Must be one of: {valid_types}"
        )

    # Parse trigger date
    try:
        trigger_date = datetime.strptime(request.trigger_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid trigger_date format. Use YYYY-MM-DD"
        )

    # Get case for jurisdiction and court_type (with ownership check)
    case = db.query(Case).filter(
        Case.id == request.case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Determine jurisdiction and court_type from case
    jurisdiction = case.jurisdiction or "florida_state"
    jurisdiction_id = get_jurisdiction_id(db, jurisdiction)  # Look up from jurisdiction name
    court_type = case.case_type or "civil"

    # Map common case_type values to rules engine court_type
    court_type_map = {
        "personal_injury": "civil",
        "contract_dispute": "civil",
        "real_estate": "civil",
        "employment": "civil",
        "criminal": "criminal",
        "appellate": "appellate",
    }
    court_type = court_type_map.get(court_type.lower(), court_type.lower())

    # Build case context for CompuLaw-style formatting
    case_context = {
        "case_number": case.case_number,
        "plaintiffs": [case.plaintiff] if case.plaintiff else [],
        "defendants": [case.defendant] if case.defendant else [],
        "source_document": None,
        "case_type": court_type,
    }

    # Use Authority-Integrated Deadline Service
    integrated_service = AuthorityIntegratedDeadlineService(db)
    integrated_deadlines = await integrated_service.calculate_deadlines(
        jurisdiction_id=jurisdiction_id or "",
        trigger_type=request.trigger_type,
        trigger_date=trigger_date,
        jurisdiction_name=jurisdiction,
        court_type=court_type,
        service_method=request.service_method or "email",
        case_context=case_context
    )

    if not integrated_deadlines:
        # Return empty but successful response if no rules found
        logger.warning(
            f"No rule templates found for {trigger_type_enum.value} in "
            f"{jurisdiction}/{court_type}"
        )
        return {
            "success": True,
            "trigger_type": request.trigger_type,
            "trigger_date": request.trigger_date,
            "case_id": request.case_id,
            "jurisdiction": jurisdiction,
            "court_type": court_type,
            "deadlines_count": 0,
            "deadlines": [],
            "source": "none",
            "message": f"No rule templates found for {trigger_type_enum.value} in {jurisdiction}/{court_type}"
        }

    # Determine source (Authority Core or System Rules)
    has_authority_source = any(d.source_rule_id for d in integrated_deadlines)
    source = "authority_core" if has_authority_source else "system_rules"

    # Format response - convert to serializable format
    formatted_deadlines = []
    for deadline in integrated_deadlines:
        formatted_deadlines.append({
            "title": deadline.title,
            "description": deadline.description,
            "deadline_date": deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            "priority": deadline.priority,
            "party_role": deadline.party_role,
            "action_required": deadline.action_required,
            "rule_citation": deadline.rule_citation,
            "calculation_basis": deadline.calculation_basis,
            "trigger_formula": deadline.trigger_formula or "",
            "days_count": deadline.days_count,
            "calculation_type": deadline.calculation_type,
            "short_explanation": deadline.short_explanation or "",
            # Extra fields for UI
            "trigger_event": deadline.trigger_event,
            "trigger_date": deadline.trigger_date.isoformat() if deadline.trigger_date else trigger_date.isoformat(),
            "jurisdiction": deadline.jurisdiction or jurisdiction,
            "court_type": deadline.court_type or court_type,
            "trigger_code": deadline.trigger_code or "",
            "party_string": deadline.party_string or "",
            # Authority Core tracking
            "source_rule_id": deadline.source_rule_id,
            "source_rule_name": deadline.source_rule_name,
            "source": "authority_core" if deadline.source_rule_id else "system_rules",
        })

    # Sort by deadline_date
    formatted_deadlines.sort(key=lambda d: d["deadline_date"] or "9999-12-31")

    logger.info(
        f"Simulated {len(formatted_deadlines)} deadlines for {trigger_type_enum.value} "
        f"on {trigger_date} for case {request.case_id} (source: {source})"
    )

    return {
        "success": True,
        "trigger_type": request.trigger_type,
        "trigger_date": request.trigger_date,
        "case_id": request.case_id,
        "case_number": case.case_number,
        "jurisdiction": jurisdiction,
        "court_type": court_type,
        "deadlines_count": len(formatted_deadlines),
        "deadlines": formatted_deadlines,
        "source": source,
        "authority_core_enabled": USE_AUTHORITY_CORE,
    }


@router.get("/event-types")
def get_event_types(
    jurisdiction: Optional[str] = None,
    court_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all available event types for SmartEventEntry.
    Returns event types with categories, deadline counts, and descriptions.
    """
    templates = rules_engine.get_all_templates()

    # Filter if requested
    if jurisdiction:
        templates = [t for t in templates if t.jurisdiction == jurisdiction]
    if court_type:
        templates = [t for t in templates if t.court_type == court_type]

    # Build event types with categories
    event_types = []
    seen_types = set()

    # Category mapping based on trigger type
    category_map = {
        'trial_date': 'trial',
        'complaint_served': 'pleading',
        'summons_served': 'pleading',
        'answer_filed': 'pleading',
        'discovery_cutoff': 'discovery',
        'deposition_notice': 'discovery',
        'motion_filed': 'motion',
        'motion_hearing': 'motion',
        'appeal_filed': 'appellate',
        'notice_of_appeal': 'appellate',
    }

    for template in templates:
        trigger_type = template.trigger_type.value
        if trigger_type in seen_types:
            continue
        seen_types.add(trigger_type)

        # Determine category
        category = category_map.get(trigger_type, 'other')

        event_types.append({
            'id': trigger_type,
            'name': template.name,
            'description': template.description,
            'category': category,
            'deadline_count': len(template.dependent_deadlines),
            'jurisdiction': template.jurisdiction,
            'court_type': template.court_type,
            'citation': template.citation
        })

    # Sort by category then name
    category_order = ['trial', 'pleading', 'discovery', 'motion', 'appellate', 'other']
    event_types.sort(key=lambda e: (category_order.index(e['category']) if e['category'] in category_order else 99, e['name']))

    return event_types


@router.post("/preview")
async def preview_trigger_deadlines(
    request: PreviewTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview deadlines that would be created by a trigger without saving.
    Used by SmartEventEntry for live cascade preview.

    **Authority Core Integration**: Queries Authority Core rules first, with fallback
    to hardcoded rules if no Authority rules exist for this jurisdiction/trigger.
    """
    logger.info(f"Previewing trigger: type={request.trigger_type}, date={request.trigger_date}")

    # Parse trigger date
    try:
        trigger_date = date_type.fromisoformat(request.trigger_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Get trigger type enum
    try:
        trigger_enum = TriggerType(request.trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger type: {request.trigger_type}"
        )

    # Build case context for CompuLaw-style formatting
    case_context = {
        'plaintiffs': [],
        'defendants': [],
        'case_number': 'Preview',
        'source_document': f"Trigger Event: {request.trigger_type}",
        'case_type': request.court_type,
    }

    # Use Authority-Integrated Deadline Service
    # Note: jurisdiction_id is empty for preview since we don't have a case context
    integrated_service = AuthorityIntegratedDeadlineService(db)
    integrated_deadlines = await integrated_service.calculate_deadlines(
        jurisdiction_id="",  # No specific jurisdiction ID for preview
        trigger_type=request.trigger_type,
        trigger_date=trigger_date,
        jurisdiction_name=request.jurisdiction,
        court_type=request.court_type,
        service_method=request.service_method or "email",
        case_context=case_context
    )

    if not integrated_deadlines:
        return {
            'success': True,
            'trigger_type': request.trigger_type,
            'trigger_date': trigger_date.isoformat(),
            'deadlines': [],
            'source': 'none'
        }

    # Determine source
    has_authority_source = any(d.source_rule_id for d in integrated_deadlines)
    source = "authority_core" if has_authority_source else "system_rules"

    # Format response
    all_deadlines = []
    for deadline in integrated_deadlines:
        all_deadlines.append({
            'title': deadline.title,
            'description': deadline.description,
            'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            'priority': deadline.priority,
            'rule_citation': deadline.rule_citation,
            'calculation_basis': deadline.calculation_basis,
            'party_role': deadline.party_role,
            'action_required': deadline.action_required,
            # Authority Core tracking
            'source_rule_id': deadline.source_rule_id,
            'source': "authority_core" if deadline.source_rule_id else "system_rules",
        })

    # Sort by deadline date
    all_deadlines.sort(key=lambda d: d['deadline_date'] or '9999-12-31')

    return {
        'success': True,
        'trigger_type': request.trigger_type,
        'trigger_date': trigger_date.isoformat(),
        'deadlines': all_deadlines,
        'source': source,
        'authority_core_enabled': USE_AUTHORITY_CORE,
    }


@router.get("/templates")
def get_available_templates(
    jurisdiction: Optional[str] = None,
    court_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all available rule templates"""
    templates = rules_engine.get_all_templates()

    # Filter if requested
    if jurisdiction:
        templates = [t for t in templates if t.jurisdiction == jurisdiction]
    if court_type:
        templates = [t for t in templates if t.court_type == court_type]

    return [
        RuleTemplateResponse(
            rule_id=t.rule_id,
            name=t.name,
            description=t.description,
            jurisdiction=t.jurisdiction,
            court_type=t.court_type,
            trigger_type=t.trigger_type.value,
            citation=t.citation,
            num_dependent_deadlines=len(t.dependent_deadlines)
        )
        for t in templates
    ]


@router.post("/create")
async def create_trigger_event(
    request: CreateTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a trigger event and generate all dependent deadlines

    This is the "magic" - enter one date, get 50+ deadlines auto-calculated

    **Authority Core Integration**: Queries Authority Core rules first, with fallback
    to hardcoded rules if no Authority rules exist. Each deadline created will have
    its `source_rule_id` populated if it came from an Authority Core rule.
    """
    logger.info(f"Creating trigger: type={request.trigger_type}, date={request.trigger_date}, case={request.case_id}")

    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == request.case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Parse trigger date
    try:
        trigger_date = date_type.fromisoformat(request.trigger_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Validate trigger type
    try:
        trigger_enum = TriggerType(request.trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger type: {request.trigger_type}"
        )

    # Get jurisdiction info from case
    jurisdiction_name = case.jurisdiction or request.jurisdiction or "florida_state"
    jurisdiction_id = get_jurisdiction_id(db, jurisdiction_name)  # Look up from jurisdiction name
    court_type = case.case_type or request.court_type or "civil"

    # Map common case_type values to rules engine court_type
    court_type_map = {
        "personal_injury": "civil",
        "contract_dispute": "civil",
        "real_estate": "civil",
        "employment": "civil",
        "criminal": "criminal",
        "appellate": "appellate",
    }
    court_type = court_type_map.get(court_type.lower(), court_type.lower())

    # Build case context for CompuLaw-style formatting
    case_context = {
        'plaintiffs': [],
        'defendants': [],
        'case_number': case.case_number,
        'source_document': request.notes or f"Trigger Event: {request.trigger_type}",
        'case_type': court_type,
    }

    # Extract party names from case.parties (if available)
    if case.parties:
        for party in case.parties:
            party_name = party.get('name', '')
            party_role = party.get('role', '').lower()
            if party_name:
                if 'plaintiff' in party_role:
                    case_context['plaintiffs'].append(party_name)
                elif 'defendant' in party_role:
                    case_context['defendants'].append(party_name)

    # CONVERSATIONAL INTAKE: Merge user-provided context for conditional deadline filtering
    # User context contains answers like {"jury_status": true, "trial_duration_days": 3}
    if request.context:
        case_context.update(request.context)
        logger.info(f"Using conversational context: {request.context}")

    # Use Authority-Integrated Deadline Service
    integrated_service = AuthorityIntegratedDeadlineService(db)
    integrated_deadlines = await integrated_service.calculate_deadlines(
        jurisdiction_id=jurisdiction_id or "",
        trigger_type=request.trigger_type,
        trigger_date=trigger_date,
        jurisdiction_name=jurisdiction_name,
        court_type=court_type,
        service_method=request.service_method or "email",
        case_context=case_context,
        user_id=str(current_user.id),
        case_id=request.case_id
    )

    if not integrated_deadlines:
        raise HTTPException(
            status_code=404,
            detail=f"No rule templates found for {jurisdiction_name} {court_type} {request.trigger_type}"
        )

    # Determine source for logging
    has_authority_source = any(d.source_rule_id for d in integrated_deadlines)
    source = "authority_core" if has_authority_source else "system_rules"
    logger.info(f"Using {len(integrated_deadlines)} deadlines from {source}")

    # Create the trigger deadline (the "parent")
    trigger_deadline = Deadline(
        case_id=request.case_id,
        user_id=str(current_user.id),
        title=f"{request.trigger_type.replace('_', ' ').title()}",
        description=f"Trigger event: {request.trigger_type}. {request.notes if request.notes else ''}".strip(),
        deadline_date=trigger_date,
        trigger_event=request.trigger_type,
        trigger_date=trigger_date,
        is_calculated=False,
        is_dependent=False,
        priority="important",
        status="completed"  # Trigger already happened
    )

    db.add(trigger_deadline)
    db.flush()  # Get ID for parent reference

    # Generate all dependent deadlines
    all_dependent_deadlines = []

    for deadline_data in integrated_deadlines:
        title = deadline_data.title

        # Check if this deadline is excluded
        if request.exclusions and title in request.exclusions:
            logger.info(f"Excluding deadline: {title}")
            continue

        # Check for date override
        final_date = deadline_data.deadline_date
        is_overridden = False

        if request.overrides and title in request.overrides:
            try:
                override_date = date_type.fromisoformat(request.overrides[title])
                final_date = override_date
                is_overridden = True
                logger.info(f"Override applied for '{title}': {deadline_data.deadline_date} -> {override_date}")
            except ValueError:
                logger.warning(f"Invalid override date for '{title}': {request.overrides[title]}")

        deadline = Deadline(
            case_id=request.case_id,
            user_id=str(current_user.id),
            parent_deadline_id=str(trigger_deadline.id),
            title=title,
            description=deadline_data.description,
            deadline_date=final_date,
            priority=deadline_data.priority,
            party_role=deadline_data.party_role,
            action_required=deadline_data.action_required,
            applicable_rule=deadline_data.rule_citation,
            rule_citation=deadline_data.source_citation,  # Full citation text
            calculation_basis=deadline_data.calculation_basis,
            trigger_event=deadline_data.trigger_event,
            trigger_date=deadline_data.trigger_date,
            is_calculated=True,
            is_dependent=True,
            auto_recalculate=not is_overridden,  # Don't auto-recalculate if manually overridden
            is_manually_overridden=is_overridden,
            original_deadline_date=deadline_data.deadline_date,
            service_method=request.service_method,
            # Authority Core integration - link to source rule
            source_rule_id=deadline_data.source_rule_id,
        )

        db.add(deadline)
        all_dependent_deadlines.append(deadline)

    db.commit()

    # Update case summary to reflect trigger creation
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=request.case_id,
            event_type="trigger_created",
            event_details={
                "trigger_id": str(trigger_deadline.id),
                "trigger_type": request.trigger_type,
                "trigger_date": trigger_date.isoformat(),
                "deadlines_created": len(all_dependent_deadlines),
                "source": source,
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'trigger_deadline_id': str(trigger_deadline.id),
        'trigger_date': trigger_date.isoformat(),
        'dependent_deadlines_created': len(all_dependent_deadlines),
        'source': source,
        'authority_core_enabled': USE_AUTHORITY_CORE,
        'deadlines': [
            {
                'id': str(d.id),
                'title': d.title,
                'deadline_date': d.deadline_date.isoformat() if d.deadline_date else None,
                'priority': d.priority,
                'rule_citation': d.applicable_rule,
                'source_rule_id': d.source_rule_id,
                'source': 'authority_core' if d.source_rule_id else 'system_rules',
            }
            for d in all_dependent_deadlines
        ]
    }


@router.patch("/{trigger_deadline_id}/recalculate")
async def recalculate_dependent_deadlines(
    trigger_deadline_id: str,
    request: UpdateTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retroactive Recalculation - Automatic cascade updates
    If the trigger date changes, all 50+ dependent deadlines shift instantly
    """

    # Get trigger deadline
    trigger = db.query(Deadline).filter(
        Deadline.id == trigger_deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger deadline not found")

    # Parse new trigger date
    try:
        new_trigger_date = date_type.fromisoformat(request.new_trigger_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    old_trigger_date = trigger.deadline_date

    # Update trigger deadline
    trigger.deadline_date = new_trigger_date
    trigger.trigger_date = new_trigger_date
    trigger.modified_by = current_user.email
    trigger.modification_reason = request.modification_reason

    # Get all dependent deadlines
    dependent_deadlines = db.query(Deadline).filter(
        Deadline.parent_deadline_id == trigger_deadline_id,
        Deadline.auto_recalculate == True
    ).all()

    # Recalculate each dependent deadline
    updated_deadlines = []

    for deadline in dependent_deadlines:
        if not deadline.original_deadline_date or not old_trigger_date:
            continue

        # Calculate the offset from original trigger
        days_offset = (deadline.original_deadline_date - old_trigger_date).days

        # Apply same offset to new trigger date
        new_deadline_date = new_trigger_date + timedelta(days=days_offset)

        # Adjust for holidays/weekends
        # Determine jurisdiction from case
        case = db.query(Case).filter(Case.id == deadline.case_id).first()
        jurisdiction = case.jurisdiction if case and case.jurisdiction else "florida_state"

        new_deadline_date = calendar_service.adjust_for_holidays_and_weekends(
            new_deadline_date,
            jurisdiction=jurisdiction
        )

        # Update deadline
        deadline.deadline_date = new_deadline_date
        deadline.trigger_date = new_trigger_date
        deadline.modified_by = current_user.email
        deadline.modification_reason = f"Trigger date changed: {request.modification_reason}"

        updated_deadlines.append({
            'id': str(deadline.id),
            'title': deadline.title,
            'old_date': deadline.original_deadline_date.isoformat() if deadline.original_deadline_date else None,
            'new_date': new_deadline_date.isoformat()
        })

    db.commit()

    # Update case summary to reflect trigger recalculation
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=str(trigger.case_id),
            event_type="trigger_recalculated",
            event_details={
                "trigger_id": trigger_deadline_id,
                "old_date": old_trigger_date.isoformat() if old_trigger_date else None,
                "new_date": new_trigger_date.isoformat(),
                "deadlines_updated": len(updated_deadlines)
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'trigger_deadline_id': trigger_deadline_id,
        'old_trigger_date': old_trigger_date.isoformat() if old_trigger_date else None,
        'new_trigger_date': new_trigger_date.isoformat(),
        'dependent_deadlines_updated': len(updated_deadlines),
        'updated_deadlines': updated_deadlines
    }


@router.get("/case/{case_id}/triggers")
def get_case_triggers(
    case_id: str,
    include_children: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all trigger events for a case with nested child deadlines.

    Returns a Sovereign UI-ready structure with:
    - child_deadlines: Array of all deadlines generated by this trigger
    - status_summary: Pre-calculated counts for frontend badges
    """
    try:
        logger.info(f"Getting triggers for case {case_id}, user {current_user.id}")

        # Verify case belongs to user
        case = db.query(Case).filter(
            Case.id == case_id,
            Case.user_id == str(current_user.id)
        ).first()

        if not case:
            logger.warning(f"Case {case_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Case not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying case {case_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred")

    try:
        # ============================================================================
        # PERFORMANCE FIX: Avoid N+1 query problem (Issue #4)
        # Instead of querying child deadlines for each trigger in a loop,
        # we fetch ALL deadlines for the case in a single query and group in Python.
        # This reduces database queries from O(n) to O(1) - instant response time.
        # ============================================================================

        # Single query: Get ALL trigger deadlines (non-dependent, active only)
        triggers = db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.is_dependent == False,
            Deadline.trigger_event.isnot(None),
            Deadline.status.notin_(['completed', 'cancelled'])
        ).order_by(Deadline.deadline_date.asc()).all()

        # Single query: Get ALL child deadlines for this case at once
        all_child_deadlines = db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.is_dependent == True
        ).order_by(Deadline.deadline_date.asc()).all()

        # Group child deadlines by trigger_event in Python (O(n) in-memory, no DB calls)
        child_deadlines_by_trigger: dict[str, list] = {}
        for child in all_child_deadlines:
            trigger_event = child.trigger_event or ''
            if trigger_event not in child_deadlines_by_trigger:
                child_deadlines_by_trigger[trigger_event] = []
            child_deadlines_by_trigger[trigger_event].append(child)

        logger.info(f"Found {len(triggers)} triggers and {len(all_child_deadlines)} child deadlines for case {case_id}")
        today = datetime.now().date()
        result = []

        for trigger in triggers:
            # Get child deadlines from pre-fetched dict (O(1) lookup, no DB query!)
            child_deadlines = child_deadlines_by_trigger.get(trigger.trigger_event or '', [])

            # Calculate status summary for frontend badges
            status_summary = {
                'overdue': 0,
                'pending': 0,
                'completed': 0,
                'cancelled': 0,
                'total': len(child_deadlines)
            }

            child_deadlines_data = []
            for child in child_deadlines:
                # Determine if overdue
                is_overdue = (
                    child.status == 'pending' and
                    child.deadline_date and
                    child.deadline_date < today
                )

                # Update status counts
                if is_overdue:
                    status_summary['overdue'] += 1
                elif child.status == 'pending':
                    status_summary['pending'] += 1
                elif child.status == 'completed':
                    status_summary['completed'] += 1
                elif child.status == 'cancelled':
                    status_summary['cancelled'] += 1

                if include_children:
                    child_deadlines_data.append({
                        'id': str(child.id),
                        'title': child.title,
                        'description': child.description,
                        'deadline_date': child.deadline_date.isoformat() if child.deadline_date else None,
                        'priority': child.priority,
                        'status': child.status,
                        'is_overdue': is_overdue,
                        'applicable_rule': child.applicable_rule,
                        'calculation_basis': child.calculation_basis,
                        'party_role': child.party_role,
                        'action_required': child.action_required,
                        'is_manually_overridden': child.is_manually_overridden or False,
                        'auto_recalculate': child.auto_recalculate if child.auto_recalculate is not None else True,
                    })

            result.append({
                'id': str(trigger.id),
                'trigger_type': trigger.trigger_event,
                'trigger_date': trigger.deadline_date.isoformat() if trigger.deadline_date else None,
                'title': trigger.title,
                'status': trigger.status,
                'description': trigger.description,  # Fixed: 'notes' doesn't exist, use 'description'
                'created_at': trigger.created_at.isoformat() if trigger.created_at else None,
                # Nested structure for Sovereign UI
                'status_summary': status_summary,
                'child_deadlines': child_deadlines_data if include_children else [],
                # Legacy field for backwards compatibility
                'dependent_deadlines_count': status_summary['total'],
            })

        logger.info(f"Successfully processed {len(result)} triggers for case {case_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing triggers for case {case_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing triggers")


class UpdateTriggerDateRequest(BaseModel):
    new_date: str  # ISO format YYYY-MM-DD


class CascadePreviewItem(BaseModel):
    deadline_id: str
    title: str
    current_date: str | None
    new_date: str | None
    days_changed: int
    is_manually_overridden: bool
    will_update: bool


@router.get("/{trigger_id}/preview-cascade")
def preview_cascade_changes(
    trigger_id: str,
    new_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview what deadlines would change if the trigger date is updated.
    Does not make any actual changes.
    """

    # Get trigger deadline
    trigger = db.query(Deadline).filter(
        Deadline.id == trigger_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Parse new date
    try:
        new_trigger_date = date_type.fromisoformat(new_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    old_trigger_date = trigger.deadline_date
    if not old_trigger_date:
        raise HTTPException(status_code=400, detail="Trigger has no date set")

    # Calculate days difference
    days_diff = (new_trigger_date - old_trigger_date).days

    # Get all dependent deadlines for this trigger
    dependent_deadlines = db.query(Deadline).filter(
        Deadline.trigger_event == trigger.trigger_event,
        Deadline.case_id == trigger.case_id,
        Deadline.id != trigger_id  # Exclude the trigger itself
    ).all()

    preview = []
    for deadline in dependent_deadlines:
        current_date = deadline.deadline_date
        new_deadline_date = None

        if current_date:
            new_deadline_date = current_date + timedelta(days=days_diff)

        # Check if manually overridden
        is_manually_overridden = (
            deadline.is_manually_overridden == True or
            deadline.auto_recalculate == False
        )

        # Will update if: has auto_recalculate=True, is pending, and not manually overridden
        will_update = (
            deadline.auto_recalculate == True and
            deadline.status == 'pending' and
            not is_manually_overridden
        )

        preview.append(CascadePreviewItem(
            deadline_id=str(deadline.id),
            title=deadline.title,
            current_date=current_date.isoformat() if current_date else None,
            new_date=new_deadline_date.isoformat() if new_deadline_date else None,
            days_changed=days_diff,
            is_manually_overridden=is_manually_overridden,
            will_update=will_update
        ))

    return preview


@router.patch("/{trigger_id}/update-date")
async def update_trigger_date(
    trigger_id: str,
    request: UpdateTriggerDateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update trigger date and cascade changes to dependent deadlines.
    Simpler endpoint than /recalculate - just takes the new date.
    """

    # Get trigger deadline
    trigger = db.query(Deadline).filter(
        Deadline.id == trigger_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Parse new date
    try:
        new_trigger_date = date_type.fromisoformat(request.new_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    old_trigger_date = trigger.deadline_date
    if not old_trigger_date:
        raise HTTPException(status_code=400, detail="Trigger has no date set")

    # Calculate days difference
    days_diff = (new_trigger_date - old_trigger_date).days

    # Update trigger deadline
    trigger.deadline_date = new_trigger_date
    trigger.trigger_date = new_trigger_date
    trigger.modified_by = current_user.email

    # Get all dependent deadlines that should be updated
    dependent_deadlines = db.query(Deadline).filter(
        Deadline.trigger_event == trigger.trigger_event,
        Deadline.case_id == trigger.case_id,
        Deadline.id != trigger_id,
        Deadline.auto_recalculate == True,
        Deadline.status == 'pending'
    ).all()

    # Update each dependent deadline
    updated_count = 0
    for deadline in dependent_deadlines:
        # Skip if manually overridden
        if deadline.is_manually_overridden:
            continue

        if deadline.deadline_date:
            # Determine jurisdiction from case for holiday adjustment
            case = db.query(Case).filter(Case.id == deadline.case_id).first()
            jurisdiction = case.jurisdiction if case and case.jurisdiction else "florida_state"

            new_deadline_date = deadline.deadline_date + timedelta(days=days_diff)

            # Adjust for holidays/weekends
            new_deadline_date = calendar_service.adjust_for_holidays_and_weekends(
                new_deadline_date,
                jurisdiction=jurisdiction
            )

            deadline.deadline_date = new_deadline_date
            deadline.trigger_date = new_trigger_date
            deadline.modified_by = current_user.email
            updated_count += 1

    db.commit()

    # Update case summary to reflect trigger date change
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=str(trigger.case_id),
            event_type="trigger_date_changed",
            event_details={
                "trigger_id": trigger_id,
                "old_date": old_trigger_date.isoformat(),
                "new_date": new_trigger_date.isoformat(),
                "deadlines_updated": updated_count
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'trigger_id': trigger_id,
        'old_date': old_trigger_date.isoformat(),
        'new_date': new_trigger_date.isoformat(),
        'deadlines_updated': updated_count
    }
