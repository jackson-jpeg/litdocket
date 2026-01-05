"""
Rules Engine - CompuLaw-inspired trigger-based deadline calculation
Handles Florida State, Federal, and Local court rules with dependency chains
"""
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from dataclasses import dataclass
from enum import Enum


class DeadlinePriority(Enum):
    """Deadline priority levels"""
    INFORMATIONAL = "informational"  # FYI only
    STANDARD = "standard"  # Normal deadline
    IMPORTANT = "important"  # Needs attention
    CRITICAL = "critical"  # Mission critical
    FATAL = "fatal"  # Missing this = malpractice


class TriggerType(Enum):
    """Types of trigger events"""
    CASE_FILED = "case_filed"
    SERVICE_COMPLETED = "service_completed"
    COMPLAINT_SERVED = "complaint_served"
    ANSWER_DUE = "answer_due"
    DISCOVERY_COMMENCED = "discovery_commenced"
    DISCOVERY_DEADLINE = "discovery_deadline"
    DISPOSITIVE_MOTIONS_DUE = "dispositive_motions_due"
    PRETRIAL_CONFERENCE = "pretrial_conference"
    TRIAL_DATE = "trial_date"
    HEARING_SCHEDULED = "hearing_scheduled"
    MOTION_FILED = "motion_filed"
    ORDER_ENTERED = "order_entered"
    APPEAL_FILED = "appeal_filed"
    CUSTOM_TRIGGER = "custom_trigger"


@dataclass
class RuleTemplate:
    """A rule template defining dependent deadlines from a trigger"""
    rule_id: str
    name: str
    description: str
    jurisdiction: str  # "federal", "florida_state", "florida_local"
    court_type: str  # "civil", "criminal", "appellate"
    trigger_type: TriggerType
    dependent_deadlines: List['DependentDeadline']
    citation: str  # Rule citation (e.g., "FRCP 12(a)(1)")


@dataclass
class DependentDeadline:
    """A deadline that depends on a trigger event"""
    name: str
    description: str
    days_from_trigger: int  # Can be negative (before) or positive (after)
    priority: DeadlinePriority
    party_responsible: str  # "plaintiff", "defendant", "both", "court"
    action_required: str
    calculation_method: str  # "calendar_days", "business_days", "court_days"
    add_service_method_days: bool  # Add 5 days if served by mail
    rule_citation: str
    notes: Optional[str] = None


