"""
Rule Extraction Service - AI-Powered Rule Extraction with Tool Use

Enhanced version using Anthropic tool use for reliable structured extraction.

Key improvements over text-based parsing:
1. Uses Claude's native tool use (no JSON parsing failures)
2. Complexity assessment for tiered AI pipeline
3. Structured output with type safety
4. Better error handling
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import logging
import hashlib
import httpx

from anthropic import Anthropic
from anthropic.types import Message, ToolUseBlock

from app.config import settings
from app.models.enums import TriggerType, AuthorityTier

logger = logging.getLogger(__name__)


# =============================================================
# DATACLASSES
# =============================================================

@dataclass
class ExtractedDeadline:
    """A deadline specification extracted from rule text"""
    title: str
    days_from_trigger: int
    calculation_method: str
    priority: str
    party_responsible: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


@dataclass
class RelatedRule:
    """A citation to another rule referenced in the extracted rule"""
    citation: str  # e.g., "FRCP 6(a)"
    purpose: str  # Why it's referenced (e.g., "computation of time")


@dataclass
class ExtractedRuleData:
    """Complete extracted rule data ready for proposal creation"""
    rule_code: str
    rule_name: str
    trigger_type: str
    authority_tier: str
    citation: str
    source_url: Optional[str]
    source_text: str
    deadlines: List[ExtractedDeadline]
    conditions: Optional[Dict[str, Any]] = None
    service_extensions: Optional[Dict[str, int]] = None
    confidence_score: float = 0.0
    extraction_notes: Optional[str] = None
    complexity: Optional[int] = None  # 1-10 complexity score
    related_rules: List[RelatedRule] = field(default_factory=list)
    extraction_reasoning: List[str] = field(default_factory=list)


@dataclass
class ScrapedContent:
    """Result from scraping a court URL"""
    raw_text: str  # Clean legal text with nav/UI filtered out
    content_hash: str  # For change detection (first 1000 chars hash)
    source_urls: List[str]  # Grounding URLs for the content


@dataclass
class DetectedConflict:
    """A conflict between an extracted rule and cited authority"""
    rule_a: str  # The extracted rule citation
    rule_b: str  # The cited authority (e.g., FRCP 6)
    discrepancy: str  # Description of the conflict
    ai_resolution_recommendation: str  # AI's recommended resolution


@dataclass
class SearchResult:
    """A search result from web search"""
    url: str
    title: str
    snippet: str
    relevance_score: float


# =============================================================
# TOOL DEFINITIONS
# =============================================================

EXTRACTION_TOOL = {
    "name": "submit_extraction",
    "description": "Submit the extracted rule data in structured format",
    "input_schema": {
        "type": "object",
        "properties": {
            "rule_code": {
                "type": "string",
                "description": "Unique identifier (e.g., 'SDFL_LR_7.1_a_2' for S.D. Florida Local Rule 7.1(a)(2))"
            },
            "rule_name": {
                "type": "string",
                "description": "Human-readable name (e.g., 'Motion Response Time')"
            },
            "trigger_type": {
                "type": "string",
                "enum": [
                    "case_filed", "service_completed", "complaint_served", "answer_due",
                    "discovery_commenced", "discovery_deadline", "dispositive_motions_due",
                    "pretrial_conference", "trial_date", "hearing_scheduled",
                    "motion_filed", "order_entered", "appeal_filed", "mediation_scheduled",
                    "custom_trigger"
                ],
                "description": "What event triggers this rule"
            },
            "authority_tier": {
                "type": "string",
                "enum": ["federal", "state", "local", "standing_order", "firm"],
                "description": "Authority level (federal > state > local > standing_order > firm)"
            },
            "citation": {
                "type": "string",
                "description": "Official citation (e.g., 'S.D. Fla. L.R. 7.1(a)(2)')"
            },
            "deadlines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Deadline name"},
                        "days_from_trigger": {
                            "type": "integer",
                            "description": "Days from trigger (negative = before, positive = after)"
                        },
                        "calculation_method": {
                            "type": "string",
                            "enum": ["calendar_days", "business_days", "court_days"]
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["informational", "standard", "important", "critical", "fatal"]
                        },
                        "party_responsible": {
                            "type": "string",
                            "enum": ["plaintiff", "defendant", "moving_party", "opposing_party", "both", "court"]
                        },
                        "description": {"type": "string", "description": "What must be done"},
                        "conditions": {
                            "type": "object",
                            "description": "Conditions when this deadline applies"
                        }
                    },
                    "required": ["title", "days_from_trigger", "calculation_method", "priority"]
                }
            },
            "related_rules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "citation": {"type": "string"},
                        "purpose": {"type": "string"}
                    },
                    "required": ["citation", "purpose"]
                },
                "description": "Related rules that are referenced"
            },
            "conditions": {
                "type": "object",
                "description": "When the rule applies (case_types, motion_types, etc.)"
            },
            "service_extensions": {
                "type": "object",
                "description": "Additional days for service methods",
                "properties": {
                    "mail": {"type": "integer"},
                    "electronic": {"type": "integer"},
                    "personal": {"type": "integer"}
                }
            },
            "confidence_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": "Confidence in extraction accuracy (0-100)"
            },
            "extraction_reasoning": {
                "type": "string",
                "description": "Brief explanation of extraction decisions"
            }
        },
        "required": [
            "rule_code", "rule_name", "trigger_type", "authority_tier",
            "citation", "deadlines", "confidence_score", "extraction_reasoning"
        ]
    }
}

COMPLEXITY_TOOL = {
    "name": "assess_complexity",
    "description": "Assess the complexity of the rule for tiered AI processing",
    "input_schema": {
        "type": "object",
        "properties": {
            "complexity_score": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "description": "Complexity score (1=simple deadline, 10=highly complex multi-conditional rule)"
            },
            "reasoning": {
                "type": "string",
                "description": "Why this complexity score was assigned"
            },
            "factors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Complexity factors (e.g., 'multiple deadlines', 'conditional logic', 'cross-references')"
            }
        },
        "required": ["complexity_score", "reasoning", "factors"]
    }
}


# =============================================================
# EXTRACTION SERVICE
# =============================================================

class RuleExtractionService:
    """
    Service for extracting court rules using Claude AI with tool use.

    This service uses Claude's native tool use capability for reliable
    structured extraction without brittle JSON parsing.
    """

    EXTRACTION_SYSTEM_PROMPT = """You are Authority Core, an expert legal AI that extracts procedural court rules from legal documents and websites.

