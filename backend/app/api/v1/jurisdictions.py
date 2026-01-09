"""
Jurisdiction and Rule Set API Endpoints

Provides endpoints for:
- Listing jurisdictions and rule sets
- Detecting jurisdiction from document text
- Managing case rule set assignments
- Calculating deadlines from triggers with proper rule sets
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.auth import get_current_user
from app.models.user import User
from app.models.case import Case
from app.models.jurisdiction import (
    Jurisdiction, RuleSet, RuleSetDependency, CourtLocation,
    RuleTemplate, RuleTemplateDeadline, CaseRuleSet,
    JurisdictionType, CourtType
)
from app.schemas.jurisdiction import (
    JurisdictionResponse, JurisdictionWithChildren,
    RuleSetResponse, RuleSetWithDependencies,
    CourtLocationResponse, CourtLocationWithRules,
    RuleTemplateResponse, RuleTemplateWithDeadlines,
    JurisdictionDetectionRequest, JurisdictionDetectionResult,
    CaseRuleSetCreate, CaseRuleSetResponse,
    TriggerTypeEnum
)
from app.services.jurisdiction_detector import JurisdictionDetector, DetectionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jurisdictions", tags=["Jurisdictions"])


# ============================================================
# Jurisdiction Endpoints
# ============================================================

@router.get("", response_model=List[JurisdictionResponse])
async def list_jurisdictions(
    jurisdiction_type: Optional[JurisdictionType] = None,
    state: Optional[str] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all jurisdictions with optional filtering
    """
    query = db.query(Jurisdiction)

    if not include_inactive:
        query = query.filter(Jurisdiction.is_active == True)

    if jurisdiction_type:
        query = query.filter(Jurisdiction.jurisdiction_type == jurisdiction_type)

    if state:
        query = query.filter(Jurisdiction.state == state.upper())

    jurisdictions = query.order_by(Jurisdiction.name).all()
    return jurisdictions


