"""
Authority Core Service - Main Orchestration Service

This service coordinates:
1. Web scraping pipeline for rule extraction
2. Proposal management (create, approve, reject)
3. Rules database queries for deadline calculation
4. Conflict detection between rules
"""
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import uuid
import json
import logging
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from app.models.authority_core import (
    AuthorityRule,
    ScrapeJob,
    RuleProposal,
    RuleConflict,
    AuthorityRuleUsage,
    AuthorityRuleHistory
)
from app.models.jurisdiction import Jurisdiction
from app.models.enums import (
    TriggerType,
    AuthorityTier,
    ProposalStatus,
    ScrapeStatus,
    ConflictResolution
)
from app.services.rule_extraction_service import (
    RuleExtractionService,
    ExtractedRuleData,
    rule_extraction_service
)
from app.services.inbox_service import InboxService
from app.schemas.authority_core import (
    ScrapeProgress,
    DeadlineSpec,
    CalculatedDeadline
)
from app.utils.deadline_calculator import AuthoritativeDeadlineCalculator, CalculationMethod

logger = logging.getLogger(__name__)


# Authority tier precedence (lower number = higher priority)
TIER_PRECEDENCE = {
    AuthorityTier.FEDERAL: 1,
    AuthorityTier.STATE: 2,
    AuthorityTier.LOCAL: 3,
    AuthorityTier.STANDING_ORDER: 4,
    AuthorityTier.FIRM: 5,
}


@dataclass
class ScrapeProgressEvent:
    """Progress event for SSE streaming"""
    job_id: str
    status: ScrapeStatus
    progress_pct: int
    message: str
    urls_processed: List[str]
    rules_found: int
    current_action: Optional[str] = None


