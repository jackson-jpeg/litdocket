"""
Rules Engine - Trigger-based deadline calculation
Handles Florida State, Federal, and Local court rules with dependency chains

This engine uses the AuthoritativeDeadlineCalculator to ensure every deadline
includes complete rule citations and calculation basis for legal defensibility.
"""
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from dataclasses import dataclass
from enum import Enum

# Import authoritative legal rules constants
from app.constants.legal_rules import get_service_extension_days, get_rule_citation
from app.utils.deadline_calculator import (
    AuthoritativeDeadlineCalculator,
    CalculationMethod,
    DeadlineCalculation
)


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
    Trigger-based deadline architecture
    """

    def __init__(self):
        self.rule_templates: Dict[str, RuleTemplate] = {}
        self._load_florida_civil_rules()
        self._load_federal_civil_rules()
        self._load_florida_pretrial_rules()
        self._load_federal_pretrial_rules()
        self._load_appellate_rules()

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

        # Hearing Scheduled Trigger - generates dependent deadlines before hearing
        hearing_rule = RuleTemplate(
            rule_id="FL_CIV_HEARING",
            name="Hearing Dependencies",
            description="Deadlines calculated from scheduled hearing date",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.HEARING_SCHEDULED,
            citation="Fla. R. Civ. P. 1.200",
            dependent_deadlines=[
                DependentDeadline(
                    name="Memorandum of Law Due",
                    description="File memorandum of law in support of position",
                    days_from_trigger=-5,  # 5 days BEFORE hearing
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File memorandum of law or brief",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules (varies by district)",
                    notes="Check local rules - some courts require 7 or 10 days"
                ),
                DependentDeadline(
                    name="Hearing Exhibits Due",
                    description="Exchange exhibits for hearing",
                    days_from_trigger=-3,  # 3 days BEFORE hearing
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="Exchange hearing exhibits",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    notes="Check local rules for specific requirements"
                ),
            ]
        )
        self.rule_templates[hearing_rule.rule_id] = hearing_rule

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

        # Federal Hearing Scheduled Trigger
        fed_hearing_rule = RuleTemplate(
            rule_id="FED_CIV_HEARING",
            name="Federal Hearing Dependencies",
            description="Deadlines calculated from scheduled hearing date (Federal)",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.HEARING_SCHEDULED,
            citation="FRCP 1 and Local Rules",
            dependent_deadlines=[
                DependentDeadline(
                    name="Memorandum of Law Due (Federal)",
                    description="File memorandum of law in support of position",
                    days_from_trigger=-7,  # 7 days BEFORE hearing (Federal typically requires more notice)
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File memorandum of law or brief",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules (varies by district)",
                    notes="Check local rules - some districts require 14 days"
                ),
                DependentDeadline(
                    name="Hearing Exhibits Due (Federal)",
                    description="Exchange exhibits for hearing",
                    days_from_trigger=-5,  # 5 days BEFORE hearing
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="Exchange hearing exhibits",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    notes="Check local rules for specific requirements"
                ),
            ]
        )
        self.rule_templates[fed_hearing_rule.rule_id] = fed_hearing_rule

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
        Calculate all dependent deadlines from a trigger event with 10/10 legal defensibility

        Uses AuthoritativeDeadlineCalculator to ensure complete transparency:
        - Full rule citations for every calculation step
        - Detailed calculation basis with roll logic explanation
        - Jurisdiction-specific service method extensions
        - Court days vs calendar days properly handled

        Args:
            trigger_date: Date of the trigger event
            rule_template: Rule template to apply
            service_method: "electronic", "mail", or "hand_delivery"

        Returns:
            List of calculated deadlines with complete audit trails
        """
        from app.utils.florida_holidays import subtract_court_days

        calculated_deadlines = []

        # Initialize calculator for this jurisdiction
        calculator = AuthoritativeDeadlineCalculator(jurisdiction=rule_template.jurisdiction)

        for dependent in rule_template.dependent_deadlines:
            # Determine if this is before or after the trigger
            base_days = abs(dependent.days_from_trigger)
            is_before_trigger = dependent.days_from_trigger < 0

            # Determine calculation method
            if dependent.calculation_method.lower() in ["court_days", "business_days"]:
                calc_method = CalculationMethod.COURT_DAYS
            else:
                calc_method = CalculationMethod.CALENDAR_DAYS

            # Calculate deadline using authoritative calculator
            if is_before_trigger:
                # For "before" deadlines, calculate backwards
                if calc_method == CalculationMethod.COURT_DAYS:
                    # Use court days calculation for backwards counting
                    final_date = subtract_court_days(trigger_date, base_days)

                    # Create manual calculation record
                    calculation_basis = (
                        f"CALCULATION BASIS:\n"
                        f"1. Trigger Event: {trigger_date.strftime('%m/%d/%Y')}\n"
                        f"2. Base Period: {base_days} court days BEFORE trigger\n"
                        f"   Rule: {dependent.rule_citation}\n"
                        f"   = {trigger_date.strftime('%m/%d/%Y')} - {base_days} court days (excluding weekends/holidays)\n"
                        f"\nFINAL DEADLINE: {final_date.strftime('%A, %B %d, %Y')}"
                    )

                    roll_info = ""
                else:
                    # Simple calendar day backwards calculation
                    final_date = trigger_date - timedelta(days=base_days)

                    calculation_basis = (
                        f"CALCULATION BASIS:\n"
                        f"1. Trigger Event: {trigger_date.strftime('%m/%d/%Y')}\n"
                        f"2. Base Period: {base_days} calendar days BEFORE trigger\n"
                        f"   Rule: {dependent.rule_citation}\n"
                        f"   = {trigger_date.strftime('%m/%d/%Y')} - {base_days} days = {final_date.strftime('%m/%d/%Y')}\n"
                        f"\nFINAL DEADLINE: {final_date.strftime('%A, %B %d, %Y')}"
                    )

                    roll_info = ""

            else:
                # For "after" deadlines, use full authoritative calculator
                service_to_use = service_method if dependent.add_service_method_days else "personal"

                result: DeadlineCalculation = calculator.calculate_deadline(
                    trigger_date=trigger_date,
                    base_days=base_days,
                    service_method=service_to_use,
                    calculation_method=calc_method
                )

                final_date = result.final_deadline
                calculation_basis = result.calculation_basis

                # Extract roll info if present
                if result.roll_adjustment:
                    roll_info = f" (rolled from {result.roll_adjustment.original_date.strftime('%m/%d/%y')} - {result.roll_adjustment.reason})"
                else:
                    roll_info = ""

            # Build short explanation for UI
            short_explanation = f"{base_days} {calc_method.value.replace('_', ' ')}"
            if dependent.add_service_method_days and not is_before_trigger:
                try:
                    ext_days = get_service_extension_days(rule_template.jurisdiction, service_method)
                    if ext_days > 0:
                        short_explanation += f" + {ext_days} ({service_method})"
                except (ValueError, KeyError) as e:
                    # Service method not recognized - skip extension info in explanation
                    pass

            if is_before_trigger:
                short_explanation += " before trigger"
            else:
                short_explanation += " after trigger"

            calculated_deadlines.append({
                'title': dependent.name,
                'description': dependent.description,
                'deadline_date': final_date,
                'priority': dependent.priority.value,
                'party_role': dependent.party_responsible,
                'action_required': dependent.action_required,
                'rule_citation': dependent.rule_citation,
                'calculation_basis': calculation_basis,  # Full detailed basis
                'trigger_event': rule_template.trigger_type.value,
                'trigger_date': trigger_date,
                'is_calculated': True,
                'is_dependent': True,
                'notes': dependent.notes,
                # Enhanced metadata
                'calculation_type': calc_method.value,
                'days_count': base_days,
                'service_method': service_method,
                'short_explanation': short_explanation + roll_info,
                'jurisdiction': rule_template.jurisdiction,
                'court_type': rule_template.court_type
            })

        return calculated_deadlines

    def get_all_templates(self) -> List[RuleTemplate]:
        """Get all available rule templates"""
        return list(self.rule_templates.values())

    def get_template_by_id(self, rule_id: str) -> Optional[RuleTemplate]:
        """Get specific rule template by ID"""
        return self.rule_templates.get(rule_id)

    def _load_florida_pretrial_rules(self):
        """Load Florida pretrial and case management templates"""

        # Mediation Chain ($MC trigger)
        mediation_rule = RuleTemplate(
            rule_id="FL_CIV_MEDIATION",
            name="Mediation Conference",
            description="Deadlines triggered by mediation date",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.PRETRIAL_CONFERENCE,
            citation="Fla. R. Civ. P. 1.700-1.750",
            dependent_deadlines=[
                DependentDeadline(
                    name="Mediation Preparation Due",
                    description="Exchange mediation statements and documents",
                    days_from_trigger=-7,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Prepare and exchange mediation statements",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local court rules (varies)",
                    notes="7 days before mediation"
                ),
                DependentDeadline(
                    name="Mediation Fee Due",
                    description="Pay mediator retainer fee",
                    days_from_trigger=-10,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="Pay mediation fee to mediator",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Mediation agreement",
                    notes="Typically 10 days before mediation"
                )
            ]
        )
        self.rule_templates[mediation_rule.rule_id] = mediation_rule

        # Case Management Order Chain
        cmo_rule = RuleTemplate(
            rule_id="FL_CIV_CMO",
            name="Case Management Order",
            description="Case management deadlines from case filing",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.CASE_FILED,
            citation="Fla. R. Civ. P. 1.200",
            dependent_deadlines=[
                DependentDeadline(
                    name="Case Management Conference",
                    description="Attend case management conference",
                    days_from_trigger=90,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Attend case management conference",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.200",
                    notes="Typically within 90 days of filing"
                ),
                DependentDeadline(
                    name="Joint Case Management Report Due",
                    description="File joint case management report",
                    days_from_trigger=83,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Prepare and file joint case management report",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.200",
                    notes="7 days before case management conference"
                )
            ]
        )
        self.rule_templates[cmo_rule.rule_id] = cmo_rule

    def _load_federal_pretrial_rules(self):
        """Load Federal pretrial and trial preparation templates"""

        # Federal Pretrial Conference (Rule 16)
        federal_pretrial_rule = RuleTemplate(
            rule_id="FED_CIV_PRETRIAL_CONF",
            name="Federal Pretrial Conference",
            description="Federal Rule 16 pretrial conference requirements",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.PRETRIAL_CONFERENCE,
            citation="FRCP 16",
            dependent_deadlines=[
                DependentDeadline(
                    name="Joint Pretrial Statement Due",
                    description="File joint pretrial statement",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File joint pretrial statement with exhibits and witness lists",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 16(d)",
                    notes="14 days before pretrial conference (S.D. Fla local rule)"
                ),
                DependentDeadline(
                    name="Proposed Jury Instructions Due",
                    description="Submit proposed jury instructions",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Submit proposed jury instructions and verdict forms",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    notes="If jury trial"
                )
            ]
        )
        self.rule_templates[federal_pretrial_rule.rule_id] = federal_pretrial_rule

        # Federal Expert Disclosures (Rule 26)
        expert_disclosure_rule = RuleTemplate(
            rule_id="FED_CIV_EXPERT_DISC",
            name="Federal Expert Disclosures",
            description="FRCP 26(a)(2) expert disclosure deadlines",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.DISCOVERY_DEADLINE,
            citation="FRCP 26(a)(2)",
            dependent_deadlines=[
                DependentDeadline(
                    name="Plaintiff Expert Disclosures Due",
                    description="Disclose expert witnesses and reports",
                    days_from_trigger=-90,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="plaintiff",
                    action_required="Serve expert witness disclosures and reports",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26(a)(2)(D)",
                    notes="At least 90 days before trial"
                ),
                DependentDeadline(
                    name="Defendant Expert Disclosures Due",
                    description="Disclose expert witnesses and reports",
                    days_from_trigger=-60,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="defendant",
                    action_required="Serve expert witness disclosures and reports",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26(a)(2)(D)",
                    notes="At least 60 days before trial (30 days after plaintiff)"
                ),
                DependentDeadline(
                    name="Expert Discovery Cutoff",
                    description="Complete all expert discovery",
                    days_from_trigger=-30,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Complete all expert depositions",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26",
                    notes="Typically 30 days before trial"
                )
            ]
        )
        self.rule_templates[expert_disclosure_rule.rule_id] = expert_disclosure_rule

    def _load_appellate_rules(self):
        """Load Florida and Federal appellate procedure templates"""

        # Florida Appellate - Notice of Appeal
        fl_appeal_rule = RuleTemplate(
            rule_id="FL_APP_NOTICE",
            name="Florida Notice of Appeal",
            description="Florida appellate deadlines from final judgment",
            jurisdiction="florida_state",
            court_type="appellate",
            trigger_type=TriggerType.ORDER_ENTERED,
            citation="Fla. R. App. P. 9.110",
            dependent_deadlines=[
                DependentDeadline(
                    name="Notice of Appeal Due",
                    description="File notice of appeal",
                    days_from_trigger=30,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="appellant",
                    action_required="File notice of appeal with trial court",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. App. P. 9.110(b)",
                    notes="30 days from rendition of order (+ 5 if by mail)"
                ),
                DependentDeadline(
                    name="Designation of Record",
                    description="File designation of record",
                    days_from_trigger=40,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="appellant",
                    action_required="Designate record on appeal",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. App. P. 9.200(a)(1)",
                    notes="10 days after filing notice of appeal"
                )
            ]
        )
        self.rule_templates[fl_appeal_rule.rule_id] = fl_appeal_rule

        # Florida Appellate - Initial Brief
        fl_brief_rule = RuleTemplate(
            rule_id="FL_APP_BRIEF",
            name="Florida Appellate Briefs",
            description="Florida appellate briefing schedule",
            jurisdiction="florida_state",
            court_type="appellate",
            trigger_type=TriggerType.APPEAL_FILED,
            citation="Fla. R. App. P. 9.210",
            dependent_deadlines=[
                DependentDeadline(
                    name="Initial Brief Due",
                    description="File appellant's initial brief",
                    days_from_trigger=70,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="appellant",
                    action_required="File and serve initial brief",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. App. P. 9.210(b)(1)",
                    notes="70 days from filing of notice of appeal"
                ),
                DependentDeadline(
                    name="Answer Brief Due",
                    description="File appellee's answer brief",
                    days_from_trigger=100,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="appellee",
                    action_required="File and serve answer brief",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. App. P. 9.210(b)(2)",
                    notes="30 days after service of initial brief"
                ),
                DependentDeadline(
                    name="Reply Brief Due",
                    description="File appellant's reply brief (optional)",
                    days_from_trigger=120,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="appellant",
                    action_required="File and serve reply brief (if desired)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. App. P. 9.210(b)(3)",
                    notes="20 days after service of answer brief"
                )
            ]
        )
        self.rule_templates[fl_brief_rule.rule_id] = fl_brief_rule

        # Federal Appellate - Notice of Appeal
        fed_appeal_rule = RuleTemplate(
            rule_id="FED_APP_NOTICE",
            name="Federal Notice of Appeal",
            description="Federal appellate deadlines from final judgment",
            jurisdiction="federal",
            court_type="appellate",
            trigger_type=TriggerType.ORDER_ENTERED,
            citation="FRAP 4(a)(1)",
            dependent_deadlines=[
                DependentDeadline(
                    name="Notice of Appeal Due",
                    description="File notice of appeal",
                    days_from_trigger=30,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="appellant",
                    action_required="File notice of appeal with district court clerk",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRAP 4(a)(1)(A)",
                    notes="30 days from entry of judgment (60 days if USA is party)"
                )
            ]
        )
        self.rule_templates[fed_appeal_rule.rule_id] = fed_appeal_rule

        # Federal Appellate - Briefs
        fed_brief_rule = RuleTemplate(
            rule_id="FED_APP_BRIEF",
            name="Federal Appellate Briefs",
            description="Federal appellate briefing schedule",
            jurisdiction="federal",
            court_type="appellate",
            trigger_type=TriggerType.APPEAL_FILED,
            citation="FRAP 31",
            dependent_deadlines=[
                DependentDeadline(
                    name="Appellant's Brief Due",
                    description="File appellant's opening brief",
                    days_from_trigger=40,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="appellant",
                    action_required="File and serve opening brief",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRAP 31(a)(1)",
                    notes="40 days from docketing notice or order setting briefing"
                ),
                DependentDeadline(
                    name="Appellee's Brief Due",
                    description="File appellee's response brief",
                    days_from_trigger=70,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="appellee",
                    action_required="File and serve response brief",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRAP 31(a)(1)",
                    notes="30 days after appellant's brief served"
                ),
                DependentDeadline(
                    name="Reply Brief Due",
                    description="File appellant's reply brief (optional)",
                    days_from_trigger=84,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="appellant",
                    action_required="File and serve reply brief (if desired)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRAP 31(a)(1)",
                    notes="14 days after appellee's brief served"
                )
            ]
        )
        self.rule_templates[fed_brief_rule.rule_id] = fed_brief_rule


# Singleton instance
rules_engine = RulesEngine()
