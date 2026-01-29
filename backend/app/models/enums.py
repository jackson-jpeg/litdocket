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
    APPELLATE = "appellate"


class CourtType(enum.Enum):
    """Types of courts within a jurisdiction"""
    DISTRICT = "district"
    CIRCUIT = "circuit"
    COUNTY = "county"
    BANKRUPTCY = "bankruptcy"
    APPELLATE = "appellate"
    SUPREME = "supreme"


class TriggerStatus(enum.Enum):
    """
    Status of document-to-trigger matching.

    Used by DocumentClassificationService to indicate whether a document
    matches a known trigger pattern or requires further research.

    MATCHED: Document matches a known trigger pattern with established rules
    UNRECOGNIZED: Document type identified but no matching rules exist
    NEEDS_RESEARCH: Document may trigger deadlines but requires rule research
    RESEARCH_COMPLETE: Research performed, proposal awaiting review
    """
    MATCHED = "matched"
    UNRECOGNIZED = "unrecognized"
    NEEDS_RESEARCH = "needs_research"
    RESEARCH_COMPLETE = "research_complete"


class DocumentClassificationStatus(enum.Enum):
    """
    Classification status for uploaded documents.

    Tracks the document's journey through the classification pipeline.
    """
    PENDING = "pending"           # Not yet classified
    MATCHED = "matched"           # Matched to known trigger
    UNRECOGNIZED = "unrecognized" # Doc type known, no rule exists
    NEEDS_RESEARCH = "needs_research"  # Flagged for rule discovery
    RESEARCHED = "researched"     # Rule research complete, awaiting review
    MANUAL = "manual"             # User manually classified


class RuleProposalStatus(enum.Enum):
    """
    Status of AI-proposed rules.

    Used to track rule proposals through the review workflow.
    """
    PENDING = "pending"     # Awaiting attorney review
    APPROVED = "approved"   # Accepted and converted to active rule
    REJECTED = "rejected"   # Rejected by attorney
    MODIFIED = "modified"   # Approved with modifications