Your task is to extract structured rule data from the provided text. Be precise with:
- Day counts (verify against source text)
- Exact citations from the source
- Correct trigger_type based on what event starts the countdown
- Authority tier (federal > state > local > standing_order > firm)
- Conditions that limit when the rule applies

Use the submit_extraction tool to return your analysis."""

    COMPLEXITY_SYSTEM_PROMPT = """You are a legal complexity analyst. Assess the complexity of this court rule.

Complexity factors:
- Number of deadlines (1 = simple, 5+ = complex)
- Conditional logic (if/then, exceptions)
- Cross-references to other rules
- Calculation method complexity (business days vs calendar days)
- Service method variations
- Party-specific requirements

Score: 1-3 (simple), 4-6 (moderate), 7-10 (highly complex)

Use the assess_complexity tool to submit your assessment."""

    TRIGGER_TYPE_KEYWORDS = {
        TriggerType.CASE_FILED: ["case filed", "filing", "commencement", "initiation"],
        TriggerType.SERVICE_COMPLETED: ["service", "served", "service of process"],
        TriggerType.COMPLAINT_SERVED: ["complaint served", "service of complaint", "summons"],
        TriggerType.ANSWER_DUE: ["answer", "responsive pleading", "response to complaint"],
        TriggerType.DISCOVERY_COMMENCED: ["discovery", "interrogatories", "requests for production"],
        TriggerType.DISCOVERY_DEADLINE: ["discovery cutoff", "discovery deadline", "close of discovery"],
        TriggerType.DISPOSITIVE_MOTIONS_DUE: ["dispositive motion", "summary judgment", "motion to dismiss"],
        TriggerType.PRETRIAL_CONFERENCE: ["pretrial conference", "scheduling conference", "case management"],
        TriggerType.TRIAL_DATE: ["trial", "trial date", "jury trial", "bench trial"],
        TriggerType.HEARING_SCHEDULED: ["hearing", "motion hearing", "oral argument"],
        TriggerType.MOTION_FILED: ["motion filed", "motion", "response to motion", "reply"],
        TriggerType.ORDER_ENTERED: ["order", "court order", "judgment"],
        TriggerType.APPEAL_FILED: ["appeal", "notice of appeal", "appellate"],
        TriggerType.MEDIATION_SCHEDULED: ["mediation", "settlement conference", "ADR"],
    }

    def __init__(self):
        api_key = settings.ANTHROPIC_API_KEY.strip()
        self.anthropic = Anthropic(api_key=api_key, max_retries=3)
        self.model = settings.DEFAULT_AI_MODEL

    async def extract_from_content(
        self,
        content: str,
        jurisdiction_name: str,
        source_url: Optional[str] = None,
        assess_complexity: bool = True
    ) -> List[ExtractedRuleData]:
        """
        Extract rules from provided content using Claude with tool use.

        Args:
            content: The text content containing court rules
            jurisdiction_name: Name of the jurisdiction for context
            source_url: Optional URL where content was found
            assess_complexity: Whether to assess complexity (default: True)

        Returns:
            List of extracted rule data
        """
        prompt = f"""Extract all procedural rules from this legal text.

