"""
Proactive Rule Recommendation Assistant

Phase 6: Advanced Intelligence & Self-Healing

Monitors user context and proactively suggests relevant rules:
- Document upload triggers (MSJ → response deadline)
- Trigger event creation (trial date → pretrial deadlines)
- Case type patterns (bankruptcy → adversary proceeding rules)
- Chat conversation analysis (user mentions motion → suggest filing rules)

Delivers non-intrusive, contextual suggestions via chat or notifications.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import logging
import re

from app.models.case import Case
from app.models.document import Document
from app.models.deadline import Deadline
from app.models.authority_core import AuthorityRule
from app.models.enums import TriggerType, DocumentType
from app.services.authority_core_service import AuthorityCoreService

logger = logging.getLogger(__name__)


class ProactiveRuleAssistant:
    """
    Intelligent rule suggestion engine.

    Analyzes user actions and case context to suggest relevant
    Authority Core rules before they're explicitly requested.
    """

    # Document keyword → trigger type mappings
    DOCUMENT_TRIGGERS = {
        # Motion keywords
        r"\b(msj|motion\s+for\s+summary\s+judgment|summary\s+judgment)\b": "motion_for_summary_judgment",
        r"\b(motion\s+to\s+dismiss|mtd|12\(b\)\(6\))\b": "motion_to_dismiss",
        r"\b(motion\s+in\s+limine|mil)\b": "motion_in_limine",
        r"\b(motion\s+to\s+compel|compel\s+discovery)\b": "discovery_motion",

        # Discovery keywords
        r"\b(interrogatories|interrogatory)\b": "interrogatory_responses",
        r"\b(request\s+for\s+production|rfp|document\s+requests?)\b": "document_production",
        r"\b(request\s+for\s+admission|rfa)\b": "admission_responses",
        r"\b(deposition\s+notice)\b": "deposition_notice",

        # Pleading keywords
        r"\b(complaint|petition)\b": "complaint_served",
        r"\b(answer|response\s+to\s+complaint)\b": "answer_filed",
        r"\b(counterclaim)\b": "counterclaim_filed",
        r"\b(amended\s+complaint)\b": "amended_complaint",

        # Trial keywords
        r"\b(pretrial\s+order|pto)\b": "pretrial_order",
        r"\b(trial\s+brief)\b": "trial_brief",
        r"\b(witness\s+list)\b": "witness_disclosure",
        r"\b(exhibit\s+list)\b": "exhibit_list",
    }

    # Case type → relevant rule categories
    CASE_TYPE_RULES = {
        "civil": ["motion_to_dismiss", "discovery_deadline", "trial_date", "motion_for_summary_judgment"],
        "bankruptcy": ["adversary_proceeding", "proof_of_claim", "objection_deadline"],
        "criminal": ["arraignment", "preliminary_hearing", "trial_date"],
        "family": ["hearing_date", "temporary_orders", "final_orders"],
        "probate": ["notice_to_creditors", "inventory_filing", "final_accounting"],
    }

    def __init__(self, db: Session):
        self.db = db
        self.authority_service = AuthorityCoreService(db)

    async def analyze_document_upload(
        self,
        document: Document,
        case: Case
    ) -> Dict[str, Any]:
        """
        Analyze uploaded document and suggest relevant rules.

        Args:
            document: Uploaded document
            case: Case context

        Returns:
            Suggestions with confidence scores
        """
        logger.info(f"Analyzing document upload: {document.filename}")

        suggestions = []

        # Analyze filename and document type
        filename_lower = document.filename.lower()
        doc_type_str = document.document_type if document.document_type else ""

        # Pattern matching on filename
        detected_triggers = []
        for pattern, trigger_type in self.DOCUMENT_TRIGGERS.items():
            if re.search(pattern, filename_lower, re.IGNORECASE):
                detected_triggers.append(trigger_type)

        # Get relevant rules for detected triggers
        if detected_triggers:
            for trigger in detected_triggers:
                rules = await self.authority_service.search_rules(
                    jurisdiction_id=case.jurisdiction_id,
                    trigger_type=trigger,
                    limit=3
                )

                if rules:
                    suggestions.append({
                        "trigger_type": trigger,
                        "reason": f"Detected '{trigger.replace('_', ' ')}' in document filename",
                        "rules": [
                            {
                                "rule_id": rule.id,
                                "rule_code": rule.rule_code,
                                "rule_name": rule.rule_name,
                                "confidence": rule.confidence_score,
                                "deadlines": rule.deadlines
                            }
                            for rule in rules[:3]
                        ],
                        "priority": "high" if any(kw in filename_lower for kw in ["msj", "motion to dismiss", "trial"]) else "medium"
                    })

        # Check for missing common deadlines in case
        missing_deadlines = await self._check_missing_deadlines(case)
        if missing_deadlines:
            suggestions.extend(missing_deadlines)

        logger.info(f"Generated {len(suggestions)} proactive suggestions for document upload")

        return {
            "document_id": document.id,
            "suggestions": suggestions,
            "suggestion_count": len(suggestions)
        }

    async def analyze_trigger_creation(
        self,
        trigger_type: str,
        trigger_date: datetime,
        case: Case
    ) -> Dict[str, Any]:
        """
        Analyze trigger creation and suggest related rules.

        Example: User sets trial date → suggest pretrial deadline rules

        Args:
            trigger_type: Type of trigger created
            trigger_date: Date of trigger
            case: Case context

        Returns:
            Related rule suggestions
        """
        logger.info(f"Analyzing trigger creation: {trigger_type}")

        suggestions = []

        # Define related trigger patterns
        related_triggers = self._get_related_triggers(trigger_type)

        for related_trigger in related_triggers:
            rules = await self.authority_service.search_rules(
                jurisdiction_id=case.jurisdiction_id,
                trigger_type=related_trigger,
                limit=2
            )

            if rules:
                suggestions.append({
                    "trigger_type": related_trigger,
                    "reason": f"Related to your '{trigger_type.replace('_', ' ')}' trigger",
                    "rules": [
                        {
                            "rule_id": rule.id,
                            "rule_code": rule.rule_code,
                            "rule_name": rule.rule_name,
                            "confidence": rule.confidence_score,
                            "deadlines": rule.deadlines
                        }
                        for rule in rules[:2]
                    ],
                    "priority": "medium"
                })

        return {
            "trigger_type": trigger_type,
            "suggestions": suggestions,
            "suggestion_count": len(suggestions)
        }

    async def analyze_chat_message(
        self,
        message: str,
        case: Case
    ) -> Dict[str, Any]:
        """
        Analyze chat message and suggest relevant rules.

        Example: User says "I need to file a motion" → suggest filing deadline rules

        Args:
            message: User's chat message
            case: Case context

        Returns:
            Rule suggestions based on message content
        """
        logger.info("Analyzing chat message for proactive suggestions")

        suggestions = []
        message_lower = message.lower()

        # Pattern matching on chat message
        detected_triggers = []
        for pattern, trigger_type in self.DOCUMENT_TRIGGERS.items():
            if re.search(pattern, message_lower, re.IGNORECASE):
                detected_triggers.append(trigger_type)

        # Get rules for detected patterns
        if detected_triggers:
            for trigger in detected_triggers[:3]:  # Limit to top 3 to avoid spam
                rules = await self.authority_service.search_rules(
                    jurisdiction_id=case.jurisdiction_id,
                    trigger_type=trigger,
                    limit=2
                )

                if rules:
                    suggestions.append({
                        "trigger_type": trigger,
                        "reason": f"Detected discussion about '{trigger.replace('_', ' ')}'",
                        "rules": [
                            {
                                "rule_id": rule.id,
                                "rule_code": rule.rule_code,
                                "rule_name": rule.rule_name,
                                "confidence": rule.confidence_score,
                                "summary": self._summarize_rule(rule)
                            }
                            for rule in rules[:2]
                        ],
                        "priority": "low"  # Chat suggestions are low priority - non-intrusive
                    })

        return {
            "suggestions": suggestions,
            "suggestion_count": len(suggestions),
            "should_display": len(suggestions) > 0 and len(suggestions) <= 3  # Only show if reasonable number
        }

    async def analyze_case_context(
        self,
        case: Case
    ) -> Dict[str, Any]:
        """
        Analyze overall case context and suggest missing rules.

        Checks for common gaps in deadline coverage.

        Args:
            case: Case to analyze

        Returns:
            Suggestions for missing deadlines
        """
        logger.info(f"Analyzing case context for case {case.id}")

        suggestions = []

        # Get existing deadlines
        existing_deadlines = self.db.query(Deadline).filter(
            Deadline.case_id == case.id,
            Deadline.is_deleted == False
        ).all()

        existing_triggers = {d.trigger_type for d in existing_deadlines if d.trigger_type}

        # Get case type recommendations
        case_type = case.case_type or "civil"
        recommended_triggers = self.CASE_TYPE_RULES.get(case_type, [])

        # Find missing triggers
        missing_triggers = [t for t in recommended_triggers if t not in existing_triggers]

        for trigger in missing_triggers[:5]:  # Limit to top 5
            rules = await self.authority_service.search_rules(
                jurisdiction_id=case.jurisdiction_id,
                trigger_type=trigger,
                limit=1
            )

            if rules:
                rule = rules[0]
                suggestions.append({
                    "trigger_type": trigger,
                    "reason": f"Common deadline for {case_type} cases",
                    "rule": {
                        "rule_id": rule.id,
                        "rule_code": rule.rule_code,
                        "rule_name": rule.rule_name,
                        "confidence": rule.confidence_score
                    },
                    "priority": "low"
                })

        return {
            "case_id": case.id,
            "suggestions": suggestions,
            "suggestion_count": len(suggestions),
            "coverage_score": len(existing_triggers) / max(len(recommended_triggers), 1)
        }

    def _get_related_triggers(self, trigger_type: str) -> List[str]:
        """Get related trigger types for a given trigger."""
        # Define related trigger clusters
        related_map = {
            "trial_date": ["pretrial_conference", "witness_disclosure", "exhibit_list", "trial_brief"],
            "motion_for_summary_judgment": ["opposition_deadline", "reply_deadline", "hearing_date"],
            "discovery_deadline": ["interrogatory_responses", "document_production", "deposition_deadline"],
            "complaint_served": ["answer_filed", "motion_to_dismiss", "remove_to_federal"],
            "motion_filed": ["opposition_deadline", "reply_deadline", "hearing_date"],
        }

        return related_map.get(trigger_type, [])

    async def _check_missing_deadlines(self, case: Case) -> List[Dict[str, Any]]:
        """Check for common missing deadlines in case."""
        suggestions = []

        # Get existing deadlines
        existing_deadlines = self.db.query(Deadline).filter(
            Deadline.case_id == case.id,
            Deadline.is_deleted == False
        ).all()

        # Check for trial date without pretrial deadlines
        has_trial = any(d.trigger_type == "trial_date" for d in existing_deadlines)
        has_pretrial = any(d.trigger_type in ["pretrial_conference", "witness_disclosure"] for d in existing_deadlines)

        if has_trial and not has_pretrial:
            rules = await self.authority_service.search_rules(
                jurisdiction_id=case.jurisdiction_id,
                trigger_type="pretrial_conference",
                limit=1
            )

            if rules:
                suggestions.append({
                    "trigger_type": "pretrial_conference",
                    "reason": "You have a trial date but no pretrial deadlines",
                    "rules": [{
                        "rule_id": rules[0].id,
                        "rule_code": rules[0].rule_code,
                        "rule_name": rules[0].rule_name,
                        "confidence": rules[0].confidence_score
                    }],
                    "priority": "high"
                })

        return suggestions

    def _summarize_rule(self, rule: AuthorityRule) -> str:
        """Generate brief summary of rule for chat display."""
        if not rule.deadlines:
            return f"{rule.rule_name}"

        deadline_count = len(rule.deadlines)
        if deadline_count == 1:
            return f"{rule.rule_name} - {rule.deadlines[0].get('days_from_trigger')} days"
        else:
            return f"{rule.rule_name} - {deadline_count} deadlines"

    def format_suggestion_for_chat(self, suggestions: List[Dict[str, Any]]) -> str:
        """
        Format suggestions for non-intrusive chat display.

        Args:
            suggestions: List of suggestion objects

        Returns:
            Formatted markdown string for chat
        """
        if not suggestions:
            return ""

        # Only show high/medium priority suggestions in chat
        relevant = [s for s in suggestions if s.get("priority") in ["high", "medium"]]

        if not relevant:
            return ""

        output = "💡 **Suggested Rules:**\n\n"

        for suggestion in relevant[:3]:  # Limit to 3 to avoid clutter
            trigger = suggestion['trigger_type'].replace('_', ' ').title()
            reason = suggestion['reason']
            rules = suggestion.get('rules', [])

            output += f"**{trigger}**\n"
            output += f"_{reason}_\n"

            for rule in rules[:2]:  # Max 2 rules per suggestion
                output += f"- {rule['rule_code']}: {rule['rule_name']} (confidence: {rule['confidence']:.0%})\n"

            output += "\n"

        output += "_Use `find_applicable_rules` to explore these suggestions._"

        return output


# =========================================================================
# INTEGRATION HELPERS
# =========================================================================

async def suggest_rules_for_document(
    db: Session,
    document: Document,
    case: Case
) -> Dict[str, Any]:
    """
    Convenience function for document upload integration.

    Call this from document upload endpoint to get proactive suggestions.

    Args:
        db: Database session
        document: Uploaded document
        case: Case context

    Returns:
        Suggestion report
    """
    assistant = ProactiveRuleAssistant(db)
    return await assistant.analyze_document_upload(document, case)


async def suggest_rules_for_trigger(
    db: Session,
    trigger_type: str,
    trigger_date: datetime,
    case: Case
) -> Dict[str, Any]:
    """
    Convenience function for trigger creation integration.

    Call this from trigger creation endpoint to get proactive suggestions.

    Args:
        db: Database session
        trigger_type: Type of trigger
        trigger_date: Date of trigger
        case: Case context

    Returns:
        Suggestion report
    """
    assistant = ProactiveRuleAssistant(db)
    return await assistant.analyze_trigger_creation(trigger_type, trigger_date, case)


async def suggest_rules_for_chat(
    db: Session,
    message: str,
    case: Case
) -> str:
    """
    Convenience function for chat integration.

    Call this from chat service to get non-intrusive suggestions.

    Args:
        db: Database session
        message: User's chat message
        case: Case context

    Returns:
        Formatted suggestion string (markdown) or empty string
    """
    assistant = ProactiveRuleAssistant(db)
    result = await assistant.analyze_chat_message(message, case)

    if result['should_display']:
        return assistant.format_suggestion_for_chat(result['suggestions'])

    return ""
