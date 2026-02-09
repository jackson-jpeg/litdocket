#!/usr/bin/env python3
"""
Migrate Hardcoded Rules to Authority Core

This script extracts all hardcoded rule templates from rules_engine.py
and creates them as AuthorityRule entries in the database.

Usage:
    python scripts/migrate_hardcoded_rules.py [--dry-run] [--jurisdiction JURISDICTION]

Options:
    --dry-run           Preview migration without creating rules
    --jurisdiction      Only migrate rules for a specific jurisdiction (florida_state, federal)
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.authority_core import AuthorityRule
from app.models.jurisdiction import Jurisdiction
from app.models.enums import AuthorityTier, TriggerType, DeadlinePriority

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Jurisdiction mapping: rules_engine jurisdiction strings to codes
JURISDICTION_MAPPING = {
    "federal": "FED",
    "florida_state": "FL",
    "florida": "FL",
}

# Trigger type mapping (maps enum to string values for Authority Core)
TRIGGER_TYPE_MAPPING = {
    TriggerType.CASE_FILED: "case_filed",
    TriggerType.SERVICE_COMPLETED: "service_completed",
    TriggerType.COMPLAINT_SERVED: "complaint_served",
    TriggerType.ANSWER_DUE: "answer_due",
    TriggerType.DISCOVERY_COMMENCED: "discovery_commenced",
    TriggerType.DISCOVERY_DEADLINE: "discovery_deadline",
    TriggerType.DISPOSITIVE_MOTIONS_DUE: "dispositive_motions_due",
    TriggerType.PRETRIAL_CONFERENCE: "pretrial_conference",
    TriggerType.TRIAL_DATE: "trial_date",
    TriggerType.HEARING_SCHEDULED: "hearing_scheduled",
    TriggerType.MOTION_FILED: "motion_filed",
    TriggerType.ORDER_ENTERED: "order_entered",
    TriggerType.APPEAL_FILED: "appeal_filed",
    TriggerType.MEDIATION_SCHEDULED: "mediation_scheduled",
    TriggerType.CUSTOM_TRIGGER: "custom_trigger",
}

# Priority mapping
PRIORITY_MAPPING = {
    DeadlinePriority.FATAL: "fatal",
    DeadlinePriority.CRITICAL: "critical",
    DeadlinePriority.IMPORTANT: "important",
    DeadlinePriority.STANDARD: "standard",
    DeadlinePriority.INFORMATIONAL: "informational",
}

# Authority tier mapping based on jurisdiction
TIER_MAPPING = {
    "federal": AuthorityTier.FEDERAL,
    "florida_state": AuthorityTier.STATE,
    "florida": AuthorityTier.STATE,
}


def get_hardcoded_rules() -> List[Dict[str, Any]]:
    """
    Extract all hardcoded rules from rules_engine.py.

    Returns a list of rule dictionaries in a format suitable for migration.
    """
    # Import the rules engine to get the templates
    from app.services.rules_engine import RulesEngine

    engine = RulesEngine()
    rules = []

    for rule_id, template in engine.rule_templates.items():
        # Skip database-loaded rules (they start with "DB_")
        if rule_id.startswith("DB_"):
            continue

        # Convert trigger type
        trigger_type = TRIGGER_TYPE_MAPPING.get(template.trigger_type, "custom")

        # Convert deadlines
        deadlines = []
        for deadline in template.dependent_deadlines:
            priority = PRIORITY_MAPPING.get(deadline.priority, "standard")

            deadline_spec = {
                "title": deadline.name,
                "days_from_trigger": deadline.days_from_trigger,
                "calculation_method": deadline.calculation_method or "calendar_days",
                "priority": priority,
                "party_responsible": deadline.party_responsible,
                "description": deadline.description,
            }

            # Add conditions if present
            if deadline.condition_field:
                deadline_spec["conditions"] = {
                    deadline.condition_field: deadline.condition_value
                }

            deadlines.append(deadline_spec)

        # Determine authority tier
        tier = TIER_MAPPING.get(template.jurisdiction, AuthorityTier.STATE)

        # Build service extensions based on add_service_method_days flag
        has_service_extensions = any(d.add_service_method_days for d in template.dependent_deadlines)
        service_extensions = {
            "mail": 5 if "florida" in template.jurisdiction.lower() else 3,
            "electronic": 0,
            "personal": 0
        } if has_service_extensions else {"mail": 0, "electronic": 0, "personal": 0}

        rule = {
            "rule_id": rule_id,
            "rule_code": rule_id,
            "rule_name": template.name,
            "trigger_type": trigger_type,
            "jurisdiction": template.jurisdiction,
            "court_type": template.court_type,
            "citation": template.citation,
            "description": template.description,
            "authority_tier": tier,
            "deadlines": deadlines,
            "conditions": {
                "court_type": template.court_type
            } if template.court_type else None,
            "service_extensions": service_extensions,
        }

        rules.append(rule)

    return rules


def get_jurisdiction_id(db: Session, jurisdiction_str: str) -> Optional[str]:
    """Get the jurisdiction UUID from the jurisdiction string."""
    code = JURISDICTION_MAPPING.get(jurisdiction_str.lower())
    if not code:
        return None

    jurisdiction = db.query(Jurisdiction).filter(Jurisdiction.code == code).first()
    return jurisdiction.id if jurisdiction else None


def calculate_complexity(rule: Dict[str, Any]) -> int:
    """
    Calculate complexity score (1-10) for tiered AI pipeline.

    Factors:
    - Number of deadlines (base score)
    - Presence of conditions (+2)
    - Service extensions (+1)
    - Number of condition fields (+1 each)
    """
    complexity = min(len(rule["deadlines"]), 5)  # Base: 1-5 based on deadline count

    if rule.get("conditions"):
        complexity += 2
        complexity += len(rule["conditions"]) - 1  # Additional conditions

    if rule.get("service_extensions") and any(v > 0 for v in rule.get("service_extensions", {}).values()):
        complexity += 1

    # Cap at 10
    return min(complexity, 10)


def create_authority_rule(
    db: Session,
    rule: Dict[str, Any],
    jurisdiction_id: str,
    user_id: Optional[str] = None
) -> AuthorityRule:
    """Create an AuthorityRule from a hardcoded rule definition."""
    # Build raw_text for content hashing
    raw_text = f"{rule['rule_name']}\n{rule.get('citation', '')}\n{rule.get('description', '')}"

    authority_rule = AuthorityRule(
        id=str(uuid.uuid4()),
        user_id=user_id,
        jurisdiction_id=jurisdiction_id,
        authority_tier=rule["authority_tier"],
        rule_code=rule["rule_code"],
        rule_name=rule["rule_name"],
        trigger_type=rule["trigger_type"],
        citation=rule["citation"],
        source_text=rule.get("description"),
        raw_text=raw_text,
        deadlines=rule["deadlines"],
        conditions=rule.get("conditions"),
        service_extensions=rule.get("service_extensions", {"mail": 3, "electronic": 0, "personal": 0}),
        confidence_score=1.0,  # Hardcoded rules have perfect confidence
        is_verified=True,
        verified_at=datetime.now(timezone.utc),
        is_active=True,
        # Rules Harvester integration fields
        complexity=calculate_complexity(rule),
        version=1,  # Initial version
        previous_raw_text=None,  # No previous version for initial migration
    )

    return authority_rule


def migrate_rules(
    db: Session,
    dry_run: bool = False,
    jurisdiction_filter: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Migrate all hardcoded rules to Authority Core.

    Returns a summary of the migration.
    """
    rules = get_hardcoded_rules()

    results = {
        "total_rules": len(rules),
        "migrated": 0,
        "skipped": 0,
        "errors": [],
        "details": []
    }

    for rule in rules:
        # Filter by jurisdiction if specified
        if jurisdiction_filter and rule["jurisdiction"].lower() != jurisdiction_filter.lower():
            results["skipped"] += 1
            continue

        # Get jurisdiction ID
        jurisdiction_id = get_jurisdiction_id(db, rule["jurisdiction"])
        if not jurisdiction_id:
            results["errors"].append({
                "rule_id": rule["rule_id"],
                "error": f"Unknown jurisdiction: {rule['jurisdiction']}"
            })
            results["skipped"] += 1
            continue

        # Check if rule already exists
        existing = db.query(AuthorityRule).filter(
            AuthorityRule.rule_code == rule["rule_code"],
            AuthorityRule.jurisdiction_id == jurisdiction_id,
            AuthorityRule.is_active == True
        ).first()

        if existing:
            results["details"].append({
                "rule_id": rule["rule_id"],
                "status": "skipped",
                "reason": "Already exists"
            })
            results["skipped"] += 1
            continue

        # Create the rule
        if not dry_run:
            try:
                authority_rule = create_authority_rule(
                    db, rule, jurisdiction_id, user_id
                )
                db.add(authority_rule)
                db.flush()  # Get the ID

                results["details"].append({
                    "rule_id": rule["rule_id"],
                    "authority_rule_id": authority_rule.id,
                    "status": "created",
                    "deadlines_count": len(rule["deadlines"])
                })
                results["migrated"] += 1

            except Exception as e:
                results["errors"].append({
                    "rule_id": rule["rule_id"],
                    "error": str(e)
                })
                db.rollback()
        else:
            results["details"].append({
                "rule_id": rule["rule_id"],
                "status": "would_create",
                "deadlines_count": len(rule["deadlines"]),
                "jurisdiction": rule["jurisdiction"],
                "trigger_type": rule["trigger_type"]
            })
            results["migrated"] += 1

    if not dry_run:
        db.commit()

    return results


