"""
Authority-Integrated Deadline Service

This service integrates the Authority Core rules database with the main
deadline calculation flow. It:
1. Queries Authority Core rules first (approved, verified rules)
2. Falls back to hardcoded rules_engine if no Authority rules exist
3. Records rule usage for audit trail
4. Returns calculated deadlines with source_rule_id populated

This is the bridge between the Authority Core system and the trigger-based
deadline generation in triggers.py.
"""
from typing import Dict, List, Optional, Any
from datetime import date
from dataclasses import dataclass
import logging
import os

from sqlalchemy.orm import Session

from app.models.authority_core import AuthorityRule
from app.services.authority_core_service import AuthorityCoreService
from app.services.rules_engine import rules_engine, RuleTemplate, TriggerType
from app.schemas.authority_core import CalculatedDeadline

logger = logging.getLogger(__name__)


# Feature flag for safe rollout
USE_AUTHORITY_CORE = os.environ.get("USE_AUTHORITY_CORE", "true").lower() == "true"


@dataclass
class IntegratedDeadline:
    """
    A deadline calculated from either Authority Core or hardcoded rules.

    This dataclass provides a unified structure regardless of the source,
    with source_rule_id populated for Authority Core deadlines and None
    for hardcoded rule deadlines.
    """
    title: str
    description: str
    deadline_date: date
    priority: str
    party_role: str
    action_required: str
    rule_citation: str
    calculation_basis: str
    trigger_event: str
    trigger_date: date
    days_count: int
    calculation_type: str
    # Authority Core source tracking
    source_rule_id: Optional[str] = None
    source_rule_name: Optional[str] = None
    source_citation: Optional[str] = None
    # CompuLaw-style fields
    trigger_formula: Optional[str] = None
    short_explanation: Optional[str] = None
    trigger_code: Optional[str] = None
    party_string: Optional[str] = None
    jurisdiction: Optional[str] = None
    court_type: Optional[str] = None


