"""
Rules Scraper Service - Haiku-powered continuous court rules gathering

This service uses Claude Haiku for high-volume, cost-efficient extraction
of court rules from various sources. Rules are queued for validation
by Opus 4.5 before being added to the production database.

Architecture:
1. SCRAPE: Haiku extracts raw rules from court websites/PDFs
2. QUEUE: Extracted rules go to validation queue
3. VALIDATE: Opus 4.5 validates and enriches rules
4. APPROVE: Admin reviews and approves rules
5. DEPLOY: Approved rules added to production

Coverage Goal: All 50 states + DC + Federal courts
"""

from anthropic import Anthropic
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import re
import logging
import asyncio
from app.config import settings
from app.services.ai_models import haiku_model, opus_model, AITask

logger = logging.getLogger(__name__)


class RuleStatus(Enum):
    """Status of a scraped rule in the pipeline"""
    SCRAPED = "scraped"  # Raw extraction complete
    QUEUED = "queued"  # Waiting for validation
    VALIDATING = "validating"  # Being validated by Opus
    VALIDATED = "validated"  # Passed validation
    REJECTED = "rejected"  # Failed validation
    PENDING_APPROVAL = "pending_approval"  # Waiting for admin
    APPROVED = "approved"  # Ready for production
    DEPLOYED = "deployed"  # Live in production


class CourtType(Enum):
    """Types of courts for rule scraping"""
    STATE_TRIAL = "state_trial"
    STATE_APPELLATE = "state_appellate"
    STATE_SUPREME = "state_supreme"
    FEDERAL_DISTRICT = "federal_district"
    FEDERAL_CIRCUIT = "federal_circuit"
    FEDERAL_SUPREME = "federal_supreme"
    BANKRUPTCY = "bankruptcy"
    TAX = "tax"
    ADMINISTRATIVE = "administrative"


@dataclass
class ScrapedRule:
    """A rule extracted from a court source"""
    id: str
    jurisdiction: str  # e.g., "FL", "CA", "USDC-SDFL"
    court_type: CourtType
    rule_number: str  # e.g., "1.140", "12(b)(6)"
    rule_title: str
    rule_text: str
    source_url: Optional[str]
    source_document: Optional[str]
    effective_date: Optional[str]
    triggers: List[str]  # Events that activate this rule
    deadlines: List[Dict[str, Any]]  # Deadline templates
    status: RuleStatus = RuleStatus.SCRAPED
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validated_at: Optional[datetime] = None
    validation_notes: Optional[str] = None
    confidence_score: float = 0.0


@dataclass
class JurisdictionCoverage:
    """Coverage tracking for a jurisdiction"""
    jurisdiction_code: str
    jurisdiction_name: str
    total_rules_expected: int
    rules_scraped: int
    rules_validated: int
    rules_deployed: int
    last_updated: datetime
    coverage_percentage: float = 0.0

    def __post_init__(self):
        if self.total_rules_expected > 0:
            self.coverage_percentage = (self.rules_deployed / self.total_rules_expected) * 100


# US States and Territories
US_JURISDICTIONS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
    "PR": "Puerto Rico", "GU": "Guam", "VI": "Virgin Islands"
}

# Federal Courts
FEDERAL_JURISDICTIONS = {
    "USSC": "United States Supreme Court",
    "USCA-1": "First Circuit", "USCA-2": "Second Circuit", "USCA-3": "Third Circuit",
    "USCA-4": "Fourth Circuit", "USCA-5": "Fifth Circuit", "USCA-6": "Sixth Circuit",
    "USCA-7": "Seventh Circuit", "USCA-8": "Eighth Circuit", "USCA-9": "Ninth Circuit",
    "USCA-10": "Tenth Circuit", "USCA-11": "Eleventh Circuit", "USCA-DC": "DC Circuit",
    "USCA-FC": "Federal Circuit",
    # District Courts (94 total - major ones listed)
    "USDC-SDNY": "Southern District of New York",
    "USDC-EDNY": "Eastern District of New York",
    "USDC-NDCA": "Northern District of California",
    "USDC-CDCA": "Central District of California",
    "USDC-SDFL": "Southern District of Florida",
    "USDC-MDFL": "Middle District of Florida",
    "USDC-NDFL": "Northern District of Florida",
    "USDC-NDTX": "Northern District of Texas",
    "USDC-SDTX": "Southern District of Texas",
    "USDC-EDTX": "Eastern District of Texas",
    "USDC-WDTX": "Western District of Texas",
    "USDC-NDIL": "Northern District of Illinois",
    "USDC-DDC": "District of Columbia",
}


