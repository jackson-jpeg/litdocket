"""
Document Classification Service

Phase 1 of the intelligent document recognition system. This service merges
pattern-based matching from the rules engine with AI analysis to provide
rich classification for both recognized and unrecognized documents.

Instead of failing silently on unknown documents, this service:
1. Identifies what the document is (even if we don't have rules for it)
2. Assesses whether it likely triggers deadlines
3. Suggests next steps (apply rules, research, or manual review)
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.models.enums import (
    TriggerStatus,
    DocumentClassificationStatus,
    TriggerType
)
from app.services.rules_engine import RulesEngine
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of document classification."""
    # Core classification
    trigger_status: TriggerStatus
    classification_status: DocumentClassificationStatus
    detected_document_type: str
    document_category: str  # motion, order, notice, pleading, discovery, etc.

    # Confidence and matching
    classification_confidence: float  # 0.0 - 1.0
    matched_trigger_type: Optional[TriggerType]
    matched_pattern: Optional[str]

    # For unrecognized documents
    potential_trigger_event: Optional[str]
    response_required: bool
    response_party: Optional[str]
    response_deadline_days: Optional[int]

    # Context
    procedural_posture: Optional[str]
    relief_sought: Optional[str]
    urgency_indicators: List[str]
    rule_references: List[str]

    # Next steps
    suggested_action: str  # "apply_rules", "research_deadlines", "manual_review", "none"
    action_description: str

    # Rule application (if matched)
    rule_set_code: Optional[str]
    expected_deadlines: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "trigger_status": self.trigger_status.value,
            "classification_status": self.classification_status.value,
            "detected_document_type": self.detected_document_type,
            "document_category": self.document_category,
            "classification_confidence": self.classification_confidence,
            "matched_trigger_type": self.matched_trigger_type.value if self.matched_trigger_type else None,
            "matched_pattern": self.matched_pattern,
            "potential_trigger_event": self.potential_trigger_event,
            "response_required": self.response_required,
            "response_party": self.response_party,
            "response_deadline_days": self.response_deadline_days,
            "procedural_posture": self.procedural_posture,
            "relief_sought": self.relief_sought,
            "urgency_indicators": self.urgency_indicators,
            "rule_references": self.rule_references,
            "suggested_action": self.suggested_action,
            "action_description": self.action_description,
            "rule_set_code": self.rule_set_code,
            "expected_deadlines": self.expected_deadlines,
        }


