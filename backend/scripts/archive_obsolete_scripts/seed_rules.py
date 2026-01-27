"""
Seed Script: Convert Hardcoded Rules to Database Format

This script demonstrates the migration path from hardcoded Python rules
to user-editable JSON-based rules in the database.

Converts the FL_CIV_ANSWER rule as a proof of concept.

Usage:
    python -m scripts.seed_rules
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.rule_template import RuleTemplate, RuleVersion
from app.models.user import User

def create_florida_answer_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    Convert FL_CIV_ANSWER hardcoded rule to database format.

    Original hardcoded rule:
    - Trigger: COMPLAINT_SERVED
    - Deadline: Answer Due (20 days + service extension)
    - Priority: FATAL
    - Jurisdiction: florida_state
    """

    # Create rule schema in new JSON format
    rule_schema = {
        "metadata": {
            "name": "Answer to Complaint - Florida Civil",
            "description": "Defendant must answer complaint within 20 days of service (plus service method extension)",
            "effective_date": "2024-01-01",
            "citations": ["Fla. R. Civ. P. 1.140(a)(1)"],
            "migrated_from": "FL_CIV_ANSWER"
        },
        "trigger": {
            "type": "COMPLAINT_SERVED",
            "required_fields": [
                {
                    "name": "service_date",
                    "type": "date",
                    "label": "Date Complaint Was Served",
                    "required": True
                },
                {
                    "name": "service_method",
                    "type": "select",
                    "label": "How was the complaint served?",
                    "options": ["personal", "mail", "email"],
                    "required": True,
                    "default": "personal"
                }
            ]
        },
        "deadlines": [
            {
                "id": "answer_due",
                "title": "Answer Due",
                "offset_days": 20,
                "offset_direction": "after",
                "priority": "FATAL",
                "description": "Defendant must file and serve Answer to Complaint",
                "applicable_rule": "Fla. R. Civ. P. 1.140(a)(1)",
                "add_service_days": True,
                "party_responsible": "defendant",
                "action_required": "File and serve Answer to Complaint",
                "calculation_method": "calendar_days",
                "notes": "20 days after service (+ 5 days if by mail, email=0 post-2019)",
                "conditions": []
            }
        ],
        "dependencies": [],
        "validation": {
            "min_deadlines": 1,
            "max_deadlines": 1,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14, 21]
        }
    }

    # Create template
    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Answer to Complaint - Florida Civil",
        slug="florida-civil-answer-to-complaint",
        jurisdiction="florida_civil",
        trigger_type="COMPLAINT_SERVED",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="Defendant must answer complaint within 20 days of service (plus service method extension)",
        tags=["florida", "civil", "answer", "complaint", "response"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    # Create version
    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Initial Migration",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Migrated from hardcoded FL_CIV_ANSWER rule",
        is_validated=True,
        test_cases_passed=0,
        test_cases_failed=0,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


def create_florida_trial_date_rule(db: Session, user_id: str) -> RuleTemplate:
    """
    Convert FL_CIV_TRIAL rule to database format (simplified version with 5 key deadlines).

    Full version has 50+ deadlines - this shows the structure.
    """

    rule_schema = {
        "metadata": {
            "name": "Trial Date Dependencies - Florida Civil",
            "description": "Comprehensive deadlines calculated from trial date for Florida civil litigation",
            "effective_date": "2024-01-01",
            "citations": ["Fla. R. Civ. P. 1.200", "Fla. R. Civ. P. 1.280"],
            "migrated_from": "FL_CIV_TRIAL"
        },
        "trigger": {
            "type": "TRIAL_DATE",
            "required_fields": [
                {
                    "name": "trial_date",
                    "type": "date",
                    "label": "Trial Date",
                    "required": True
                },
                {
                    "name": "trial_type",
                    "type": "select",
                    "label": "Type of Trial",
                    "options": ["jury", "bench", "summary_judgment"],
                    "required": True,
                    "default": "jury"
                }
            ]
        },
        "deadlines": [
            {
                "id": "discovery_cutoff",
                "title": "Discovery Cutoff",
                "offset_days": -45,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "Last day to serve discovery requests (responses due before trial)",
                "applicable_rule": "Fla. R. Civ. P. 1.280; Local Rules",
                "add_service_days": False,
                "party_responsible": "both",
                "action_required": "Complete all discovery. No new discovery may be served after this date.",
                "calculation_method": "calendar_days",
                "notes": "Varies by circuit - 30-60 days typical"
            },
            {
                "id": "discovery_responses_due",
                "title": "Discovery Responses Due",
                "offset_days": -30,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "All pending discovery responses must be served",
                "applicable_rule": "Fla. R. Civ. P. 1.340, 1.350, 1.370",
                "add_service_days": False,
                "party_responsible": "both",
                "action_required": "Serve all outstanding discovery responses"
            },
            {
                "id": "plaintiff_expert_disclosure",
                "title": "Plaintiff Expert Disclosure",
                "offset_days": -90,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "Disclose plaintiff's expert witnesses and opinions",
                "applicable_rule": "Fla. R. Civ. P. 1.280(b)(5)",
                "add_service_days": False,
                "party_responsible": "plaintiff",
                "action_required": "Disclose expert witnesses, opinions, and reports"
            },
            {
                "id": "defendant_expert_disclosure",
                "title": "Defendant Expert Disclosure",
                "offset_days": -60,
                "offset_direction": "before",
                "priority": "CRITICAL",
                "description": "Disclose defendant's expert witnesses (rebuttal)",
                "applicable_rule": "Fla. R. Civ. P. 1.280(b)(5)",
                "add_service_days": False,
                "party_responsible": "defendant",
                "action_required": "Disclose rebuttal expert witnesses"
            },
            {
                "id": "pretrial_motions_deadline",
                "title": "Pretrial Motions Deadline",
                "offset_days": -21,
                "offset_direction": "before",
                "priority": "IMPORTANT",
                "description": "Last day to file motions in limine and other pretrial motions",
                "applicable_rule": "Fla. R. Civ. P. 1.200; Local Rules",
                "add_service_days": True,
                "party_responsible": "both",
                "action_required": "File motions in limine and other pretrial motions"
            }
        ],
        "dependencies": [
            {
                "deadline_id": "defendant_expert_disclosure",
                "depends_on": "plaintiff_expert_disclosure",
                "type": "must_come_after",
                "min_gap_days": 30
            },
            {
                "deadline_id": "discovery_responses_due",
                "depends_on": "discovery_cutoff",
                "type": "must_come_after",
                "min_gap_days": 15
            }
        ],
        "validation": {
            "min_deadlines": 5,
            "max_deadlines": 100,
            "require_citations": True
        },
        "settings": {
            "auto_cascade_updates": True,
            "allow_manual_override": True,
            "notification_lead_days": [1, 3, 7, 14, 21, 30]
        }
    }

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="Trial Date Dependencies - Florida Civil",
        slug="florida-civil-trial-date-chain",
        jurisdiction="florida_civil",
        trigger_type="TRIAL_DATE",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="Comprehensive deadlines calculated from trial date for Florida civil litigation (simplified 5-deadline version)",
        tags=["florida", "civil", "trial", "discovery", "experts", "pretrial"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Initial Migration (Simplified)",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Migrated from hardcoded FL_CIV_TRIAL rule (simplified to 5 key deadlines)",
        is_validated=True,
        test_cases_passed=0,
        test_cases_failed=0,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template


def main():
    """Seed database with converted rules."""
    print("🌱 Seeding Rules Database...")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Get first user (or create a system user)
        user = db.query(User).first()

        if not user:
            print("❌ No users found in database. Please create a user first.")
            print("   Run: python -m scripts.create_user")
            return

        print(f"📌 Using user: {user.email} ({user.id})")
        print()

        # Create Answer rule
        print("1️⃣  Creating Florida Answer Rule...")
        answer_rule = create_florida_answer_rule(db, user.id)
        print(f"   ✅ Created: {answer_rule.rule_name}")
        print(f"      Slug: {answer_rule.slug}")
        print(f"      ID: {answer_rule.id}")
        print()

        # Create Trial Date rule
        print("2️⃣  Creating Florida Trial Date Rule...")
        trial_rule = create_florida_trial_date_rule(db, user.id)
        print(f"   ✅ Created: {trial_rule.rule_name}")
        print(f"      Slug: {trial_rule.slug}")
        print(f"      ID: {trial_rule.id}")
        print()

        print("=" * 60)
        print("✨ Seeding Complete!")
        print()
        print("Next steps:")
        print("  1. Test rules at: http://localhost:3000/rules")
        print("  2. Execute via API: POST /api/v1/rules/execute")
        print("  3. View in marketplace: GET /api/v1/rules/marketplace")

    except Exception as e:
        print(f"❌ Error seeding rules: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