JURISDICTION: {jurisdiction_name}

SOURCE TEXT:
{content[:15000]}

Extract each rule and submit using the submit_extraction tool."""

        try:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.EXTRACTION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                tools=[EXTRACTION_TOOL],
                tool_choice={"type": "any"}  # Allow but don't require tool use
            )

            # Extract tool uses from response
            extracted_rules = self._extract_tool_results(response)

            # Convert to ExtractedRuleData objects
            results = []
            for rule_dict in extracted_rules:
                try:
                    # Parse deadlines
                    deadlines = [
                        ExtractedDeadline(
                            title=d.get("title", ""),
                            days_from_trigger=d.get("days_from_trigger", 0),
                            calculation_method=d.get("calculation_method", "calendar_days"),
                            priority=d.get("priority", "standard"),
                            party_responsible=d.get("party_responsible"),
                            conditions=d.get("conditions"),
                            description=d.get("description")
                        )
                        for d in rule_dict.get("deadlines", [])
                    ]

                    # Parse related rules
                    related_rules = [
                        RelatedRule(
                            citation=r.get("citation", ""),
                            purpose=r.get("purpose", "")
                        )
                        for r in rule_dict.get("related_rules", [])
                    ]

                    rule_data = ExtractedRuleData(
                        rule_code=rule_dict.get("rule_code", "UNKNOWN"),
                        rule_name=rule_dict.get("rule_name", "Unknown Rule"),
                        trigger_type=rule_dict.get("trigger_type", "custom_trigger"),
                        authority_tier=rule_dict.get("authority_tier", "state"),
                        citation=rule_dict.get("citation", ""),
                        source_url=source_url,
                        source_text=content[:2000],  # Store first 2000 chars
                        deadlines=deadlines,
                        conditions=rule_dict.get("conditions"),
                        service_extensions=rule_dict.get("service_extensions", {
                            "mail": 3, "electronic": 0, "personal": 0
                        }),
                        confidence_score=float(rule_dict.get("confidence_score", 0.0)),
                        extraction_notes=rule_dict.get("extraction_reasoning"),
                        related_rules=related_rules,
                        extraction_reasoning=[rule_dict.get("extraction_reasoning", "")]
                    )

                    # Assess complexity if requested
                    if assess_complexity and deadlines:
                        complexity_score = await self._assess_complexity(content[:4000], rule_data)
                        rule_data.complexity = complexity_score

                    results.append(rule_data)

                except Exception as e:
                    logger.warning(f"Failed to parse rule: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Rule extraction failed: {e}")
            return []

    async def _assess_complexity(
        self,
        rule_text: str,
        rule_data: ExtractedRuleData
    ) -> int:
        """
        Assess the complexity of a rule for tiered AI processing.

        Args:
            rule_text: The rule text to assess
            rule_data: The extracted rule data

        Returns:
            Complexity score (1-10)
        """
        prompt = f"""Assess the complexity of this court rule.

RULE: {rule_data.rule_name}
CITATION: {rule_data.citation}
DEADLINES: {len(rule_data.deadlines)} deadline(s)

RULE TEXT:
{rule_text}

