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
    AuthorityRuleUsage
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
            "service_extensions": extracted_data.service_extensions
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

        logger.info(f"Created proposal {proposal.id} for rule {extracted_data.rule_code}")
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
        """Check if rule conditions match the case context"""
        if not rule_conditions:
            return True

        # Check case_types
        if "case_types" in rule_conditions:
            case_type = case_context.get("case_type")
            if case_type and case_type not in rule_conditions["case_types"]:
                return False

        # Check motion_types
        if "motion_types" in rule_conditions:
            motion_type = case_context.get("motion_type")
            if motion_type and motion_type not in rule_conditions["motion_types"]:
                return False

        # Check exclusions
        if "exclusions" in rule_conditions:
            for key, excluded_values in rule_conditions["exclusions"].items():
                if case_context.get(key) in excluded_values:
                    return False

        return True

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
            service_method: Service method for extensions

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
            # Get service extension days
            extensions = rule.service_extensions or {}
            extension_days = extensions.get(service_method, 0)

            for deadline_spec in rule.deadlines or []:
                # Check deadline-specific conditions
                if deadline_spec.get("conditions") and case_context:
                    if not self._conditions_match(deadline_spec["conditions"], case_context):
                        continue

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

                # Calculate the date
                deadline_date = calculator.calculate_deadline(
                    start_date=trigger_date,
                    days=days,
                    method=calc_method
                )

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

    # =========================================================================
    # CONFLICT DETECTION
    # =========================================================================

    async def _check_for_conflicts(self, new_rule: AuthorityRule) -> List[RuleConflict]:
        """
        Check for conflicts between new rule and existing rules.

        Conflicts are detected when:
        1. Same trigger type and jurisdiction
        2. Different deadline days for same deadline title
        3. Different calculation methods
        """
        conflicts = []

        # Find existing rules with same trigger and jurisdiction
        existing_rules = self.db.query(AuthorityRule).filter(
            AuthorityRule.jurisdiction_id == new_rule.jurisdiction_id,
            AuthorityRule.trigger_type == new_rule.trigger_type,
            AuthorityRule.is_active == True,
            AuthorityRule.id != new_rule.id
        ).all()

        for existing in existing_rules:
            # Compare deadlines
            new_deadlines = {d.get("title"): d for d in (new_rule.deadlines or [])}
            existing_deadlines = {d.get("title"): d for d in (existing.deadlines or [])}

            for title, new_dl in new_deadlines.items():
                if title in existing_deadlines:
                    existing_dl = existing_deadlines[title]

                    # Check days mismatch
                    if new_dl.get("days_from_trigger") != existing_dl.get("days_from_trigger"):
                        conflict = RuleConflict(
                            id=str(uuid.uuid4()),
                            rule_a_id=new_rule.id,
                            rule_b_id=existing.id,
                            conflict_type="days_mismatch",
                            severity="warning",
                            description=f"Deadline '{title}' has different days: {new_dl.get('days_from_trigger')} vs {existing_dl.get('days_from_trigger')}",
                            resolution=ConflictResolution.PENDING
                        )
                        self.db.add(conflict)
                        conflicts.append(conflict)

                    # Check method mismatch
                    if new_dl.get("calculation_method") != existing_dl.get("calculation_method"):
                        conflict = RuleConflict(
                            id=str(uuid.uuid4()),
                            rule_a_id=new_rule.id,
                            rule_b_id=existing.id,
                            conflict_type="method_mismatch",
                            severity="info",
                            description=f"Deadline '{title}' has different calculation methods",
                            resolution=ConflictResolution.PENDING
                        )
                        self.db.add(conflict)
                        conflicts.append(conflict)

        if conflicts:
            self.db.commit()
            logger.info(f"Detected {len(conflicts)} conflicts for rule {new_rule.id}")

        return conflicts

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