@router.get("/{jurisdiction_id}", response_model=JurisdictionWithChildren)
async def get_jurisdiction(
    jurisdiction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific jurisdiction with its children and rule sets
    """
    jurisdiction = db.query(Jurisdiction).filter(
        Jurisdiction.id == jurisdiction_id
    ).first()

    if not jurisdiction:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")

    return jurisdiction


# ============================================================
# Rule Set Endpoints
# ============================================================

@router.get("/rule-sets", response_model=List[RuleSetResponse])
async def list_rule_sets(
    jurisdiction_id: Optional[str] = None,
    court_type: Optional[CourtType] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all rule sets with optional filtering
    """
    query = db.query(RuleSet)

    if not include_inactive:
        query = query.filter(RuleSet.is_active == True)

    if jurisdiction_id:
        query = query.filter(RuleSet.jurisdiction_id == jurisdiction_id)

    if court_type:
        query = query.filter(RuleSet.court_type == court_type)

    rule_sets = query.order_by(RuleSet.code).all()
    return rule_sets


@router.get("/rule-sets/{rule_set_id}", response_model=RuleSetWithDependencies)
async def get_rule_set(
    rule_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific rule set with its dependencies and templates
    """
    rule_set = db.query(RuleSet).filter(
        RuleSet.id == rule_set_id
    ).first()

    if not rule_set:
        raise HTTPException(status_code=404, detail="Rule set not found")

    return rule_set


@router.get("/rule-sets/{rule_set_id}/templates", response_model=List[RuleTemplateWithDeadlines])
async def get_rule_set_templates(
    rule_set_id: str,
    trigger_type: Optional[TriggerTypeEnum] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all rule templates for a rule set
    """
    query = db.query(RuleTemplate).filter(
        RuleTemplate.rule_set_id == rule_set_id,
        RuleTemplate.is_active == True
    )

    if trigger_type:
        from app.models.jurisdiction import TriggerType
        query = query.filter(RuleTemplate.trigger_type == TriggerType(trigger_type.value))

    templates = query.order_by(RuleTemplate.name).all()
    return templates


# ============================================================
# Court Location Endpoints
# ============================================================

@router.get("/court-locations", response_model=List[CourtLocationResponse])
async def list_court_locations(
    jurisdiction_id: Optional[str] = None,
    court_type: Optional[CourtType] = None,
    district: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all court locations with optional filtering
    """
    query = db.query(CourtLocation).filter(CourtLocation.is_active == True)

    if jurisdiction_id:
        query = query.filter(CourtLocation.jurisdiction_id == jurisdiction_id)

    if court_type:
        query = query.filter(CourtLocation.court_type == court_type)

    if district:
        query = query.filter(CourtLocation.district == district)

    locations = query.order_by(CourtLocation.name).all()
    return locations


@router.get("/court-locations/{location_id}", response_model=CourtLocationWithRules)
async def get_court_location(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific court location with its applicable rule sets
    """
    location = db.query(CourtLocation).filter(
        CourtLocation.id == location_id
    ).first()

    if not location:
        raise HTTPException(status_code=404, detail="Court location not found")

    # Get all applicable rule sets
    detector = JurisdictionDetector(db)
    applicable_rule_sets = detector._get_applicable_rule_sets(
        location.jurisdiction,
        location,
        location.court_type
    )

    # Convert to response format
    response = CourtLocationWithRules(
        **{k: v for k, v in location.__dict__.items() if not k.startswith('_')},
        default_rule_set=location.default_rule_set,
        local_rule_set=location.local_rule_set,
        all_applicable_rule_sets=applicable_rule_sets
    )

    return response


# ============================================================
# Jurisdiction Detection Endpoints
# ============================================================

@router.post("/detect", response_model=JurisdictionDetectionResult)
async def detect_jurisdiction(
    request: JurisdictionDetectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Detect jurisdiction from document text

    Analyzes the provided text and returns:
    - Detected jurisdiction (if found)
    - Detected court location (if matched)
    - All applicable rule sets (including dependencies)
    - Detection confidence score
    """
    detector = JurisdictionDetector(db)

    result = detector.detect_from_text(
        text=request.text,
        case_number=request.case_number,
        court_name=request.court_name
    )

    return JurisdictionDetectionResult(
        detected=result.detected,
        confidence=result.confidence,
        jurisdiction=result.jurisdiction,
        court_location=result.court_location,
        applicable_rule_sets=result.applicable_rule_sets,
        detected_court_name=result.detected_court_name,
        detected_district=result.detected_district,
        detected_case_number=result.detected_case_number,
        matched_patterns=result.matched_patterns
    )


# ============================================================
# Case Rule Set Management
# ============================================================

@router.get("/cases/{case_id}/rule-sets", response_model=List[CaseRuleSetResponse])
async def get_case_rule_sets(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all rule sets assigned to a case
    """
    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    assignments = db.query(CaseRuleSet).filter(
        CaseRuleSet.case_id == case_id,
        CaseRuleSet.is_active == True
    ).all()

    # If no manual assignments, auto-detect from case
    if not assignments:
        detector = JurisdictionDetector(db)
        rule_sets = detector.get_rule_sets_for_case(case_id)

        # Return detected rule sets as response
        return [
            CaseRuleSetResponse(
                id=f"auto-{rs.id}",
                case_id=case_id,
                rule_set_id=rs.id,
                assignment_method="auto_detected",
                priority=0,
                is_active=True,
                created_at=case.created_at,
                rule_set=rs
            )
            for rs in rule_sets
        ]

    # Return manual assignments with rule set details
    for assignment in assignments:
        assignment.rule_set = db.query(RuleSet).get(assignment.rule_set_id)

    return assignments


@router.post("/cases/{case_id}/rule-sets", response_model=CaseRuleSetResponse)
async def assign_rule_set_to_case(
    case_id: str,
    request: CaseRuleSetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually assign a rule set to a case
    """
    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Verify rule set exists
    rule_set = db.query(RuleSet).filter(
        RuleSet.id == request.rule_set_id,
        RuleSet.is_active == True
    ).first()

    if not rule_set:
        raise HTTPException(status_code=404, detail="Rule set not found")

    # Check if already assigned
    existing = db.query(CaseRuleSet).filter(
        CaseRuleSet.case_id == case_id,
        CaseRuleSet.rule_set_id == request.rule_set_id
    ).first()

    if existing:
        # Reactivate if inactive
        existing.is_active = True
        existing.assignment_method = request.assignment_method
        db.commit()
        db.refresh(existing)
        existing.rule_set = rule_set
        return existing

    # Create new assignment
    import uuid
    assignment = CaseRuleSet(
        id=str(uuid.uuid4()),
        case_id=case_id,
        rule_set_id=request.rule_set_id,
        assignment_method=request.assignment_method,
        priority=request.priority
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    assignment.rule_set = rule_set
    return assignment


@router.delete("/cases/{case_id}/rule-sets/{rule_set_id}")
async def remove_rule_set_from_case(
    case_id: str,
    rule_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a rule set assignment from a case
    """
    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Find and deactivate assignment
    assignment = db.query(CaseRuleSet).filter(
        CaseRuleSet.case_id == case_id,
        CaseRuleSet.rule_set_id == rule_set_id
    ).first()

    if assignment:
        assignment.is_active = False
        db.commit()

    return {"status": "success", "message": "Rule set removed from case"}


# ============================================================
# Seed Data Endpoint (Admin only - for initial setup)
# ============================================================

@router.post("/seed")
async def seed_jurisdiction_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Seed the database with Florida and Federal rule sets

    This should only be run once during initial setup.
    """
    try:
        from app.seed.rule_sets import run_seed
        run_seed(db)
        return {"status": "success", "message": "Seed data created successfully"}
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        raise HTTPException(status_code=500, detail=f"Error seeding data: {str(e)}")
