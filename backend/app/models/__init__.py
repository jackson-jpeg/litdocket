from app.database import Base
from app.models.user import User
from app.models.case import Case
from app.models.document import Document
from app.models.deadline import Deadline
from app.models.chat_message import ChatMessage
from app.models.calendar_event import CalendarEvent

# V3.0 Enhancement Models - RAG, Dependencies, Audit Trail
from app.models.document_embedding import DocumentEmbedding
from app.models.deadline_chain import DeadlineChain
from app.models.deadline_dependency import DeadlineDependency
from app.models.deadline_history import DeadlineHistory
from app.models.ai_extraction_feedback import AIExtractionFeedback
from app.models.local_rule import LocalRule
from app.models.deadline_template import DeadlineTemplate

# Phase 3 Models - Real-time Collaboration
from app.models.case_access import CaseAccess
from app.models.active_session import ActiveSession

# Notification System
from app.models.notification import Notification, NotificationPreferences

# Document Tagging
from app.models.document_tag import Tag, DocumentTag

# Case Templates
from app.models.case_template import CaseTemplate

# CompuLaw-style Jurisdiction and Rule System
from app.models.jurisdiction import (
    Jurisdiction,
    RuleSet,
    RuleSetDependency,
    CourtLocation,
    RuleTemplate,
    RuleTemplateDeadline,
    CaseRuleSet,
    JurisdictionType,
    CourtType,
    DependencyType,
    TriggerType,
    DeadlinePriority,
    CalculationMethod,
)

__all__ = [
    "Base",
    "User",
    "Case",
    "Document",
    "Deadline",
    "ChatMessage",
    "CalendarEvent",
    # V3.0 Models
    "DocumentEmbedding",
    "DeadlineChain",
    "DeadlineDependency",
    "DeadlineHistory",
    "AIExtractionFeedback",
    "LocalRule",
    "DeadlineTemplate",
    # Phase 3 Models
    "CaseAccess",
    "ActiveSession",
    # Notifications
    "Notification",
    "NotificationPreferences",
    # Document Tagging
    "Tag",
    "DocumentTag",
    # Case Templates
    "CaseTemplate",
    # CompuLaw-style Jurisdiction System
    "Jurisdiction",
    "RuleSet",
    "RuleSetDependency",
    "CourtLocation",
    "RuleTemplate",
    "RuleTemplateDeadline",
    "CaseRuleSet",
    "JurisdictionType",
    "CourtType",
    "DependencyType",
    "TriggerType",
    "DeadlinePriority",
    "CalculationMethod",
]
