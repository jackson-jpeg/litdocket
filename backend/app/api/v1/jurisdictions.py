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
    TriggerTypeEnum,
    HierarchyNode, JurisdictionHierarchyResponse,
    CaseJurisdictionUpdate, JurisdictionChangeResult,
    JurisdictionTreeResponse, JurisdictionTreeItem, RuleSetTreeItem, RuleSetDependencySimple
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


# ============================================================
# Hierarchy Endpoint (CompuLaw-style cascading dropdowns)
# ============================================================

@router.get("/hierarchy", response_model=JurisdictionHierarchyResponse)
async def get_jurisdiction_hierarchy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the full jurisdiction hierarchy for cascading dropdown selection.

    Returns a tree structure:
    - Level 1 (System): Federal Courts vs State Courts
    - Level 2 (Jurisdiction): 11th Circuit (Federal) or Florida (State)
    - Level 3 (Venue/Court): M.D. Florida or Hillsborough County (13th Circuit)
    - Level 4 (Authority): Judge Cynthia Oster (if available)
    """
    from datetime import datetime

    # Build the hierarchy
    systems = []

    # Get all jurisdictions
    all_jurisdictions = db.query(Jurisdiction).filter(
        Jurisdiction.is_active == True
    ).all()

    # Get all court locations
    all_court_locations = db.query(CourtLocation).filter(
        CourtLocation.is_active == True
    ).all()

    # Get all rule sets for code lookup
    all_rule_sets = db.query(RuleSet).filter(RuleSet.is_active == True).all()
    rule_set_by_jurisdiction = {}
    for rs in all_rule_sets:
        if rs.jurisdiction_id not in rule_set_by_jurisdiction:
            rule_set_by_jurisdiction[rs.jurisdiction_id] = []
        rule_set_by_jurisdiction[rs.jurisdiction_id].append(rs.code)

    # Build System level nodes (Federal vs State)
    federal_system = HierarchyNode(
        id="system-federal",
        code="FEDERAL",
        name="Federal Courts",
        level=1,
        level_name="system",
        parent_id=None,
        children=[],
        metadata={"description": "United States Federal Court System"},
        rule_set_codes=[]
    )

    state_system = HierarchyNode(
        id="system-state",
        code="STATE",
        name="State Courts",
        level=1,
        level_name="system",
        parent_id=None,
        children=[],
        metadata={"description": "State Court Systems"},
        rule_set_codes=[]
    )

    # Build jurisdiction nodes
    for j in all_jurisdictions:
        if j.parent_jurisdiction_id is not None:
            continue  # Skip children, handle them with parents

        jurisdiction_node = HierarchyNode(
            id=j.id,
            code=j.code,
            name=j.name,
            level=2,
            level_name="jurisdiction",
            parent_id=f"system-{j.jurisdiction_type.value}" if j.jurisdiction_type in [JurisdictionType.FEDERAL, JurisdictionType.STATE] else None,
            children=[],
            metadata={
                "type": j.jurisdiction_type.value,
                "state": j.state,
                "federal_circuit": j.federal_circuit
            },
            rule_set_codes=rule_set_by_jurisdiction.get(j.id, [])
        )

        # Add court locations as children (Level 3)
        for cl in all_court_locations:
            if cl.jurisdiction_id == j.id:
                court_node = HierarchyNode(
                    id=cl.id,
                    code=cl.short_name or cl.name[:20],
                    name=cl.name,
                    level=3,
                    level_name="court",
                    parent_id=j.id,
                    children=[],  # Judge level would go here if we had judges in DB
                    metadata={
                        "court_type": cl.court_type.value if cl.court_type else None,
                        "district": cl.district,
                        "circuit": cl.circuit,
                        "division": cl.division
                    },
                    rule_set_codes=[]
                )
                # Add rule set codes from default and local
                if cl.default_rule_set_id:
                    default_rs = next((rs for rs in all_rule_sets if rs.id == cl.default_rule_set_id), None)
                    if default_rs:
                        court_node.rule_set_codes.append(default_rs.code)
                if cl.local_rule_set_id:
                    local_rs = next((rs for rs in all_rule_sets if rs.id == cl.local_rule_set_id), None)
                    if local_rs:
                        court_node.rule_set_codes.append(local_rs.code)

                jurisdiction_node.children.append(court_node)

        # Add child jurisdictions (for local courts under state)
        for child_j in all_jurisdictions:
            if child_j.parent_jurisdiction_id == j.id:
                child_node = HierarchyNode(
                    id=child_j.id,
                    code=child_j.code,
                    name=child_j.name,
                    level=3,
                    level_name="court",
                    parent_id=j.id,
                    children=[],
                    metadata={
                        "type": child_j.jurisdiction_type.value,
                        "state": child_j.state
                    },
                    rule_set_codes=rule_set_by_jurisdiction.get(child_j.id, [])
                )
                jurisdiction_node.children.append(child_node)

        # Add to appropriate system
        if j.jurisdiction_type == JurisdictionType.FEDERAL:
            federal_system.children.append(jurisdiction_node)
        elif j.jurisdiction_type == JurisdictionType.STATE:
            state_system.children.append(jurisdiction_node)

    # Collect rule set codes for systems
    for child in federal_system.children:
        federal_system.rule_set_codes.extend(child.rule_set_codes)
    for child in state_system.children:
        state_system.rule_set_codes.extend(child.rule_set_codes)

    systems = [federal_system, state_system]

    return JurisdictionHierarchyResponse(
        systems=systems,
        last_updated=datetime.utcnow()
    )


# ============================================================
# Tree Endpoint (for frontend tree selector)
# ============================================================

@router.get("/tree", response_model=JurisdictionTreeResponse)
async def get_jurisdiction_tree(
    filter_by_state: Optional[str] = Query(None, description="Filter by state code (e.g., FL)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get jurisdictions and rule sets for the tree selector.

    Returns all active jurisdictions and rule sets with their dependencies,
    formatted for the JurisdictionTreeSelector component.
    """
    try:
        # Build jurisdiction query
        j_query = db.query(Jurisdiction).filter(Jurisdiction.is_active == True)

        if filter_by_state:
            # Include federal + matching state
            j_query = j_query.filter(
                (Jurisdiction.state == filter_by_state.upper()) |
                (Jurisdiction.jurisdiction_type == JurisdictionType.FEDERAL)
            )

        jurisdictions = j_query.order_by(Jurisdiction.name).all()

        # Build rule sets query with dependencies
        rs_query = db.query(RuleSet).filter(RuleSet.is_active == True)
        rule_sets = rs_query.order_by(RuleSet.code).all()

        # Get dependencies
        dependencies = db.query(RuleSetDependency).all()
        dep_by_rule_set = {}
        for dep in dependencies:
            if dep.rule_set_id not in dep_by_rule_set:
                dep_by_rule_set[dep.rule_set_id] = []
            dep_by_rule_set[dep.rule_set_id].append(RuleSetDependencySimple(
                required_rule_set_id=dep.required_rule_set_id,
                dependency_type=dep.dependency_type.value if dep.dependency_type else "concurrent",
                priority=dep.priority or 0
            ))

        # Convert to response format
        jurisdiction_items = [
            JurisdictionTreeItem(
                id=j.id,
                code=j.code,
                name=j.name,
                jurisdiction_type=j.jurisdiction_type.value if j.jurisdiction_type else "state",
                parent_jurisdiction_id=j.parent_jurisdiction_id
            )
            for j in jurisdictions
        ]

        rule_set_items = [
            RuleSetTreeItem(
                id=rs.id,
                code=rs.code,
                name=rs.name,
                jurisdiction_id=rs.jurisdiction_id,
                court_type=rs.court_type.value if rs.court_type else None,
                is_local=rs.is_local or False,
                dependencies=dep_by_rule_set.get(rs.id, [])
            )
            for rs in rule_sets
        ]

        return JurisdictionTreeResponse(
            jurisdictions=jurisdiction_items,
            rule_sets=rule_set_items
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load jurisdiction tree: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Unable to load jurisdiction data. Please refresh or try again shortly."
        )