def preview_migration() -> List[Dict[str, Any]]:
    """Preview all rules that would be migrated."""
    rules = get_hardcoded_rules()

    preview = []
    for rule in rules:
        preview.append({
            "rule_id": rule["rule_id"],
            "rule_name": rule["rule_name"],
            "jurisdiction": rule["jurisdiction"],
            "trigger_type": rule["trigger_type"],
            "citation": rule["citation"],
            "deadlines_count": len(rule["deadlines"]),
            "authority_tier": rule["authority_tier"].value if hasattr(rule["authority_tier"], "value") else str(rule["authority_tier"]),
            "complexity": calculate_complexity(rule),
        })

    return preview


def main():
    parser = argparse.ArgumentParser(description="Migrate hardcoded rules to Authority Core")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating rules")
    parser.add_argument("--jurisdiction", type=str, help="Only migrate specific jurisdiction")
    parser.add_argument("--preview", action="store_true", help="Show preview of rules to migrate")
    args = parser.parse_args()

    if args.preview:
        rules = preview_migration()
        print(f"\n{'='*60}")
        print(f"HARDCODED RULES PREVIEW ({len(rules)} rules)")
        print(f"{'='*60}\n")

        for rule in rules:
            print(f"  {rule['rule_id']}")
            print(f"    Name: {rule['rule_name']}")
            print(f"    Jurisdiction: {rule['jurisdiction']}")
            print(f"    Trigger: {rule['trigger_type']}")
            print(f"    Citation: {rule['citation']}")
            print(f"    Deadlines: {rule['deadlines_count']}")
            print(f"    Tier: {rule['authority_tier']}")
            print(f"    Complexity: {rule['complexity']}/10 (AI tier: {'BASIC' if rule['complexity'] <= 3 else 'STANDARD' if rule['complexity'] <= 6 else 'ADVANCED'})")
            print()
        return

    db = SessionLocal()
    try:
        results = migrate_rules(
            db,
            dry_run=args.dry_run,
            jurisdiction_filter=args.jurisdiction
        )

        print(f"\n{'='*60}")
        print(f"MIGRATION {'PREVIEW' if args.dry_run else 'RESULTS'}")
        print(f"{'='*60}\n")

        print(f"Total Rules: {results['total_rules']}")
        print(f"Migrated: {results['migrated']}")
        print(f"Skipped: {results['skipped']}")
        print(f"Errors: {len(results['errors'])}")

        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error['rule_id']}: {error['error']}")

        if args.dry_run:
            print("\n[DRY RUN] No rules were actually created.")
            print("Run without --dry-run to execute migration.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