class AuthorityIntegratedDeadlineService:
    """
    Service that integrates Authority Core rules with deadline calculation.

    This service provides a unified interface for calculating deadlines from
    triggers, automatically choosing between Authority Core rules and hardcoded
    rules based on availability.

    Usage:
        service = AuthorityIntegratedDeadlineService(db)
        deadlines = await service.calculate_deadlines(
            jurisdiction_id="...",
            trigger_type="trial_date",
            trigger_date=date(2025, 6, 15),
            service_method="electronic",
            case_context={"case_type": "civil"}
        )
    """

    def __init__(self, db: Session):
        self.db = db
        self.authority_service = AuthorityCoreService(db)

    async def calculate_deadlines(
        self,
        jurisdiction_id: str,
        trigger_type: str,
        trigger_date: date,
        jurisdiction_name: str = "florida_state",
        court_type: str = "civil",
        service_method: str = "electronic",
        case_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None,
    ) -> List[IntegratedDeadline]:
        """
        Calculate deadlines from the best available source.

        Priority:
        1. Authority Core rules (if USE_AUTHORITY_CORE=true and rules exist)
        2. Hardcoded rules_engine rules (fallback)

        Args:
            jurisdiction_id: UUID of the target jurisdiction
            trigger_type: The trigger event type (e.g., "trial_date")
            trigger_date: Date of the trigger event
            jurisdiction_name: Jurisdiction name for hardcoded rules (e.g., "florida_state")
            court_type: Court type for hardcoded rules (e.g., "civil")
            service_method: Service method for time extensions
            case_context: Optional context for conditions and CompuLaw formatting
            user_id: Optional user ID for recording rule usage
            case_id: Optional case ID for recording rule usage

        Returns:
            List of IntegratedDeadline objects with source tracking
        """
        deadlines: List[IntegratedDeadline] = []
        authority_rules_used: List[AuthorityRule] = []

        # Try Authority Core first (if enabled)
        if USE_AUTHORITY_CORE:
            authority_deadlines = await self._get_authority_core_deadlines(
                jurisdiction_id=jurisdiction_id,
                trigger_type=trigger_type,
                trigger_date=trigger_date,
                service_method=service_method,
                case_context=case_context
            )

            if authority_deadlines:
                deadlines = authority_deadlines
                logger.info(
                    f"Using {len(deadlines)} deadlines from Authority Core "
                    f"for {trigger_type} in jurisdiction {jurisdiction_id}"
                )

                # Track which rules were used for audit trail
                rule_ids = set(d.source_rule_id for d in deadlines if d.source_rule_id)
                for rule_id in rule_ids:
                    rule = self.db.query(AuthorityRule).filter(
                        AuthorityRule.id == rule_id
                    ).first()
                    if rule:
                        authority_rules_used.append(rule)

        # Fall back to hardcoded rules if no Authority Core rules
        if not deadlines:
            deadlines = await self._get_hardcoded_deadlines(
                jurisdiction_name=jurisdiction_name,
                court_type=court_type,
                trigger_type=trigger_type,
                trigger_date=trigger_date,
                service_method=service_method,
                case_context=case_context
            )

            if deadlines:
                logger.info(
                    f"Using {len(deadlines)} deadlines from hardcoded rules_engine "
                    f"for {trigger_type} in {jurisdiction_name}/{court_type}"
                )
            else:
                logger.warning(
                    f"No rules found for {trigger_type} in "
                    f"{jurisdiction_id}/{jurisdiction_name}/{court_type}"
                )

        # Record rule usage for audit trail (if Authority Core rules were used)
        if authority_rules_used and user_id:
            for rule in authority_rules_used:
                rule_deadlines = [d for d in deadlines if d.source_rule_id == rule.id]
                await self.authority_service.record_rule_usage(
                    rule_id=rule.id,
                    user_id=user_id,
                    case_id=case_id,
                    trigger_type=trigger_type,
                    trigger_date=trigger_date,
                    deadlines_generated=len(rule_deadlines)
                )

        return deadlines

    async def _get_authority_core_deadlines(
        self,
        jurisdiction_id: str,
        trigger_type: str,
        trigger_date: date,
        service_method: str,
        case_context: Optional[Dict[str, Any]] = None
    ) -> List[IntegratedDeadline]:
        """
        Get deadlines from Authority Core rules database.

        Returns:
            List of IntegratedDeadline with source_rule_id populated
        """
        try:
            calculated = await self.authority_service.calculate_deadlines(
                jurisdiction_id=jurisdiction_id,
                trigger_type=trigger_type,
                trigger_date=trigger_date,
                case_context=case_context,
                service_method=service_method
            )

            if not calculated:
                return []

            # Convert CalculatedDeadline to IntegratedDeadline
            deadlines = []
            for calc in calculated:
                deadline = IntegratedDeadline(
                    title=calc.title,
                    description=f"Calculated from {calc.rule_name}: {calc.citation or ''}",
                    deadline_date=calc.deadline_date,
                    priority=calc.priority.upper() if calc.priority else "STANDARD",
                    party_role=calc.party_responsible or "",
                    action_required=calc.title,
                    rule_citation=calc.citation or "",
                    calculation_basis=f"{calc.days_from_trigger} {calc.calculation_method} from trigger",
                    trigger_event=trigger_type,
                    trigger_date=trigger_date,
                    days_count=calc.days_from_trigger,
                    calculation_type=calc.calculation_method,
                    # Authority Core source tracking
                    source_rule_id=calc.source_rule_id,
                    source_rule_name=calc.rule_name,
                    source_citation=calc.citation
                )
                deadlines.append(deadline)

            return deadlines

        except Exception as e:
            logger.error(f"Error getting Authority Core deadlines: {e}")
            return []

    async def _get_hardcoded_deadlines(
        self,
        jurisdiction_name: str,
        court_type: str,
        trigger_type: str,
        trigger_date: date,
        service_method: str,
        case_context: Optional[Dict[str, Any]] = None
    ) -> List[IntegratedDeadline]:
        """
        Get deadlines from hardcoded rules_engine.

        Returns:
            List of IntegratedDeadline with source_rule_id=None
        """
        try:
            # Convert trigger_type string to enum
            try:
                trigger_enum = TriggerType(trigger_type)
            except ValueError:
                logger.warning(f"Unknown trigger type: {trigger_type}")
                return []

            # Get applicable rule templates
            templates = rules_engine.get_applicable_rules(
                jurisdiction=jurisdiction_name,
                court_type=court_type,
                trigger_type=trigger_enum
            )

            if not templates:
                return []

            # Calculate deadlines from all templates
            deadlines = []
            for template in templates:
                calculated = rules_engine.calculate_dependent_deadlines(
                    trigger_date=trigger_date,
                    rule_template=template,
                    service_method=service_method,
                    case_context=case_context or {}
                )

                for calc in calculated:
                    deadline = IntegratedDeadline(
                        title=calc.get("title", ""),
                        description=calc.get("description", ""),
                        deadline_date=calc.get("deadline_date"),
                        priority=calc.get("priority", "STANDARD"),
                        party_role=calc.get("party_role", ""),
                        action_required=calc.get("action_required", ""),
                        rule_citation=calc.get("rule_citation", ""),
                        calculation_basis=calc.get("calculation_basis", ""),
                        trigger_event=calc.get("trigger_event", trigger_type),
                        trigger_date=calc.get("trigger_date", trigger_date),
                        days_count=calc.get("days_count", 0),
                        calculation_type=calc.get("calculation_type", "calendar_days"),
                        # No Authority Core source for hardcoded rules
                        source_rule_id=None,
                        source_rule_name=None,
                        source_citation=None,
                        # CompuLaw-style fields
                        trigger_formula=calc.get("trigger_formula"),
                        short_explanation=calc.get("short_explanation"),
                        trigger_code=calc.get("trigger_code"),
                        party_string=calc.get("party_string"),
                        jurisdiction=calc.get("jurisdiction", jurisdiction_name),
                        court_type=calc.get("court_type", court_type)
                    )
                    deadlines.append(deadline)

            return deadlines

        except Exception as e:
            logger.error(f"Error getting hardcoded deadlines: {e}")
            return []

    def has_authority_core_rules(
        self,
        jurisdiction_id: str,
        trigger_type: str
    ) -> bool:
        """
        Check if Authority Core has rules for this jurisdiction and trigger type.

        Useful for determining whether to show "Source: Authority Core" or
        "Source: System Rules" in the UI.
        """
        count = self.db.query(AuthorityRule).filter(
            AuthorityRule.jurisdiction_id == jurisdiction_id,
            AuthorityRule.trigger_type == trigger_type,
            AuthorityRule.is_active == True,
            AuthorityRule.is_verified == True
        ).count()
        return count > 0