# ============================================================
# Retroactive Ripple - Jurisdiction Change
# ============================================================

@router.patch("/cases/{case_id}/jurisdiction", response_model=JurisdictionChangeResult)
async def update_case_jurisdiction(
    case_id: str,
    request: CaseJurisdictionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a case's jurisdiction and optionally recalculate all deadlines.

    The "Retroactive Ripple" Pattern:
    1. Receive PATCH with new jurisdiction_id
    2. If recalculate_deadlines is True:
       - Re-run every existing trigger against the NEW rule set
       - Update deadlines that changed
       - Remove deadlines that don't exist in new rules
       - Add deadlines that are new in the jurisdiction
    3. Log an audit entry with the change details
    """
    from app.models.deadline import Deadline
    from app.models.trigger import Trigger

    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Store previous jurisdiction for audit
    previous_jurisdiction = case.jurisdiction
    previous_court = case.court
    previous_judge = case.judge

    warnings = []
    deadlines_updated = 0
    deadlines_removed = 0
    deadlines_added = 0

    # Get the new jurisdiction details
    new_jurisdiction_name = None
    new_court_name = None

    if request.jurisdiction_id:
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == request.jurisdiction_id
        ).first()
        if jurisdiction:
            new_jurisdiction_name = jurisdiction.jurisdiction_type.value
            case.jurisdiction = jurisdiction.jurisdiction_type.value

            # Update district/circuit if it's a specific jurisdiction
            if jurisdiction.jurisdiction_type == JurisdictionType.LOCAL:
                case.circuit = str(jurisdiction.federal_circuit) if jurisdiction.federal_circuit else None

    if request.court_location_id:
        court_location = db.query(CourtLocation).filter(
            CourtLocation.id == request.court_location_id
        ).first()
        if court_location:
            new_court_name = court_location.name
            case.court = court_location.name
            case.district = court_location.district
            if court_location.circuit:
                case.circuit = str(court_location.circuit)

    if request.judge:
        case.judge = request.judge

    # Perform Retroactive Ripple if requested
    if request.recalculate_deadlines:
        try:
            # Get all triggers for this case
            triggers = db.query(Trigger).filter(
                Trigger.case_id == case_id,
                Trigger.status != 'cancelled'
            ).all()

            if triggers:
                # Get the new rule sets for the jurisdiction
                detector = JurisdictionDetector(db)

                # Get existing calculated deadlines (from triggers)
                existing_calculated_deadlines = db.query(Deadline).filter(
                    Deadline.case_id == case_id,
                    Deadline.is_calculated == True
                ).all()

                existing_deadline_ids = {d.id for d in existing_calculated_deadlines}

                # For each trigger, recalculate deadlines with new rules
                from app.services.rules_engine import RulesEngine
                rules_engine = RulesEngine(db)

                new_jurisdiction = case.jurisdiction or 'florida_state'
                court_type = case.case_type or 'civil'

                for trigger in triggers:
                    try:
                        # Get templates for this trigger type with new jurisdiction
                        templates = rules_engine.get_rule_templates(
                            jurisdiction=new_jurisdiction,
                            court_type=court_type,
                            trigger_type=trigger.trigger_type
                        )

                        if not templates:
                            warnings.append(f"No templates found for {trigger.trigger_type} in {new_jurisdiction}")
                            continue

                        # Mark existing deadlines for this trigger
                        trigger_deadlines = [d for d in existing_calculated_deadlines
                                           if d.trigger_event == trigger.trigger_type]

                        # Calculate new deadlines from templates
                        for template in templates:
                            calculated = rules_engine.calculate_deadlines_from_template(
                                template=template,
                                trigger_date=trigger.trigger_date,
                                case_id=case_id,
                                user_id=str(current_user.id),
                                service_method=trigger.service_method or 'electronic'
                            )

                            for calc_deadline in calculated:
                                # Check if a similar deadline exists
                                existing = next(
                                    (d for d in trigger_deadlines
                                     if d.title == calc_deadline['title']),
                                    None
                                )

                                if existing:
                                    # Update existing deadline if date changed
                                    if str(existing.deadline_date) != str(calc_deadline['deadline_date']):
                                        existing.deadline_date = calc_deadline['deadline_date']
                                        existing.calculation_basis = calc_deadline.get('calculation_basis')
                                        deadlines_updated += 1
                                else:
                                    # Add new deadline
                                    from datetime import datetime
                                    import uuid
                                    new_deadline = Deadline(
                                        id=str(uuid.uuid4()),
                                        case_id=case_id,
                                        user_id=str(current_user.id),
                                        title=calc_deadline['title'],
                                        description=calc_deadline.get('description', ''),
                                        deadline_date=calc_deadline['deadline_date'],
                                        deadline_type=calc_deadline.get('deadline_type', 'court'),
                                        priority=calc_deadline.get('priority', 'standard'),
                                        status='pending',
                                        trigger_event=trigger.trigger_type,
                                        is_calculated=True,
                                        is_dependent=True,
                                        calculation_basis=calc_deadline.get('calculation_basis'),
                                        applicable_rule=calc_deadline.get('rule_citation')
                                    )
                                    db.add(new_deadline)
                                    deadlines_added += 1

                    except Exception as te:
                        logger.warning(f"Error recalculating trigger {trigger.id}: {te}")
                        warnings.append(f"Error recalculating {trigger.trigger_type}: {str(te)}")

                # Note: We don't remove deadlines that might still be valid
                # User should manually review and remove if needed

        except Exception as e:
            logger.error(f"Error in Retroactive Ripple: {e}")
            warnings.append(f"Partial recalculation: {str(e)}")

    # Commit changes
    db.commit()
    db.refresh(case)

    # Build audit message
    changes = []
    if previous_jurisdiction != case.jurisdiction:
        changes.append(f"jurisdiction: {previous_jurisdiction} → {case.jurisdiction}")
    if previous_court != case.court:
        changes.append(f"court: {previous_court} → {case.court}")
    if previous_judge != case.judge:
        changes.append(f"judge: {previous_judge} → {case.judge}")

    audit_message = f"Jurisdiction changed by User. "
    if deadlines_updated or deadlines_added or deadlines_removed:
        audit_message += f"{deadlines_updated} deadlines updated. "
        if deadlines_added:
            audit_message += f"{deadlines_added} deadlines added. "
        if deadlines_removed:
            audit_message += f"{deadlines_removed} deadlines removed. "
    else:
        audit_message += "No deadline changes required."

    logger.info(f"Jurisdiction change for case {case_id}: {audit_message}")

    return JurisdictionChangeResult(
        case_id=case_id,
        previous_jurisdiction=previous_jurisdiction,
        new_jurisdiction=case.jurisdiction,
        deadlines_updated=deadlines_updated,
        deadlines_removed=deadlines_removed,
        deadlines_added=deadlines_added,
        audit_message=audit_message,
        warnings=warnings
    )
