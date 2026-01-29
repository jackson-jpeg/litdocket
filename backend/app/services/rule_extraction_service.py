"""
Rule Extraction Service - AI-Powered Rule Extraction from Court Documents

Uses Claude's capabilities to:
1. Search for court rules via web search
2. Extract structured rule data from legal text
3. Calculate confidence scores for extractions
4. Map extracted rules to trigger types
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import re
import logging

from anthropic import Anthropic

from app.config import settings
from app.models.enums import TriggerType, AuthorityTier

logger = logging.getLogger(__name__)


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


@dataclass
class SearchResult:
    """A search result from web search"""
    url: str
    title: str
    snippet: str
    relevance_score: float


class RuleExtractionService:
    """
    Service for extracting court rules using Claude AI.

    This service uses Claude's capabilities to:
    1. Search the web for court rules
    2. Extract structured data from rule text
    3. Map rules to trigger types
    4. Calculate confidence scores
    """

    EXTRACTION_PROMPT = """You are Authority Core, an expert legal AI that extracts procedural court rules from legal documents and websites.

Your task is to extract structured rule data from the provided text. For each rule found, extract:

1. **rule_code**: A unique identifier (e.g., "SDFL_LR_7.1_a_2" for S.D. Florida Local Rule 7.1(a)(2))
2. **rule_name**: Human-readable name (e.g., "Motion Response Time")
3. **trigger_type**: What event triggers this rule. Must be one of:
   - case_filed, service_completed, complaint_served, answer_due
   - discovery_commenced, discovery_deadline, dispositive_motions_due
   - pretrial_conference, trial_date, hearing_scheduled
   - motion_filed, order_entered, appeal_filed, mediation_scheduled
   - custom_trigger
4. **citation**: Official citation (e.g., "S.D. Fla. L.R. 7.1(a)(2)")
5. **deadlines**: Array of deadline specifications:
   - title: Deadline name
   - days_from_trigger: Integer (negative for before trigger, positive for after)
   - calculation_method: "calendar_days", "business_days", or "court_days"
   - priority: "informational", "standard", "important", "critical", or "fatal"
   - party_responsible: "plaintiff", "defendant", "moving_party", "opposing_party", "both", or "court"
   - conditions: Optional object with conditions when this deadline applies
6. **conditions**: When the rule applies (case_types, motion_types, etc.)
7. **service_extensions**: Additional days for service methods {"mail": 3, "electronic": 0, "personal": 0}

Return a JSON array of extracted rules. If no rules are found, return an empty array.

IMPORTANT:
- Be precise with day counts - verify against the source text
- Include the exact citation from the source
- Map to the correct trigger_type based on what event starts the countdown
- For federal rules, use "federal" tier; for state rules use "state"; for local rules use "local"
- Include any conditions that limit when the rule applies

Example output:
[
  {
    "rule_code": "SDFL_LR_7.1_a_2",
    "rule_name": "Response to Motion - S.D. Florida",
    "trigger_type": "motion_filed",
    "authority_tier": "local",
    "citation": "S.D. Fla. L.R. 7.1(a)(2)",
    "deadlines": [
      {
        "title": "Response to Motion Due",
        "days_from_trigger": 14,
        "calculation_method": "calendar_days",
        "priority": "important",
        "party_responsible": "opposing_party"
      }
    ],
    "service_extensions": {"mail": 3, "electronic": 0, "personal": 0}
  }
]"""

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
        source_url: Optional[str] = None
    ) -> List[ExtractedRuleData]:
        """
        Extract rules from provided content using Claude.

        Args:
            content: The text content containing court rules
            jurisdiction_name: Name of the jurisdiction for context
            source_url: Optional URL where content was found

        Returns:
            List of extracted rule data
        """
        prompt = f"""{self.EXTRACTION_PROMPT}

JURISDICTION CONTEXT: {jurisdiction_name}

SOURCE TEXT:
{content[:15000]}  # Limit to ~15k chars to stay within context