Consider:
- Number of deadlines
- Conditional logic
- Cross-references
- Calculation complexity
- Service method variations"""

        try:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=512,
                system=self.COMPLEXITY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                tools=[COMPLEXITY_TOOL],
                tool_choice={"type": "tool", "name": "assess_complexity"}
            )

            # Extract complexity score from tool use
            for block in response.content:
                if isinstance(block, ToolUseBlock) and block.name == "assess_complexity":
                    score = block.input.get("complexity_score", 5)
                    reasoning = block.input.get("reasoning", "")
                    logger.info(f"Complexity assessment for {rule_data.rule_code}: {score}/10 - {reasoning}")
                    return score

            # Default to medium complexity if assessment fails
            return 5

        except Exception as e:
            logger.warning(f"Complexity assessment failed: {e}")
            # Heuristic fallback
            return self._heuristic_complexity(rule_data)

    def _heuristic_complexity(self, rule_data: ExtractedRuleData) -> int:
        """
        Fallback heuristic complexity scoring.

        Args:
            rule_data: The extracted rule data

        Returns:
            Complexity score (1-10)
        """
        score = 1

        # Number of deadlines
        num_deadlines = len(rule_data.deadlines)
        if num_deadlines >= 5:
            score += 3
        elif num_deadlines >= 3:
            score += 2
        elif num_deadlines >= 2:
            score += 1

        # Conditions present
        if rule_data.conditions:
            score += 2

        # Related rules (cross-references)
        if rule_data.related_rules and len(rule_data.related_rules) > 0:
            score += 1

        # Service extensions (indicates calculation complexity)
        if rule_data.service_extensions:
            extensions = rule_data.service_extensions
            if any(v > 0 for v in extensions.values()):
                score += 1

        # Mixed calculation methods
        methods = set(d.calculation_method for d in rule_data.deadlines)
        if len(methods) > 1:
            score += 1

        return min(score, 10)

    def _extract_tool_results(self, response: Message) -> List[Dict[str, Any]]:
        """
        Extract tool use results from Claude's response.

        Args:
            response: Claude's message response

        Returns:
            List of extracted rule dictionaries
        """
        results = []

        for block in response.content:
            if isinstance(block, ToolUseBlock) and block.name == "submit_extraction":
                results.append(block.input)

        return results

    async def scrape_url_content(self, url: str) -> ScrapedContent:
        """
        Fetch and clean legal text from a court URL.

        Uses Claude to extract clean legal text from court websites,
        filtering out navigation, sidebars, footers, and other UI noise.

        Args:
            url: The URL to scrape (e.g., court rules page)

        Returns:
            ScrapedContent with cleaned text, content hash, and source URLs
        """
        # Fetch the raw HTML content
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "LitDocket/1.0 (Legal Research Bot; +https://litdocket.com)"
                    }
                )
                response.raise_for_status()
                raw_html = response.text
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            raise ValueError(f"Failed to fetch URL: {e}")

        # Use Claude to extract clean legal text from HTML
        extraction_prompt = """You are a legal content extraction assistant. Extract the main legal rule text from this HTML page.

INSTRUCTIONS:
1. Extract ONLY the substantive legal rule content (statutes, rules, procedures)
2. REMOVE all navigation elements, sidebars, footers, headers, menus
3. REMOVE any advertisements, related links, or non-rule content
4. PRESERVE the exact text of rules, citations, and legal language
5. PRESERVE formatting like numbered sections, subsections, and indentation
6. Include the rule citation/title if present

Return ONLY the clean legal text. If no legal rule content is found, return "NO_LEGAL_CONTENT_FOUND".

HTML CONTENT:
{html}"""

        try:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=8192,
                messages=[{
                    "role": "user",
                    "content": extraction_prompt.format(html=raw_html[:50000])  # Limit HTML size
                }]
            )

            raw_text = response.content[0].text.strip()

            if raw_text == "NO_LEGAL_CONTENT_FOUND":
                raise ValueError("No legal content found at URL")

            # Generate content hash for change detection (first 1000 chars)
            content_hash = hashlib.sha256(raw_text[:1000].encode()).hexdigest()[:16]

            return ScrapedContent(
                raw_text=raw_text,
                content_hash=content_hash,
                source_urls=[url]
            )

        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {e}")
            raise ValueError(f"Content extraction failed: {e}")

    def map_to_trigger_type(self, rule_text: str) -> str:
        """
        Attempt to map rule text to a trigger type based on keywords.

        Args:
            rule_text: The rule text to analyze

        Returns:
            Trigger type string
        """
        lower_text = rule_text.lower()

        # Check each trigger type's keywords
        best_match = TriggerType.CUSTOM_TRIGGER
        best_score = 0

        for trigger_type, keywords in self.TRIGGER_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower_text)
            if score > best_score:
                best_score = score
                best_match = trigger_type

        return best_match.value


# Singleton instance
rule_extraction_service = RuleExtractionService()