class AuthorityCoreService:
    """
    Main orchestration service for Authority Core.

    Manages:
    - Rule scraping pipeline
    - Proposal workflow
    - Rules database queries
    - Conflict detection
    """

    def __init__(self, db: Session, extraction_service: Optional[RuleExtractionService] = None):
        self.db = db
        self.extraction_service = extraction_service or rule_extraction_service

    # =========================================================================
    # SCRAPING PIPELINE
    # =========================================================================

    async def start_scrape(
        self,
        jurisdiction_id: str,
        search_query: str,
        user_id: str
    ) -> ScrapeJob:
        """
        Start a new scraping job.

        Args:
            jurisdiction_id: Target jurisdiction UUID
            search_query: User's search query
            user_id: User who initiated the scrape

        Returns:
            Created ScrapeJob
        """
        job = ScrapeJob(
            id=str(uuid.uuid4()),
            user_id=user_id,
            jurisdiction_id=jurisdiction_id,
            search_query=search_query,
            status=ScrapeStatus.QUEUED,
            progress_pct=0,
            rules_found=0,
            proposals_created=0,
            urls_processed=[]
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        logger.info(f"Created scrape job {job.id} for jurisdiction {jurisdiction_id}")
        return job

    async def process_scrape_job(
        self,
        job_id: str,
        content: str,
        source_url: Optional[str] = None
    ) -> AsyncGenerator[ScrapeProgressEvent, None]:
        """
        Process a scraping job with the provided content.

        This method:
        1. Updates job status to SEARCHING
        2. Extracts rules from content using AI
        3. Creates proposals for each extracted rule
        4. Updates job with results

        Args:
            job_id: The scrape job ID
            content: The content to extract rules from
            source_url: Optional source URL

        Yields:
            ScrapeProgressEvent updates
        """
        job = self.db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
        if not job:
            raise ValueError(f"Scrape job {job_id} not found")

        # Get jurisdiction for context
        jurisdiction = None
        jurisdiction_name = "Unknown Jurisdiction"
        if job.jurisdiction_id:
            jurisdiction = self.db.query(Jurisdiction).filter(
                Jurisdiction.id == job.jurisdiction_id
            ).first()
            if jurisdiction:
                jurisdiction_name = jurisdiction.name

        try:
            # Update status to searching
            job.status = ScrapeStatus.SEARCHING
            job.started_at = datetime.utcnow()
            self.db.commit()

            yield ScrapeProgressEvent(
                job_id=job_id,
                status=ScrapeStatus.SEARCHING,
                progress_pct=10,
                message="Searching for rules...",
                urls_processed=[],
                rules_found=0,
                current_action="Analyzing content"
            )

            # Update status to extracting
            job.status = ScrapeStatus.EXTRACTING
            self.db.commit()

            yield ScrapeProgressEvent(
                job_id=job_id,
                status=ScrapeStatus.EXTRACTING,
                progress_pct=30,
                message="Extracting rules from content...",
                urls_processed=[source_url] if source_url else [],
                rules_found=0,
                current_action="AI extraction in progress"
            )

            # Extract rules using AI
            extracted_rules = await self.extraction_service.extract_from_content(
                content=content,
                jurisdiction_name=jurisdiction_name,
                source_url=source_url
            )

            yield ScrapeProgressEvent(
                job_id=job_id,
                status=ScrapeStatus.EXTRACTING,
                progress_pct=60,
                message=f"Found {len(extracted_rules)} rules, creating proposals...",
                urls_processed=[source_url] if source_url else [],
                rules_found=len(extracted_rules),
                current_action="Creating proposals"
            )

            # Create proposals for each extracted rule
            proposals_created = 0
            for rule_data in extracted_rules:
                try:
                    proposal = await self.create_proposal(
                        extracted_data=rule_data,
                        scrape_job_id=job_id,
                        jurisdiction_id=job.jurisdiction_id,
                        user_id=job.user_id
                    )
                    proposals_created += 1
                except Exception as e:
                    logger.warning(f"Failed to create proposal: {e}")

            # Update job with results
            job.status = ScrapeStatus.COMPLETED
            job.rules_found = len(extracted_rules)
            job.proposals_created = proposals_created
            job.urls_processed = [source_url] if source_url else []
            job.completed_at = datetime.utcnow()
            job.progress_pct = 100
            self.db.commit()

            yield ScrapeProgressEvent(
                job_id=job_id,
                status=ScrapeStatus.COMPLETED,
                progress_pct=100,
                message=f"Completed! Found {len(extracted_rules)} rules, created {proposals_created} proposals",
                urls_processed=[source_url] if source_url else [],
                rules_found=len(extracted_rules),
                current_action=None
            )

        except Exception as e:
            logger.error(f"Scrape job {job_id} failed: {e}")
            job.status = ScrapeStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            self.db.commit()

            yield ScrapeProgressEvent(
                job_id=job_id,
                status=ScrapeStatus.FAILED,
                progress_pct=0,
                message=f"Failed: {str(e)}",
                urls_processed=job.urls_processed or [],
                rules_found=0,
                current_action=None
            )

    def get_scrape_job(self, job_id: str, user_id: str) -> Optional[ScrapeJob]:
        """Get a scrape job by ID with ownership check"""
        return self.db.query(ScrapeJob).filter(
            ScrapeJob.id == job_id,
            ScrapeJob.user_id == user_id
        ).first()

    def list_scrape_jobs(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScrapeJob]:
        """List scrape jobs for a user"""
        return self.db.query(ScrapeJob).filter(
            ScrapeJob.user_id == user_id
        ).order_by(desc(ScrapeJob.created_at)).offset(offset).limit(limit).all()

    # =========================================================================
    # PROPOSAL MANAGEMENT
    # =========================================================================

    async def create_proposal(
        self,
        extracted_data: ExtractedRuleData,
        scrape_job_id: Optional[str],
        jurisdiction_id: Optional[str],
        user_id: str
    ) -> RuleProposal:
        """
        Create a proposal from extracted rule data.

        Args:
            extracted_data: The extracted rule data
            scrape_job_id: Optional parent scrape job
            jurisdiction_id: Target jurisdiction
            user_id: User creating the proposal

        Returns:
            Created RuleProposal
        """
        # Convert ExtractedRuleData to dict for JSONB storage
        proposed_data = {
            "rule_code": extracted_data.rule_code,
            "rule_name": extracted_data.rule_name,
            "trigger_type": extracted_data.trigger_type,
            "authority_tier": extracted_data.authority_tier,
            "citation": extracted_data.citation,
            "deadlines": [
                {
                    "title": d.title,
                    "days_from_trigger": d.days_from_trigger,
                    "calculation_method": d.calculation_method,
                    "priority": d.priority,
                    "party_responsible": d.party_responsible,
                    "conditions": d.conditions,
                    "description": d.description
                }
                for d in extracted_data.deadlines
            ],
            "conditions": extracted_data.conditions,
            "service_extensions": extracted_data.service_extensions,
            "complexity": extracted_data.complexity  # Store complexity for tiered processing
        }

        proposal = RuleProposal(
            id=str(uuid.uuid4()),
            user_id=user_id,
            scrape_job_id=scrape_job_id,
            jurisdiction_id=jurisdiction_id,
            proposed_rule_data=proposed_data,
            source_url=extracted_data.source_url,
            source_text=extracted_data.source_text,
            confidence_score=extracted_data.confidence_score,
            extraction_notes=extracted_data.extraction_notes,
            status=ProposalStatus.PENDING
        )

        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)

        # Phase 3: Create inbox item for attorney review
        try:
            inbox_service = InboxService(self.db)

            # Get jurisdiction name for display
            jurisdiction = self.db.query(Jurisdiction).filter(
                Jurisdiction.id == jurisdiction_id
            ).first()
            jurisdiction_name = jurisdiction.name if jurisdiction else "Unknown"

            # Determine priority based on confidence score
            if extracted_data.confidence_score >= 0.95:
                priority = "low"  # High confidence - likely auto-approved
            elif extracted_data.confidence_score >= 0.80:
                priority = "medium"  # Medium confidence - recommend approval
            else:
                priority = "high"  # Low confidence - requires careful review

            inbox_service.create_inbox_item(
                type="RULE_VERIFICATION",
                title=f"New Rule: {extracted_data.rule_name}",
                description=f"Extracted rule from {jurisdiction_name} requires verification. Confidence: {extracted_data.confidence_score:.0%}",
                jurisdiction_id=jurisdiction_id,
                rule_id=None,  # Will be set when approved
                metadata={
                    "proposal_id": proposal.id,
                    "rule_code": extracted_data.rule_code,
                    "citation": extracted_data.citation,
                    "trigger_type": extracted_data.trigger_type,
                    "deadlines_count": len(extracted_data.deadlines),
                    "confidence": extracted_data.confidence_score,
                    "source_url": extracted_data.source_url,
                    "complexity": extracted_data.complexity,
                    "extraction_notes": extracted_data.extraction_notes
                },
                priority=priority
            )

            logger.info(f"Created inbox item for proposal {proposal.id}")

        except Exception as e:
            logger.error(f"Failed to create inbox item for proposal {proposal.id}: {str(e)}")
            # Don't fail proposal creation if inbox item fails

        logger.info(
            f"Created proposal {proposal.id} for rule {extracted_data.rule_code} "
            f"(complexity: {extracted_data.complexity}/10)"
        )
        return proposal

    async def approve_proposal(
        self,
        proposal_id: str,
        user_id: str,
        modifications: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> AuthorityRule:
        """
        Approve a proposal and create the AuthorityRule.

        Args:
            proposal_id: The proposal to approve
            user_id: The approving user
            modifications: Optional modifications to the proposed data
            notes: Optional reviewer notes

        Returns:
            Created AuthorityRule
        """
        proposal = self.db.query(RuleProposal).filter(
            RuleProposal.id == proposal_id
        ).first()

        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Proposal {proposal_id} is not pending")

        # Use modifications if provided, otherwise use original proposed data
        rule_data = modifications or proposal.proposed_rule_data

        # Map authority tier string to enum
        tier_str = rule_data.get("authority_tier", "state")
        tier_map = {
            "federal": AuthorityTier.FEDERAL,
            "state": AuthorityTier.STATE,
            "local": AuthorityTier.LOCAL,
            "standing_order": AuthorityTier.STANDING_ORDER,
            "firm": AuthorityTier.FIRM
        }
        authority_tier = tier_map.get(tier_str.lower(), AuthorityTier.STATE)

        # Create the AuthorityRule
        rule = AuthorityRule(
            id=str(uuid.uuid4()),
            user_id=proposal.user_id,
            jurisdiction_id=proposal.jurisdiction_id,
            authority_tier=authority_tier,
            rule_code=rule_data.get("rule_code"),
            rule_name=rule_data.get("rule_name"),
            trigger_type=rule_data.get("trigger_type"),
            citation=rule_data.get("citation"),
            source_url=proposal.source_url,
            source_text=proposal.source_text,
            deadlines=rule_data.get("deadlines", []),
            conditions=rule_data.get("conditions"),
            service_extensions=rule_data.get("service_extensions", {
                "mail": 3, "electronic": 0, "personal": 0
            }),
            confidence_score=proposal.confidence_score,
            complexity=rule_data.get("complexity"),  # Store complexity score
            is_verified=True,
            verified_by=user_id,
            verified_at=datetime.utcnow(),
            is_active=True
        )

        self.db.add(rule)

        # Update proposal
        proposal.status = ProposalStatus.APPROVED
        proposal.reviewed_by = user_id
        proposal.reviewer_notes = notes
        proposal.reviewed_at = datetime.utcnow()
        proposal.approved_rule_id = rule.id

        self.db.commit()
        self.db.refresh(rule)

        # Check for conflicts with existing rules
        await self._check_for_conflicts(rule)

        logger.info(f"Approved proposal {proposal_id}, created rule {rule.id}")
        return rule

    async def reject_proposal(
        self,
        proposal_id: str,
        user_id: str,
        reason: str
    ) -> None:
        """Reject a proposal"""
        proposal = self.db.query(RuleProposal).filter(
            RuleProposal.id == proposal_id
        ).first()

        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        proposal.status = ProposalStatus.REJECTED
        proposal.reviewed_by = user_id
        proposal.reviewer_notes = reason
        proposal.reviewed_at = datetime.utcnow()

        self.db.commit()
        logger.info(f"Rejected proposal {proposal_id}: {reason}")

    async def request_revision(
        self,
        proposal_id: str,
        user_id: str,
        notes: str
    ) -> None:
        """Mark a proposal as needing revision"""
        proposal = self.db.query(RuleProposal).filter(
            RuleProposal.id == proposal_id
        ).first()

        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        proposal.status = ProposalStatus.NEEDS_REVISION
        proposal.reviewed_by = user_id
        proposal.reviewer_notes = notes
        proposal.reviewed_at = datetime.utcnow()

        self.db.commit()
        logger.info(f"Requested revision for proposal {proposal_id}")

    def list_proposals(
        self,
        user_id: str,
        status: Optional[ProposalStatus] = None,
        jurisdiction_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RuleProposal]:
        """List proposals with optional filters"""
        query = self.db.query(RuleProposal).filter(
            RuleProposal.user_id == user_id
        )

        if status:
            query = query.filter(RuleProposal.status == status)
        if jurisdiction_id:
            query = query.filter(RuleProposal.jurisdiction_id == jurisdiction_id)

        return query.order_by(desc(RuleProposal.created_at)).offset(offset).limit(limit).all()

    def get_proposal(self, proposal_id: str, user_id: str) -> Optional[RuleProposal]:
        """Get a proposal by ID with ownership check"""
        return self.db.query(RuleProposal).filter(
            RuleProposal.id == proposal_id,
            RuleProposal.user_id == user_id
        ).first()

    # =========================================================================
    # RULES DATABASE QUERIES
    # =========================================================================

    async def get_rules_for_trigger(
        self,
        jurisdiction_id: str,
        trigger_type: str,
        include_higher_tiers: bool = True
    ) -> List[AuthorityRule]:
        """
        Get active rules for a specific trigger type.

        Args:
            jurisdiction_id: Target jurisdiction
            trigger_type: The trigger type to query
            include_higher_tiers: Whether to include federal rules for state jurisdictions

        Returns:
            List of matching AuthorityRule objects, sorted by tier precedence
        """
        query = self.db.query(AuthorityRule).filter(
            AuthorityRule.trigger_type == trigger_type,
            AuthorityRule.is_active == True,
            AuthorityRule.is_verified == True
        )

        if include_higher_tiers:
            # Get rules for this jurisdiction OR higher-tier (federal) rules
            query = query.filter(
                or_(
                    AuthorityRule.jurisdiction_id == jurisdiction_id,
                    AuthorityRule.authority_tier == AuthorityTier.FEDERAL
                )
            )
        else:
            query = query.filter(AuthorityRule.jurisdiction_id == jurisdiction_id)

        rules = query.all()

        # Sort by tier precedence (lower = higher priority)
        rules.sort(key=lambda r: TIER_PRECEDENCE.get(r.authority_tier, 99))

        return rules

    async def get_effective_rules(
        self,
        jurisdiction_id: str,
        trigger_type: str,
        case_context: Optional[Dict[str, Any]] = None
    ) -> List[AuthorityRule]:
        """
        Get effective rules considering tier precedence and conditions.

        This method:
        1. Gets all matching rules
        2. Filters by conditions if case_context provided
        3. Resolves conflicts using tier precedence

        Args:
            jurisdiction_id: Target jurisdiction
            trigger_type: The trigger type
            case_context: Optional context for condition evaluation

        Returns:
            List of effective rules to apply
        """
        rules = await self.get_rules_for_trigger(
            jurisdiction_id=jurisdiction_id,
            trigger_type=trigger_type,
            include_higher_tiers=True
        )

        if not rules:
            return []

        # Filter by conditions if context provided
        if case_context:
            rules = [r for r in rules if self._conditions_match(r.conditions, case_context)]

        return rules

    def _conditions_match(
        self,
        rule_conditions: Optional[Dict[str, Any]],
        case_context: Dict[str, Any]
    ) -> bool:
        """
        Check if rule conditions match the case context.

        Supports:
        - Simple value matching (case_types, motion_types)
        - Exclusions (exclusions.field = [excluded_values])
        - Date ranges (date_range.field = {after: date, before: date})
        - Boolean logic (AND, OR, NOT)
        - Regex patterns (regex.field = pattern)
        - Numeric comparisons (numeric.field = {gt: N, lt: N, gte: N, lte: N, eq: N})

        Args:
            rule_conditions: The conditions to check
            case_context: The case context to check against

        Returns:
            True if all conditions match, False otherwise
        """
        if not rule_conditions:
            return True

        # Check for boolean logic wrappers
        if "$and" in rule_conditions:
            return all(
                self._conditions_match(sub_cond, case_context)
                for sub_cond in rule_conditions["$and"]
            )

        if "$or" in rule_conditions:
            return any(
                self._conditions_match(sub_cond, case_context)
                for sub_cond in rule_conditions["$or"]
            )

        if "$not" in rule_conditions:
            return not self._conditions_match(rule_conditions["$not"], case_context)

        # Simple value matching: case_types
        if "case_types" in rule_conditions:
            case_type = case_context.get("case_type")
            allowed_types = rule_conditions["case_types"]

            if case_type:
                # Support regex patterns in case_types
                if any(self._match_with_regex(case_type, pattern) for pattern in allowed_types):
                    pass  # Match found
                elif case_type not in allowed_types:
                    return False

        # Simple value matching: motion_types
        if "motion_types" in rule_conditions:
            motion_type = case_context.get("motion_type")
            if motion_type and motion_type not in rule_conditions["motion_types"]:
                return False

        # Exclusions
        if "exclusions" in rule_conditions:
            for key, excluded_values in rule_conditions["exclusions"].items():
                context_value = case_context.get(key)
                if context_value is not None and context_value in excluded_values:
                    return False

        # Date range conditions
        if "date_range" in rule_conditions:
            if not self._check_date_range_conditions(
                rule_conditions["date_range"], case_context
            ):
                return False

        # Regex conditions
        if "regex" in rule_conditions:
            if not self._check_regex_conditions(
                rule_conditions["regex"], case_context
            ):
                return False

        # Numeric conditions
        if "numeric" in rule_conditions:
            if not self._check_numeric_conditions(
                rule_conditions["numeric"], case_context
            ):
                return False

        # Field existence checks
        if "required_fields" in rule_conditions:
            for field in rule_conditions["required_fields"]:
                if field not in case_context or case_context[field] is None:
                    return False

        # Boolean field checks
        if "boolean" in rule_conditions:
            for field, expected_value in rule_conditions["boolean"].items():
                actual_value = case_context.get(field)
                # Normalize boolean-like values
                normalized = self._normalize_boolean(actual_value)
                expected = self._normalize_boolean(expected_value)
                if normalized != expected:
                    return False

        return True

    def _match_with_regex(self, value: str, pattern: str) -> bool:
        """
        Check if a value matches a pattern.

        Pattern can be:
        - Plain string: exact match
        - String starting with "regex:": regex pattern
        - String with wildcards (*): glob-style matching
        """
        import re

        if pattern.startswith("regex:"):
            # Explicit regex pattern
            regex_pattern = pattern[6:]  # Remove "regex:" prefix
            try:
                return bool(re.match(regex_pattern, value, re.IGNORECASE))
            except re.error:
                logger.warning(f"Invalid regex pattern: {regex_pattern}")
                return False

        elif "*" in pattern:
            # Glob-style pattern - convert to regex
            regex_pattern = pattern.replace("*", ".*")
            try:
                return bool(re.match(f"^{regex_pattern}$", value, re.IGNORECASE))
            except re.error:
                return False

        else:
            # Exact match (case-insensitive)
            return value.lower() == pattern.lower()

    def _check_date_range_conditions(
        self,
        date_conditions: Dict[str, Any],
        case_context: Dict[str, Any]
    ) -> bool:
        """
        Check date range conditions.

        Supports:
        - after: date must be after this date
        - before: date must be before this date
        - on_or_after: date must be on or after this date
        - on_or_before: date must be on or before this date
        """
        from datetime import datetime as dt

        for field, conditions in date_conditions.items():
            context_value = case_context.get(field)
            if not context_value:
                continue

            # Parse the context date
            if isinstance(context_value, str):
                try:
                    context_date = dt.fromisoformat(context_value.replace('Z', '+00:00')).date()
                except ValueError:
                    logger.warning(f"Invalid date format in context: {context_value}")
                    continue
            elif isinstance(context_value, date):
                context_date = context_value
            else:
                continue

            # Check each condition
            if "after" in conditions:
                after_date = self._parse_date_condition(conditions["after"])
                if after_date and context_date <= after_date:
                    return False

            if "before" in conditions:
                before_date = self._parse_date_condition(conditions["before"])
                if before_date and context_date >= before_date:
                    return False

            if "on_or_after" in conditions:
                after_date = self._parse_date_condition(conditions["on_or_after"])
                if after_date and context_date < after_date:
                    return False

            if "on_or_before" in conditions:
                before_date = self._parse_date_condition(conditions["on_or_before"])
                if before_date and context_date > before_date:
                    return False

        return True

    def _parse_date_condition(self, value: Any) -> Optional[date]:
        """Parse a date from a condition value"""
        from datetime import datetime as dt

        if isinstance(value, date):
            return value
        if isinstance(value, str):
            # Handle special values
            if value == "today":
                return date.today()
            try:
                return dt.fromisoformat(value.replace('Z', '+00:00')).date()
            except ValueError:
                return None
        return None

    def _check_regex_conditions(
        self,
        regex_conditions: Dict[str, str],
        case_context: Dict[str, Any]
    ) -> bool:
        """
        Check regex pattern conditions.

        Format: {"field_name": "pattern"}
        """
        import re

        for field, pattern in regex_conditions.items():
            context_value = case_context.get(field)
            if context_value is None:
                continue

            # Convert to string if necessary
            value_str = str(context_value)

            try:
                if not re.search(pattern, value_str, re.IGNORECASE):
                    return False
            except re.error:
                logger.warning(f"Invalid regex pattern for {field}: {pattern}")
                continue

        return True

    def _check_numeric_conditions(
        self,
        numeric_conditions: Dict[str, Dict[str, Any]],
        case_context: Dict[str, Any]
    ) -> bool:
        """
        Check numeric comparison conditions.

        Format: {"field_name": {"gt": N, "lt": N, "gte": N, "lte": N, "eq": N}}
        """
        for field, conditions in numeric_conditions.items():
            context_value = case_context.get(field)
            if context_value is None:
                continue

            try:
                num_value = float(context_value)
            except (ValueError, TypeError):
                continue

            # Check each comparison
            if "gt" in conditions and not (num_value > conditions["gt"]):
                return False
            if "lt" in conditions and not (num_value < conditions["lt"]):
                return False
            if "gte" in conditions and not (num_value >= conditions["gte"]):
                return False
            if "lte" in conditions and not (num_value <= conditions["lte"]):
                return False
            if "eq" in conditions and not (num_value == conditions["eq"]):
                return False
            if "ne" in conditions and not (num_value != conditions["ne"]):
                return False

        return True

    def _normalize_boolean(self, value: Any) -> Optional[bool]:
        """Normalize various boolean-like values to actual booleans"""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower = value.lower().strip()
            if lower in ("true", "yes", "1", "y", "on"):
                return True
            if lower in ("false", "no", "0", "n", "off"):
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return None

    async def search_rules(
        self,
        query: str,
        jurisdiction_id: Optional[str] = None,
        trigger_type: Optional[str] = None,
        limit: int = 20
    ) -> List[AuthorityRule]:
        """
        Search rules by keyword.

        Args:
            query: Search query
            jurisdiction_id: Optional jurisdiction filter
            trigger_type: Optional trigger type filter
            limit: Maximum results

        Returns:
            List of matching rules
        """
        search_filter = or_(
            AuthorityRule.rule_name.ilike(f"%{query}%"),
            AuthorityRule.rule_code.ilike(f"%{query}%"),
            AuthorityRule.citation.ilike(f"%{query}%"),
            AuthorityRule.source_text.ilike(f"%{query}%")
        )

        db_query = self.db.query(AuthorityRule).filter(
            search_filter,
            AuthorityRule.is_active == True
        )

        if jurisdiction_id:
            db_query = db_query.filter(
                or_(
                    AuthorityRule.jurisdiction_id == jurisdiction_id,
                    AuthorityRule.authority_tier == AuthorityTier.FEDERAL
                )
            )

        if trigger_type:
            db_query = db_query.filter(AuthorityRule.trigger_type == trigger_type)

        return db_query.limit(limit).all()

    def get_rule(self, rule_id: str) -> Optional[AuthorityRule]:
        """Get a rule by ID"""
        return self.db.query(AuthorityRule).filter(
            AuthorityRule.id == rule_id
        ).first()

    def list_rules(
        self,
        jurisdiction_id: Optional[str] = None,
        trigger_type: Optional[str] = None,
        verified_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuthorityRule]:
        """List rules with optional filters"""
        query = self.db.query(AuthorityRule).filter(
            AuthorityRule.is_active == True
        )

        if verified_only:
            query = query.filter(AuthorityRule.is_verified == True)
        if jurisdiction_id:
            query = query.filter(AuthorityRule.jurisdiction_id == jurisdiction_id)
        if trigger_type:
            query = query.filter(AuthorityRule.trigger_type == trigger_type)

        return query.order_by(
            AuthorityRule.authority_tier,
            AuthorityRule.rule_name
        ).offset(offset).limit(limit).all()

    # =========================================================================
    # DEADLINE CALCULATION
    # =========================================================================

    async def calculate_deadlines(
        self,
        jurisdiction_id: str,
        trigger_type: str,
        trigger_date: date,
        case_context: Optional[Dict[str, Any]] = None,
        service_method: str = "electronic"
    ) -> List[CalculatedDeadline]:
        """
        Calculate deadlines from Authority Core rules.

        Args:
            jurisdiction_id: Target jurisdiction
            trigger_type: The trigger event type
            trigger_date: Date of the trigger event
            case_context: Optional context for conditions
            service_method: Service method for extensions (mail, electronic, personal)

        Returns:
            List of calculated deadlines
        """
        rules = await self.get_effective_rules(
            jurisdiction_id=jurisdiction_id,
            trigger_type=trigger_type,
            case_context=case_context
        )

        if not rules:
            logger.info(f"No Authority Core rules found for {trigger_type} in {jurisdiction_id}")
            return []

        calculated = []
        calculator = AuthoritativeDeadlineCalculator()

        for rule in rules:
            # Get rule-level service extensions (defaults)
            rule_extensions = rule.service_extensions or {"mail": 3, "electronic": 0, "personal": 0}

            for deadline_spec in rule.deadlines or []:
                # Check deadline-specific conditions
                if deadline_spec.get("conditions") and case_context:
                    if not self._conditions_match(deadline_spec["conditions"], case_context):
                        continue

                # =====================================================================
                # Per-Deadline Service Extensions
                # Priority: deadline-level > rule-level > default (0)
                # =====================================================================
                extension_days = self._get_service_extension_days(
                    service_method=service_method,
                    rule_extensions=rule_extensions,
                    deadline_extensions=deadline_spec.get("service_extensions")
                )

                # Calculate the deadline date
                days = deadline_spec.get("days_from_trigger", 0) + extension_days
                method_str = deadline_spec.get("calculation_method", "calendar_days")

                # Map to CalculationMethod enum
                method_map = {
                    "calendar_days": CalculationMethod.CALENDAR_DAYS,
                    "business_days": CalculationMethod.BUSINESS_DAYS,
                    "court_days": CalculationMethod.COURT_DAYS
                }
                calc_method = method_map.get(method_str, CalculationMethod.CALENDAR_DAYS)

                # Calculate the date using AuthoritativeDeadlineCalculator
                # Get jurisdiction name for the calculator
                jurisdiction_obj = self.db.query(Jurisdiction).filter(
                    Jurisdiction.id == jurisdiction_id
                ).first()
                jurisdiction_name = "state" if jurisdiction_obj and jurisdiction_obj.code == "FL" else "federal"

                calculation = calculator.calculate_deadline(
                    trigger_date=trigger_date,
                    base_days=days,
                    service_method=service_method,
                    calculation_method=calc_method,
                    jurisdiction=jurisdiction_name
                )

                # Extract the deadline date from the DeadlineCalculation object
                deadline_date = calculation.final_deadline

                calculated.append(CalculatedDeadline(
                    title=deadline_spec.get("title", "Unknown"),
                    deadline_date=deadline_date,
                    days_from_trigger=deadline_spec.get("days_from_trigger", 0),
                    calculation_method=method_str,
                    priority=deadline_spec.get("priority", "standard"),
                    party_responsible=deadline_spec.get("party_responsible"),
                    source_rule_id=rule.id,
                    citation=rule.citation,
                    rule_name=rule.rule_name,
                    conditions_met=case_context or {}
                ))

        return calculated

    def _get_service_extension_days(
        self,
        service_method: str,
        rule_extensions: Dict[str, int],
        deadline_extensions: Optional[Dict[str, Any]]
    ) -> int:
        """
        Calculate service extension days with per-deadline override support.

        Priority:
        1. If deadline has no_extensions=True, return 0
        2. If deadline has explicit extension for this method, use it
        3. Otherwise, use rule-level extension
        4. Default to 0 if nothing specified

        Args:
            service_method: The service method (mail, electronic, personal)
            rule_extensions: Rule-level service extensions dict
            deadline_extensions: Per-deadline service extensions dict (optional)

        Returns:
            Number of extension days to add
        """
        # If deadline has explicit service_extensions
        if deadline_extensions:
            # Check if no_extensions flag is set
            if deadline_extensions.get("no_extensions", False):
                return 0

            # Check if deadline has explicit value for this service method
            deadline_value = deadline_extensions.get(service_method)
            if deadline_value is not None:
                return deadline_value

        # Fall back to rule-level extension
        return rule_extensions.get(service_method, 0)

    # =========================================================================
    # CONFLICT DETECTION
    # =========================================================================

    async def _check_for_conflicts(self, new_rule: AuthorityRule) -> List[RuleConflict]:
        """
        Check for conflicts between new rule and existing rules.

        Conflicts are detected:
        1. Within same jurisdiction (same trigger type)
        2. Across tiers (Federal vs State vs Local) for same trigger type
        3. Different deadline days for same deadline title
        4. Different calculation methods

        Severity is determined by:
        - "error": Same tier, same jurisdiction - must be resolved
        - "warning": Cross-tier conflict (lower tier conflicts with higher)
        - "info": Method mismatch or minor differences

        Cross-tier conflicts with clear precedence are auto-resolved.
        """
        conflicts = []

        # =====================================================================
        # 1. Check within same jurisdiction (existing behavior)
        # =====================================================================
        same_jurisdiction_rules = self.db.query(AuthorityRule).filter(
            AuthorityRule.jurisdiction_id == new_rule.jurisdiction_id,
            AuthorityRule.trigger_type == new_rule.trigger_type,
            AuthorityRule.is_active == True,
            AuthorityRule.id != new_rule.id
        ).all()

        for existing in same_jurisdiction_rules:
            new_conflicts = self._compare_rule_deadlines(
                new_rule, existing,
                is_same_jurisdiction=True,
                is_cross_tier=False
            )
            conflicts.extend(new_conflicts)

        # =====================================================================
        # 2. Check cross-tier conflicts (Federal vs State vs Local)
        # =====================================================================
        # Get all rules with same trigger type but different jurisdictions/tiers
        cross_tier_rules = self.db.query(AuthorityRule).filter(
            AuthorityRule.trigger_type == new_rule.trigger_type,
            AuthorityRule.is_active == True,
            AuthorityRule.id != new_rule.id,
            # Different jurisdiction OR same jurisdiction but different tier
            or_(
                AuthorityRule.jurisdiction_id != new_rule.jurisdiction_id,
                and_(
                    AuthorityRule.jurisdiction_id == new_rule.jurisdiction_id,
                    AuthorityRule.authority_tier != new_rule.authority_tier
                )
            )
        ).all()

        for existing in cross_tier_rules:
            # Only check if there's a tier difference
            if existing.authority_tier != new_rule.authority_tier:
                new_conflicts = self._compare_rule_deadlines(
                    new_rule, existing,
                    is_same_jurisdiction=(existing.jurisdiction_id == new_rule.jurisdiction_id),
                    is_cross_tier=True
                )
                conflicts.extend(new_conflicts)

        if conflicts:
            self.db.commit()
            logger.info(f"Detected {len(conflicts)} conflicts for rule {new_rule.id}")

            # Auto-resolve cross-tier conflicts with clear precedence
            await self._auto_resolve_cross_tier_conflicts(conflicts)

        return conflicts

    def _compare_rule_deadlines(
        self,
        rule_a: AuthorityRule,
        rule_b: AuthorityRule,
        is_same_jurisdiction: bool,
        is_cross_tier: bool
    ) -> List[RuleConflict]:
        """
        Compare deadlines between two rules and create conflict records.

        Args:
            rule_a: The new rule being checked
            rule_b: The existing rule to compare against
            is_same_jurisdiction: Whether rules are in the same jurisdiction
            is_cross_tier: Whether rules are from different authority tiers

        Returns:
            List of RuleConflict records created
        """
        conflicts = []

        # Compare deadlines
        deadlines_a = {d.get("title"): d for d in (rule_a.deadlines or [])}
        deadlines_b = {d.get("title"): d for d in (rule_b.deadlines or [])}

        for title, dl_a in deadlines_a.items():
            if title in deadlines_b:
                dl_b = deadlines_b[title]

                # Determine severity based on context
                base_severity = self._determine_conflict_severity(
                    rule_a, rule_b, is_same_jurisdiction, is_cross_tier
                )

                # Check days mismatch
                days_a = dl_a.get("days_from_trigger")
                days_b = dl_b.get("days_from_trigger")
                if days_a != days_b:
                    # Build description with tier info for cross-tier conflicts
                    if is_cross_tier:
                        desc = (
                            f"Cross-tier conflict: '{title}' has different days. "
                            f"{rule_a.authority_tier.value.upper()} ({rule_a.rule_code}): {days_a} days vs "
                            f"{rule_b.authority_tier.value.upper()} ({rule_b.rule_code}): {days_b} days"
                        )
                    else:
                        desc = f"Deadline '{title}' has different days: {days_a} vs {days_b}"

                    conflict = RuleConflict(
                        id=str(uuid.uuid4()),
                        rule_a_id=rule_a.id,
                        rule_b_id=rule_b.id,
                        conflict_type="days_mismatch" if not is_cross_tier else "cross_tier_days_mismatch",
                        severity=base_severity,
                        description=desc,
                        resolution=ConflictResolution.PENDING
                    )
                    self.db.add(conflict)
                    conflicts.append(conflict)

                # Check method mismatch
                method_a = dl_a.get("calculation_method")
                method_b = dl_b.get("calculation_method")
                if method_a != method_b:
                    if is_cross_tier:
                        desc = (
                            f"Cross-tier conflict: '{title}' has different calculation methods. "
                            f"{rule_a.authority_tier.value.upper()}: {method_a} vs "
                            f"{rule_b.authority_tier.value.upper()}: {method_b}"
                        )
                    else:
                        desc = f"Deadline '{title}' has different calculation methods: {method_a} vs {method_b}"

                    conflict = RuleConflict(
                        id=str(uuid.uuid4()),
                        rule_a_id=rule_a.id,
                        rule_b_id=rule_b.id,
                        conflict_type="method_mismatch" if not is_cross_tier else "cross_tier_method_mismatch",
                        severity="info",  # Method mismatches are always informational
                        description=desc,
                        resolution=ConflictResolution.PENDING
                    )
                    self.db.add(conflict)
                    conflicts.append(conflict)

                # Check priority mismatch (cross-tier only)
                if is_cross_tier:
                    priority_a = dl_a.get("priority")
                    priority_b = dl_b.get("priority")
                    if priority_a != priority_b:
                        conflict = RuleConflict(
                            id=str(uuid.uuid4()),
                            rule_a_id=rule_a.id,
                            rule_b_id=rule_b.id,
                            conflict_type="cross_tier_priority_mismatch",
                            severity="info",
                            description=(
                                f"Cross-tier priority mismatch: '{title}'. "
                                f"{rule_a.authority_tier.value.upper()}: {priority_a} vs "
                                f"{rule_b.authority_tier.value.upper()}: {priority_b}"
                            ),
                            resolution=ConflictResolution.PENDING
                        )
                        self.db.add(conflict)
                        conflicts.append(conflict)

        return conflicts

    def _determine_conflict_severity(
        self,
        rule_a: AuthorityRule,
        rule_b: AuthorityRule,
        is_same_jurisdiction: bool,
        is_cross_tier: bool
    ) -> str:
        """
        Determine the severity of a conflict based on context.

        Returns:
            "error": Same tier, same jurisdiction - must be manually resolved
            "warning": Cross-tier conflict - may be auto-resolved
            "info": Minor differences
        """
        if is_same_jurisdiction and not is_cross_tier:
            # Same jurisdiction, same tier - this is a serious conflict
            return "error"
        elif is_cross_tier:
            # Cross-tier conflicts are warnings - can often be auto-resolved
            return "warning"
        else:
            return "info"

    async def _auto_resolve_cross_tier_conflicts(self, conflicts: List[RuleConflict]) -> None:
        """
        Auto-resolve cross-tier conflicts where tier precedence is clear.

        Federal > State > Local > Standing Order > Firm
        """
        for conflict in conflicts:
            if conflict.resolution != ConflictResolution.PENDING:
                continue

            if not conflict.conflict_type.startswith("cross_tier_"):
                continue

            # Get both rules
            rule_a = self.db.query(AuthorityRule).filter(
                AuthorityRule.id == conflict.rule_a_id
            ).first()
            rule_b = self.db.query(AuthorityRule).filter(
                AuthorityRule.id == conflict.rule_b_id
            ).first()

            if not rule_a or not rule_b:
                continue

            # Determine winner by tier precedence
            tier_a = TIER_PRECEDENCE.get(rule_a.authority_tier, 99)
            tier_b = TIER_PRECEDENCE.get(rule_b.authority_tier, 99)

            if tier_a < tier_b:
                # Rule A is higher tier - it wins
                conflict.resolution = ConflictResolution.USE_HIGHER_TIER
                conflict.resolution_notes = (
                    f"Auto-resolved: {rule_a.authority_tier.value.upper()} tier "
                    f"takes precedence over {rule_b.authority_tier.value.upper()} tier"
                )
                conflict.resolved_at = datetime.utcnow()
                logger.info(
                    f"Auto-resolved conflict {conflict.id}: "
                    f"{rule_a.authority_tier.value} > {rule_b.authority_tier.value}"
                )
            elif tier_b < tier_a:
                # Rule B is higher tier - it wins
                conflict.resolution = ConflictResolution.USE_HIGHER_TIER
                conflict.resolution_notes = (
                    f"Auto-resolved: {rule_b.authority_tier.value.upper()} tier "
                    f"takes precedence over {rule_a.authority_tier.value.upper()} tier"
                )
                conflict.resolved_at = datetime.utcnow()
                logger.info(
                    f"Auto-resolved conflict {conflict.id}: "
                    f"{rule_b.authority_tier.value} > {rule_a.authority_tier.value}"
                )
            # If same tier, leave as PENDING for manual resolution

        self.db.commit()

    async def auto_resolve_by_tier(
        self,
        conflict_id: Optional[str] = None,
        resolve_all_pending: bool = False
    ) -> List[str]:
        """
        Auto-resolve conflicts based on tier precedence.

        Federal > State > Local > Standing Order > Firm

        Args:
            conflict_id: Specific conflict to resolve (optional)
            resolve_all_pending: If True, resolve all pending cross-tier conflicts

        Returns:
            List of conflict IDs that were resolved
        """
        resolved_ids = []

        if conflict_id:
            # Resolve specific conflict
            conflicts = [self.db.query(RuleConflict).filter(
                RuleConflict.id == conflict_id,
                RuleConflict.resolution == ConflictResolution.PENDING
            ).first()]
            conflicts = [c for c in conflicts if c]  # Remove None
        elif resolve_all_pending:
            # Resolve all pending cross-tier conflicts
            conflicts = self.db.query(RuleConflict).filter(
                RuleConflict.resolution == ConflictResolution.PENDING,
                RuleConflict.conflict_type.like("cross_tier_%")
            ).all()
        else:
            return []

        for conflict in conflicts:
            # Get both rules
            rule_a = self.db.query(AuthorityRule).filter(
                AuthorityRule.id == conflict.rule_a_id
            ).first()
            rule_b = self.db.query(AuthorityRule).filter(
                AuthorityRule.id == conflict.rule_b_id
            ).first()

            if not rule_a or not rule_b:
                continue

            # Determine winner by tier precedence
            tier_a = TIER_PRECEDENCE.get(rule_a.authority_tier, 99)
            tier_b = TIER_PRECEDENCE.get(rule_b.authority_tier, 99)

            if tier_a != tier_b:
                winner = rule_a if tier_a < tier_b else rule_b
                loser = rule_b if tier_a < tier_b else rule_a

                conflict.resolution = ConflictResolution.USE_HIGHER_TIER
                conflict.resolution_notes = (
                    f"Auto-resolved by tier precedence: {winner.authority_tier.value.upper()} "
                    f"({winner.rule_code}) takes precedence over "
                    f"{loser.authority_tier.value.upper()} ({loser.rule_code})"
                )
                conflict.resolved_at = datetime.utcnow()
                resolved_ids.append(conflict.id)
                logger.info(f"Auto-resolved conflict {conflict.id} by tier precedence")

        if resolved_ids:
            self.db.commit()

        return resolved_ids

    def list_conflicts(
        self,
        resolution: Optional[ConflictResolution] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[RuleConflict]:
        """List rule conflicts"""
        query = self.db.query(RuleConflict)

        if resolution:
            query = query.filter(RuleConflict.resolution == resolution)

        return query.order_by(desc(RuleConflict.created_at)).offset(offset).limit(limit).all()

    async def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
        user_id: str,
        notes: Optional[str] = None
    ) -> None:
        """Resolve a conflict"""
        conflict = self.db.query(RuleConflict).filter(
            RuleConflict.id == conflict_id
        ).first()

        if not conflict:
            raise ValueError(f"Conflict {conflict_id} not found")

        conflict.resolution = resolution
        conflict.resolved_by = user_id
        conflict.resolved_at = datetime.utcnow()
        conflict.resolution_notes = notes

        self.db.commit()
        logger.info(f"Resolved conflict {conflict_id} as {resolution.value}")

    # =========================================================================
    # USAGE TRACKING
    # =========================================================================

    async def record_rule_usage(
        self,
        rule_id: str,
        user_id: str,
        case_id: Optional[str] = None,
        deadline_id: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_date: Optional[date] = None,
        deadlines_generated: int = 0
    ) -> AuthorityRuleUsage:
        """Record that a rule was used to generate deadlines"""
        usage = AuthorityRuleUsage(
            id=str(uuid.uuid4()),
            rule_id=rule_id,
            user_id=user_id,
            case_id=case_id,
            deadline_id=deadline_id,
            trigger_type=trigger_type,
            trigger_date=trigger_date,
            deadlines_generated=deadlines_generated
        )
        self.db.add(usage)
        self.db.commit()
        return usage

    def get_rule_usage_stats(self, rule_id: str) -> Dict[str, Any]:
        """Get usage statistics for a rule"""
        usage_count = self.db.query(func.count(AuthorityRuleUsage.id)).filter(
            AuthorityRuleUsage.rule_id == rule_id
        ).scalar()

        total_deadlines = self.db.query(func.sum(AuthorityRuleUsage.deadlines_generated)).filter(
            AuthorityRuleUsage.rule_id == rule_id
        ).scalar()

        return {
            "usage_count": usage_count or 0,
            "total_deadlines_generated": total_deadlines or 0
        }

    # =========================================================================
    # RULE HISTORY & VERSIONING
    # =========================================================================

    def get_rule_history(
        self,
        rule_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[AuthorityRuleHistory]:
        """
        Get the change history for a rule.

        Args:
            rule_id: The rule to get history for
            limit: Maximum records to return
            offset: Records to skip

        Returns:
            List of AuthorityRuleHistory records, newest first
        """
        return self.db.query(AuthorityRuleHistory).filter(
            AuthorityRuleHistory.rule_id == rule_id
        ).order_by(
            desc(AuthorityRuleHistory.version)
        ).offset(offset).limit(limit).all()

    def get_rule_at_version(
        self,
        rule_id: str,
        version: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get the state of a rule at a specific version.

        Args:
            rule_id: The rule ID
            version: The version number to retrieve

        Returns:
            Rule data as stored at that version, or None if not found
        """
        history = self.db.query(AuthorityRuleHistory).filter(
            AuthorityRuleHistory.rule_id == rule_id,
            AuthorityRuleHistory.version == version
        ).first()

        if history:
            return history.new_data
        return None

    def get_latest_rule_version(self, rule_id: str) -> int:
        """Get the latest version number for a rule"""
        result = self.db.query(func.max(AuthorityRuleHistory.version)).filter(
            AuthorityRuleHistory.rule_id == rule_id
        ).scalar()
        return result or 0

    async def record_manual_history(
        self,
        rule_id: str,
        change_type: str,
        user_id: str,
        change_reason: Optional[str] = None,
        previous_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        changed_fields: Optional[List[str]] = None
    ) -> AuthorityRuleHistory:
        """
        Manually record a history entry for a rule.

        Use this for:
        - Recording changes made outside normal update flow
        - Adding explanatory history entries
        - Migration/import operations

        Args:
            rule_id: The rule being modified
            change_type: Type of change (created, updated, superseded, etc.)
            user_id: User making the change
            change_reason: Why the change was made
            previous_data: State before change
            new_data: State after change
            changed_fields: List of field names that changed

        Returns:
            Created AuthorityRuleHistory record
        """
        # Get next version number
        next_version = self.get_latest_rule_version(rule_id) + 1

        # If new_data not provided, snapshot the current rule
        if new_data is None:
            rule = self.get_rule(rule_id)
            if rule:
                new_data = self._rule_to_snapshot(rule)
            else:
                raise ValueError(f"Rule {rule_id} not found")

        history = AuthorityRuleHistory(
            id=str(uuid.uuid4()),
            rule_id=rule_id,
            version=next_version,
            changed_by=user_id,
            change_type=change_type,
            previous_data=previous_data,
            new_data=new_data,
            changed_fields=changed_fields,
            change_reason=change_reason
        )

        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

        logger.info(f"Recorded manual history v{next_version} for rule {rule_id}: {change_type}")
        return history

    def _rule_to_snapshot(self, rule: AuthorityRule) -> Dict[str, Any]:
        """Convert a rule to a JSON-serializable snapshot for history storage"""
        return {
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "trigger_type": rule.trigger_type,
            "authority_tier": rule.authority_tier.value if rule.authority_tier else None,
            "citation": rule.citation,
            "source_url": rule.source_url,
            "source_text": rule.source_text,
            "deadlines": rule.deadlines,
            "conditions": rule.conditions,
            "service_extensions": rule.service_extensions,
            "confidence_score": float(rule.confidence_score) if rule.confidence_score else None,
            "is_verified": rule.is_verified,
            "is_active": rule.is_active,
            "effective_date": rule.effective_date.isoformat() if rule.effective_date else None,
            "superseded_date": rule.superseded_date.isoformat() if rule.superseded_date else None
        }

    def compare_rule_versions(
        self,
        rule_id: str,
        from_version: int,
        to_version: int
    ) -> Dict[str, Any]:
        """
        Compare two versions of a rule and return the differences.

        Args:
            rule_id: The rule to compare
            from_version: Earlier version number
            to_version: Later version number

        Returns:
            Dict with changed fields and their old/new values
        """
        from_data = self.get_rule_at_version(rule_id, from_version)
        to_data = self.get_rule_at_version(rule_id, to_version)

        if not from_data or not to_data:
            return {"error": "One or both versions not found"}

        changes = {}
        all_keys = set(from_data.keys()) | set(to_data.keys())

        for key in all_keys:
            old_val = from_data.get(key)
            new_val = to_data.get(key)
            if old_val != new_val:
                changes[key] = {
                    "from": old_val,
                    "to": new_val
                }

        return {
            "rule_id": rule_id,
            "from_version": from_version,
            "to_version": to_version,
            "changes": changes,
            "fields_changed": list(changes.keys())
        }

    # =========================================================================
    # TIERED AI PROCESSING (Complexity-Based Cost Optimization)
    # =========================================================================

    def should_use_extended_thinking(self, complexity: Optional[int]) -> bool:
        """
        Determine if extended thinking should be used based on complexity.

        Tiered approach:
        - Simple (1-3): Basic extraction only
        - Medium (4-6): + Conflict detection
        - Complex (7-10): + Extended thinking + Full analysis

        Args:
            complexity: Rule complexity score (1-10)

        Returns:
            True if extended thinking should be used
        """
        if complexity is None:
            return False  # Default to basic extraction if unknown

        return complexity >= 7

    def should_check_conflicts(self, complexity: Optional[int]) -> bool:
        """
        Determine if conflict checking should be performed.

        Args:
            complexity: Rule complexity score (1-10)

        Returns:
            True if conflict checking should be performed
        """
        if complexity is None:
            return True  # Default to checking if unknown (safer)

        return complexity >= 4

    def get_processing_tier(self, complexity: Optional[int]) -> str:
        """
        Get the processing tier for a rule based on complexity.

        Tiers:
        - BASIC (1-3): Simple deadline, minimal processing
        - STANDARD (4-6): Normal processing with conflict checks
        - ADVANCED (7-10): Full analysis with extended thinking

        Args:
            complexity: Rule complexity score (1-10)

        Returns:
            Processing tier name
        """
        if complexity is None:
            return "STANDARD"

        if complexity <= 3:
            return "BASIC"
        elif complexity <= 6:
            return "STANDARD"
        else:
            return "ADVANCED"

    async def process_with_tiered_pipeline(
        self,
        extracted_data: ExtractedRuleData,
        jurisdiction_id: str,
        user_id: str
    ) -> RuleProposal:
        """
        Process extracted rule data with complexity-based tiered pipeline.

        This method orchestrates the full extraction workflow with cost optimization:
        1. Assess complexity
        2. Skip expensive operations for simple rules
        3. Apply full analysis only for complex rules

        Args:
            extracted_data: The extracted rule data
            jurisdiction_id: Target jurisdiction
            user_id: User creating the proposal

        Returns:
            Created RuleProposal
        """
        complexity = extracted_data.complexity or 5  # Default to medium
        tier = self.get_processing_tier(complexity)

        logger.info(
            f"Processing rule {extracted_data.rule_code} with {tier} tier "
            f"(complexity: {complexity}/10)"
        )

        # BASIC tier - Skip conflict checks and extended analysis
        if tier == "BASIC":
            logger.info(f"Using BASIC tier for {extracted_data.rule_code} (cost optimization)")
            proposal = await self.create_proposal(
                extracted_data=extracted_data,
                scrape_job_id=None,
                jurisdiction_id=jurisdiction_id,
                user_id=user_id
            )
            return proposal

        # STANDARD tier - Include conflict checks
        elif tier == "STANDARD":
            logger.info(f"Using STANDARD tier for {extracted_data.rule_code}")
            proposal = await self.create_proposal(
                extracted_data=extracted_data,
                scrape_job_id=None,
                jurisdiction_id=jurisdiction_id,
                user_id=user_id
            )

            # Check for conflicts if rule is approved
            if proposal.status == ProposalStatus.APPROVED and proposal.approved_rule_id:
                rule = self.get_rule(proposal.approved_rule_id)
                if rule:
                    await self._check_for_conflicts(rule)

            return proposal

        # ADVANCED tier - Full analysis with extended thinking
        else:  # tier == "ADVANCED"
            logger.info(f"Using ADVANCED tier for {extracted_data.rule_code} (full analysis)")

            # Note: Extended thinking is already done in extraction if enabled
            # This tier would include additional analysis like:
            # - Swarm debate (multi-agent verification)
            # - DNA analysis (jurisdiction pattern matching)
            # - Risk profiling (malpractice risk assessment)
            # These features can be added in the future

            proposal = await self.create_proposal(
                extracted_data=extracted_data,
                scrape_job_id=None,
                jurisdiction_id=jurisdiction_id,
                user_id=user_id
            )

            # Full conflict analysis
            if proposal.status == ProposalStatus.APPROVED and proposal.approved_rule_id:
                rule = self.get_rule(proposal.approved_rule_id)
                if rule:
                    await self._check_for_conflicts(rule)

            return proposal

    def get_cost_savings_estimate(self, complexity: Optional[int]) -> Dict[str, Any]:
        """
        Estimate cost savings from tiered processing.

        Args:
            complexity: Rule complexity score (1-10)

        Returns:
            Dict with cost savings information
        """
        tier = self.get_processing_tier(complexity)

        # Estimated token usage by tier (approximate)
        token_usage = {
            "BASIC": 2000,      # ~$0.006 per rule
            "STANDARD": 5000,   # ~$0.015 per rule
            "ADVANCED": 15000   # ~$0.045 per rule
        }

        # Cost per 1M tokens (Claude Sonnet 4.5)
        cost_per_million_input = 3.00
        cost_per_million_output = 15.00
        avg_cost_per_million = (cost_per_million_input + cost_per_million_output) / 2

        tokens = token_usage.get(tier, 5000)
        estimated_cost = (tokens / 1_000_000) * avg_cost_per_million

        # Savings vs always using ADVANCED
        advanced_cost = (token_usage["ADVANCED"] / 1_000_000) * avg_cost_per_million
        savings = advanced_cost - estimated_cost
        savings_pct = (savings / advanced_cost) * 100 if advanced_cost > 0 else 0

        return {
            "tier": tier,
            "complexity": complexity,
            "estimated_tokens": tokens,
            "estimated_cost_usd": round(estimated_cost, 4),
            "savings_vs_advanced_usd": round(savings, 4),
            "savings_pct": round(savings_pct, 1),
            "features_enabled": {
                "conflict_detection": self.should_check_conflicts(complexity),
                "extended_thinking": self.should_use_extended_thinking(complexity)
            }
        }