class RulesScraperService:
    """
    High-volume rules scraper using Claude Haiku.

    This service is designed for continuous, automated gathering of court rules.
    It uses Haiku for cost-efficient extraction and queues results for
    validation by the more powerful Opus 4.5 model.
    """

    def __init__(self):
        api_key = settings.ANTHROPIC_API_KEY.strip()
        self.anthropic = Anthropic(api_key=api_key, max_retries=3)
        self.haiku_model = haiku_model()
        self.opus_model = opus_model()
        self.rules_queue: List[ScrapedRule] = []
        self.coverage: Dict[str, JurisdictionCoverage] = {}
        logger.info(f"Rules Scraper initialized with Haiku: {self.haiku_model}")

    async def extract_rules_from_text(
        self,
        text: str,
        jurisdiction: str,
        court_type: CourtType,
        source_url: Optional[str] = None
    ) -> List[ScrapedRule]:
        """
        Extract court rules from raw text using Haiku.

        This is the primary scraping function. It uses Haiku for cost-efficient
        extraction of rules from court documents, websites, or PDFs.

        Args:
            text: Raw text content from court source
            jurisdiction: Jurisdiction code (e.g., "FL", "USDC-SDFL")
            court_type: Type of court
            source_url: Optional URL where content was found

        Returns:
            List of ScrapedRule objects
        """
        system_prompt = """You are a legal rules extraction specialist. Extract court rules from the provided text.

For each rule found, identify:
1. Rule number and title
2. The complete rule text
3. Trigger events that activate this rule (e.g., "complaint served", "motion filed")
4. Deadline templates (days, calculation method, what must be done)
5. Effective date if mentioned

Focus on procedural rules that create deadlines or filing requirements."""

        user_prompt = f"""Extract all court rules from this {jurisdiction} {court_type.value} court text.

TEXT:
{text[:20000]}

Return as JSON array:
[
  {{
    "rule_number": "string (e.g., '1.140', '12(b)(6)')",
    "rule_title": "string",
    "rule_text": "complete rule text",
    "effective_date": "YYYY-MM-DD or null",
    "triggers": ["event that activates this rule"],
    "deadlines": [
      {{
        "description": "what must be done",
        "days": number,
        "calculation_method": "calendar_days|business_days|court_days",
        "from_event": "trigger event this deadline counts from",
        "priority": "fatal|critical|important|standard"
      }}
    ]
  }}
]

Return ONLY valid JSON, no markdown or explanation."""

        try:
            response = self.anthropic.messages.create(
                model=self.haiku_model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            rules_data = self._parse_json_response(response.content[0].text)

            if not isinstance(rules_data, list):
                rules_data = [rules_data] if rules_data else []

            scraped_rules = []
            for i, rule_data in enumerate(rules_data):
                if not rule_data or not isinstance(rule_data, dict):
                    continue

                rule = ScrapedRule(
                    id=f"{jurisdiction}-{court_type.value}-{i}-{datetime.now().timestamp()}",
                    jurisdiction=jurisdiction,
                    court_type=court_type,
                    rule_number=rule_data.get("rule_number", "unknown"),
                    rule_title=rule_data.get("rule_title", ""),
                    rule_text=rule_data.get("rule_text", ""),
                    source_url=source_url,
                    source_document=text[:500],  # First 500 chars for reference
                    effective_date=rule_data.get("effective_date"),
                    triggers=rule_data.get("triggers", []),
                    deadlines=rule_data.get("deadlines", []),
                    status=RuleStatus.SCRAPED,
                    confidence_score=0.7  # Haiku extraction baseline
                )
                scraped_rules.append(rule)
                self.rules_queue.append(rule)

            logger.info(f"Extracted {len(scraped_rules)} rules from {jurisdiction} {court_type.value}")
            return scraped_rules

        except Exception as e:
            logger.error(f"Rule extraction failed: {e}")
            return []

    async def validate_rule(self, rule: ScrapedRule) -> ScrapedRule:
        """
        Validate a scraped rule using Opus 4.5.

        This is the quality gate. Opus validates:
        1. Rule accuracy (correct interpretation)
        2. Deadline calculations (mathematically correct)
        3. Trigger mappings (correct events)
        4. Completeness (all required fields)

        Args:
            rule: A previously scraped rule

        Returns:
            Updated ScrapedRule with validation status
        """
        rule.status = RuleStatus.VALIDATING

        system_prompt = """You are an expert legal rules validator with deep knowledge of court procedures across all US jurisdictions.

Your task is to validate extracted court rules for accuracy and completeness.

Validation criteria:
1. ACCURACY: Does the rule text match known court rules?
2. DEADLINES: Are the deadline calculations correct?
3. TRIGGERS: Are the trigger events properly identified?
4. COMPLETENESS: Are all relevant deadlines captured?
5. PRIORITY: Are deadline priorities correctly assigned?

Be strict - reject rules that could cause missed deadlines."""

        user_prompt = f"""Validate this extracted court rule:

JURISDICTION: {rule.jurisdiction}
COURT TYPE: {rule.court_type.value}
RULE NUMBER: {rule.rule_number}
RULE TITLE: {rule.rule_title}

RULE TEXT:
{rule.rule_text}

EXTRACTED TRIGGERS:
{json.dumps(rule.triggers, indent=2)}

EXTRACTED DEADLINES:
{json.dumps(rule.deadlines, indent=2)}

Validate and return JSON:
{{
  "is_valid": true/false,
  "confidence_score": 0.0-1.0,
  "issues": ["list of issues found"],
  "corrections": {{
    "rule_title": "corrected title if needed",
    "triggers": ["corrected triggers if needed"],
    "deadlines": [corrected deadlines if needed]
  }},
  "notes": "validation notes",
  "recommendation": "approve|reject|needs_review"
}}

Return ONLY valid JSON."""

        try:
            response = self.anthropic.messages.create(
                model=self.opus_model,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            validation = self._parse_json_response(response.content[0].text)

            if validation.get("is_valid"):
                rule.status = RuleStatus.VALIDATED
                rule.confidence_score = validation.get("confidence_score", 0.9)

                # Apply corrections if any
                if validation.get("corrections"):
                    corrections = validation["corrections"]
                    if corrections.get("triggers"):
                        rule.triggers = corrections["triggers"]
                    if corrections.get("deadlines"):
                        rule.deadlines = corrections["deadlines"]
                    if corrections.get("rule_title"):
                        rule.rule_title = corrections["rule_title"]
            else:
                rule.status = RuleStatus.REJECTED

            rule.validated_at = datetime.now(timezone.utc)
            rule.validation_notes = validation.get("notes", "")

            logger.info(f"Rule {rule.rule_number} validation: {rule.status.value}")
            return rule

        except Exception as e:
            logger.error(f"Rule validation failed: {e}")
            rule.status = RuleStatus.REJECTED
            rule.validation_notes = f"Validation error: {str(e)}"
            return rule

    async def batch_scrape_jurisdiction(
        self,
        jurisdiction: str,
        texts: List[Dict[str, Any]]
    ) -> List[ScrapedRule]:
        """
        Batch scrape rules for a jurisdiction.

        Args:
            jurisdiction: Jurisdiction code
            texts: List of {"text": str, "court_type": CourtType, "source_url": str}

        Returns:
            All scraped rules from the batch
        """
        all_rules = []

        for item in texts:
            rules = await self.extract_rules_from_text(
                text=item["text"],
                jurisdiction=jurisdiction,
                court_type=item.get("court_type", CourtType.STATE_TRIAL),
                source_url=item.get("source_url")
            )
            all_rules.extend(rules)
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        logger.info(f"Batch scraped {len(all_rules)} rules for {jurisdiction}")
        return all_rules

    async def validate_queue(self, batch_size: int = 10) -> Dict[str, int]:
        """
        Process validation queue in batches.

        Returns:
            Stats on validated, rejected, remaining
        """
        queued = [r for r in self.rules_queue if r.status == RuleStatus.SCRAPED]
        to_validate = queued[:batch_size]

        validated = 0
        rejected = 0

        for rule in to_validate:
            result = await self.validate_rule(rule)
            if result.status == RuleStatus.VALIDATED:
                validated += 1
                result.status = RuleStatus.PENDING_APPROVAL
            else:
                rejected += 1

        return {
            "validated": validated,
            "rejected": rejected,
            "remaining": len(queued) - batch_size
        }

    def get_coverage_stats(self) -> Dict[str, Any]:
        """Get current coverage statistics"""
        total_jurisdictions = len(US_JURISDICTIONS) + len(FEDERAL_JURISDICTIONS)
        covered = len([c for c in self.coverage.values() if c.rules_deployed > 0])

        # Count rules by status
        status_counts = {}
        for rule in self.rules_queue:
            status = rule.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_jurisdictions": total_jurisdictions,
            "jurisdictions_covered": covered,
            "coverage_percentage": (covered / total_jurisdictions) * 100 if total_jurisdictions > 0 else 0,
            "total_rules_in_queue": len(self.rules_queue),
            "rules_by_status": status_counts,
            "us_states": len(US_JURISDICTIONS),
            "federal_courts": len(FEDERAL_JURISDICTIONS)
        }

    def get_queue_summary(self) -> List[Dict[str, Any]]:
        """Get summary of rules in queue"""
        return [
            {
                "id": r.id,
                "jurisdiction": r.jurisdiction,
                "rule_number": r.rule_number,
                "rule_title": r.rule_title,
                "status": r.status.value,
                "confidence": r.confidence_score,
                "scraped_at": r.scraped_at.isoformat()
            }
            for r in self.rules_queue[:100]  # Limit to 100 for performance
        ]

    def _parse_json_response(self, text: str) -> Any:
        """Extract and parse JSON from AI response"""
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        json_match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed: {e}")

        return {"raw_text": text, "parse_error": True}


# Singleton instance
rules_scraper = RulesScraperService()
