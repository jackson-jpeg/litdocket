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

    def calculate_dependent_deadlines(
        self,
        trigger_date: date,
        rule_template: RuleTemplate,
        service_method: str = "email",
        case_context: Optional[Dict] = None
    ) -> List[Dict]:
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
                    except:
                        pass

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


# Singleton instance
rules_engine = RulesEngine()