Extract all procedural rules from this text and return as JSON array."""

        try:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            extracted = self._parse_extraction_response(response.content[0].text)

            # Convert to ExtractedRuleData objects
            results = []
            for rule_dict in extracted:
                try:
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
                        confidence_score=self._calculate_confidence(rule_dict),
                        extraction_notes=None
                    )
                    results.append(rule_data)
                except Exception as e:
                    logger.warning(f"Failed to parse rule: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Rule extraction failed: {e}")
            return []

    async def search_court_rules(
        self,
        jurisdiction_name: str,
        query: str
    ) -> List[SearchResult]:
        """
        Search for court rules using Claude's web search capability.

        Note: This method prepares search queries. The actual web search
        would be performed by the Authority Core service using WebFetch/WebSearch.

        Args:
            jurisdiction_name: Name of the jurisdiction
            query: User's search query

        Returns:
            List of suggested search queries/URLs
        """
        # Build search query
        search_terms = f"{jurisdiction_name} court rules {query}"

        # Return suggested search patterns
        return [
            SearchResult(
                url=f"https://www.uscourts.gov/rules-policies/current-rules",
                title="Federal Rules",
                snippet="Federal Rules of Civil Procedure",
                relevance_score=0.9
            ),
            SearchResult(
                url=f"https://www.flcourts.org/Resources-Services/Court-Rules",
                title="Florida Court Rules",
                snippet="Florida Rules of Civil Procedure",
                relevance_score=0.9
            )
        ]

    def _calculate_confidence(self, rule_dict: Dict[str, Any]) -> float:
        """
        Calculate confidence score for an extracted rule.

        Factors:
        - Has citation: +0.3
        - Has deadlines with days specified: +0.2
        - Has valid trigger type: +0.2
        - Has rule code: +0.15
        - Has conditions: +0.1
        - Has service extensions: +0.05
        """
        score = 0.0

        # Citation check
        if rule_dict.get("citation"):
            score += 0.3

        # Deadlines check
        deadlines = rule_dict.get("deadlines", [])
        if deadlines and all(d.get("days_from_trigger") is not None for d in deadlines):
            score += 0.2

        # Trigger type check
        trigger_type = rule_dict.get("trigger_type", "")
        valid_triggers = [t.value for t in TriggerType]
        if trigger_type in valid_triggers:
            score += 0.2

        # Rule code check
        if rule_dict.get("rule_code") and rule_dict.get("rule_code") != "UNKNOWN":
            score += 0.15

        # Conditions check
        if rule_dict.get("conditions"):
            score += 0.1

        # Service extensions check
        if rule_dict.get("service_extensions"):
            score += 0.05

        return min(score, 1.0)

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

    def _parse_extraction_response(self, text: str) -> List[Dict[str, Any]]:
        """Parse JSON array from Claude's response"""
        # Remove markdown code blocks if present
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        # Try to find JSON array in response
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed: {e}")

        # Try parsing as single object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return [result] if isinstance(result, dict) else []
            except json.JSONDecodeError:
                pass

        logger.warning(f"Could not parse extraction response: {text[:200]}...")
        return []

    async def refine_extraction(
        self,
        original_extraction: ExtractedRuleData,
        feedback: str
    ) -> ExtractedRuleData:
        """
        Refine an extraction based on reviewer feedback.

        Args:
            original_extraction: The original extracted rule data
            feedback: Feedback from the reviewer

        Returns:
            Refined extraction
        """
        prompt = f"""You previously extracted this rule:

{json.dumps({
    "rule_code": original_extraction.rule_code,
    "rule_name": original_extraction.rule_name,
    "trigger_type": original_extraction.trigger_type,
    "citation": original_extraction.citation,
    "deadlines": [
        {
            "title": d.title,
            "days_from_trigger": d.days_from_trigger,
            "calculation_method": d.calculation_method,
            "priority": d.priority,
            "party_responsible": d.party_responsible
        }
        for d in original_extraction.deadlines
    ]
}, indent=2)}

From this source text:
{original_extraction.source_text[:2000]}

Reviewer feedback: {feedback}

Please provide a corrected extraction as JSON. If the feedback indicates the extraction was wrong, correct it. If the feedback suggests additions, include them."""

        try:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            extracted_list = self._parse_extraction_response(response.content[0].text)
            if extracted_list:
                rule_dict = extracted_list[0]
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

                return ExtractedRuleData(
                    rule_code=rule_dict.get("rule_code", original_extraction.rule_code),
                    rule_name=rule_dict.get("rule_name", original_extraction.rule_name),
                    trigger_type=rule_dict.get("trigger_type", original_extraction.trigger_type),
                    authority_tier=rule_dict.get("authority_tier", original_extraction.authority_tier),
                    citation=rule_dict.get("citation", original_extraction.citation),
                    source_url=original_extraction.source_url,
                    source_text=original_extraction.source_text,
                    deadlines=deadlines,
                    conditions=rule_dict.get("conditions", original_extraction.conditions),
                    service_extensions=rule_dict.get("service_extensions", original_extraction.service_extensions),
                    confidence_score=self._calculate_confidence(rule_dict),
                    extraction_notes=f"Refined based on feedback: {feedback[:200]}"
                )

        except Exception as e:
            logger.error(f"Refinement failed: {e}")

        return original_extraction


# Singleton instance
rule_extraction_service = RuleExtractionService()