class DocumentClassificationService:
    """
    Service for classifying legal documents and determining deadline implications.

    This service combines:
    1. Pattern matching from RulesEngine
    2. AI analysis from AIService
    3. Heuristics for unrecognized documents

    The goal is to never return "unknown" - instead, provide rich context
    about what the document is and what the user should do next.
    """

    def __init__(self, rules_engine: Optional[RulesEngine] = None):
        self.rules_engine = rules_engine or RulesEngine()
        self.ai_service = AIService()

    async def classify_document(
        self,
        document_text: str,
        ai_analysis: Optional[Dict[str, Any]] = None,
        jurisdiction: str = "florida_state",
        court_type: str = "civil"
    ) -> ClassificationResult:
        """
        Classify a document and determine its deadline implications.

        This is the main entry point for document classification. It:
        1. Runs AI analysis if not already provided
        2. Attempts pattern matching with the rules engine
        3. For unmatched documents, extracts rich context about what it is

        Args:
            document_text: The extracted text from the document
            ai_analysis: Optional pre-computed AI analysis (to avoid duplicate calls)
            jurisdiction: Target jurisdiction for rule matching
            court_type: Type of court (civil, criminal, etc.)

        Returns:
            ClassificationResult with full classification details
        """
        # Step 1: Get AI analysis if not provided
        if ai_analysis is None:
            logger.info("Running AI analysis for document classification")
            ai_analysis = await self.ai_service.analyze_legal_document(document_text)

        # Extract document type from AI analysis
        document_type = ai_analysis.get("document_type", "Unknown Document")
        document_category = ai_analysis.get("document_category", "other")

        # Step 2: Try pattern matching with rules engine
        # Pass AI analysis to enable enhanced matching
        match_result = self.rules_engine.match_document_to_trigger(
            document_type=document_type,
            jurisdiction=jurisdiction,
            court_type=court_type,
            ai_analysis=ai_analysis
        )

        # Step 3: Build classification result based on match outcome
        if match_result.get("matches_trigger"):
            return self._build_matched_result(match_result, ai_analysis, document_category)
        else:
            return self._build_unmatched_result(match_result, ai_analysis, document_category)

    def _build_matched_result(
        self,
        match_result: Dict[str, Any],
        ai_analysis: Dict[str, Any],
        document_category: str
    ) -> ClassificationResult:
        """Build result for documents that matched a trigger pattern."""
        return ClassificationResult(
            # Core classification
            trigger_status=TriggerStatus.MATCHED,
            classification_status=DocumentClassificationStatus.MATCHED,
            detected_document_type=match_result.get("detected_document_type", ""),
            document_category=document_category,

            # Confidence and matching
            classification_confidence=match_result.get("classification_confidence", 0.95),
            matched_trigger_type=match_result.get("trigger_type"),
            matched_pattern=match_result.get("matched_pattern"),

            # For matched documents, these are less relevant but included for completeness
            potential_trigger_event=None,
            response_required=match_result.get("response_required", False),
            response_party=ai_analysis.get("response_party"),
            response_deadline_days=ai_analysis.get("response_deadline_days"),

            # Context from AI
            procedural_posture=ai_analysis.get("procedural_posture"),
            relief_sought=ai_analysis.get("relief_sought"),
            urgency_indicators=ai_analysis.get("urgency_indicators", []),
            rule_references=ai_analysis.get("rule_references", []),

            # Next steps
            suggested_action="apply_rules",
            action_description=match_result.get("trigger_description", "Apply deadline rules"),

            # Rule application
            rule_set_code=match_result.get("rule_set_code"),
            expected_deadlines=match_result.get("expected_deadlines", 0),
        )

    def _build_unmatched_result(
        self,
        match_result: Dict[str, Any],
        ai_analysis: Dict[str, Any],
        document_category: str
    ) -> ClassificationResult:
        """Build result for documents that didn't match a trigger pattern."""
        trigger_status = match_result.get("trigger_status", TriggerStatus.UNRECOGNIZED)
        suggested_action = match_result.get("suggested_action", "manual_review")

        # Map suggested action to classification status
        if suggested_action == "research_deadlines":
            classification_status = DocumentClassificationStatus.NEEDS_RESEARCH
        elif suggested_action == "manual_review":
            classification_status = DocumentClassificationStatus.UNRECOGNIZED
        else:
            classification_status = DocumentClassificationStatus.UNRECOGNIZED

        # Build action description
        document_type = match_result.get("detected_document_type", ai_analysis.get("document_type", "Unknown"))
        if suggested_action == "research_deadlines":
            action_description = (
                f"Document identified as '{document_type}'. "
                f"This document type may trigger deadlines but no rule template exists. "
                f"Click 'Research Deadlines' to find applicable rules."
            )
        elif suggested_action == "manual_review":
            action_description = (
                f"Document identified as '{document_type}'. "
                f"Unable to determine if this triggers deadlines. Manual review recommended."
            )
        else:
            action_description = (
                f"Document identified as '{document_type}'. "
                f"This document type typically does not trigger deadline requirements."
            )

        return ClassificationResult(
            # Core classification
            trigger_status=trigger_status,
            classification_status=classification_status,
            detected_document_type=document_type,
            document_category=document_category,

            # Confidence and matching
            classification_confidence=match_result.get("classification_confidence", 0.5),
            matched_trigger_type=None,
            matched_pattern=None,

            # For unmatched documents, these are critical
            potential_trigger_event=match_result.get("potential_trigger_event") or ai_analysis.get("potential_trigger_event"),
            response_required=match_result.get("response_required", False) or ai_analysis.get("response_required", False),
            response_party=ai_analysis.get("response_party"),
            response_deadline_days=ai_analysis.get("response_deadline_days"),

            # Context from AI
            procedural_posture=ai_analysis.get("procedural_posture"),
            relief_sought=ai_analysis.get("relief_sought") or match_result.get("relief_sought"),
            urgency_indicators=ai_analysis.get("urgency_indicators", []),
            rule_references=ai_analysis.get("rule_references", []),

            # Next steps
            suggested_action=suggested_action,
            action_description=action_description,

            # Rule application (none for unmatched)
            rule_set_code=None,
            expected_deadlines=0,
        )

    def get_similar_known_triggers(self, document_type: str) -> List[Dict[str, Any]]:
        """
        Find triggers that are similar to the given document type.

        This helps users understand what known triggers exist that might
        be related to their unrecognized document.

        Args:
            document_type: The detected document type

        Returns:
            List of similar trigger types with match scores
        """
        doc_lower = (document_type or "").lower()
        similar_triggers = []

        # Define trigger categories with their keywords
        trigger_keywords = {
            TriggerType.MOTION_FILED: [
                "motion", "move", "request", "petition"
            ],
            TriggerType.COMPLAINT_SERVED: [
                "complaint", "summons", "petition", "commencement"
            ],
            TriggerType.DISCOVERY_COMMENCED: [
                "discovery", "interrogator", "production", "admission", "deposition"
            ],
            TriggerType.ORDER_ENTERED: [
                "order", "judgment", "decree", "ruling"
            ],
            TriggerType.HEARING_SCHEDULED: [
                "hearing", "conference", "scheduling"
            ],
            TriggerType.TRIAL_DATE: [
                "trial", "trial notice", "calendar call"
            ],
        }

        for trigger_type, keywords in trigger_keywords.items():
            # Calculate match score based on keyword overlap
            matches = sum(1 for kw in keywords if kw in doc_lower)
            if matches > 0:
                score = matches / len(keywords)
                similar_triggers.append({
                    "trigger_type": trigger_type.value,
                    "similarity_score": round(score, 2),
                    "matched_keywords": [kw for kw in keywords if kw in doc_lower],
                    "description": self._get_trigger_description(trigger_type),
                })

        # Sort by score descending
        similar_triggers.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar_triggers[:3]  # Return top 3

    def _get_trigger_description(self, trigger_type: TriggerType) -> str:
        """Get human-readable description for a trigger type."""
        descriptions = {
            TriggerType.COMPLAINT_SERVED: "Commencement of Action - generates Answer deadline",
            TriggerType.MOTION_FILED: "Motion Filed - generates Response deadline",
            TriggerType.DISCOVERY_COMMENCED: "Discovery Request - generates 30-day response deadline",
            TriggerType.ORDER_ENTERED: "Order Entered - generates post-judgment deadlines",
            TriggerType.HEARING_SCHEDULED: "Hearing Scheduled - generates hearing prep deadlines",
            TriggerType.TRIAL_DATE: "Trial Date Set - generates pretrial deadlines",
        }
        return descriptions.get(trigger_type, "Unknown trigger type")

    def assess_urgency(self, ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the urgency of a document based on AI analysis.

        Args:
            ai_analysis: The AI analysis result

        Returns:
            Urgency assessment with level and factors
        """
        urgency_indicators = ai_analysis.get("urgency_indicators", [])
        response_deadline_days = ai_analysis.get("response_deadline_days")

        # Calculate urgency score
        urgency_score = 0.0
        factors = []

        # Check urgency indicators
        high_urgency_keywords = ["emergency", "ex parte", "tro", "immediate", "expedited"]
        medium_urgency_keywords = ["shortened time", "time-sensitive", "urgent"]

        for indicator in urgency_indicators:
            indicator_lower = indicator.lower()
            if any(kw in indicator_lower for kw in high_urgency_keywords):
                urgency_score += 0.4
                factors.append(f"High urgency indicator: {indicator}")
            elif any(kw in indicator_lower for kw in medium_urgency_keywords):
                urgency_score += 0.2
                factors.append(f"Medium urgency indicator: {indicator}")

        # Check response deadline
        if response_deadline_days is not None:
            if response_deadline_days <= 5:
                urgency_score += 0.3
                factors.append(f"Very short deadline: {response_deadline_days} days")
            elif response_deadline_days <= 10:
                urgency_score += 0.2
                factors.append(f"Short deadline: {response_deadline_days} days")
            elif response_deadline_days <= 20:
                urgency_score += 0.1
                factors.append(f"Standard deadline: {response_deadline_days} days")

        # Determine urgency level
        if urgency_score >= 0.6:
            level = "high"
        elif urgency_score >= 0.3:
            level = "medium"
        else:
            level = "low"

        return {
            "urgency_level": level,
            "urgency_score": min(1.0, urgency_score),
            "factors": factors,
            "requires_immediate_attention": level == "high",
        }


# Singleton instance for convenience
document_classification_service = DocumentClassificationService()