class RulesEngine:
    """
    The "Brain" - Manages court rules and generates dependent deadlines
    CompuLaw-inspired trigger-based architecture
    """

    def __init__(self):
        self.rule_templates: Dict[str, RuleTemplate] = {}
        self._load_florida_civil_rules()
        self._load_federal_civil_rules()

    def _load_florida_civil_rules(self):
        """Load Florida Rules of Civil Procedure templates"""

        # Florida Rule 1.140(a) - Answer to Complaint
        answer_rule = RuleTemplate(
            rule_id="FL_CIV_ANSWER",
            name="Answer to Complaint",
            description="Defendant must answer complaint",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.COMPLAINT_SERVED,
            citation="Fla. R. Civ. P. 1.140(a)",
            dependent_deadlines=[
                DependentDeadline(
                    name="Answer Due",
                    description="Defendant must file and serve Answer",
                    days_from_trigger=20,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="defendant",
                    action_required="File and serve Answer to Complaint",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.140(a)(1)",
                    notes="20 days after service (+ 5 days if by mail, email=0 post-2019)"
                )
            ]
        )
        self.rule_templates[answer_rule.rule_id] = answer_rule

        # Florida Discovery Deadlines (assuming standard 180-day discovery period)
        discovery_rule = RuleTemplate(
            rule_id="FL_CIV_DISCOVERY",
            name="Discovery Period",
            description="Standard discovery deadlines from case filing",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.CASE_FILED,
            citation="Fla. R. Civ. P. 1.280",
            dependent_deadlines=[
                DependentDeadline(
                    name="Initial Disclosures Due",
                    description="Mandatory initial disclosures",
                    days_from_trigger=30,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Exchange initial disclosures",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.280(b)",
                ),
                DependentDeadline(
                    name="Discovery Cut-off",
                    description="Last day to serve discovery requests",
                    days_from_trigger=150,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Complete all discovery",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.280",
                )
            ]
        )
        self.rule_templates[discovery_rule.rule_id] = discovery_rule

        # Trial Date Trigger - generates many dependent deadlines
        trial_rule = RuleTemplate(
            rule_id="FL_CIV_TRIAL",
            name="Trial Date Dependencies",
            description="Deadlines calculated from trial date",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.TRIAL_DATE,
            citation="Fla. R. Civ. P. 1.200",
            dependent_deadlines=[
                DependentDeadline(
                    name="Pretrial Stipulation Due",
                    description="Joint pretrial stipulation",
                    days_from_trigger=-15,  # 15 days BEFORE trial
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File pretrial stipulation",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules (varies by district)",
                ),
                DependentDeadline(
                    name="Witness List Due",
                    description="Exchange witness lists",
                    days_from_trigger=-30,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Exchange witness lists",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                DependentDeadline(
                    name="Exhibit List Due",
                    description="Exchange exhibit lists",
                    days_from_trigger=-30,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Exchange exhibit lists",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                DependentDeadline(
                    name="Dispositive Motions Deadline",
                    description="Last day to file dispositive motions",
                    days_from_trigger=-60,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File any dispositive motions (MSJ, etc.)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                DependentDeadline(
                    name="Motions in Limine Due",
                    description="Motions to exclude evidence",
                    days_from_trigger=-21,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File motions in limine",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
            ]
        )
        self.rule_templates[trial_rule.rule_id] = trial_rule

    def _load_federal_civil_rules(self):
        """Load Federal Rules of Civil Procedure templates"""

        # FRCP 12(a) - Answer to Complaint (Federal)
        fed_answer_rule = RuleTemplate(
            rule_id="FED_CIV_ANSWER",
            name="Answer to Complaint (Federal)",
            description="Defendant must answer complaint under FRCP",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.COMPLAINT_SERVED,
            citation="FRCP 12(a)(1)(A)",
            dependent_deadlines=[
                DependentDeadline(
                    name="Answer Due (Federal)",
                    description="Defendant must file and serve Answer",
                    days_from_trigger=21,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="defendant",
                    action_required="File and serve Answer to Complaint",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="FRCP 12(a)(1)(A)(i)",
                    notes="21 days after service (+ 3 days if by mail under FRCP 6(d))"
                )
            ]
        )
        self.rule_templates[fed_answer_rule.rule_id] = fed_answer_rule

        # Federal Discovery
        fed_discovery_rule = RuleTemplate(
            rule_id="FED_CIV_DISCOVERY",
            name="Federal Discovery Deadlines",
            description="FRCP discovery deadlines",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.CASE_FILED,
            citation="FRCP 26",
            dependent_deadlines=[
                DependentDeadline(
                    name="Initial Disclosures Due (Federal)",
                    description="FRCP 26(a)(1) initial disclosures",
                    days_from_trigger=14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Exchange FRCP 26(a)(1) initial disclosures",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26(a)(1)(C)",
                    notes="Within 14 days after Rule 26(f) conference"
                ),
            ]
        )
        self.rule_templates[fed_discovery_rule.rule_id] = fed_discovery_rule

    def get_applicable_rules(
        self,
        jurisdiction: str,
        court_type: str,
        trigger_type: TriggerType
    ) -> List[RuleTemplate]:
        """Get all applicable rule templates for a given context"""

        applicable = []
        for rule in self.rule_templates.values():
            if (rule.jurisdiction == jurisdiction and
                rule.court_type == court_type and
                rule.trigger_type == trigger_type):
                applicable.append(rule)

        return applicable

    def calculate_dependent_deadlines(
        self,
        trigger_date: date,
        rule_template: RuleTemplate,
        service_method: str = "email"
    ) -> List[Dict]:
        """
        Calculate all dependent deadlines from a trigger event

        Args:
            trigger_date: Date of the trigger event
            rule_template: Rule template to apply
            service_method: "email", "mail", "personal"

        Returns:
            List of calculated deadlines with all metadata
        """

        from app.services.calendar_service import calendar_service

        calculated_deadlines = []

        for dependent in rule_template.dependent_deadlines:
            # Calculate base deadline
            base_date = trigger_date + timedelta(days=dependent.days_from_trigger)

            # Add service method days if applicable
            service_days = 0
            if dependent.add_service_method_days:
                if service_method.lower() in ['mail', 'u.s. mail', 'usps']:
                    service_days = 5 if rule_template.jurisdiction == "florida_state" else 3
                elif service_method.lower() in ['email', 'e-portal', 'electronic']:
                    service_days = 0

            base_date = base_date + timedelta(days=service_days)

            # Adjust for holidays and weekends
            final_date = calendar_service.adjust_for_holidays_and_weekends(
                base_date,
                jurisdiction=rule_template.jurisdiction
            )

            # Build calculation explanation (Jackson's style)
            calculation_parts = []
            calculation_parts.append(f"{abs(dependent.days_from_trigger)} days {'after' if dependent.days_from_trigger > 0 else 'before'} trigger")
            if service_days > 0:
                calculation_parts.append(f"+ {service_days} days ({service_method} service)")
            if final_date != base_date:
                calculation_parts.append(f"adjusted for holidays/weekends")

            calculation_explanation = "; ".join(calculation_parts)

            calculated_deadlines.append({
                'title': dependent.name,
                'description': dependent.description,
                'deadline_date': final_date,
                'priority': dependent.priority.value,
                'party_role': dependent.party_responsible,
                'action_required': dependent.action_required,
                'rule_citation': dependent.rule_citation,
                'calculation_basis': f"({calculation_explanation})",
                'trigger_event': rule_template.trigger_type.value,
                'trigger_date': trigger_date,
                'is_calculated': True,
                'is_dependent': True,
                'notes': dependent.notes
            })

        return calculated_deadlines

    def get_all_templates(self) -> List[RuleTemplate]:
        """Get all available rule templates"""
        return list(self.rule_templates.values())

    def get_template_by_id(self, rule_id: str) -> Optional[RuleTemplate]:
        """Get specific rule template by ID"""
        return self.rule_templates.get(rule_id)


# Singleton instance
rules_engine = RulesEngine()
