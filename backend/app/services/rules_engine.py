"""
Rules Engine - Trigger-based deadline calculation
Handles Florida State, Federal, and Local court rules with dependency chains

This engine uses the AuthoritativeDeadlineCalculator to ensure every deadline
includes complete rule citations and calculation basis for legal defensibility.

Supports both:
1. Hardcoded rule templates (legacy, always available)
2. Database-loaded rule templates (from jurisdiction system)
"""
from typing import Dict, List, Optional, Any, TYPE_CHECKING, Union
from datetime import date, timedelta
from dataclasses import dataclass, field
import logging

# Import centralized enums
from app.models.enums import TriggerType, DeadlinePriority

# Import authoritative legal rules constants
from app.constants.legal_rules import get_service_extension_days
from app.utils.deadline_calculator import (
    AuthoritativeDeadlineCalculator,
    CalculationMethod,
    DeadlineCalculation
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

__all__ = ['TriggerType', 'DeadlinePriority', 'rules_engine', 'RulesEngine']

@dataclass
class RequiredField:
    """A field that must be gathered before executing a trigger."""
    field_name: str
    display_label: str
    field_type: str
    enum_options: Optional[List[str]] = None
    default_value: Optional[Any] = None
    validation_rules: Optional[Dict[str, Any]] = None
    affects_deadlines: Optional[List[str]] = None

@dataclass
class ClarificationQuestion:
    """A follow-up question to refine deadline generation."""
    question_id: str
    question_text: str
    trigger_condition: Optional[str] = None
    expected_answer_type: str = "text"
    affects_deadlines: List[str] = field(default_factory=list)

@dataclass
class DependentDeadline:
    """A deadline that is calculated relative to a trigger event."""
    name: str
    description: str
    days_from_trigger: int
    priority: DeadlinePriority
    party_responsible: str
    action_required: str
    calculation_method: str
    add_service_method_days: bool
    rule_citation: str
    notes: Optional[str] = None
    # Conditional Logic Fields
    condition_field: Optional[str] = None
    condition_value: Any = True

@dataclass
class RuleTemplate:
    """Defines a set of deadlines triggered by a specific event."""
    rule_id: str
    name: str
    description: str
    jurisdiction: str
    court_type: str
    trigger_type: TriggerType
    dependent_deadlines: List[DependentDeadline]
    citation: str
    # Conversational Fields
    required_fields: List[RequiredField] = field(default_factory=list)
    clarification_questions: List[ClarificationQuestion] = field(default_factory=list)
    conditional_logic: Optional[Dict[str, Any]] = None


class RulesEngine:
    """
    The "Brain" - Manages court rules and generates dependent deadlines
    Trigger-based deadline architecture

    DEPRECATION NOTICE:
    -------------------
    This class contains hardcoded rule templates that are being replaced by
    Authority Core (app.services.authority_core_service.AuthorityCoreService).

    Authority Core provides:
    - Database-driven rules that can be updated without code changes
    - AI-powered rule extraction from court websites
    - Attorney approval workflow for new rules
    - Full audit trail and version history
    - Conflict detection and resolution

    Migration Path:
    1. Use the migration tool at /admin/migrate-rules to migrate hardcoded rules
    2. Once migrated, rules will be served from Authority Core
    3. Hardcoded rules are used as fallback only when Authority Core has no rules

    See: app.services.authority_integrated_deadline_service.AuthorityIntegratedDeadlineService
    """

    # Deprecation flag - set to True to log warnings when hardcoded rules are used
    _DEPRECATION_WARNING_ENABLED = True
    _deprecation_warned = False

    def __init__(self):
        self.rule_templates: Dict[str, RuleTemplate] = {}
        self._load_florida_civil_rules()
        self._load_federal_civil_rules()
        self._load_florida_pretrial_rules()
        self._load_federal_pretrial_rules()
        self._load_appellate_rules()

        # Log deprecation notice once per session
        if self._DEPRECATION_WARNING_ENABLED and not RulesEngine._deprecation_warned:
            logger.warning(
                "RulesEngine: Hardcoded rules are deprecated. "
                "Consider migrating to Authority Core for dynamic rule management. "
                "Use /admin/migrate-rules or run scripts/migrate_hardcoded_rules.py"
            )
            RulesEngine._deprecation_warned = True

    def _normalize_value(self, value: Any) -> Any:
        """
        Normalize values for soft matching in conditional deadline logic.

        Handles type mismatches between LLM-provided strings and expected types:
        - "true"/"yes"/"1" → True
        - "false"/"no"/"0" → False
        - "123" → 123
        - Otherwise returns value as-is

        This prevents strict inequality failures when LLM returns "true" (string)
        but rule expects True (boolean).

        Args:
            value: Raw value from user context or condition

        Returns:
            Normalized value for comparison
        """
        if isinstance(value, str):
            # Boolean string normalization
            lower_val = value.lower().strip()
            if lower_val in ("true", "yes", "1", "y"):
                return True
            elif lower_val in ("false", "no", "0", "n"):
                return False

            # Integer string normalization
            try:
                # Check if it's a valid integer
                if lower_val.isdigit() or (lower_val.startswith('-') and lower_val[1:].isdigit()):
                    return int(lower_val)
            except (ValueError, AttributeError):
                pass

        # Return as-is for all other types (bool, int, float, None, etc.)
        return value

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

        # =============================================================
        # TRIAL DATE TRIGGER - COMPREHENSIVE (50+ DEADLINES)
        # This is the "CompuLaw killer" - one date generates everything
        # =============================================================
        trial_rule = RuleTemplate(
            rule_id="FL_CIV_TRIAL",
            name="Trial Date Dependencies",
            description="Comprehensive deadlines calculated from trial date - Florida Civil",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.TRIAL_DATE,
            citation="Fla. R. Civ. P. 1.200",
            dependent_deadlines=[
                # ========== DISCOVERY DEADLINES ==========
                DependentDeadline(
                    name="Discovery Cutoff",
                    description="Last day to serve discovery requests (responses due before trial)",
                    days_from_trigger=-45,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Complete all discovery. No new discovery may be served after this date.",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.280; Local Rules",
                    notes="Varies by circuit - 30-60 days typical"
                ),
                DependentDeadline(
                    name="Discovery Responses Due",
                    description="All pending discovery responses must be served",
                    days_from_trigger=-30,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Serve all outstanding discovery responses",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.340, 1.350, 1.370",
                ),
                # ========== EXPERT DEADLINES ==========
                DependentDeadline(
                    name="Plaintiff Expert Disclosure",
                    description="Disclose plaintiff's expert witnesses and opinions",
                    days_from_trigger=-90,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="plaintiff",
                    action_required="Serve expert witness list with opinions, basis, and qualifications",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.280(b)(5)",
                    notes="Party with burden of proof discloses first"
                ),
                DependentDeadline(
                    name="Defendant Expert Disclosure",
                    description="Disclose defendant's expert witnesses and opinions",
                    days_from_trigger=-60,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="defendant",
                    action_required="Serve expert witness list with opinions, basis, and qualifications",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.280(b)(5)",
                    notes="30 days after plaintiff's disclosure"
                ),
                DependentDeadline(
                    name="Rebuttal Expert Disclosure",
                    description="Disclose rebuttal expert witnesses",
                    days_from_trigger=-45,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="plaintiff",
                    action_required="Serve rebuttal expert witness disclosure",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.280(b)(5)",
                    notes="15 days after defendant's disclosure"
                ),
                DependentDeadline(
                    name="Expert Deposition Cutoff",
                    description="Complete all expert depositions",
                    days_from_trigger=-30,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Complete all expert witness depositions",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.280; Local Rules",
                ),
                # ========== DISPOSITIVE MOTIONS ==========
                DependentDeadline(
                    name="Motion for Summary Judgment Deadline",
                    description="Last day to file motion for summary judgment",
                    days_from_trigger=-60,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File motion for summary judgment with supporting evidence",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.510(c)",
                    notes="Must be heard at least 20 days before trial"
                ),
                DependentDeadline(
                    name="MSJ Response Deadline",
                    description="Response to motion for summary judgment due",
                    days_from_trigger=-40,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File response with opposing affidavits/evidence",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.510(c)",
                    notes="20 days to respond (+ 5 if by mail)"
                ),
                DependentDeadline(
                    name="MSJ Reply Deadline",
                    description="Reply memorandum on summary judgment",
                    days_from_trigger=-35,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="File reply memorandum if desired",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.510",
                ),
                # ========== PRETRIAL PREPARATION ==========
                DependentDeadline(
                    name="Pretrial Stipulation Due",
                    description="Joint pretrial stipulation",
                    days_from_trigger=-15,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File joint pretrial stipulation",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules (varies by circuit)",
                    notes="10-15 days typical; check local rules"
                ),
                DependentDeadline(
                    name="Final Witness List Due",
                    description="Exchange final witness lists for trial",
                    days_from_trigger=-30,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Exchange final witness lists with estimated testimony times",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                DependentDeadline(
                    name="Final Exhibit List Due",
                    description="Exchange final exhibit lists for trial",
                    days_from_trigger=-30,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Exchange exhibit lists with Bates numbers and descriptions",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                DependentDeadline(
                    name="Exchange Trial Exhibits",
                    description="Exchange copies of all trial exhibits",
                    days_from_trigger=-21,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Exchange physical/electronic copies of all exhibits",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                DependentDeadline(
                    name="Exhibit Objections Due",
                    description="File objections to opposing exhibits",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File written objections to exhibits with legal basis",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                # ========== MOTIONS IN LIMINE ==========
                DependentDeadline(
                    name="Motions in Limine Due",
                    description="File motions to exclude evidence",
                    days_from_trigger=-21,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File motions in limine with supporting memoranda",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    notes="Varies 14-30 days by circuit"
                ),
                DependentDeadline(
                    name="Motions in Limine Response Due",
                    description="Respond to motions in limine",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File responses to opposing motions in limine",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                # ========== JURY TRIAL SPECIFICS ==========
                DependentDeadline(
                    name="Proposed Jury Instructions Due",
                    description="Submit proposed jury instructions",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File proposed jury instructions with supporting authority",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.470(b); Local Rules",
                    # CONDITIONAL: Only for jury trials
                    condition_field="jury_status",
                    condition_value=True
                ),
                DependentDeadline(
                    name="Proposed Verdict Form Due",
                    description="Submit proposed verdict form",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File proposed special verdict form",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.480; Local Rules",
                    # CONDITIONAL: Only for jury trials
                    condition_field="jury_status",
                    condition_value=True
                ),
                DependentDeadline(
                    name="Proposed Voir Dire Questions",
                    description="Submit proposed voir dire questions",
                    days_from_trigger=-10,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="File proposed voir dire questions",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    # CONDITIONAL: Only for jury trials
                    condition_field="jury_status",
                    condition_value=True
                ),
                # ========== DEPOSITION DESIGNATIONS ==========
                DependentDeadline(
                    name="Deposition Designations Due",
                    description="Designate deposition testimony for trial",
                    days_from_trigger=-21,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Serve deposition designations (page/line citations)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.330(a)(2); Local Rules",
                ),
                DependentDeadline(
                    name="Counter-Designations Due",
                    description="Counter-designate deposition testimony",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Serve counter-designations to complete context",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.330(a)(2); Local Rules",
                ),
                DependentDeadline(
                    name="Objections to Depo Designations",
                    description="Object to deposition designations",
                    days_from_trigger=-10,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="File objections to deposition designations",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.330; Local Rules",
                ),
                # ========== TRIAL SUBPOENAS ==========
                DependentDeadline(
                    name="Trial Subpoena Deadline (Non-Party)",
                    description="Last day to serve subpoenas on non-party witnesses",
                    days_from_trigger=-10,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Serve trial subpoenas on all non-party witnesses",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.410(d)",
                    notes="Reasonable time required - typically 10+ days"
                ),
                # ========== TRIAL MEMORANDA ==========
                DependentDeadline(
                    name="Trial Brief/Memorandum Due",
                    description="File trial brief summarizing case",
                    days_from_trigger=-7,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="File trial memorandum with legal authorities",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    notes="Check local rules - not required in all circuits"
                ),
                # ========== SETTLEMENT ==========
                DependentDeadline(
                    name="Last Settlement Conference",
                    description="Final opportunity for settlement conference",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="Attend settlement conference if ordered",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                # ========== PRETRIAL CONFERENCE ==========
                DependentDeadline(
                    name="Pretrial Conference",
                    description="Attend pretrial conference with court",
                    days_from_trigger=-7,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Attend pretrial conference; counsel must have settlement authority",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.200; Local Rules",
                    notes="Typically 5-14 days before trial"
                ),
            ],
            # =============================================================
            # CONVERSATIONAL INTAKE: Required Context for Trial Deadlines
            # =============================================================
            required_fields=[
                RequiredField(
                    field_name="jury_status",
                    display_label="Is this a jury trial?",
                    field_type="boolean",
                    default_value=True,  # Assume jury trial if not specified
                    affects_deadlines=[
                        "Proposed Jury Instructions Due",
                        "Proposed Verdict Form Due",
                        "Proposed Voir Dire Questions"
                    ]
                ),
                RequiredField(
                    field_name="trial_duration_days",
                    display_label="Expected trial duration (in days)",
                    field_type="integer",
                    validation_rules={"min": 1, "max": 30},
                    default_value=None,  # No default - MUST ask
                    affects_deadlines=["Trial Subpoena Deadline (Non-Party)", "Exchange Trial Exhibits"]
                ),
                RequiredField(
                    field_name="court_location",
                    display_label="Court location/circuit",
                    field_type="enum",
                    enum_options=["Miami-Dade (11th)", "Broward (17th)", "Palm Beach (15th)", "Other"],
                    default_value="Miami-Dade (11th)",
                    affects_deadlines=["Pretrial Stipulation Due", "Motions in Limine Due"]
                )
            ],
            clarification_questions=[
                ClarificationQuestion(
                    question_id="confirm_expert_witnesses",
                    question_text="Will either party be using expert witnesses?",
                    trigger_condition="None",  # Always ask
                    expected_answer_type="boolean",
                    affects_deadlines=[
                        "Plaintiff Expert Disclosure",
                        "Defendant Expert Disclosure",
                        "Expert Deposition Cutoff"
                    ]
                ),
                ClarificationQuestion(
                    question_id="confirm_summary_judgment",
                    question_text="Do you plan to file a motion for summary judgment?",
                    trigger_condition="None",
                    expected_answer_type="boolean",
                    affects_deadlines=[
                        "Motion for Summary Judgment Deadline",
                        "MSJ Response Deadline",
                        "MSJ Reply Deadline"
                    ]
                )
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

        # =============================================================
        # MOTION FILED TRIGGER - Response deadlines
        # =============================================================
        motion_rule = RuleTemplate(
            rule_id="FL_CIV_MOTION",
            name="Motion Response Deadlines",
            description="Deadlines triggered when a motion is filed/served",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.MOTION_FILED,
            citation="Fla. R. Civ. P. 1.140(b)",
            dependent_deadlines=[
                DependentDeadline(
                    name="Response to Motion Due",
                    description="File response/opposition to motion",
                    days_from_trigger=10,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="opposing",
                    action_required="File and serve response to motion with supporting memorandum",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.140(b); Local Rules",
                    notes="10 days to respond (+ 5 if by mail, 0 if email)"
                ),
                DependentDeadline(
                    name="Reply Memorandum Due",
                    description="File reply to response (if desired)",
                    days_from_trigger=15,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="movant",
                    action_required="File reply memorandum (optional)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    notes="5 days after response due; check local rules"
                ),
            ]
        )
        self.rule_templates[motion_rule.rule_id] = motion_rule

        # =============================================================
        # DISCOVERY SERVED TRIGGERS - Individual Discovery Responses
        # =============================================================

        # Interrogatories Served
        interrogatory_rule = RuleTemplate(
            rule_id="FL_CIV_INTERROGATORIES",
            name="Interrogatories Response",
            description="Response deadline when interrogatories are served",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.DISCOVERY_COMMENCED,
            citation="Fla. R. Civ. P. 1.340",
            dependent_deadlines=[
                DependentDeadline(
                    name="Answers to Interrogatories Due",
                    description="Serve answers to interrogatories",
                    days_from_trigger=30,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="responding",
                    action_required="Serve verified answers to interrogatories with objections",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.340(a)",
                    notes="30 days to respond (+ 5 if by mail)"
                ),
            ]
        )
        self.rule_templates[interrogatory_rule.rule_id] = interrogatory_rule

        # Request for Production Served
        rfp_rule = RuleTemplate(
            rule_id="FL_CIV_RFP",
            name="Request for Production Response",
            description="Response deadline when RFP is served",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.DISCOVERY_COMMENCED,
            citation="Fla. R. Civ. P. 1.350",
            dependent_deadlines=[
                DependentDeadline(
                    name="Response to RFP Due",
                    description="Serve response to request for production",
                    days_from_trigger=30,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="responding",
                    action_required="Serve written response and produce documents",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.350(b)",
                    notes="30 days to respond (+ 5 if by mail)"
                ),
            ]
        )
        self.rule_templates[rfp_rule.rule_id] = rfp_rule

        # Request for Admissions Served - CRITICAL (auto-admit if not answered!)
        rfa_rule = RuleTemplate(
            rule_id="FL_CIV_RFA",
            name="Request for Admissions Response",
            description="Response deadline when RFA is served - FAILURE TO RESPOND = DEEMED ADMITTED",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.DISCOVERY_COMMENCED,
            citation="Fla. R. Civ. P. 1.370",
            dependent_deadlines=[
                DependentDeadline(
                    name="Response to RFA Due - CRITICAL",
                    description="Serve response to request for admissions - DEEMED ADMITTED IF NOT TIMELY",
                    days_from_trigger=30,
                    priority=DeadlinePriority.FATAL,  # FATAL because failure = deemed admitted!
                    party_responsible="responding",
                    action_required="Serve written responses - FAILURE TO RESPOND = DEEMED ADMITTED",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.370(a)",
                    notes="⚠️ CRITICAL: 30 days to respond (+ 5 if mail). FAILURE = DEEMED ADMITTED!"
                ),
            ]
        )
        self.rule_templates[rfa_rule.rule_id] = rfa_rule

        # Deposition Noticed
        deposition_rule = RuleTemplate(
            rule_id="FL_CIV_DEPOSITION",
            name="Deposition Notice Deadlines",
            description="Deadlines triggered by deposition notice",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.HEARING_SCHEDULED,  # Using hearing as proxy for deposition
            citation="Fla. R. Civ. P. 1.310",
            dependent_deadlines=[
                DependentDeadline(
                    name="Deposition Preparation",
                    description="Prepare witness for deposition",
                    days_from_trigger=-2,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Prepare witness; review documents and anticipated questions",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Best practice",
                    notes="At least 2 days before deposition for preparation"
                ),
                DependentDeadline(
                    name="Document Request for Deposition",
                    description="Deadline to request documents be brought to deposition",
                    days_from_trigger=-10,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="Serve subpoena duces tecum for documents",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.310(b)(5)",
                    notes="Reasonable time before deposition"
                ),
            ]
        )
        self.rule_templates[deposition_rule.rule_id] = deposition_rule

        # =============================================================
        # COMPLAINT SERVED - Full Defendant Response Chain
        # =============================================================
        complaint_served_rule = RuleTemplate(
            rule_id="FL_CIV_COMPLAINT_SERVED",
            name="Complaint Served - Full Response Chain",
            description="All defendant response deadlines from service of complaint",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.COMPLAINT_SERVED,
            citation="Fla. R. Civ. P. 1.140",
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
                    notes="20 days after service (+ 5 if by mail, 0 if email)"
                ),
                DependentDeadline(
                    name="Motion to Dismiss Deadline",
                    description="Last day to file motion to dismiss (instead of answer)",
                    days_from_trigger=20,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="defendant",
                    action_required="File motion to dismiss under Rule 1.140(b) if challenging jurisdiction, venue, or pleading sufficiency",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.140(b)",
                    notes="Must be filed BEFORE answer; same deadline"
                ),
                DependentDeadline(
                    name="Affirmative Defenses Due",
                    description="Affirmative defenses must be raised in Answer",
                    days_from_trigger=20,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="defendant",
                    action_required="Include all affirmative defenses in Answer or they may be waived",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.110(d)",
                    notes="Affirmative defenses must be pled or waived"
                ),
                DependentDeadline(
                    name="Counterclaim/Crossclaim Deadline",
                    description="File any compulsory counterclaims with Answer",
                    days_from_trigger=20,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="defendant",
                    action_required="File compulsory counterclaims with Answer (permissive counterclaims may be filed later)",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.170",
                    notes="Compulsory counterclaims may be waived if not timely filed"
                ),
                DependentDeadline(
                    name="Third-Party Complaint Deadline",
                    description="File third-party complaint (impleader)",
                    days_from_trigger=20,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="defendant",
                    action_required="File third-party complaint if seeking contribution or indemnification",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.180",
                    notes="May file as of right within time for Answer; leave required thereafter"
                ),
            ]
        )
        self.rule_templates[complaint_served_rule.rule_id] = complaint_served_rule

        # =============================================================
        # ORDER ENTERED - Post-Judgment Deadlines
        # =============================================================
        order_entered_rule = RuleTemplate(
            rule_id="FL_CIV_ORDER_ENTERED",
            name="Order/Judgment Entered - Post-Judgment Deadlines",
            description="Critical deadlines after entry of order or judgment",
            jurisdiction="florida_state",
            court_type="civil",
            trigger_type=TriggerType.ORDER_ENTERED,
            citation="Fla. R. Civ. P. 1.530",
            dependent_deadlines=[
                DependentDeadline(
                    name="Motion for Rehearing Due",
                    description="File motion for rehearing or reconsideration",
                    days_from_trigger=15,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File motion for rehearing under Rule 1.530",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.530(b)",
                    notes="15 days after service of written order"
                ),
                DependentDeadline(
                    name="Motion for New Trial Due",
                    description="File motion for new trial",
                    days_from_trigger=15,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File motion for new trial under Rule 1.530",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. Civ. P. 1.530(b)",
                    notes="15 days from service; may toll appeal deadline"
                ),
                DependentDeadline(
                    name="Notice of Appeal Deadline",
                    description="File notice of appeal",
                    days_from_trigger=30,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="both",
                    action_required="File notice of appeal with trial court",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Fla. R. App. P. 9.110(b)",
                    notes="JURISDICTIONAL - 30 days from rendition; tolled by timely rehearing motion"
                ),
                DependentDeadline(
                    name="Motion to Tax Costs Due",
                    description="File motion for costs",
                    days_from_trigger=30,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="prevailing",
                    action_required="File motion to tax costs with supporting documentation",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.525",
                    notes="30 days after filing of judgment"
                ),
                DependentDeadline(
                    name="Motion for Attorney Fees Due",
                    description="File motion for attorney fees",
                    days_from_trigger=30,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="prevailing",
                    action_required="File motion for attorney fees if entitled",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Fla. R. Civ. P. 1.525",
                    notes="30 days after filing of judgment; check contract/statute for entitlement"
                ),
            ]
        )
        self.rule_templates[order_entered_rule.rule_id] = order_entered_rule

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

        # =============================================================
        # FEDERAL TRIAL DATE - COMPREHENSIVE (40+ DEADLINES)
        # =============================================================
        fed_trial_rule = RuleTemplate(
            rule_id="FED_CIV_TRIAL",
            name="Federal Trial Date Dependencies",
            description="Comprehensive deadlines calculated from trial date - Federal Civil",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.TRIAL_DATE,
            citation="FRCP 16; Local Rules",
            dependent_deadlines=[
                # ========== DISCOVERY DEADLINES ==========
                DependentDeadline(
                    name="Discovery Cutoff",
                    description="Last day to serve discovery requests",
                    days_from_trigger=-60,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Complete all discovery; no new discovery after this date",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26; Scheduling Order",
                    notes="Varies by scheduling order - typically 30-90 days before trial"
                ),
                DependentDeadline(
                    name="Fact Discovery Responses Due",
                    description="All outstanding discovery responses must be served",
                    days_from_trigger=-45,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Serve all outstanding fact discovery responses",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 33, 34, 36",
                ),
                # ========== EXPERT DEADLINES ==========
                DependentDeadline(
                    name="Plaintiff Expert Reports Due",
                    description="Serve plaintiff's expert witness reports",
                    days_from_trigger=-90,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="plaintiff",
                    action_required="Serve complete expert reports under FRCP 26(a)(2)(B)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26(a)(2)(D)",
                    notes="At least 90 days before trial"
                ),
                DependentDeadline(
                    name="Defendant Expert Reports Due",
                    description="Serve defendant's expert witness reports",
                    days_from_trigger=-60,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="defendant",
                    action_required="Serve complete expert reports under FRCP 26(a)(2)(B)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26(a)(2)(D)",
                    notes="Within 30 days after plaintiff's experts"
                ),
                DependentDeadline(
                    name="Rebuttal Expert Reports Due",
                    description="Serve rebuttal expert reports",
                    days_from_trigger=-45,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="plaintiff",
                    action_required="Serve rebuttal expert reports",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26(a)(2)(D)(ii)",
                    notes="Within 30 days of opposing expert disclosure"
                ),
                DependentDeadline(
                    name="Expert Deposition Cutoff",
                    description="Complete all expert depositions",
                    days_from_trigger=-30,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Complete all expert depositions",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26; Scheduling Order",
                ),
                # ========== DISPOSITIVE MOTIONS ==========
                DependentDeadline(
                    name="Summary Judgment Motion Deadline",
                    description="Last day to file motion for summary judgment",
                    days_from_trigger=-60,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File MSJ with supporting memorandum, statement of facts, and evidence",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 56(b); Local Rules",
                    notes="Check local rules for specific deadline"
                ),
                DependentDeadline(
                    name="MSJ Opposition Due",
                    description="Opposition to motion for summary judgment",
                    days_from_trigger=-39,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File opposition with counter-statement of facts and evidence",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="FRCP 56(c); Local Rules",
                    notes="21 days to oppose (varies by local rule)"
                ),
                DependentDeadline(
                    name="MSJ Reply Due",
                    description="Reply memorandum on summary judgment",
                    days_from_trigger=-32,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="File reply memorandum if desired",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    notes="7 days after opposition (varies by local rule)"
                ),
                # ========== PRETRIAL PREPARATION ==========
                DependentDeadline(
                    name="Final Pretrial Statement Due",
                    description="File joint pretrial statement",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File joint final pretrial statement per FRCP 16(e)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 16(e); Local Rules",
                ),
                DependentDeadline(
                    name="Final Witness List Due",
                    description="Exchange final witness lists",
                    days_from_trigger=-21,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Exchange final witness lists with summaries of expected testimony",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26(a)(3)(A)",
                ),
                DependentDeadline(
                    name="Final Exhibit List Due",
                    description="Exchange final exhibit lists",
                    days_from_trigger=-21,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Exchange exhibit lists per FRCP 26(a)(3)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26(a)(3)(A)(iii)",
                ),
                DependentDeadline(
                    name="Exhibit Objections Due",
                    description="File objections to trial exhibits",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File objections to exhibits; waived if not timely",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 26(a)(3)(B)",
                    notes="WAIVER: Objections not made timely are WAIVED (except FRE 402-403)"
                ),
                # ========== MOTIONS IN LIMINE ==========
                DependentDeadline(
                    name="Motions in Limine Due",
                    description="File motions to exclude evidence",
                    days_from_trigger=-21,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File motions in limine with supporting memoranda",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                DependentDeadline(
                    name="MIL Responses Due",
                    description="Respond to motions in limine",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File responses to opposing motions in limine",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                # ========== JURY TRIAL SPECIFICS ==========
                DependentDeadline(
                    name="Proposed Jury Instructions Due",
                    description="Submit proposed jury instructions",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File proposed jury instructions with legal citations",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 51; Local Rules",
                    # CONDITIONAL: Only for jury trials
                    condition_field="jury_status",
                    condition_value=True
                ),
                DependentDeadline(
                    name="Proposed Verdict Form Due",
                    description="Submit proposed verdict form",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="File proposed special verdict form or general verdict with interrogatories",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 49; Local Rules",
                    # CONDITIONAL: Only for jury trials
                    condition_field="jury_status",
                    condition_value=True
                ),
                DependentDeadline(
                    name="Proposed Voir Dire Questions",
                    description="Submit proposed voir dire questions",
                    days_from_trigger=-7,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="File proposed voir dire questions",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    # CONDITIONAL: Only for jury trials
                    condition_field="jury_status",
                    condition_value=True
                ),
                # ========== DEPOSITION DESIGNATIONS ==========
                DependentDeadline(
                    name="Deposition Designations Due",
                    description="Designate deposition testimony for trial",
                    days_from_trigger=-21,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Serve deposition designations (page/line citations)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 32(a); Local Rules",
                ),
                DependentDeadline(
                    name="Counter-Designations Due",
                    description="Counter-designate deposition testimony",
                    days_from_trigger=-14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="both",
                    action_required="Serve counter-designations",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 32(a); Local Rules",
                ),
                DependentDeadline(
                    name="Objections to Designations",
                    description="Object to deposition designations",
                    days_from_trigger=-10,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="File objections to deposition designations",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 32; Local Rules",
                ),
                # ========== TRIAL MEMORANDA ==========
                DependentDeadline(
                    name="Trial Brief Due",
                    description="File trial brief",
                    days_from_trigger=-7,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="both",
                    action_required="File trial brief summarizing legal issues",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                ),
                # ========== FINAL PRETRIAL CONFERENCE ==========
                DependentDeadline(
                    name="Final Pretrial Conference",
                    description="Attend final pretrial conference",
                    days_from_trigger=-7,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="Attend FPTC; lead counsel required; must have settlement authority",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 16(e)",
                    notes="Typically 7-14 days before trial"
                ),
            ]
        )
        self.rule_templates[fed_trial_rule.rule_id] = fed_trial_rule

        # =============================================================
        # FEDERAL MOTION FILED - Response Deadlines
        # =============================================================
        fed_motion_rule = RuleTemplate(
            rule_id="FED_CIV_MOTION",
            name="Federal Motion Response Deadlines",
            description="Response deadlines when a motion is filed (Federal)",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.MOTION_FILED,
            citation="FRCP 6(c)(1); Local Rules",
            dependent_deadlines=[
                DependentDeadline(
                    name="Opposition to Motion Due",
                    description="File opposition/response to motion",
                    days_from_trigger=21,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="opposing",
                    action_required="File opposition memorandum with supporting declarations/evidence",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="Local Rules (S.D. Fla. L.R. 7.1(c))",
                    notes="14-21 days varies by district (+ 3 if by mail under FRCP 6(d))"
                ),
                DependentDeadline(
                    name="Reply Memorandum Due",
                    description="File reply in support of motion",
                    days_from_trigger=28,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="movant",
                    action_required="File reply memorandum (optional)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="Local Rules",
                    notes="7 days after opposition typically"
                ),
            ]
        )
        self.rule_templates[fed_motion_rule.rule_id] = fed_motion_rule

        # =============================================================
        # FEDERAL COMPLAINT SERVED - Full Response Chain
        # =============================================================
        fed_complaint_served_rule = RuleTemplate(
            rule_id="FED_CIV_COMPLAINT_SERVED",
            name="Federal Complaint Served - Response Chain",
            description="All defendant response deadlines from service (Federal)",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.COMPLAINT_SERVED,
            citation="FRCP 12",
            dependent_deadlines=[
                DependentDeadline(
                    name="Answer Due",
                    description="Defendant must file Answer",
                    days_from_trigger=21,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="defendant",
                    action_required="File Answer to Complaint",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="FRCP 12(a)(1)(A)(i)",
                    notes="21 days (+ 3 if by mail under FRCP 6(d))"
                ),
                DependentDeadline(
                    name="Rule 12 Motion Deadline",
                    description="File pre-answer Rule 12 motion (instead of Answer)",
                    days_from_trigger=21,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="defendant",
                    action_required="File Rule 12(b) motion to dismiss or Rule 12(e)/(f) motion",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="FRCP 12(b)",
                    notes="Must be filed BEFORE Answer; same deadline"
                ),
                DependentDeadline(
                    name="Waiver of Service Response",
                    description="If waiver requested, extended deadline",
                    days_from_trigger=60,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="defendant",
                    action_required="Answer due if waiver of service was executed",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 4(d)(3)",
                    notes="60 days from when waiver request was sent (90 if foreign)"
                ),
                DependentDeadline(
                    name="Compulsory Counterclaims Due",
                    description="File compulsory counterclaims with Answer",
                    days_from_trigger=21,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="defendant",
                    action_required="Include compulsory counterclaims in Answer or risk waiver",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="FRCP 13(a)",
                    notes="Compulsory counterclaims must be pled or waived"
                ),
            ]
        )
        self.rule_templates[fed_complaint_served_rule.rule_id] = fed_complaint_served_rule

        # =============================================================
        # FEDERAL DISCOVERY RESPONSES
        # =============================================================
        fed_interrogatory_rule = RuleTemplate(
            rule_id="FED_CIV_INTERROGATORIES",
            name="Federal Interrogatories Response",
            description="Response deadline for interrogatories (Federal)",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.DISCOVERY_COMMENCED,
            citation="FRCP 33",
            dependent_deadlines=[
                DependentDeadline(
                    name="Answers to Interrogatories Due",
                    description="Serve answers to interrogatories",
                    days_from_trigger=30,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="responding",
                    action_required="Serve written answers and objections under oath",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="FRCP 33(b)(2)",
                    notes="30 days (+ 3 if by mail under FRCP 6(d))"
                ),
            ]
        )
        self.rule_templates[fed_interrogatory_rule.rule_id] = fed_interrogatory_rule

        fed_rfp_rule = RuleTemplate(
            rule_id="FED_CIV_RFP",
            name="Federal Request for Production Response",
            description="Response deadline for RFP (Federal)",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.DISCOVERY_COMMENCED,
            citation="FRCP 34",
            dependent_deadlines=[
                DependentDeadline(
                    name="Response to RFP Due",
                    description="Serve response to request for production",
                    days_from_trigger=30,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="responding",
                    action_required="Serve written response and produce/make available documents",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="FRCP 34(b)(2)(A)",
                    notes="30 days (+ 3 if by mail)"
                ),
            ]
        )
        self.rule_templates[fed_rfp_rule.rule_id] = fed_rfp_rule

        fed_rfa_rule = RuleTemplate(
            rule_id="FED_CIV_RFA",
            name="Federal Request for Admissions Response",
            description="Response deadline for RFA - DEEMED ADMITTED IF NOT TIMELY",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.DISCOVERY_COMMENCED,
            citation="FRCP 36",
            dependent_deadlines=[
                DependentDeadline(
                    name="Response to RFA Due - CRITICAL",
                    description="Serve response to request for admissions - DEEMED ADMITTED IF LATE",
                    days_from_trigger=30,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="responding",
                    action_required="Serve written responses - FAILURE = DEEMED ADMITTED",
                    calculation_method="calendar_days",
                    add_service_method_days=True,
                    rule_citation="FRCP 36(a)(3)",
                    notes="⚠️ CRITICAL: 30 days (+ 3 if mail). FAILURE = DEEMED ADMITTED!"
                ),
            ]
        )
        self.rule_templates[fed_rfa_rule.rule_id] = fed_rfa_rule

        # =============================================================
        # FEDERAL ORDER ENTERED - Post-Judgment Deadlines
        # =============================================================
        fed_order_entered_rule = RuleTemplate(
            rule_id="FED_CIV_ORDER_ENTERED",
            name="Federal Order/Judgment Entered - Post-Judgment Deadlines",
            description="Critical post-judgment deadlines (Federal)",
            jurisdiction="federal",
            court_type="civil",
            trigger_type=TriggerType.ORDER_ENTERED,
            citation="FRCP 59, 60; FRAP 4",
            dependent_deadlines=[
                DependentDeadline(
                    name="Motion for New Trial Due",
                    description="File motion for new trial under FRCP 59",
                    days_from_trigger=28,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File motion for new trial under FRCP 59(b)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 59(b)",
                    notes="28 days after entry of judgment; tolls appeal deadline"
                ),
                DependentDeadline(
                    name="Motion to Alter/Amend Judgment Due",
                    description="File motion to alter or amend judgment",
                    days_from_trigger=28,
                    priority=DeadlinePriority.CRITICAL,
                    party_responsible="both",
                    action_required="File FRCP 59(e) motion",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 59(e)",
                    notes="28 days; tolls appeal deadline"
                ),
                DependentDeadline(
                    name="Notice of Appeal Deadline",
                    description="File notice of appeal",
                    days_from_trigger=30,
                    priority=DeadlinePriority.FATAL,
                    party_responsible="both",
                    action_required="File notice of appeal with district court clerk",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRAP 4(a)(1)(A)",
                    notes="JURISDICTIONAL - 30 days (60 if USA is party); tolled by FRCP 59/60 motions"
                ),
                DependentDeadline(
                    name="Bill of Costs Due",
                    description="File bill of costs",
                    days_from_trigger=14,
                    priority=DeadlinePriority.STANDARD,
                    party_responsible="prevailing",
                    action_required="File bill of costs per FRCP 54(d)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 54(d)(1); Local Rules",
                    notes="14 days typical; check local rules"
                ),
                DependentDeadline(
                    name="Motion for Attorney Fees Due",
                    description="File motion for attorney fees",
                    days_from_trigger=14,
                    priority=DeadlinePriority.IMPORTANT,
                    party_responsible="prevailing",
                    action_required="File motion for attorney fees under FRCP 54(d)(2)",
                    calculation_method="calendar_days",
                    add_service_method_days=False,
                    rule_citation="FRCP 54(d)(2)(B)",
                    notes="14 days after entry of judgment"
                ),
            ]
        )
        self.rule_templates[fed_order_entered_rule.rule_id] = fed_order_entered_rule

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

    def match_document_to_trigger(
        self,
        document_type: str,
        jurisdiction: str = "florida_state",
        court_type: str = "civil"
    ) -> Dict[str, Any]:
        """
        SINGLE SOURCE OF TRUTH: Map document types to trigger events.

        This is the authoritative method for determining if a document type
        triggers rule-based deadline generation. Called by deadline_service.py
        to avoid hardcoded duplicate logic.

        Args:
            document_type: Type of document (e.g., "Complaint", "Motion to Dismiss")
            jurisdiction: "florida_state" or "federal"
            court_type: "civil", "criminal", or "appellate"

        Returns:
            Dict with:
                - matches_trigger: bool
                - trigger_type: TriggerType or None
                - trigger_type_str: str (for API responses)
                - rule_set_code: str (e.g., "FL:RCP")
                - expected_deadlines: int
                - trigger_description: str
                - matched_pattern: str (which keyword matched)
        """
        doc_type_lower = (document_type or "").lower()

        # Document type to TriggerType mapping
        # This is the SINGLE SOURCE OF TRUTH - no duplicates elsewhere
        DOCUMENT_PATTERNS = [
            # Complaint/Summons/Petition → COMPLAINT_SERVED
            {
                "patterns": ["complaint", "summons", "petition"],
                "trigger_type": TriggerType.COMPLAINT_SERVED,
                "description": "Commencement of Action - generates Answer deadline and filing requirements",
            },
            # Trial notices → TRIAL_DATE
            {
                "patterns": ["trial notice", "notice of trial", "order setting trial", "trial order"],
                "trigger_type": TriggerType.TRIAL_DATE,
                "description": "Trial Date Set - generates pretrial deadlines (witness lists, exhibits, jury instructions)",
            },
            # Motions → MOTION_FILED
            {
                "patterns": ["motion to dismiss", "motion for summary judgment", "motion to compel"],
                "trigger_type": TriggerType.MOTION_FILED,
                "exclude_patterns": ["response", "opposition", "reply"],
                "description": "Motion Filed - generates Response deadline",
            },
            # Discovery → DISCOVERY_COMMENCED
            {
                "patterns": ["interrogator", "request for production", "request for admission", "rfp", "rfa"],
                "trigger_type": TriggerType.DISCOVERY_COMMENCED,
                "exclude_patterns": ["response", "answer"],
                "description": "Discovery Request - generates 30-day response deadline",
            },
            # Orders → ORDER_ENTERED
            {
                "patterns": ["order granting", "order denying", "final judgment", "judgment"],
                "trigger_type": TriggerType.ORDER_ENTERED,
                "description": "Order Entered - generates post-judgment and appeal deadlines",
            },
            # Hearing → HEARING_SCHEDULED
            {
                "patterns": ["notice of hearing", "hearing notice", "scheduling order"],
                "trigger_type": TriggerType.HEARING_SCHEDULED,
                "description": "Hearing Scheduled - generates hearing prep deadlines",
            },
        ]

        # Check each pattern
        for pattern_info in DOCUMENT_PATTERNS:
            patterns = pattern_info["patterns"]
            exclude_patterns = pattern_info.get("exclude_patterns", [])

            # Check if any pattern matches
            matched_pattern = None
            for pattern in patterns:
                if pattern in doc_type_lower:
                    matched_pattern = pattern
                    break

            if not matched_pattern:
                continue

            # Check exclusions
            if any(excl in doc_type_lower for excl in exclude_patterns):
                continue

            trigger_type = pattern_info["trigger_type"]

            # Get applicable rules to count expected deadlines
            applicable_rules = self.get_applicable_rules(jurisdiction, court_type, trigger_type)
            expected_deadlines = sum(len(r.dependent_deadlines) for r in applicable_rules)

            # Determine rule set code
            rule_set_code = "FL:RCP" if jurisdiction == "florida_state" else "FRCP"

            return {
                "matches_trigger": True,
                "trigger_type": trigger_type,
                "trigger_type_str": trigger_type.value,
                "rule_set_code": rule_set_code,
                "expected_deadlines": expected_deadlines,
                "trigger_description": pattern_info["description"],
                "matched_pattern": matched_pattern,
            }

        # No match found
        return {
            "matches_trigger": False,
            "trigger_type": None,
            "trigger_type_str": None,
            "rule_set_code": None,
            "expected_deadlines": 0,
            "trigger_description": "No standard rule template found - will extract deadlines from document text",
            "matched_pattern": None,
        }

    def calculate_dependent_deadlines(
        self,
        trigger_date: date,
        rule_template: RuleTemplate,
        service_method: str = "email",
        case_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate all dependent deadlines from a trigger event with 10/10 legal defensibility

        Uses AuthoritativeDeadlineCalculator to ensure complete transparency:
        - Full rule citations for every calculation step
        - Detailed calculation basis with roll logic explanation
        - Jurisdiction-specific service method extensions
        - Court days vs calendar days properly handled

        CompuLaw-style output includes:
        - Party-specific titles: "Deadline for Defendant, John Smith to file Answer"
        - Calculation explanations: "(Calculated: 20 days after service of complaint)"
        - Trigger formulas: "triggered 20 Days after $CMPSVD"

        Args:
            trigger_date: Date of the trigger event
            rule_template: Rule template to apply
            service_method: "electronic", "mail", or "hand_delivery"
            case_context: Optional dict with case info for CompuLaw-style titles
                - plaintiffs: List of plaintiff names
                - defendants: List of defendant names
                - case_number: Case number
                - source_document: Source document name/number

        Returns:
            List of calculated deadlines with complete audit trails
        """
        from app.utils.florida_holidays import subtract_court_days

        # Log deprecation warning when hardcoded rules are used
        if not rule_template.rule_id.startswith("DB_") and not rule_template.rule_id.startswith("AC_"):
            logger.info(
                f"Using hardcoded rule '{rule_template.rule_id}' for {rule_template.trigger_type.value}. "
                "Consider migrating to Authority Core for dynamic rule management."
            )

        calculated_deadlines = []

        # Initialize calculator for this jurisdiction
        calculator = AuthoritativeDeadlineCalculator(jurisdiction=rule_template.jurisdiction)

        # Extract case context for CompuLaw-style formatting
        plaintiffs = case_context.get('plaintiffs', []) if case_context else []
        defendants = case_context.get('defendants', []) if case_context else []
        case_number = case_context.get('case_number', '') if case_context else ''
        source_document = case_context.get('source_document', '') if case_context else ''

        # Build trigger code for CompuLaw-style formula (e.g., $TR, $CMPSVD, $MDRF)
        trigger_codes = {
            'trial_date': '$TR',
            'complaint_served': '$CMPSVD',
            'case_filed': '$CF',
            'discovery_commenced': '$DC',
            'discovery_deadline': '$DCUTOFF',
            'pretrial_conference': '$PC',
            'hearing_scheduled': '$HR',
            'motion_filed': '$MTN',
            'order_entered': '$ORD',
            'appeal_filed': '$NOA',
            'service_completed': '$SVC',
            'answer_due': '$ANS',
        }
        trigger_code = trigger_codes.get(rule_template.trigger_type.value, '$TRIG')

        for dependent in rule_template.dependent_deadlines:
            # =============================================================
            # CONDITIONAL DEADLINES: Filter based on user-provided context
            # =============================================================
            if dependent.condition_field is not None:
                # This deadline has a condition - check if context satisfies it
                if case_context and dependent.condition_field in case_context:
                    # Context has the field - check if value matches
                    actual_value = case_context[dependent.condition_field]

                    # SOFT MATCH: Normalize both sides before comparing
                    # Handles "true" (string) vs True (boolean) mismatches from LLM
                    norm_actual = self._normalize_value(actual_value)
                    norm_expected = self._normalize_value(dependent.condition_value)

                    if norm_actual != norm_expected:
                        # Condition not met - skip this deadline
                        logger.debug(
                            f"Skipping deadline '{dependent.name}' - condition not met: "
                            f"{dependent.condition_field}={norm_actual} (expected {norm_expected}) "
                            f"[raw: {actual_value} vs {dependent.condition_value}]"
                        )
                        continue
                else:
                    # SAFETY FALLBACK: Field missing from context
                    # Better to have an extra deadline than miss a fatal one
                    logger.warning(
                        f"Condition field '{dependent.condition_field}' not in context for deadline '{dependent.name}'. "
                        f"Creating deadline as safety fallback."
                    )
                    # Continue to create the deadline

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

            # ================================================================
            # COMPULAW-STYLE FORMATTING
            # ================================================================

            # Build party string based on who's responsible
            party_str = ""
            if dependent.party_responsible == "plaintiff":
                if plaintiffs:
                    party_str = f"Plaintiff{'s' if len(plaintiffs) > 1 else ''}, {' and '.join(plaintiffs)}"
                else:
                    party_str = "Plaintiff"
            elif dependent.party_responsible == "defendant":
                if defendants:
                    party_str = f"Defendant{'s' if len(defendants) > 1 else ''}, {' and '.join(defendants)}"
                else:
                    party_str = "Defendant"
            elif dependent.party_responsible == "both":
                party_str = "All Parties"
            elif dependent.party_responsible == "court":
                party_str = "Court"
            else:
                party_str = dependent.party_responsible.title()

            # Build CompuLaw-style trigger formula
            if calc_method == CalculationMethod.COURT_DAYS:
                day_type = "Court Day" if base_days == 1 else "Court Days"
            else:
                day_type = "Day" if base_days == 1 else "Days"

            if is_before_trigger:
                trigger_formula = f"triggered {base_days} {day_type} before {trigger_code}"
            else:
                # Check if there's service extension
                service_ext = 0
                if dependent.add_service_method_days:
                    try:
                        service_ext = get_service_extension_days(rule_template.jurisdiction, service_method)
                    except (ValueError, KeyError, TypeError) as e:
                        logger.warning(f"Could not get service extension days: {e}")

                if service_ext > 0:
                    trigger_formula = f"triggered {base_days} {day_type} plus {service_ext} Days ({service_method}) after {trigger_code}"
                else:
                    trigger_formula = f"triggered {base_days} {day_type} after {trigger_code}"

            # Build calculation explanation for title
            trigger_name = rule_template.trigger_type.value.replace('_', ' ')
            if is_before_trigger:
                calc_explanation = f"Calculated: {base_days} days before {trigger_name}"
            else:
                if service_ext > 0:
                    calc_explanation = f"Calculated: {base_days} days + {service_ext} days ({service_method}) after {trigger_name}"
                else:
                    calc_explanation = f"Calculated: {base_days} days after {trigger_name}"

            # Build CompuLaw-style title
            # Format: "Deadline for [Party] to [action] ([Calculation])"
            action_verb = dependent.action_required.split()[0].lower() if dependent.action_required else "complete"
            if action_verb in ['file', 'serve', 'complete', 'exchange', 'submit', 'respond', 'disclose', 'provide']:
                compulaw_title = f"Deadline for {party_str} to {dependent.action_required} ({calc_explanation})"
            else:
                compulaw_title = f"{dependent.name} - {party_str} ({calc_explanation})"

            # Build CompuLaw-style description with source reference and trigger formula
            source_ref = ""
            if source_document:
                source_ref = f"\n[per {source_document}; {trigger_date.strftime('%m/%d/%Y')}]"

            compulaw_description = f"{dependent.description}{source_ref} {trigger_formula}"

            calculated_deadlines.append({
                'title': compulaw_title,
                'description': compulaw_description,
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
                'court_type': rule_template.court_type,
                # CompuLaw-style extras
                'trigger_code': trigger_code,
                'trigger_formula': trigger_formula,
                'party_string': party_str
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


    def load_templates_from_database(self, db: "Session") -> List[RuleTemplate]:
        """
        Load rule templates from the database jurisdiction system.

        Converts database RuleTemplate models to the dataclass format
        used by the rules engine for calculation.

        Args:
            db: SQLAlchemy database session

        Returns:
            List of RuleTemplate dataclasses loaded from database
        """
        from app.models.jurisdiction import (
            RuleTemplate as DBRuleTemplate,
            RuleTemplateDeadline as DBDeadline,
            RuleSet,
            TriggerType as DBTriggerType,
            DeadlinePriority as DBPriority,
            CalculationMethod as DBCalcMethod
        )

        db_templates = []

        try:
            # Get all active rule templates with their deadlines
            templates = db.query(DBRuleTemplate).filter(
                DBRuleTemplate.is_active == True
            ).all()

            for db_template in templates:
                # Get the rule set for jurisdiction info
                rule_set = db.query(RuleSet).filter(
                    RuleSet.id == db_template.rule_set_id
                ).first()

                if not rule_set:
                    continue

                # Determine jurisdiction string from rule set
                jurisdiction = self._map_rule_set_to_jurisdiction(rule_set)
                court_type = self._map_court_type_to_string(rule_set.court_type.value if rule_set.court_type else "circuit")

                # Convert trigger type
                try:
                    trigger_type = TriggerType(db_template.trigger_type.value)
                except (ValueError, AttributeError):
                    logger.warning(f"Unknown trigger type: {db_template.trigger_type}")
                    continue

                # Convert deadlines
                dependent_deadlines = []
                for db_deadline in db_template.deadlines:
                    if not db_deadline.is_active:
                        continue

                    # Map priority
                    priority_map = {
                        "informational": DeadlinePriority.INFORMATIONAL,
                        "standard": DeadlinePriority.STANDARD,
                        "important": DeadlinePriority.IMPORTANT,
                        "critical": DeadlinePriority.CRITICAL,
                        "fatal": DeadlinePriority.FATAL,
                    }
                    priority = priority_map.get(
                        db_deadline.priority.value if db_deadline.priority else "standard",
                        DeadlinePriority.STANDARD
                    )

                    # Map calculation method
                    calc_method = "calendar_days"
                    if db_deadline.calculation_method:
                        calc_method = db_deadline.calculation_method.value

                    dependent_deadlines.append(DependentDeadline(
                        name=db_deadline.name,
                        description=db_deadline.description or "",
                        days_from_trigger=db_deadline.days_from_trigger,
                        priority=priority,
                        party_responsible=db_deadline.party_responsible or "both",
                        action_required=db_deadline.action_required or "",
                        calculation_method=calc_method,
                        add_service_method_days=db_deadline.add_service_days or False,
                        rule_citation=db_deadline.rule_citation or "",
                        notes=db_deadline.notes
                    ))

                if not dependent_deadlines:
                    continue

                # Create RuleTemplate dataclass
                template = RuleTemplate(
                    rule_id=f"DB_{rule_set.code}_{db_template.rule_code}",
                    name=db_template.name,
                    description=db_template.description or "",
                    jurisdiction=jurisdiction,
                    court_type=court_type,
                    trigger_type=trigger_type,
                    citation=db_template.citation or "",
                    dependent_deadlines=dependent_deadlines
                )

                db_templates.append(template)

            logger.info(f"Loaded {len(db_templates)} rule templates from database")

        except Exception as e:
            logger.error(f"Error loading templates from database: {e}")

        return db_templates

    def _map_rule_set_to_jurisdiction(self, rule_set: Any) -> str:
        """Map a RuleSet to a jurisdiction string for the rules engine"""
        code = rule_set.code.upper()

        # Federal rules
        if code in ["FRCP", "FRAP", "FRBP"]:
            return "federal"

        # Florida state rules
        if code.startswith("FL:"):
            return "florida_state"

        # Florida local rules
        if "LOCAL" in code or code.startswith("FL-"):
            return "florida_local"

        # Default based on jurisdiction type
        if rule_set.jurisdiction:
            jtype = rule_set.jurisdiction.jurisdiction_type
            if jtype and jtype.value == "federal":
                return "federal"
            elif jtype and jtype.value == "state":
                return "florida_state"

        return "florida_state"  # Default

    def _map_court_type_to_string(self, court_type: str) -> str:
        """Map database court type to rules engine court type string"""
        mapping = {
            "circuit": "civil",
            "county": "civil",
            "district": "civil",
            "bankruptcy": "civil",
            "appellate_state": "appellate",
            "appellate_federal": "appellate",
            "supreme_state": "appellate",
            "supreme_federal": "appellate",
        }
        return mapping.get(court_type, "civil")

    def get_all_templates_with_db(self, db: "Session") -> List[RuleTemplate]:
        """
        Get all templates including database-loaded ones.

        Database templates take precedence over hardcoded templates
        with matching rule_id prefixes.
        """
        # Start with hardcoded templates
        all_templates = list(self.rule_templates.values())

        # Load database templates
        db_templates = self.load_templates_from_database(db)

        # Add database templates (they won't conflict since IDs are prefixed with DB_)
        all_templates.extend(db_templates)

        return all_templates

    def get_applicable_rules_with_db(
        self,
        db: "Session",
        jurisdiction: str,
        court_type: str,
        trigger_type: TriggerType,
        rule_set_ids: Optional[List[str]] = None
    ) -> List[RuleTemplate]:
        """
        Get applicable rules including database-loaded ones.

        Can optionally filter by specific rule set IDs (from jurisdiction detection).
        """
        # Get hardcoded templates
        applicable = self.get_applicable_rules(jurisdiction, court_type, trigger_type)

        # Load and filter database templates
        db_templates = self.load_templates_from_database(db)

        for template in db_templates:
            if (template.jurisdiction == jurisdiction and
                template.court_type == court_type and
                template.trigger_type == trigger_type):

                # If rule_set_ids provided, filter by them
                if rule_set_ids:
                    # Extract rule set code from template ID (DB_{code}_{rule_code})
                    parts = template.rule_id.split("_", 2)
                    if len(parts) >= 2:
                        rule_set_code = parts[1]
                        if rule_set_code not in rule_set_ids:
                            continue

                applicable.append(template)

        return applicable


class DatabaseRulesEngine:
    """
    A wrapper around RulesEngine that primarily uses database-loaded rules.

    This class provides the same interface as RulesEngine but loads
    rule templates from the jurisdiction system database tables.

    Usage:
        db_engine = DatabaseRulesEngine(db_session)
        templates = db_engine.get_applicable_rules(jurisdiction, court_type, trigger_type)
    """

    def __init__(self, db: "Session"):
        self.db = db
        self._base_engine = rules_engine  # Use singleton for hardcoded templates
        self._db_templates_cache: Optional[List[RuleTemplate]] = None

    def _get_db_templates(self) -> List[RuleTemplate]:
        """Get database templates with caching"""
        if self._db_templates_cache is None:
            self._db_templates_cache = self._base_engine.load_templates_from_database(self.db)
        return self._db_templates_cache

    def get_all_templates(self) -> List[RuleTemplate]:
        """Get all templates including database ones"""
        return self._base_engine.get_all_templates_with_db(self.db)

    def get_applicable_rules(
        self,
        jurisdiction: str,
        court_type: str,
        trigger_type: TriggerType,
        rule_set_codes: Optional[List[str]] = None
    ) -> List[RuleTemplate]:
        """Get applicable rules for given context"""
        return self._base_engine.get_applicable_rules_with_db(
            self.db, jurisdiction, court_type, trigger_type, rule_set_codes
        )

    def calculate_dependent_deadlines(
        self,
        trigger_date: date,
        rule_template: RuleTemplate,
        service_method: str = "email",
        case_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Calculate deadlines (delegates to base engine)"""
        return self._base_engine.calculate_dependent_deadlines(
            trigger_date, rule_template, service_method, case_context
        )

    def get_template_by_id(self, rule_id: str) -> Optional[RuleTemplate]:
        """Get template by ID (checks both hardcoded and database)"""
        # Check hardcoded first
        template = self._base_engine.get_template_by_id(rule_id)
        if template:
            return template

        # Check database templates
        for t in self._get_db_templates():
            if t.rule_id == rule_id:
                return t

        return None

    def invalidate_cache(self):
        """Invalidate the database templates cache"""
        self._db_templates_cache = None

    # =========================================================================
    # AUTHORITY CORE INTEGRATION
    # =========================================================================

    async def get_authority_core_templates(
        self,
        jurisdiction_id: str,
        trigger_type: TriggerType,
        case_context: Optional[Dict[str, Any]] = None
    ) -> List[RuleTemplate]:
        """
        Get rule templates from Authority Core database.

        This method queries the Authority Core rules database and converts
        matching rules to RuleTemplate dataclasses for use with the deadline
        calculation engine.

        Args:
            jurisdiction_id: UUID of the target jurisdiction
            trigger_type: The trigger event type
            case_context: Optional context for condition evaluation

        Returns:
            List of RuleTemplate dataclasses from Authority Core
        """
        # Query Authority Core
        ac_rules = await get_authority_core_rules(
            self.db, jurisdiction_id, trigger_type, case_context
        )

        if not ac_rules:
            return []

        # Convert to RuleTemplates
        templates = []
        for rule_dict in ac_rules:
            template = convert_authority_rule_to_template(rule_dict)
            templates.append(template)

        logger.info(f"Loaded {len(templates)} Authority Core templates for {trigger_type.value}")
        return templates

    def get_templates_with_authority_core(
        self,
        jurisdiction_id: str,
        trigger_type: TriggerType,
        case_context: Optional[Dict[str, Any]] = None,
        fallback_jurisdiction: str = "florida_state",
        fallback_court_type: str = "civil"
    ) -> List[RuleTemplate]:
        """
        Get rule templates, prioritizing Authority Core over hardcoded rules.

        This is the primary method for getting rules in the new architecture.
        It first checks Authority Core database, then falls back to hardcoded
        templates if no Authority Core rules are found.

        Args:
            jurisdiction_id: UUID of the target jurisdiction
            trigger_type: The trigger event type
            case_context: Optional context for condition evaluation
            fallback_jurisdiction: Jurisdiction string for hardcoded fallback
            fallback_court_type: Court type for hardcoded fallback

        Returns:
            List of RuleTemplate dataclasses (Authority Core or hardcoded)
        """
        import asyncio

        # Try to get Authority Core rules (run async in sync context)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        get_authority_core_rules(self.db, jurisdiction_id, trigger_type, case_context)
                    )
                    ac_rules = future.result(timeout=5)
            else:
                ac_rules = asyncio.run(
                    get_authority_core_rules(self.db, jurisdiction_id, trigger_type, case_context)
                )
        except Exception as e:
            logger.warning(f"Authority Core query failed, using fallback: {e}")
            ac_rules = []

        if ac_rules:
            # Convert Authority Core rules to templates
            templates = []
            for rule_dict in ac_rules:
                template = convert_authority_rule_to_template(
                    rule_dict, fallback_jurisdiction, fallback_court_type
                )
                templates.append(template)

            logger.info(f"Using {len(templates)} Authority Core templates for {trigger_type.value}")
            return templates

        # Fallback to hardcoded templates
        logger.info(f"No Authority Core rules found, using hardcoded templates for {trigger_type.value}")
        return self.get_applicable_rules(
            fallback_jurisdiction, fallback_court_type, trigger_type
        )

    # =========================================================================
    # HIERARCHY RESOLUTION - The "Sovereign Brain" Graph Traversal
    # =========================================================================

    def resolve_active_rules(
        self,
        case_id: str,
        trigger_type: Optional[TriggerType] = None
    ) -> Dict[str, Any]:
        """
        Graph Traversal Engine - Resolve the complete hierarchy of rules for a case.

        This is the "moat" that makes LitDocket a CompuLaw competitor.
        It handles the complexity of concurrent rules (e.g., Bankruptcy + Local District).

        HIERARCHY RESOLUTION ORDER (highest to lowest priority):
        1. Judge Standing Orders (if available)
        2. Local Rules (circuit/district specific)
        3. State Rules (Florida Rules of Civil Procedure)
        4. Federal Rules (FRCP, FRBP)

        Args:
            case_id: UUID of the case
            trigger_type: Optional filter for specific trigger type

        Returns:
            {
                'case': Case object,
                'jurisdiction_chain': [Jurisdiction, ...],  # From most specific to general
                'active_rule_sets': [RuleSet, ...],  # Priority-sorted
                'rule_templates': [RuleTemplate, ...],  # All applicable templates
                'hierarchy_notes': str,  # Human-readable explanation
                'conflicts': [...]  # Any detected conflicts
            }
        """
        from app.models.case import Case
        from app.models.jurisdiction import (
            Jurisdiction, RuleSet, RuleSetDependency,
            CaseRuleSet, RuleTemplate as DBRuleTemplate,
            RuleTemplateDeadline, DependencyType, CourtLocation
        )

        result = {
            'case': None,
            'jurisdiction_chain': [],
            'active_rule_sets': [],
            'rule_templates': [],
            'hierarchy_notes': '',
            'conflicts': []
        }

        # Step 1: Load the case
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            logger.warning(f"Case not found: {case_id}")
            return result

        result['case'] = case
        notes = []

        # Step 2: Check for explicitly assigned rule sets (CaseRuleSet)
        case_rule_sets = self.db.query(CaseRuleSet).filter(
            CaseRuleSet.case_id == case_id,
            CaseRuleSet.is_active == True
        ).order_by(CaseRuleSet.priority.desc()).all()

        if case_rule_sets:
            notes.append(f"Found {len(case_rule_sets)} explicitly assigned rule sets")

            for crs in case_rule_sets:
                rule_set = self.db.query(RuleSet).filter(
                    RuleSet.id == crs.rule_set_id,
                    RuleSet.is_active == True
                ).first()

                if rule_set:
                    result['active_rule_sets'].append({
                        'rule_set': rule_set,
                        'priority': crs.priority,
                        'assignment_method': crs.assignment_method,
                        'source': 'explicit_assignment'
                    })

        # Step 3: Auto-detect jurisdiction from case metadata
        else:
            notes.append("No explicit rule sets - auto-detecting from case metadata")

            # Try to detect court location from case data
            court_location = None
            if case.court:
                # Search for matching court location
                court_location = self.db.query(CourtLocation).filter(
                    CourtLocation.is_active == True
                ).first()  # TODO: Match against detection_patterns

            # Build jurisdiction chain based on case metadata
            jurisdiction = case.jurisdiction or 'florida_state'
            court_type = case.case_type or 'civil'
            circuit = case.circuit
            district = case.district

            # Load base rule sets for this jurisdiction
            base_rule_sets = self._detect_applicable_rule_sets(
                jurisdiction, court_type, circuit, district
            )

            for priority, rule_set in enumerate(reversed(base_rule_sets)):
                result['active_rule_sets'].append({
                    'rule_set': rule_set,
                    'priority': priority,
                    'assignment_method': 'auto_detected',
                    'source': 'jurisdiction_detection'
                })

        # Step 4: Resolve rule set dependencies (CONCURRENT, INHERITS, SUPPLEMENTS, OVERRIDES)
        resolved_rule_sets = self._resolve_rule_set_dependencies(
            [rs['rule_set'] for rs in result['active_rule_sets']]
        )

        # Step 5: Build jurisdiction chain (for hierarchy display)
        seen_jurisdictions = set()
        for rs_info in result['active_rule_sets']:
            rule_set = rs_info['rule_set']
            if rule_set.jurisdiction and rule_set.jurisdiction_id not in seen_jurisdictions:
                # Walk up the jurisdiction tree
                jurisdiction = rule_set.jurisdiction
                chain = []
                while jurisdiction:
                    if jurisdiction.id not in seen_jurisdictions:
                        chain.append(jurisdiction)
                        seen_jurisdictions.add(jurisdiction.id)
                    jurisdiction = jurisdiction.parent
                result['jurisdiction_chain'].extend(chain)

        # Step 6: Load rule templates from resolved rule sets
        rule_set_ids = [rs.id for rs in resolved_rule_sets]
        db_templates = self.db.query(DBRuleTemplate).filter(
            DBRuleTemplate.rule_set_id.in_(rule_set_ids),
            DBRuleTemplate.is_active == True
        )

        if trigger_type:
            db_templates = db_templates.filter(DBRuleTemplate.trigger_type == trigger_type)

        for db_template in db_templates.all():
            # Convert to RuleTemplate dataclass for compatibility
            converted = self._convert_db_template_to_dataclass(db_template)
            if converted:
                result['rule_templates'].append(converted)

        # Step 7: Add hardcoded templates that match the case's jurisdiction
        jurisdiction_str = self._map_case_jurisdiction(case)
        court_type_str = case.case_type or 'civil'

        for template in self._base_engine.rule_templates.values():
            if template.jurisdiction == jurisdiction_str and template.court_type == court_type_str:
                if trigger_type is None or template.trigger_type == trigger_type:
                    result['rule_templates'].append(template)

        # Step 8: Detect conflicts between overlapping rule sets
        if len(result['active_rule_sets']) > 1:
            for i, rs_a in enumerate(result['active_rule_sets'][:-1]):
                for rs_b in result['active_rule_sets'][i+1:]:
                    conflicts = self.detect_conflicts(
                        rs_a['rule_set'],
                        rs_b['rule_set'],
                        trigger_type
                    )
                    result['conflicts'].extend(conflicts)

        # Build human-readable hierarchy notes
        if result['jurisdiction_chain']:
            chain_names = [j.name for j in result['jurisdiction_chain']]
            notes.append(f"Jurisdiction chain: {' → '.join(chain_names)}")

        if result['active_rule_sets']:
            rs_names = [rs['rule_set'].name for rs in result['active_rule_sets']]
            notes.append(f"Active rule sets: {', '.join(rs_names)}")

        if result['conflicts']:
            notes.append(f"⚠️ {len(result['conflicts'])} conflicts detected - review required")

        result['hierarchy_notes'] = '\n'.join(notes)

        logger.info(f"Resolved {len(result['rule_templates'])} templates for case {case_id}")
        return result

    def _detect_applicable_rule_sets(
        self,
        jurisdiction: str,
        court_type: str,
        circuit: Optional[str],
        district: Optional[str]
    ) -> List:
        """Auto-detect applicable rule sets based on case metadata"""
        from app.models.jurisdiction import RuleSet, Jurisdiction, JurisdictionType

        rule_sets = []

        # Map jurisdiction string to type
        if jurisdiction in ['federal', 'florida_federal']:
            juris_type = JurisdictionType.FEDERAL
        elif jurisdiction in ['florida_state', 'state']:
            juris_type = JurisdictionType.STATE
        else:
            juris_type = JurisdictionType.STATE  # Default

        # 1. Load base jurisdiction rule sets
        base_jurisdictions = self.db.query(Jurisdiction).filter(
            Jurisdiction.jurisdiction_type == juris_type,
            Jurisdiction.is_active == True
        ).all()

        # Collect all jurisdiction IDs first, then do a single query
        base_jurisdiction_ids = [juris.id for juris in base_jurisdictions]
        if base_jurisdiction_ids:
            juris_rule_sets = self.db.query(RuleSet).filter(
                RuleSet.jurisdiction_id.in_(base_jurisdiction_ids),
                RuleSet.is_active == True,
                RuleSet.is_local == False
            ).all()
            rule_sets.extend(juris_rule_sets)

        # 2. Load local rules for circuit/district
        if circuit or district:
            local_jurisdictions_query = self.db.query(Jurisdiction).filter(
                Jurisdiction.jurisdiction_type == JurisdictionType.LOCAL,
                Jurisdiction.is_active == True
            )

            if circuit:
                local_jurisdictions_query = local_jurisdictions_query.filter(
                    Jurisdiction.code.like(f'%{circuit}%')
                )

            local_jurisdictions = local_jurisdictions_query.all()
            local_jurisdiction_ids = [local_juris.id for local_juris in local_jurisdictions]

            if local_jurisdiction_ids:
                local_rule_sets = self.db.query(RuleSet).filter(
                    RuleSet.jurisdiction_id.in_(local_jurisdiction_ids),
                    RuleSet.is_active == True,
                    RuleSet.is_local == True
                ).all()
                rule_sets.extend(local_rule_sets)

        return rule_sets

    def _resolve_rule_set_dependencies(self, rule_sets: List[Any]) -> List[Any]:
        """
        Resolve dependencies and build complete list of rule sets.

        Handles CONCURRENT, INHERITS, SUPPLEMENTS, and OVERRIDES relationships.
        """
        from app.models.jurisdiction import RuleSet, RuleSetDependency, DependencyType

        resolved = []
        seen_ids = set()

        def add_with_dependencies(rule_set, depth=0):
            if rule_set.id in seen_ids or depth > 10:  # Prevent infinite loops
                return
            seen_ids.add(rule_set.id)
            resolved.append(rule_set)

            # Load dependencies
            dependencies = self.db.query(RuleSetDependency).filter(
                RuleSetDependency.rule_set_id == rule_set.id
            ).order_by(RuleSetDependency.priority.desc()).all()

            for dep in dependencies:
                required_rs = self.db.query(RuleSet).filter(
                    RuleSet.id == dep.required_rule_set_id,
                    RuleSet.is_active == True
                ).first()

                if required_rs:
                    add_with_dependencies(required_rs, depth + 1)

        for rs in rule_sets:
            add_with_dependencies(rs)

        return resolved

    def _convert_db_template_to_dataclass(self, db_template: Any) -> Optional[RuleTemplate]:
        """Convert a database RuleTemplate to the dataclass RuleTemplate"""
        try:
            from app.models.jurisdiction import RuleTemplateDeadline

            # Load deadlines
            db_deadlines = self.db.query(RuleTemplateDeadline).filter(
                RuleTemplateDeadline.rule_template_id == db_template.id,
                RuleTemplateDeadline.is_active == True
            ).order_by(RuleTemplateDeadline.display_order).all()

            dependent_deadlines = []
            for dd in db_deadlines:
                calc_method = dd.calculation_method.value if dd.calculation_method else 'calendar_days'
                priority = DeadlinePriority(dd.priority.value) if dd.priority else DeadlinePriority.STANDARD

                dependent_deadlines.append(DependentDeadline(
                    name=dd.name,
                    description=dd.description or '',
                    days_from_trigger=dd.days_from_trigger,
                    priority=priority,
                    party_responsible=dd.party_responsible or 'both',
                    action_required=dd.action_required or '',
                    calculation_method=calc_method,
                    add_service_method_days=dd.add_service_days or False,
                    rule_citation=dd.rule_citation or '',
                    notes=dd.notes
                ))

            # Map trigger type
            trigger_type = TriggerType(db_template.trigger_type.value) if db_template.trigger_type else TriggerType.CUSTOM_TRIGGER

            # Map jurisdiction and court type
            jurisdiction = self._base_engine._map_jurisdiction_to_string(db_template.rule_set) if db_template.rule_set else 'florida_state'
            court_type = self._base_engine._map_court_type_to_string(
                db_template.court_type.value if db_template.court_type else 'circuit'
            )

            return RuleTemplate(
                rule_id=f"DB_{db_template.rule_set.code if db_template.rule_set else 'UNKNOWN'}_{db_template.rule_code}",
                name=db_template.name,
                description=db_template.description or '',
                jurisdiction=jurisdiction,
                court_type=court_type,
                trigger_type=trigger_type,
                citation=db_template.citation or '',
                dependent_deadlines=dependent_deadlines
            )
        except Exception as e:
            logger.error(f"Error converting DB template {db_template.id}: {e}")
            return None

    def _map_case_jurisdiction(self, case: Any) -> str:
        """Map case jurisdiction field to rules engine jurisdiction string"""
        juris = (case.jurisdiction or '').lower()
        if juris in ['federal', 'florida_federal']:
            return 'federal'
        return 'florida_state'

    # =========================================================================
    # CONFLICT DETECTION - Identify when rules produce conflicting deadlines
    # =========================================================================

    def detect_conflicts(
        self,
        rule_set_a: Any,
        rule_set_b: Any,
        trigger_type: Optional[TriggerType] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify conflicts between two rule sets.

        A conflict occurs when:
        1. Two rules generate deadlines for the SAME event/action
        2. The calculated dates would be DIFFERENT

        This is critical for cases under concurrent jurisdiction
        (e.g., Bankruptcy + Local District rules).

        Args:
            rule_set_a: First RuleSet (database model or dict)
            rule_set_b: Second RuleSet (database model or dict)
            trigger_type: Optional filter for specific trigger type

        Returns:
            List of conflict objects:
            [{
                'event_name': str,
                'rule_set_a': str,  # Rule set code
                'rule_set_b': str,
                'days_a': int,
                'days_b': int,
                'difference_days': int,
                'resolution': str,  # Which rule takes precedence
                'citation_a': str,
                'citation_b': str
            }]
        """
        from app.models.jurisdiction import (
            RuleTemplate as DBRuleTemplate,
            RuleTemplateDeadline,
            RuleSetDependency,
            DependencyType
        )

        conflicts = []

        # Get rule set IDs
        rs_a_id = rule_set_a.id if hasattr(rule_set_a, 'id') else rule_set_a.get('id')
        rs_b_id = rule_set_b.id if hasattr(rule_set_b, 'id') else rule_set_b.get('id')

        if not rs_a_id or not rs_b_id:
            return conflicts

        # Load templates from both rule sets
        query_a = self.db.query(DBRuleTemplate).filter(
            DBRuleTemplate.rule_set_id == rs_a_id,
            DBRuleTemplate.is_active == True
        )
        query_b = self.db.query(DBRuleTemplate).filter(
            DBRuleTemplate.rule_set_id == rs_b_id,
            DBRuleTemplate.is_active == True
        )

        if trigger_type:
            query_a = query_a.filter(DBRuleTemplate.trigger_type == trigger_type)
            query_b = query_b.filter(DBRuleTemplate.trigger_type == trigger_type)

        templates_a = {t.trigger_type: t for t in query_a.all()}
        templates_b = {t.trigger_type: t for t in query_b.all()}

        # Find overlapping trigger types
        common_triggers = set(templates_a.keys()) & set(templates_b.keys())

        for trigger in common_triggers:
            template_a = templates_a[trigger]
            template_b = templates_b[trigger]

            # Load deadlines from both templates
            deadlines_a = self.db.query(RuleTemplateDeadline).filter(
                RuleTemplateDeadline.rule_template_id == template_a.id,
                RuleTemplateDeadline.is_active == True
            ).all()

            deadlines_b = self.db.query(RuleTemplateDeadline).filter(
                RuleTemplateDeadline.rule_template_id == template_b.id,
                RuleTemplateDeadline.is_active == True
            ).all()

            # Index deadlines by normalized name for comparison
            deadlines_a_by_name = {self._normalize_deadline_name(d.name): d for d in deadlines_a}
            deadlines_b_by_name = {self._normalize_deadline_name(d.name): d for d in deadlines_b}

            # Find overlapping deadlines
            common_names = set(deadlines_a_by_name.keys()) & set(deadlines_b_by_name.keys())

            for name in common_names:
                dl_a = deadlines_a_by_name[name]
                dl_b = deadlines_b_by_name[name]

                # Check if days are different
                if dl_a.days_from_trigger != dl_b.days_from_trigger:
                    # Determine resolution based on hierarchy
                    resolution = self._resolve_conflict(rule_set_a, rule_set_b)

                    conflicts.append({
                        'event_name': dl_a.name,
                        'trigger_type': trigger.value if hasattr(trigger, 'value') else str(trigger),
                        'rule_set_a': rule_set_a.code if hasattr(rule_set_a, 'code') else 'Unknown',
                        'rule_set_b': rule_set_b.code if hasattr(rule_set_b, 'code') else 'Unknown',
                        'days_a': dl_a.days_from_trigger,
                        'days_b': dl_b.days_from_trigger,
                        'difference_days': abs(dl_a.days_from_trigger - dl_b.days_from_trigger),
                        'resolution': resolution,
                        'citation_a': dl_a.rule_citation or '',
                        'citation_b': dl_b.rule_citation or '',
                        'shorter_deadline': 'A' if dl_a.days_from_trigger < dl_b.days_from_trigger else 'B'
                    })

        if conflicts:
            logger.warning(
                f"Detected {len(conflicts)} conflicts between rule sets "
                f"{rule_set_a.code if hasattr(rule_set_a, 'code') else '?'} and "
                f"{rule_set_b.code if hasattr(rule_set_b, 'code') else '?'}"
            )

        return conflicts

    def _normalize_deadline_name(self, name: str) -> str:
        """Normalize deadline name for comparison"""
        if not name:
            return ''
        # Lowercase, remove extra spaces, remove common suffixes
        normalized = name.lower().strip()
        for suffix in [' due', ' deadline', ' date', ' (federal)', ' (state)', ' (local)']:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        return normalized.replace('  ', ' ')

    def _resolve_conflict(self, rule_set_a: Any, rule_set_b: Any) -> str:
        """
        Determine which rule set takes precedence in a conflict.

        HIERARCHY (highest to lowest):
        1. Judge Standing Orders
        2. Local Rules (is_local=True)
        3. State Rules
        4. Federal Rules

        For same-level conflicts, the MORE RESTRICTIVE (shorter deadline) applies.
        """
        from app.models.jurisdiction import RuleSetDependency, DependencyType

        # Check for explicit override relationship
        override = self.db.query(RuleSetDependency).filter(
            RuleSetDependency.rule_set_id == rule_set_a.id,
            RuleSetDependency.required_rule_set_id == rule_set_b.id,
            RuleSetDependency.dependency_type == DependencyType.OVERRIDES
        ).first()

        if override:
            return f"{rule_set_a.code} overrides {rule_set_b.code}"

        # Check reverse
        override = self.db.query(RuleSetDependency).filter(
            RuleSetDependency.rule_set_id == rule_set_b.id,
            RuleSetDependency.required_rule_set_id == rule_set_a.id,
            RuleSetDependency.dependency_type == DependencyType.OVERRIDES
        ).first()

        if override:
            return f"{rule_set_b.code} overrides {rule_set_a.code}"

        # Check local vs non-local
        a_is_local = rule_set_a.is_local if hasattr(rule_set_a, 'is_local') else False
        b_is_local = rule_set_b.is_local if hasattr(rule_set_b, 'is_local') else False

        if a_is_local and not b_is_local:
            return f"Local rule {rule_set_a.code} takes precedence"
        if b_is_local and not a_is_local:
            return f"Local rule {rule_set_b.code} takes precedence"

        # Default: More restrictive deadline applies (safety)
        return "Use shorter (more restrictive) deadline"


# Singleton instance (for backwards compatibility with hardcoded rules)
rules_engine = RulesEngine()


# =============================================================================
# AUTHORITY CORE INTEGRATION
# =============================================================================

async def get_authority_core_rules(
    db: "Session",
    jurisdiction_id: str,
    trigger_type: TriggerType,
    case_context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Query Authority Core database for matching rules.

    This function checks the Authority Core database (authority_rules table)
    for verified rules that match the trigger type and jurisdiction.

    Authority Core rules take precedence over hardcoded templates when available.

    Args:
        db: Database session
        jurisdiction_id: UUID of the jurisdiction
        trigger_type: The trigger event type
        case_context: Optional context for condition evaluation

    Returns:
        List of rule dictionaries with deadline specifications
    """
    from app.models.authority_core import AuthorityRule
    from app.models.enums import AuthorityTier
    from sqlalchemy import or_

    try:
        # Query for matching verified rules
        query = db.query(AuthorityRule).filter(
            AuthorityRule.trigger_type == trigger_type.value,
            AuthorityRule.is_active == True,
            AuthorityRule.is_verified == True
        )

        # Include rules for this jurisdiction OR federal rules (higher precedence)
        query = query.filter(
            or_(
                AuthorityRule.jurisdiction_id == jurisdiction_id,
                AuthorityRule.authority_tier == AuthorityTier.FEDERAL
            )
        )

        rules = query.all()

        if not rules:
            logger.debug(f"No Authority Core rules found for trigger_type={trigger_type.value}, jurisdiction={jurisdiction_id}")
            return []

        # Sort by tier precedence (federal > state > local > standing_order > firm)
        tier_order = {
            AuthorityTier.FEDERAL: 1,
            AuthorityTier.STATE: 2,
            AuthorityTier.LOCAL: 3,
            AuthorityTier.STANDING_ORDER: 4,
            AuthorityTier.FIRM: 5
        }
        rules.sort(key=lambda r: tier_order.get(r.authority_tier, 99))

        # Convert to dictionaries
        result = []
        for rule in rules:
            result.append({
                'rule_id': rule.id,
                'rule_code': rule.rule_code,
                'rule_name': rule.rule_name,
                'trigger_type': rule.trigger_type,
                'authority_tier': rule.authority_tier.value if rule.authority_tier else 'state',
                'citation': rule.citation,
                'deadlines': rule.deadlines or [],
                'conditions': rule.conditions,
                'service_extensions': rule.service_extensions or {'mail': 3, 'electronic': 0, 'personal': 0},
                'source_url': rule.source_url,
                'is_verified': rule.is_verified,
                'confidence_score': float(rule.confidence_score) if rule.confidence_score else 0.0
            })

        logger.info(f"Found {len(result)} Authority Core rules for trigger_type={trigger_type.value}")
        return result

    except Exception as e:
        logger.error(f"Error querying Authority Core: {e}")
        return []


def convert_authority_rule_to_template(
    rule_dict: Dict[str, Any],
    jurisdiction: str = "florida_state",
    court_type: str = "civil"
) -> RuleTemplate:
    """
    Convert an Authority Core rule dictionary to a RuleTemplate dataclass.

    This allows Authority Core rules to be used with the existing
    calculate_dependent_deadlines method.

    Args:
        rule_dict: Rule dictionary from Authority Core
        jurisdiction: Jurisdiction string for template
        court_type: Court type for template

    Returns:
        RuleTemplate dataclass compatible with rules engine
    """
    # Convert trigger type string to enum
    trigger_type_str = rule_dict.get('trigger_type', 'custom_trigger')
    try:
        trigger_type = TriggerType(trigger_type_str)
    except ValueError:
        trigger_type = TriggerType.CUSTOM_TRIGGER

    # Convert deadlines to DependentDeadline dataclasses
    dependent_deadlines = []
    for dl_spec in rule_dict.get('deadlines', []):
        # Map priority string to enum
        priority_str = dl_spec.get('priority', 'standard')
        try:
            priority = DeadlinePriority(priority_str)
        except ValueError:
            priority = DeadlinePriority.STANDARD

        dependent_deadlines.append(DependentDeadline(
            name=dl_spec.get('title', 'Unknown Deadline'),
            description=dl_spec.get('description', ''),
            days_from_trigger=dl_spec.get('days_from_trigger', 0),
            priority=priority,
            party_responsible=dl_spec.get('party_responsible', 'both'),
            action_required=dl_spec.get('description', ''),
            calculation_method=dl_spec.get('calculation_method', 'calendar_days'),
            add_service_method_days=True,  # Authority Core rules include service extensions
            rule_citation=rule_dict.get('citation', ''),
            notes=f"Source: Authority Core ({rule_dict.get('rule_code', 'N/A')})"
        ))

    return RuleTemplate(
        rule_id=f"AC_{rule_dict.get('rule_id', 'unknown')[:8]}",
        name=rule_dict.get('rule_name', 'Authority Core Rule'),
        description=f"Authority Core verified rule: {rule_dict.get('rule_code', '')}",
        jurisdiction=jurisdiction,
        court_type=court_type,
        trigger_type=trigger_type,
        dependent_deadlines=dependent_deadlines,
        citation=rule_dict.get('citation', '')
    )


def get_rules_engine_for_case(db: "Session", case_id: str) -> DatabaseRulesEngine:
    """
    Get a DatabaseRulesEngine configured for a specific case.

    This function can be extended to auto-detect the case's jurisdiction
    and pre-filter applicable rules.
    """
    return DatabaseRulesEngine(db)
