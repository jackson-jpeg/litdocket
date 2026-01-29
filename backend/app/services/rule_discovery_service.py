"""
Rule Discovery Service

Phase 2 of the intelligent document recognition system. This service implements
the "I don't know, so I'll find out" loop - when the system encounters an
unrecognized document type, it researches applicable rules and proposes them
for attorney review.

Workflow:
1. SEARCH: Query RAG service + local rules database for relevant rules
2. REASON: Pass search results to Claude to synthesize a rule proposal
3. VALIDATE: Check proposal against existing rules for conflicts
4. STAGE: Save proposal with status='pending' for attorney review
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from app.services.ai_service import AIService
from app.services.rag_service import rag_service
from app.services.rules_engine import RulesEngine
from app.models.enums import RuleProposalStatus, DeadlinePriority
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RuleProposalResult:
    """Result of rule research and proposal generation."""
    success: bool
    proposal_id: Optional[str]
    proposed_trigger: Optional[str]
    proposed_days: Optional[int]
    proposed_priority: Optional[str]
    citation: Optional[str]
    source_text: Optional[str]
    source_url: Optional[str]
    confidence_score: float
    conflicts: List[Dict[str, Any]]
    research_summary: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "proposal_id": self.proposal_id,
            "proposed_trigger": self.proposed_trigger,
            "proposed_days": self.proposed_days,
            "proposed_priority": self.proposed_priority,
            "citation": self.citation,
            "source_text": self.source_text,
            "source_url": self.source_url,
            "confidence_score": self.confidence_score,
            "conflicts": self.conflicts,
            "research_summary": self.research_summary,
            "error": self.error,
        }


class RuleDiscoveryService:
    """
    Service for discovering and proposing deadline rules for unrecognized documents.

    This service bridges the gap between document classification and rule application.
    When a document is identified but no rule exists, this service:
    1. Searches for applicable rules in various sources
    2. Uses AI to synthesize a rule proposal
    3. Validates against existing rules for conflicts
    4. Saves for attorney review
    """

    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()
        self.rules_engine = RulesEngine()

    async def research_deadline_rule(
        self,
        document_type: str,
        jurisdiction: str,
        court: Optional[str] = None,
        document_text: Optional[str] = None,
        case_id: Optional[str] = None,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> RuleProposalResult:
        """
        Research and propose a deadline rule for an unrecognized document type.

        This is the main entry point for rule discovery. It:
        1. Searches local rules database and RAG for relevant information
        2. Uses Claude to synthesize a rule proposal
        3. Validates the proposal for conflicts
        4. Optionally saves the proposal for review

        Args:
            document_type: The document type to research (e.g., "Motion for Sanctions")
            jurisdiction: Target jurisdiction (e.g., "florida_state", "federal")
            court: Optional court name for more specific rules
            document_text: Optional document text for context
            case_id: Optional case ID to link the proposal to
            document_id: Optional document ID that triggered the research
            user_id: Optional user ID for saving the proposal

        Returns:
            RuleProposalResult with the research findings and proposal
        """
        try:
            logger.info(f"Starting rule research for '{document_type}' in {jurisdiction}")

            # Step 1: SEARCH - Query multiple sources for rule information
            search_results = await self._search_rule_sources(
                document_type=document_type,
                jurisdiction=jurisdiction,
                court=court,
                document_text=document_text,
            )

            if not search_results["found_sources"]:
                logger.warning(f"No rule sources found for '{document_type}'")
                return RuleProposalResult(
                    success=False,
                    proposal_id=None,
                    proposed_trigger=None,
                    proposed_days=None,
                    proposed_priority=None,
                    citation=None,
                    source_text=None,
                    source_url=None,
                    confidence_score=0.0,
                    conflicts=[],
                    research_summary=f"No applicable rules found for '{document_type}' in {jurisdiction}.",
                    error="No sources found",
                )

            # Step 2: REASON - Ask Claude to synthesize a rule proposal
            proposal = await self._synthesize_rule_proposal(
                document_type=document_type,
                jurisdiction=jurisdiction,
                search_results=search_results,
                document_text=document_text,
            )

            if not proposal["success"]:
                return RuleProposalResult(
                    success=False,
                    proposal_id=None,
                    proposed_trigger=None,
                    proposed_days=None,
                    proposed_priority=None,
                    citation=None,
                    source_text=None,
                    source_url=None,
                    confidence_score=0.0,
                    conflicts=[],
                    research_summary=proposal.get("error", "Failed to synthesize rule proposal"),
                    error=proposal.get("error"),
                )

            # Step 3: VALIDATE - Check for conflicts with existing rules
            conflicts = self._detect_conflicts(
                proposed_days=proposal["proposed_days"],
                document_type=document_type,
                jurisdiction=jurisdiction,
            )

            # Step 4: STAGE - Save proposal for attorney review (if user_id provided)
            proposal_id = None
            if user_id:
                proposal_id = await self._save_proposal(
                    document_type=document_type,
                    jurisdiction=jurisdiction,
                    proposal=proposal,
                    conflicts=conflicts,
                    case_id=case_id,
                    document_id=document_id,
                    user_id=user_id,
                )

            # Build research summary
            summary = self._build_research_summary(
                document_type=document_type,
                proposal=proposal,
                conflicts=conflicts,
                source_count=len(search_results.get("sources", [])),
            )

            return RuleProposalResult(
                success=True,
                proposal_id=proposal_id,
                proposed_trigger=proposal.get("proposed_trigger"),
                proposed_days=proposal.get("proposed_days"),
                proposed_priority=proposal.get("proposed_priority"),
                citation=proposal.get("citation"),
                source_text=proposal.get("source_text"),
                source_url=proposal.get("source_url"),
                confidence_score=proposal.get("confidence_score", 0.0),
                conflicts=conflicts,
                research_summary=summary,
            )

        except Exception as e:
            logger.error(f"Rule research failed for '{document_type}': {e}")
            return RuleProposalResult(
                success=False,
                proposal_id=None,
                proposed_trigger=None,
                proposed_days=None,
                proposed_priority=None,
                citation=None,
                source_text=None,
                source_url=None,
                confidence_score=0.0,
                conflicts=[],
                research_summary=f"Research failed: {str(e)}",
                error=str(e),
            )

    async def _search_rule_sources(
        self,
        document_type: str,
        jurisdiction: str,
        court: Optional[str] = None,
        document_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search multiple sources for rule information.

        Sources searched:
        1. Local rules database (local_rules table)
        2. RAG semantic search (document embeddings)
        3. Rule templates (existing rules for similar triggers)
        """
        sources = []
        found_sources = False

        # Source 1: Local Rules Database
        local_rule_results = await self._search_local_rules(
            document_type=document_type,
            jurisdiction=jurisdiction,
        )
        if local_rule_results:
            sources.extend(local_rule_results)
            found_sources = True
            logger.info(f"Found {len(local_rule_results)} local rule matches")

        # Source 2: RAG Semantic Search (if document text available)
        if document_text:
            rag_results = await self._search_rag(
                query=f"deadline response time {document_type} {jurisdiction}",
                document_text=document_text,
            )
            if rag_results:
                sources.extend(rag_results)
                found_sources = True
                logger.info(f"Found {len(rag_results)} RAG matches")

        # Source 3: Similar Rule Templates
        similar_rules = self._find_similar_rule_templates(
            document_type=document_type,
            jurisdiction=jurisdiction,
        )
        if similar_rules:
            sources.extend(similar_rules)
            found_sources = True
            logger.info(f"Found {len(similar_rules)} similar rule templates")

        return {
            "found_sources": found_sources,
            "sources": sources,
            "source_count": len(sources),
        }

    async def _search_local_rules(
        self,
        document_type: str,
        jurisdiction: str,
    ) -> List[Dict[str, Any]]:
        """Search the local_rules table for relevant rules."""
        from app.models.local_rule import LocalRule

        results = []
        doc_type_lower = document_type.lower()

        # Build search terms from document type
        search_terms = [
            doc_type_lower,
            doc_type_lower.replace("motion for ", ""),
            doc_type_lower.replace("motion to ", ""),
        ]

        # Map jurisdiction to local rule jurisdiction_type
        jurisdiction_type = "circuit" if jurisdiction == "florida_state" else "district"

        try:
            # Query local rules
            query = self.db.query(LocalRule).filter(
                LocalRule.jurisdiction_type == jurisdiction_type,
                LocalRule.affects_deadlines == True,
            )

            local_rules = query.limit(50).all()

            for rule in local_rules:
                # Check if rule text mentions our document type
                rule_text_lower = (rule.rule_text or "").lower()
                rule_title_lower = (rule.rule_title or "").lower()

                for term in search_terms:
                    if term in rule_text_lower or term in rule_title_lower:
                        results.append({
                            "source_type": "local_rule",
                            "citation": f"{rule.rule_number}",
                            "title": rule.rule_title,
                            "text": rule.rule_text[:1000] if rule.rule_text else "",
                            "deadline_days": rule.deadline_days,
                            "jurisdiction_id": rule.jurisdiction_id,
                            "relevance_score": 0.8,
                        })
                        break

        except Exception as e:
            logger.warning(f"Local rule search failed: {e}")

        return results

    async def _search_rag(
        self,
        query: str,
        document_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search RAG embeddings for relevant rule context."""
        results = []

        try:
            # Use RAG service for semantic search
            rag_results = await rag_service.semantic_search(
                query=query,
                db=self.db,
                top_k=5,
            )

            for result in rag_results:
                results.append({
                    "source_type": "rag_search",
                    "text": result.get("chunk_text", "")[:1000],
                    "document_id": result.get("document_id"),
                    "similarity": result.get("similarity", 0.0),
                    "relevance_score": result.get("similarity", 0.0),
                })

        except Exception as e:
            logger.warning(f"RAG search failed: {e}")

        return results

    def _find_similar_rule_templates(
        self,
        document_type: str,
        jurisdiction: str,
    ) -> List[Dict[str, Any]]:
        """Find existing rule templates that might be similar."""
        from app.models.jurisdiction import RuleTemplate

        results = []
        doc_type_lower = document_type.lower()

        # Keywords that suggest motion-type documents
        motion_keywords = ["motion", "request", "petition", "demand"]

        try:
            # Get all active rule templates
            templates = self.db.query(RuleTemplate).filter(
                RuleTemplate.is_active == True,
            ).limit(20).all()

            for template in templates:
                template_name_lower = (template.name or "").lower()

                # Check for keyword matches
                for keyword in motion_keywords:
                    if keyword in doc_type_lower and keyword in template_name_lower:
                        results.append({
                            "source_type": "rule_template",
                            "name": template.name,
                            "trigger_type": template.trigger_type,
                            "citation": template.citation,
                            "relevance_score": 0.6,
                        })
                        break

        except Exception as e:
            logger.warning(f"Similar template search failed: {e}")

        return results

    async def _synthesize_rule_proposal(
        self,
        document_type: str,
        jurisdiction: str,
        search_results: Dict[str, Any],
        document_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Use Claude to synthesize a rule proposal from search results.

        This is where the AI "reasons" about the search results and
        constructs a concrete rule proposal.
        """
        # Build context from search results
        sources_context = self._format_sources_for_prompt(search_results["sources"])

        # Build document context (limited to first 3000 chars)
        doc_context = ""
        if document_text:
            doc_context = f"\n\nDocument excerpt:\n{document_text[:3000]}"

        prompt = f"""You are a legal research assistant specializing in civil procedure deadlines.

I need you to research and propose a deadline rule for the following document type:

Document Type: {document_type}
Jurisdiction: {jurisdiction}

I found the following relevant sources:

{sources_context}
{doc_context}

Based on these sources, propose a deadline rule. Return your analysis as JSON:

{{
  "proposed_trigger": "string - What event does this document trigger? (e.g., 'Receipt of Motion for Sanctions')",
  "proposed_days": number - How many days to respond? (e.g., 21),
  "proposed_priority": "informational|standard|important|critical|fatal",
  "proposed_calculation_method": "calendar_days|business_days|court_days",
  "citation": "string or null - Rule citation if found (e.g., 'Fla. R. Civ. P. 1.140(b)')",
  "source_text": "string - The exact text from sources that supports this deadline",
  "confidence_score": number between 0.0 and 1.0 - How confident are you in this proposal?,
  "reasoning": "string - Explain your reasoning for this deadline",
  "warnings": ["array of strings - Any caveats or warnings about this rule"]
}}

If you cannot determine a deadline from the sources, return:
{{
  "success": false,
  "error": "Explanation of why no rule could be determined"
}}

Return ONLY the JSON object, no additional text."""

        try:
            response = await self.ai_service.analyze_with_prompt(prompt, max_tokens=2048)
            result = self.ai_service._parse_json_response(response)

            if result.get("parse_error"):
                return {"success": False, "error": "Failed to parse AI response"}

            if result.get("success") == False:
                return {"success": False, "error": result.get("error", "Unknown error")}

            # Validate required fields
            if not result.get("proposed_days"):
                return {"success": False, "error": "AI did not propose a deadline"}

            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"AI synthesis failed: {e}")
            return {"success": False, "error": str(e)}

    def _format_sources_for_prompt(self, sources: List[Dict[str, Any]]) -> str:
        """Format search result sources for the AI prompt."""
        if not sources:
            return "No sources found."

        formatted = []
        for i, source in enumerate(sources[:10], 1):  # Limit to 10 sources
            source_type = source.get("source_type", "unknown")
            text = source.get("text", source.get("title", ""))[:500]
            citation = source.get("citation", "")
            deadline_days = source.get("deadline_days")

            entry = f"Source {i} ({source_type}):"
            if citation:
                entry += f"\n  Citation: {citation}"
            if deadline_days:
                entry += f"\n  Deadline: {deadline_days} days"
            if text:
                entry += f"\n  Text: {text}"

            formatted.append(entry)

        return "\n\n".join(formatted)

    def _detect_conflicts(
        self,
        proposed_days: int,
        document_type: str,
        jurisdiction: str,
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts between the proposed rule and existing rules.

        Returns a list of conflicts with details about each.
        """
        conflicts = []

        # Check for similar document types with different deadlines
        similar_triggers = self.rules_engine._guess_potential_trigger(document_type)

        if similar_triggers:
            # Look for existing rules with different days
            doc_lower = document_type.lower()

            # Check hardcoded patterns
            if "motion" in doc_lower:
                # Standard motion response is 21 days in Florida
                if jurisdiction == "florida_state" and proposed_days != 21:
                    conflicts.append({
                        "type": "STANDARD_DEVIATION",
                        "message": f"Standard motion response in Florida is 21 days, but {proposed_days} days proposed",
                        "existing_days": 21,
                        "proposed_days": proposed_days,
                        "severity": "warning" if abs(proposed_days - 21) <= 7 else "error",
                    })

                # Federal standard is also 21 days
                if jurisdiction == "federal" and proposed_days != 21:
                    conflicts.append({
                        "type": "STANDARD_DEVIATION",
                        "message": f"Standard motion response under FRCP is 21 days, but {proposed_days} days proposed",
                        "existing_days": 21,
                        "proposed_days": proposed_days,
                        "severity": "warning" if abs(proposed_days - 21) <= 7 else "error",
                    })

            # Check for discovery response (30 days standard)
            if "discovery" in doc_lower or "interrogator" in doc_lower or "production" in doc_lower:
                if proposed_days != 30:
                    conflicts.append({
                        "type": "STANDARD_DEVIATION",
                        "message": f"Standard discovery response is 30 days, but {proposed_days} days proposed",
                        "existing_days": 30,
                        "proposed_days": proposed_days,
                        "severity": "warning",
                    })

        return conflicts

    async def _save_proposal(
        self,
        document_type: str,
        jurisdiction: str,
        proposal: Dict[str, Any],
        conflicts: List[Dict[str, Any]],
        case_id: Optional[str],
        document_id: Optional[str],
        user_id: str,
    ) -> str:
        """Save the rule proposal to the database for attorney review."""
        from app.models.rule_proposal import RuleProposal

        try:
            proposal_record = RuleProposal(
                id=str(uuid.uuid4()),
                case_id=case_id,
                document_id=document_id,
                user_id=user_id,
                proposed_trigger=proposal.get("proposed_trigger", document_type),
                proposed_trigger_type=proposal.get("proposed_trigger"),
                proposed_days=proposal.get("proposed_days", 21),
                proposed_priority=proposal.get("proposed_priority", "standard"),
                proposed_calculation_method=proposal.get("proposed_calculation_method", "calendar_days"),
                citation=proposal.get("citation"),
                source_text=proposal.get("source_text"),
                confidence_score=proposal.get("confidence_score", 0.0),
                conflicts=conflicts,
                status=RuleProposalStatus.PENDING.value,
            )

            self.db.add(proposal_record)
            self.db.commit()
            self.db.refresh(proposal_record)

            logger.info(f"Saved rule proposal {proposal_record.id} for '{document_type}'")
            return proposal_record.id

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save proposal: {e}")
            raise

    def _build_research_summary(
        self,
        document_type: str,
        proposal: Dict[str, Any],
        conflicts: List[Dict[str, Any]],
        source_count: int,
    ) -> str:
        """Build a human-readable summary of the research findings."""
        summary_parts = []

        # Opening
        summary_parts.append(f"Researched deadline rules for '{document_type}'.")

        # Sources
        summary_parts.append(f"Found {source_count} relevant source(s).")

        # Proposal
        if proposal.get("proposed_days"):
            days = proposal["proposed_days"]
            priority = proposal.get("proposed_priority", "standard")
            citation = proposal.get("citation")

            proposal_text = f"Proposed deadline: {days} days ({priority} priority)"
            if citation:
                proposal_text += f" per {citation}"
            summary_parts.append(proposal_text)

        # Confidence
        confidence = proposal.get("confidence_score", 0)
        if confidence >= 0.8:
            summary_parts.append("High confidence in this proposal.")
        elif confidence >= 0.5:
            summary_parts.append("Moderate confidence - attorney review recommended.")
        else:
            summary_parts.append("Low confidence - manual verification required.")

        # Conflicts
        if conflicts:
            conflict_msgs = [c["message"] for c in conflicts]
            summary_parts.append(f"Conflicts detected: {'; '.join(conflict_msgs)}")

        return " ".join(summary_parts)


# Factory function for creating service with database session
def get_rule_discovery_service(db: Session) -> RuleDiscoveryService:
    return RuleDiscoveryService(db)
