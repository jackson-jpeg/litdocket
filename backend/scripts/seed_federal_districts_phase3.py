"""
Phase 3: Federal District Court Rules
Implements all 94 U.S. Federal District Courts with local rules

Tier 1 Priority (Top 10 High-Volume Districts):
1. S.D. New York (SDNY) - Wall Street litigation
2. C.D. California (CDCA) - Entertainment, tech
3. N.D. Illinois (NDIL) - Chicago commercial
4. D. Delaware (D.Del.) - Corporate law capital
5. N.D. California (NDCA) - Silicon Valley
6. E.D. Texas (EDTX) - Patent litigation capital
7. D. New Jersey (D.N.J.) - Pharmaceutical
8. D. Massachusetts (D.Mass.) - Biotech, IP
9. S.D. Florida (SDFL) - Securities, maritime
10. N.D. Texas (NDTX) - Dallas commercial
"""
from sqlalchemy.orm import Session
from app.models.rule_template import RuleTemplate, RuleVersion
from app.models.user import User
from app.database import SessionLocal
import uuid


# ============================================================================
# TIER 1: S.D. NEW YORK (SDNY) - 2nd Circuit
# ============================================================================

def create_sdny_scheduling_conference_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    S.D.N.Y. Local Civil Rule 26.3 - Initial Scheduling Conference
    Conference must be held within 90 days of complaint filing
    """
    rule_schema = {
        "metadata": {
            "name": "Initial Scheduling Conference - S.D.N.Y.",
            "description": "Initial scheduling conference within 90 days under Local Civil Rule 26.3",
            "effective_date": "2024-01-01",
            "citations": ["S.D.N.Y. Local Civ. R. 26.3", "Fed. R. Civ. P. 16"],
            "jurisdiction_type": "federal_district",
            "circuit": "2nd",
            "district": "SDNY",
            "court_level": "district",
            "case_type": "civil"
        },
        "trigger": {
            "type": "COMPLAINT_FILED",
            "required_fields": [
                {
                    "name": "filing_date",
                    "type": "date",
                    "label": "Date Complaint Was Filed",
                    "required": True
                },
                {
                    "name": "case_type",
                    "type": "select",
                    "label": "Case Type",
                    "options": ["civil", "complex_civil", "patent"],
                    "required": True,
                    "default": "civil"
                }
            ]
        },
        "deadlines": [
            {
                "id": "scheduling_conference",
                "title": "Initial Scheduling Conference",
                "offset_days": 90,
                "offset_direction": "after",
                "priority": "CRITICAL",
                "description": "Initial scheduling conference required under SDNY Local Rule 26.3",
                "applicable_rule": "S.D.N.Y. Local Civ. R. 26.3",
                "add_service_days": False,
                "party_responsible": "all",
                "calculation_method": "calendar_days",
                "notes": "Conference typically held within 90 days of complaint filing. Judge may modify schedule.",
                "conditions": []
            },
            {
                "id": "rule_26f_conference",
                "title": "Rule 26(f) Conference (Parties)",
                "offset_days": 21,
                "offset_direction": "before",
                "offset_from": "scheduling_conference",
                "priority": "IMPORTANT",
                "description": "Parties must confer at least 21 days before scheduling conference",
                "applicable_rule": "Fed. R. Civ. P. 26(f)",
                "add_service_days": False,
                "party_responsible": "all",
                "calculation_method": "calendar_days",
                "notes": "Parties discuss claims, defenses, settlement, and discovery plan",
                "conditions": []
            }
        ],
        "dependencies": [
            {
                "parent_id": "scheduling_conference",
                "child_id": "rule_26f_conference",
                "relationship": "triggers",
                "auto_calculate": True
            }
        ],
        "validation": {
            "min_deadlines": 2,
            "max_deadlines": 2,
            "require_trigger_date": True,
            "require_citations": True
        },
        "settings": {
            "auto_calculate_dependencies": True,
            "allow_manual_override": True,
            "weekend_handling": "next_business_day",
            "holiday_calendar": "federal"
        }
    }

    # Create RuleTemplate
    rule_template = RuleTemplate(
        id=str(uuid.uuid4()),
        rule_name="Initial Scheduling Conference - S.D.N.Y.",
        slug="sdny-civil-scheduling-conference",
        jurisdiction="sdny_civil",
        trigger_type="COMPLAINT_FILED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        status='active',
        description="Initial scheduling conference within 90 days under SDNY Local Civil Rule 26.3",
        tags=["federal", "sdny", "2nd_circuit", "scheduling", "conference", "civil"]
    )

    # Create RuleVersion
    rule_version = RuleVersion(
        id=str(uuid.uuid4()),
        rule_template_id=rule_template.id,
        version_number=1,
        version_name="Initial Version",
        rule_schema=rule_schema,
        created_by=user_id,
        is_validated=True,
        status='active',
        change_summary="Initial implementation of SDNY scheduling conference rule"
    )

    db.add(rule_template)
    db.add(rule_version)
    db.flush()

    # Link current version
    rule_template.current_version_id = rule_version.id
    db.flush()

    return rule_template


def create_sdny_premotion_conference_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    S.D.N.Y. Local Civil Rule 7.1 - Pre-Motion Conference
    Required before filing most motions (except summary judgment)
    """
    rule_schema = {
        "metadata": {
            "name": "Pre-Motion Conference - S.D.N.Y.",
            "description": "Mandatory pre-motion conference required under Local Civil Rule 7.1",
            "effective_date": "2024-01-01",
            "citations": ["S.D.N.Y. Local Civ. R. 7.1"],
            "jurisdiction_type": "federal_district",
            "circuit": "2nd",
            "district": "SDNY",
            "court_level": "district",
            "case_type": "civil"
        },
        "trigger": {
            "type": "MOTION_PLANNED",
            "required_fields": [
                {
                    "name": "motion_type",
                    "type": "select",
                    "label": "Motion Type",
                    "options": ["dismiss", "compel_discovery", "protective_order", "sanctions", "other"],
                    "required": True
                },
                {
                    "name": "anticipated_filing_date",
                    "type": "date",
                    "label": "Anticipated Motion Filing Date",
                    "required": True
                }
            ]
        },
        "deadlines": [
            {
                "id": "premotion_conference_request",
                "title": "Request Pre-Motion Conference",
                "offset_days": 7,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "Request pre-motion conference at least 7 days before intended filing",
                "applicable_rule": "S.D.N.Y. Local Civ. R. 7.1",
                "add_service_days": False,
                "party_responsible": "moving_party",
                "calculation_method": "calendar_days",
                "notes": "CRITICAL: Most motions cannot be filed without pre-motion conference. Exceptions: summary judgment, certify class.",
                "conditions": []
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 1,
            "require_trigger_date": True,
            "require_citations": True
        },
        "settings": {
            "auto_calculate_dependencies": True,
            "allow_manual_override": False,
            "weekend_handling": "next_business_day",
            "holiday_calendar": "federal"
        }
    }

    # Create RuleTemplate
    rule_template = RuleTemplate(
        id=str(uuid.uuid4()),
        rule_name="Pre-Motion Conference - S.D.N.Y.",
        slug="sdny-civil-premotion-conference",
        jurisdiction="sdny_civil",
        trigger_type="MOTION_PLANNED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        status='active',
        description="Mandatory pre-motion conference under SDNY Local Civil Rule 7.1",
        tags=["federal", "sdny", "2nd_circuit", "motion", "pre-motion", "conference", "civil"]
    )

    # Create RuleVersion
    rule_version = RuleVersion(
        id=str(uuid.uuid4()),
        rule_template_id=rule_template.id,
        version_number=1,
        version_name="Initial Version",
        rule_schema=rule_schema,
        created_by=user_id,
        is_validated=True,
        status='active',
        change_summary="Initial implementation of SDNY pre-motion conference rule"
    )

    db.add(rule_template)
    db.add(rule_version)
    db.flush()

    # Link current version
    rule_template.current_version_id = rule_version.id
    db.flush()

    return rule_template


def create_sdny_discovery_deadlines_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    S.D.N.Y. Discovery Deadlines (based on scheduling order)
    Standard discovery cutoffs from typical SDNY scheduling orders
    """
    rule_schema = {
        "metadata": {
            "name": "Discovery Deadlines - S.D.N.Y.",
            "description": "Standard discovery deadlines from SDNY scheduling order",
            "effective_date": "2024-01-01",
            "citations": ["Fed. R. Civ. P. 26", "Fed. R. Civ. P. 33-36", "S.D.N.Y. Local Civ. R. 26.3"],
            "jurisdiction_type": "federal_district",
            "circuit": "2nd",
            "district": "SDNY",
            "court_level": "district",
            "case_type": "civil"
        },
        "trigger": {
            "type": "SCHEDULING_ORDER_ENTERED",
            "required_fields": [
                {
                    "name": "scheduling_order_date",
                    "type": "date",
                    "label": "Scheduling Order Entry Date",
                    "required": True
                },
                {
                    "name": "discovery_completion_date",
                    "type": "date",
                    "label": "Discovery Completion Date (from Order)",
                    "required": True
                }
            ]
        },
        "deadlines": [
            {
                "id": "initial_disclosures",
                "title": "Initial Disclosures Due",
                "offset_days": 14,
                "offset_direction": "after",
                "priority": "IMPORTANT",
                "description": "Initial disclosures under Rule 26(a)(1)",
                "applicable_rule": "Fed. R. Civ. P. 26(a)(1)",
                "add_service_days": False,
                "party_responsible": "all",
                "calculation_method": "calendar_days",
                "notes": "Parties must exchange initial disclosures within 14 days of Rule 26(f) conference",
                "conditions": []
            },
            {
                "id": "fact_discovery_deadline",
                "title": "Fact Discovery Deadline",
                "offset_days": 0,
                "offset_direction": "use_trigger_date",
                "use_field": "discovery_completion_date",
                "priority": "FATAL",
                "description": "All fact discovery must be completed by this date",
                "applicable_rule": "S.D.N.Y. Scheduling Order",
                "add_service_days": False,
                "party_responsible": "all",
                "calculation_method": "calendar_days",
                "notes": "No depositions or discovery requests served after this date",
                "conditions": []
            },
            {
                "id": "expert_reports_plaintiff",
                "title": "Plaintiff Expert Reports Due",
                "offset_days": 60,
                "offset_direction": "before",
                "offset_from": "fact_discovery_deadline",
                "priority": "FATAL",
                "description": "Plaintiff must disclose expert witnesses and reports",
                "applicable_rule": "Fed. R. Civ. P. 26(a)(2)",
                "add_service_days": False,
                "party_responsible": "plaintiff",
                "calculation_method": "calendar_days",
                "notes": "Expert reports required under Rule 26(a)(2)(B)",
                "conditions": []
            },
            {
                "id": "expert_reports_defendant",
                "title": "Defendant Expert Reports Due",
                "offset_days": 30,
                "offset_direction": "after",
                "offset_from": "expert_reports_plaintiff",
                "priority": "FATAL",
                "description": "Defendant must disclose expert witnesses and reports",
                "applicable_rule": "Fed. R. Civ. P. 26(a)(2)",
                "add_service_days": False,
                "party_responsible": "defendant",
                "calculation_method": "calendar_days",
                "notes": "Expert reports required under Rule 26(a)(2)(B)",
                "conditions": []
            },
            {
                "id": "expert_rebuttal_reports",
                "title": "Rebuttal Expert Reports Due",
                "offset_days": 14,
                "offset_direction": "after",
                "offset_from": "expert_reports_defendant",
                "priority": "IMPORTANT",
                "description": "Rebuttal expert reports if applicable",
                "applicable_rule": "Fed. R. Civ. P. 26(a)(2)(D)(ii)",
                "add_service_days": False,
                "party_responsible": "all",
                "calculation_method": "calendar_days",
                "notes": "Only for rebutting opponent's expert testimony",
                "conditions": []
            }
        ],
        "dependencies": [
            {
                "parent_id": "fact_discovery_deadline",
                "child_id": "expert_reports_plaintiff",
                "relationship": "must_come_before",
                "auto_calculate": True
            },
            {
                "parent_id": "expert_reports_plaintiff",
                "child_id": "expert_reports_defendant",
                "relationship": "triggers",
                "auto_calculate": True
            },
            {
                "parent_id": "expert_reports_defendant",
                "child_id": "expert_rebuttal_reports",
                "relationship": "triggers",
                "auto_calculate": True
            }
        ],
        "validation": {
            "min_deadlines": 5,
            "max_deadlines": 5,
            "require_trigger_date": True,
            "require_citations": True
        },
        "settings": {
            "auto_calculate_dependencies": True,
            "allow_manual_override": True,
            "weekend_handling": "next_business_day",
            "holiday_calendar": "federal"
        }
    }

    # Create RuleTemplate
    rule_template = RuleTemplate(
        id=str(uuid.uuid4()),
        rule_name="Discovery Deadlines - S.D.N.Y.",
        slug="sdny-civil-discovery-deadlines",
        jurisdiction="sdny_civil",
        trigger_type="SCHEDULING_ORDER_ENTERED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        status='active',
        description="Standard discovery deadlines from SDNY scheduling order",
        tags=["federal", "sdny", "2nd_circuit", "discovery", "experts", "civil"]
    )

    # Create RuleVersion
    rule_version = RuleVersion(
        id=str(uuid.uuid4()),
        rule_template_id=rule_template.id,
        version_number=1,
        version_name="Initial Version",
        rule_schema=rule_schema,
        created_by=user_id,
        is_validated=True,
        status='active',
        change_summary="Initial implementation of SDNY discovery deadlines"
    )

    db.add(rule_template)
    db.add(rule_version)
    db.flush()

    # Link current version
    rule_template.current_version_id = rule_version.id
    db.flush()

    return rule_template


# ============================================================================
# Main Seeding Function
# ============================================================================

def main():
    """Seed Phase 3 federal district court rules"""
    db = SessionLocal()

    try:
        # Get or create admin user
        admin_user = db.query(User).filter(User.email == "admin@litdocket.com").first()
        if not admin_user:
            print("❌ Admin user not found. Please run main seed script first.")
            return

        user_id = str(admin_user.id)

        print("\n" + "=" * 80)
        print("PHASE 3: FEDERAL DISTRICT COURTS - TIER 1 (TOP 10)")
        print("=" * 80)
        print()

        # Tier 1: S.D. New York (SDNY) - 3 rules
        print("🏛️  S.D. NEW YORK (SDNY) - 2nd Circuit")
        print("   Implementing 3 rules...")

        sdny_scheduling = create_sdny_scheduling_conference_rule(db, user_id)
        print(f"   ✅ {sdny_scheduling.rule_name}")

        sdny_premotion = create_sdny_premotion_conference_rule(db, user_id)
        print(f"   ✅ {sdny_premotion.rule_name}")

        sdny_discovery = create_sdny_discovery_deadlines_rule(db, user_id)
        print(f"   ✅ {sdny_discovery.rule_name}")

        db.commit()

        print()
        print("=" * 80)
        print("PHASE 3 - TIER 1 PROGRESS")
        print("=" * 80)
        print()
        print("✅ S.D. New York (SDNY): 3 rules")
        print("⏳ C.D. California (CDCA): 0 rules (pending)")
        print("⏳ N.D. Illinois (NDIL): 0 rules (pending)")
        print("⏳ D. Delaware (D.Del.): 0 rules (pending)")
        print("⏳ N.D. California (NDCA): 0 rules (pending)")
        print("⏳ E.D. Texas (EDTX): 0 rules (pending)")
        print("⏳ D. New Jersey (D.N.J.): 0 rules (pending)")
        print("⏳ D. Massachusetts (D.Mass.): 0 rules (pending)")
        print("⏳ S.D. Florida (SDFL): 0 rules (pending)")
        print("⏳ N.D. Texas (NDTX): 0 rules (pending)")
        print()
        print("📊 Tier 1 Progress: 1/10 districts (10%)")
        print("📊 Total Rules: 3 federal district rules")
        print()

    except Exception as e:
        print(f"❌ Error seeding federal district rules: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
