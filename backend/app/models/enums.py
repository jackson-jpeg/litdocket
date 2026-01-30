"""
Centralized Enum Definitions for LitDocket

This is the SINGLE SOURCE OF TRUTH for all enums used across the application.
Do NOT define duplicate enums elsewhere - import from here.
"""
import enum


class TriggerType(enum.Enum):
    """
    Types of trigger events for deadline calculation.

    These are the "starting points" that generate chains of dependent deadlines.
    Used by rules_engine.py for deadline calculation and jurisdiction models.
    """
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
    MEDIATION_SCHEDULED = "mediation_scheduled"
    CUSTOM_TRIGGER = "custom_trigger"


class DeadlinePriority(enum.Enum):
    """
    Deadline priority levels.

    Used for visual indicators and sorting in the UI.
    FATAL = missing this deadline has case-ending consequences (malpractice risk)
    """
    INFORMATIONAL = "informational"
    STANDARD = "standard"
    IMPORTANT = "important"
    CRITICAL = "critical"
    FATAL = "fatal"  # Missing = malpractice


class CalculationMethod(enum.Enum):
    """
    Methods for calculating deadline dates.

    calendar_days: Count every day including weekends/holidays
    business_days: Skip weekends and court holidays
    court_days: Same as business_days (Florida terminology)
    """
    CALENDAR_DAYS = "calendar_days"
    BUSINESS_DAYS = "business_days"
    COURT_DAYS = "court_days"


class JurisdictionType(enum.Enum):
    """Types of court jurisdictions"""
    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"
    BANKRUPTCY = "bankruptcy"
    APPELLATE = "appellate"


class CourtType(enum.Enum):
    """Types of courts within a jurisdiction"""
    DISTRICT = "district"
    CIRCUIT = "circuit"
    COUNTY = "county"
    BANKRUPTCY = "bankruptcy"
    APPELLATE = "appellate"
    SUPREME = "supreme"


class AuthorityTier(enum.Enum):
    """
    Authority levels for rules, used for precedence.

    Higher tiers take precedence over lower tiers when rules conflict.
    FEDERAL > STATE > LOCAL > STANDING_ORDER > FIRM
    """
    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"
    STANDING_ORDER = "standing_order"
    FIRM = "firm"


class ProposalStatus(enum.Enum):
    """Status of AI-extracted rule proposals awaiting review"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class ScrapeStatus(enum.Enum):
    """Status of web scraping jobs for rule extraction"""
    QUEUED = "queued"
    SEARCHING = "searching"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    FAILED = "failed"


class ConflictResolution(enum.Enum):
    """How a rule conflict was resolved"""
    PENDING = "pending"
    USE_HIGHER_TIER = "use_higher_tier"
    USE_RULE_A = "use_rule_a"
    USE_RULE_B = "use_rule_b"
    MANUAL = "manual"
    IGNORED = "ignored"
