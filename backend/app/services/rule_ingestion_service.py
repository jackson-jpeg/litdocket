"""
Rule Ingestion Service - Text File to Supabase Pipeline

This service reads rule definition files (text, JSON, YAML) and
pushes them into Supabase as the single source of truth.

The Python backend acts as an "Ingestion Engine" that:
1. Parses rule text files (CompuLaw exports, custom formats)
2. Validates and transforms rule data
3. Pushes to Supabase PostgreSQL
4. Handles parent/child rule relationships

Usage:
    from app.services.rule_ingestion_service import RuleIngestionService

    service = RuleIngestionService(db_session)
    result = service.ingest_from_file("/path/to/rules.json")
    # or
    result = service.ingest_from_text(rule_text, format="json")
"""
import json
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import uuid

from sqlalchemy.orm import Session

from app.models.jurisdiction import (
    Jurisdiction, RuleSet, RuleSetDependency, RuleTemplate,
    RuleTemplateDeadline, CourtLocation, JurisdictionType,
    CourtType, DependencyType, TriggerType, DeadlinePriority,
    CalculationMethod
)

logger = logging.getLogger(__name__)


class RuleIngestionService:
    """
    Service for ingesting rule definitions into Supabase.

    Supports multiple input formats:
    - JSON (structured rule definitions)
    - YAML (human-readable rule files)
    - Text (CompuLaw-style rule exports)

    All data is pushed to Supabase PostgreSQL as the single source of truth.
    """

    def __init__(self, db: Session):
        self.db = db
        self._stats = {
            "jurisdictions_created": 0,
            "jurisdictions_updated": 0,
            "rule_sets_created": 0,
            "rule_sets_updated": 0,
            "templates_created": 0,
            "templates_updated": 0,
            "deadlines_created": 0,
            "errors": []
        }

    def reset_stats(self):
        """Reset ingestion statistics"""
        self._stats = {
            "jurisdictions_created": 0,
            "jurisdictions_updated": 0,
            "rule_sets_created": 0,
            "rule_sets_updated": 0,
            "templates_created": 0,
            "templates_updated": 0,
            "deadlines_created": 0,
            "errors": []
        }

    @property
    def stats(self) -> Dict:
        """Get ingestion statistics"""
        return self._stats.copy()

    # ==========================================
    # Main Ingestion Methods
    # ==========================================

    def ingest_from_file(self, file_path: str, format: Optional[str] = None) -> Dict:
        """
        Ingest rules from a file.

        Args:
            file_path: Path to the rule definition file
            format: Optional format hint ('json', 'yaml', 'text')

        Returns:
            Dictionary with ingestion results and statistics
        """
        self.reset_stats()
        path = Path(file_path)

        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        # Auto-detect format from extension
        if format is None:
            suffix = path.suffix.lower()
            format = {
                ".json": "json",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".txt": "text",
            }.get(suffix, "text")

        content = path.read_text(encoding="utf-8")
        return self.ingest_from_text(content, format)

    def ingest_from_text(self, content: str, format: str = "json") -> Dict:
        """
        Ingest rules from text content.

        Args:
            content: Rule definition text
            format: Format type ('json', 'yaml', 'text')

        Returns:
            Dictionary with ingestion results and statistics
        """
        self.reset_stats()

        try:
            if format == "json":
                data = json.loads(content)
                self._process_json_rules(data)
            elif format == "yaml":
                try:
                    import yaml
                    data = yaml.safe_load(content)
                    self._process_json_rules(data)  # Same structure as JSON
                except ImportError:
                    return {"success": False, "error": "PyYAML not installed"}
            elif format == "text":
                self._process_text_rules(content)
            else:
                return {"success": False, "error": f"Unknown format: {format}"}

            self.db.commit()

            return {
                "success": True,
                "stats": self.stats,
                "message": f"Ingestion complete. Created/updated rules successfully."
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Ingestion failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": self.stats
            }

    # ==========================================
    # JSON/YAML Processing
    # ==========================================

    def _process_json_rules(self, data: Dict):
        """Process structured JSON/YAML rule definitions"""

        # Process jurisdictions
        if "jurisdictions" in data:
            for jur_data in data["jurisdictions"]:
                self._upsert_jurisdiction(jur_data)

        # Process rule sets
        if "rule_sets" in data:
            for rs_data in data["rule_sets"]:
                self._upsert_rule_set(rs_data)

        # Process dependencies
        if "dependencies" in data:
            for dep_data in data["dependencies"]:
                self._upsert_dependency(dep_data)

        # Process rule templates
        if "rule_templates" in data:
            for template_data in data["rule_templates"]:
                self._upsert_rule_template(template_data)

        # Process court locations
        if "court_locations" in data:
            for court_data in data["court_locations"]:
                self._upsert_court_location(court_data)

    def _upsert_jurisdiction(self, data: Dict) -> Optional[Jurisdiction]:
        """Insert or update a jurisdiction"""
        try:
            code = data.get("code")
            if not code:
                self._stats["errors"].append("Jurisdiction missing code")
                return None

            existing = self.db.query(Jurisdiction).filter(
                Jurisdiction.code == code
            ).first()

            jur_type = self._parse_jurisdiction_type(data.get("jurisdiction_type", "state"))

            if existing:
                existing.name = data.get("name", existing.name)
                existing.description = data.get("description", existing.description)
                existing.jurisdiction_type = jur_type
                existing.state = data.get("state", existing.state)
                existing.is_active = data.get("is_active", True)
                self._stats["jurisdictions_updated"] += 1
                return existing
            else:
                # Resolve parent jurisdiction
                parent_id = None
                if data.get("parent_code"):
                    parent = self.db.query(Jurisdiction).filter(
                        Jurisdiction.code == data["parent_code"]
                    ).first()
                    if parent:
                        parent_id = parent.id

                jurisdiction = Jurisdiction(
                    id=data.get("id", str(uuid.uuid4())),
                    code=code,
                    name=data.get("name", code),
                    description=data.get("description"),
                    jurisdiction_type=jur_type,
                    parent_jurisdiction_id=parent_id,
                    state=data.get("state"),
                    federal_circuit=data.get("federal_circuit"),
                    is_active=data.get("is_active", True)
                )
                self.db.add(jurisdiction)
                self._stats["jurisdictions_created"] += 1
                return jurisdiction

        except Exception as e:
            self._stats["errors"].append(f"Jurisdiction error: {e}")
            return None

    def _upsert_rule_set(self, data: Dict) -> Optional[RuleSet]:
        """Insert or update a rule set"""
        try:
            code = data.get("code")
            if not code:
                self._stats["errors"].append("RuleSet missing code")
                return None

            # Find jurisdiction
            jur_code = data.get("jurisdiction_code")
            jurisdiction = self.db.query(Jurisdiction).filter(
                Jurisdiction.code == jur_code
            ).first()

            if not jurisdiction:
                self._stats["errors"].append(f"Jurisdiction not found: {jur_code}")
                return None

            existing = self.db.query(RuleSet).filter(
                RuleSet.code == code
            ).first()

            court_type = self._parse_court_type(data.get("court_type", "circuit"))

            if existing:
                existing.name = data.get("name", existing.name)
                existing.description = data.get("description", existing.description)
                existing.jurisdiction_id = jurisdiction.id
                existing.court_type = court_type
                existing.is_local = data.get("is_local", False)
                existing.is_active = data.get("is_active", True)
                self._stats["rule_sets_updated"] += 1
                return existing
            else:
                rule_set = RuleSet(
                    id=data.get("id", str(uuid.uuid4())),
                    code=code,
                    name=data.get("name", code),
                    description=data.get("description"),
                    jurisdiction_id=jurisdiction.id,
                    court_type=court_type,
                    version=data.get("version", "current"),
                    is_local=data.get("is_local", False),
                    is_active=data.get("is_active", True)
                )
                self.db.add(rule_set)
                self._stats["rule_sets_created"] += 1
                return rule_set

        except Exception as e:
            self._stats["errors"].append(f"RuleSet error: {e}")
            return None

    def _upsert_dependency(self, data: Dict):
        """Insert or update a rule set dependency"""
        try:
            rule_set = self.db.query(RuleSet).filter(
                RuleSet.code == data.get("rule_set_code")
            ).first()
            required = self.db.query(RuleSet).filter(
                RuleSet.code == data.get("required_rule_set_code")
            ).first()

            if not rule_set or not required:
                return

            existing = self.db.query(RuleSetDependency).filter(
                RuleSetDependency.rule_set_id == rule_set.id,
                RuleSetDependency.required_rule_set_id == required.id
            ).first()

            if not existing:
                dep = RuleSetDependency(
                    id=str(uuid.uuid4()),
                    rule_set_id=rule_set.id,
                    required_rule_set_id=required.id,
                    dependency_type=self._parse_dependency_type(
                        data.get("dependency_type", "concurrent")
                    ),
                    priority=data.get("priority", 0),
                    notes=data.get("notes")
                )
                self.db.add(dep)

        except Exception as e:
            self._stats["errors"].append(f"Dependency error: {e}")

    def _upsert_rule_template(self, data: Dict) -> Optional[RuleTemplate]:
        """Insert or update a rule template with its deadlines"""
        try:
            rule_set = self.db.query(RuleSet).filter(
                RuleSet.code == data.get("rule_set_code")
            ).first()

            if not rule_set:
                self._stats["errors"].append(f"RuleSet not found: {data.get('rule_set_code')}")
                return None

            rule_code = data.get("rule_code")
            existing = self.db.query(RuleTemplate).filter(
                RuleTemplate.rule_set_id == rule_set.id,
                RuleTemplate.rule_code == rule_code
            ).first()

            trigger_type = self._parse_trigger_type(data.get("trigger_type", "custom_trigger"))

            if existing:
                existing.name = data.get("name", existing.name)
                existing.description = data.get("description", existing.description)
                existing.trigger_type = trigger_type
                existing.citation = data.get("citation", existing.citation)
                existing.is_active = data.get("is_active", True)
                template = existing
                self._stats["templates_updated"] += 1
            else:
                template = RuleTemplate(
                    id=data.get("id", str(uuid.uuid4())),
                    rule_set_id=rule_set.id,
                    rule_code=rule_code,
                    name=data.get("name", rule_code),
                    description=data.get("description"),
                    trigger_type=trigger_type,
                    citation=data.get("citation"),
                    is_active=data.get("is_active", True)
                )
                self.db.add(template)
                self._stats["templates_created"] += 1

            self.db.flush()

            # Process deadlines
            if "deadlines" in data:
                for deadline_data in data["deadlines"]:
                    self._upsert_template_deadline(template.id, deadline_data)

            return template

        except Exception as e:
            self._stats["errors"].append(f"RuleTemplate error: {e}")
            return None

    def _upsert_template_deadline(self, template_id: str, data: Dict):
        """Insert or update a rule template deadline"""
        try:
            deadline = RuleTemplateDeadline(
                id=data.get("id", str(uuid.uuid4())),
                rule_template_id=template_id,
                name=data.get("name"),
                description=data.get("description"),
                days_from_trigger=data.get("days_from_trigger", 0),
                priority=self._parse_priority(data.get("priority", "standard")),
                party_responsible=data.get("party_responsible"),
                action_required=data.get("action_required"),
                calculation_method=self._parse_calc_method(
                    data.get("calculation_method", "calendar_days")
                ),
                add_service_days=data.get("add_service_days", False),
                rule_citation=data.get("rule_citation"),
                notes=data.get("notes"),
                display_order=data.get("display_order", 0),
                is_active=data.get("is_active", True)
            )
            self.db.add(deadline)
            self._stats["deadlines_created"] += 1

        except Exception as e:
            self._stats["errors"].append(f"Deadline error: {e}")

    def _upsert_court_location(self, data: Dict):
        """Insert or update a court location"""
        try:
            jurisdiction = self.db.query(Jurisdiction).filter(
                Jurisdiction.code == data.get("jurisdiction_code")
            ).first()

            if not jurisdiction:
                return

            location = CourtLocation(
                id=data.get("id", str(uuid.uuid4())),
                jurisdiction_id=jurisdiction.id,
                name=data.get("name"),
                short_name=data.get("short_name"),
                court_type=self._parse_court_type(data.get("court_type", "circuit")),
                district=data.get("district"),
                circuit=data.get("circuit"),
                division=data.get("division"),
                detection_patterns=data.get("detection_patterns", []),
                case_number_pattern=data.get("case_number_pattern"),
                is_active=data.get("is_active", True)
            )
            self.db.add(location)

        except Exception as e:
            self._stats["errors"].append(f"CourtLocation error: {e}")

    # ==========================================
    # Text File Processing (CompuLaw-style)
    # ==========================================

    def _process_text_rules(self, content: str):
        """
        Process plain text rule definitions.

        Expected format (CompuLaw-style):
        ```
        [RULE_SET: FL:RCP]
        Name: Florida Rules of Civil Procedure
        Jurisdiction: FL
        Court Type: circuit

        [TEMPLATE: FL-RCP-1.140]
        Trigger: complaint_served
        Citation: Fla. R. Civ. P. 1.140

        DEADLINE: Answer Due
        Days: +20
        Priority: critical
        Party: defendant
        Action: File Answer or Motion to Dismiss
        Citation: Fla. R. Civ. P. 1.140(a)(1)
        ```
        """
        lines = content.strip().split("\n")
        current_section = None
        current_data = {}

        for line in lines:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Section headers
            if line.startswith("[RULE_SET:"):
                if current_section == "RULE_SET" and current_data:
                    self._upsert_rule_set(current_data)
                current_section = "RULE_SET"
                code = line.replace("[RULE_SET:", "").replace("]", "").strip()
                current_data = {"code": code}

            elif line.startswith("[TEMPLATE:"):
                if current_section == "TEMPLATE" and current_data:
                    self._upsert_rule_template(current_data)
                current_section = "TEMPLATE"
                rule_code = line.replace("[TEMPLATE:", "").replace("]", "").strip()
                current_data = {"rule_code": rule_code, "deadlines": []}

            elif line.startswith("DEADLINE:"):
                # Add deadline to current template
                if current_section == "TEMPLATE":
                    deadline_name = line.replace("DEADLINE:", "").strip()
                    current_data.setdefault("deadlines", []).append({"name": deadline_name})

            # Key-value pairs
            elif ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()

                if current_section == "TEMPLATE" and current_data.get("deadlines"):
                    # Add to last deadline
                    deadline = current_data["deadlines"][-1]
                    if key == "days":
                        deadline["days_from_trigger"] = int(value.replace("+", ""))
                    elif key == "priority":
                        deadline["priority"] = value.lower()
                    elif key == "party":
                        deadline["party_responsible"] = value.lower()
                    elif key == "action":
                        deadline["action_required"] = value
                    elif key == "citation":
                        deadline["rule_citation"] = value
                else:
                    # Add to current section data
                    if key == "jurisdiction":
                        current_data["jurisdiction_code"] = value
                    elif key == "court_type":
                        current_data["court_type"] = value.lower()
                    elif key == "trigger":
                        current_data["trigger_type"] = value.lower()
                    else:
                        current_data[key] = value

        # Process final section
        if current_section == "RULE_SET" and current_data:
            self._upsert_rule_set(current_data)
        elif current_section == "TEMPLATE" and current_data:
            self._upsert_rule_template(current_data)

    # ==========================================
    # Type Parsing Helpers
    # ==========================================

    def _parse_jurisdiction_type(self, value: str) -> JurisdictionType:
        mapping = {
            "federal": JurisdictionType.FEDERAL,
            "state": JurisdictionType.STATE,
            "local": JurisdictionType.LOCAL,
            "bankruptcy": JurisdictionType.BANKRUPTCY,
            "appellate": JurisdictionType.APPELLATE,
        }
        return mapping.get(value.lower(), JurisdictionType.STATE)

    def _parse_court_type(self, value: str) -> CourtType:
        mapping = {
            "circuit": CourtType.CIRCUIT,
            "county": CourtType.COUNTY,
            "district": CourtType.DISTRICT,
            "bankruptcy": CourtType.BANKRUPTCY,
            "appellate_state": CourtType.APPELLATE_STATE,
            "appellate_federal": CourtType.APPELLATE_FEDERAL,
            "supreme_state": CourtType.SUPREME_STATE,
            "supreme_federal": CourtType.SUPREME_FEDERAL,
        }
        return mapping.get(value.lower(), CourtType.CIRCUIT)

    def _parse_dependency_type(self, value: str) -> DependencyType:
        mapping = {
            "concurrent": DependencyType.CONCURRENT,
            "inherits": DependencyType.INHERITS,
            "supplements": DependencyType.SUPPLEMENTS,
            "overrides": DependencyType.OVERRIDES,
        }
        return mapping.get(value.lower(), DependencyType.CONCURRENT)

    def _parse_trigger_type(self, value: str) -> TriggerType:
        mapping = {
            "case_filed": TriggerType.CASE_FILED,
            "service_completed": TriggerType.SERVICE_COMPLETED,
            "complaint_served": TriggerType.COMPLAINT_SERVED,
            "answer_due": TriggerType.ANSWER_DUE,
            "discovery_commenced": TriggerType.DISCOVERY_COMMENCED,
            "discovery_deadline": TriggerType.DISCOVERY_DEADLINE,
            "dispositive_motions_due": TriggerType.DISPOSITIVE_MOTIONS_DUE,
            "pretrial_conference": TriggerType.PRETRIAL_CONFERENCE,
            "trial_date": TriggerType.TRIAL_DATE,
            "hearing_scheduled": TriggerType.HEARING_SCHEDULED,
            "motion_filed": TriggerType.MOTION_FILED,
            "order_entered": TriggerType.ORDER_ENTERED,
            "appeal_filed": TriggerType.APPEAL_FILED,
            "mediation_scheduled": TriggerType.MEDIATION_SCHEDULED,
            "custom_trigger": TriggerType.CUSTOM_TRIGGER,
        }
        return mapping.get(value.lower(), TriggerType.CUSTOM_TRIGGER)

    def _parse_priority(self, value: str) -> DeadlinePriority:
        mapping = {
            "informational": DeadlinePriority.INFORMATIONAL,
            "standard": DeadlinePriority.STANDARD,
            "important": DeadlinePriority.IMPORTANT,
            "critical": DeadlinePriority.CRITICAL,
            "fatal": DeadlinePriority.FATAL,
        }
        return mapping.get(value.lower(), DeadlinePriority.STANDARD)

    def _parse_calc_method(self, value: str) -> CalculationMethod:
        mapping = {
            "calendar_days": CalculationMethod.CALENDAR_DAYS,
            "court_days": CalculationMethod.COURT_DAYS,
            "business_days": CalculationMethod.BUSINESS_DAYS,
        }
        return mapping.get(value.lower(), CalculationMethod.CALENDAR_DAYS)


# ==========================================
# CLI Entry Point
# ==========================================

def ingest_rules_cli():
    """Command-line interface for rule ingestion"""
    import argparse
    from app.database import SessionLocal

    parser = argparse.ArgumentParser(description="Ingest rule definitions into Supabase")
    parser.add_argument("file", help="Path to rule definition file")
    parser.add_argument("--format", choices=["json", "yaml", "text"],
                        help="File format (auto-detected from extension)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        service = RuleIngestionService(db)
        result = service.ingest_from_file(args.file, args.format)

        if result["success"]:
            print(f"Ingestion successful!")
            print(f"Stats: {result['stats']}")
        else:
            print(f"Ingestion failed: {result.get('error')}")
            if result.get("stats", {}).get("errors"):
                print(f"Errors: {result['stats']['errors']}")
    finally:
        db.close()


if __name__ == "__main__":
    ingest_rules_cli()
