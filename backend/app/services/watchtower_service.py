"""
Watchtower Service - Smart Change Detection for Court Websites

Ported from RulesHarvester. Monitors court websites for rule changes without
expensive full scrapes.

Strategy:
1. Check "Recent Updates" or "News" pages (not full rules)
2. Hash the content (ignoring dynamic elements like dates)
3. Compare with previous hash
4. If changed, ask AI if it's relevant to civil procedure
5. Only trigger full scrape if relevant

Key Features:
- Content hashing with noise filtering (dates, scripts, etc.)
- AI relevance checking to avoid false positives
- Scheduled checks (DAILY, WEEKLY, MANUAL_ONLY)
- Jittered execution to avoid overwhelming servers
- Diff generation for version control
- Inbox integration for attorney review
"""
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass
from datetime import datetime, date, timezone
import hashlib
import re
import logging
import asyncio

from anthropic import Anthropic
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.config import settings
from app.models.jurisdiction import Jurisdiction
from app.models.authority_core import AuthorityRule, AuthorityRuleHistory
from app.models.watchtower import WatchtowerHash
from app.models.inbox import InboxItem
from app.models.enums import InboxItemType, InboxStatus, SyncFrequency

logger = logging.getLogger(__name__)


# =============================================================
# DATACLASSES
# =============================================================

@dataclass
class WatchtowerCheckResult:
    """Result from checking a jurisdiction for updates"""
    jurisdiction_id: str
    has_changes: bool
    content_hash: str
    previous_hash: Optional[str]
    relevant_update: bool
    change_description: Optional[str] = None


# =============================================================
# WATCHTOWER SERVICE
# =============================================================

class WatchtowerService:
    """
    Smart change detection for court websites.

    Monitors court websites for rule changes using content hashing
    and AI relevance checking, avoiding expensive full scrapes.
    """

    # Concurrent execution protection
    _is_running = False
    _run_started_at: Optional[datetime] = None
    MAX_RUN_DURATION_MS = 30 * 60 * 1000  # 30 minutes auto-release

    def __init__(self):
        api_key = settings.ANTHROPIC_API_KEY.strip()
        self.anthropic = Anthropic(api_key=api_key, max_retries=3)
        self.model = settings.DEFAULT_AI_MODEL

    async def check_for_updates(
        self,
        jurisdiction_id: str,
        db: Session
    ) -> WatchtowerCheckResult:
        """
        Check a single jurisdiction for updates.

        Args:
            jurisdiction_id: The jurisdiction UUID to check
            db: Database session

        Returns:
            WatchtowerCheckResult with change details
        """
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction or not jurisdiction.court_website:
            raise ValueError(f"Jurisdiction {jurisdiction_id} has no court website")

        # Try to find updates/news page
        update_urls = self._get_update_urls(jurisdiction.court_website)

        for url in update_urls:
            try:
                result = await self._check_url(jurisdiction_id, url, db)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"Watchtower: Failed to check {url}: {e}")
                continue

        # Fallback: check main page
        main_result = await self._check_url(jurisdiction_id, jurisdiction.court_website, db)
        return main_result or WatchtowerCheckResult(
            jurisdiction_id=jurisdiction_id,
            has_changes=False,
            content_hash="",
            previous_hash=None,
            relevant_update=False
        )

    def _get_update_urls(self, base_url: str) -> List[str]:
        """
        Get potential update page URLs for a court website.

        Args:
            base_url: The court's main website URL

        Returns:
            List of URLs to check for updates
        """
        base = base_url.rstrip("/")
        return [
            f"{base}/news",
            f"{base}/updates",
            f"{base}/announcements",
            f"{base}/recent-updates",
            f"{base}/rules-updates",
            f"{base}/local-rules",
            f"{base}/court-rules"
        ]

    async def _check_url(
        self,
        jurisdiction_id: str,
        url: str,
        db: Session
    ) -> Optional[WatchtowerCheckResult]:
        """
        Check a specific URL for changes.

        Args:
            jurisdiction_id: Jurisdiction UUID
            url: URL to check
            db: Database session

        Returns:
            WatchtowerCheckResult if successful, None if URL fails
        """
        try:
            # Fetch content
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "LitDocket/1.0 Watchtower"}
                )

                if not response.is_success:
                    return None

                html = response.text

            # Hash content
            content_hash = self._hash_content(html)

            # Get previous hash
            previous_hash = self._get_previous_hash(jurisdiction_id, url, db)

            if previous_hash == content_hash:
                # No changes
                return WatchtowerCheckResult(
                    jurisdiction_id=jurisdiction_id,
                    has_changes=False,
                    content_hash=content_hash,
                    previous_hash=previous_hash,
                    relevant_update=False
                )

            # Content changed! Check if relevant
            relevance = await self._check_relevance(html, url)

            # Save new hash
            self._save_content_hash(jurisdiction_id, url, content_hash, db)

            return WatchtowerCheckResult(
                jurisdiction_id=jurisdiction_id,
                has_changes=True,
                content_hash=content_hash,
                previous_hash=previous_hash,
                relevant_update=relevance["is_relevant"],
                change_description=relevance.get("description")
            )

        except Exception as e:
            logger.error(f"Watchtower: Error checking {url}: {e}")
            return None

    def _hash_content(self, html: str) -> str:
        """
        Hash page content (ignoring dynamic elements).

        Args:
            html: Raw HTML content

        Returns:
            SHA-256 hash (first 16 chars)
        """
        # Remove common dynamic elements before hashing
        cleaned = html
        cleaned = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '', cleaned)  # ISO dates
        cleaned = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', cleaned)  # US dates
        cleaned = re.sub(r'<!--[\s\S]*?-->', '', cleaned)  # Comments
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return hashlib.sha256(cleaned.encode()).hexdigest()[:16]

    async def _check_relevance(
        self,
        html: str,
        url: str
    ) -> Dict[str, Any]:
        """
        Check if content changes are relevant to civil procedure rules.

        Args:
            html: HTML content
            url: Source URL

        Returns:
            Dict with is_relevant (bool) and description (str)
        """
        # Extract text content (rough extraction)
        text_content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
        text_content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text_content, flags=re.IGNORECASE)
        text_content = re.sub(r'<[^>]+>', ' ', text_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()[:4000]  # Limit for API

        try:
            response = await self.anthropic.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": f"""Analyze this court website update page and determine if it mentions changes to:
- Civil procedure rules
- Local rules
- Filing deadlines
- Court procedures
- Standing orders

URL: {url}

Content:
{text_content}

Respond with JSON: {{"isRelevant": boolean, "description": "brief description if relevant"}}"""
                }]
            )

            text = response.content[0].text
            json_match = re.search(r'\{[\s\S]*\}', text)

            if json_match:
                import json
                result = json.loads(json_match.group(0))
                return {
                    "is_relevant": result.get("isRelevant", False),
                    "description": result.get("description")
                }

        except Exception as e:
            logger.error(f"Watchtower: Relevance check failed: {e}")

        # Default to relevant if check fails (safer)
        return {
            "is_relevant": True,
            "description": "Relevance check failed, flagged for review"
        }

    def _get_previous_hash(
        self,
        jurisdiction_id: str,
        url: str,
        db: Session
    ) -> Optional[str]:
        """
        Get previous content hash from database.

        Args:
            jurisdiction_id: Jurisdiction UUID
            url: URL that was checked
            db: Database session

        Returns:
            Previous hash or None
        """
        watchtower_hash = db.query(WatchtowerHash).filter(
            and_(
                WatchtowerHash.jurisdiction_id == jurisdiction_id,
                WatchtowerHash.url == url
            )
        ).first()

        return watchtower_hash.content_hash if watchtower_hash else None

    def _save_content_hash(
        self,
        jurisdiction_id: str,
        url: str,
        content_hash: str,
        db: Session
    ) -> None:
        """
        Save content hash to database.

        Args:
            jurisdiction_id: Jurisdiction UUID
            url: URL that was checked
            content_hash: The content hash
            db: Database session
        """
        # Upsert: update if exists, insert if not
        existing = db.query(WatchtowerHash).filter(
            and_(
                WatchtowerHash.jurisdiction_id == jurisdiction_id,
                WatchtowerHash.url == url
            )
        ).first()

        if existing:
            existing.content_hash = content_hash
            existing.checked_at = datetime.now(timezone.utc)
        else:
            from app.models.watchtower import WatchtowerHash as WH
            new_hash = WH(
                jurisdiction_id=jurisdiction_id,
                url=url,
                content_hash=content_hash
            )
            db.add(new_hash)

        db.commit()

    async def run_scheduled_checks(
        self,
        frequency: Optional[Literal["DAILY", "WEEKLY"]],
        db: Session
    ) -> List[WatchtowerCheckResult]:
        """
        Check all jurisdictions with auto-sync enabled.

        Args:
            frequency: Optional filter by sync frequency (DAILY, WEEKLY)
            db: Database session

        Returns:
            List of WatchtowerCheckResult for all checked jurisdictions
        """
        # Concurrent execution protection
        if self._is_running:
            # Check if we should auto-release (stale run)
            if self._run_started_at:
                elapsed = (datetime.now(timezone.utc) - self._run_started_at).total_seconds() * 1000
                if elapsed > self.MAX_RUN_DURATION_MS:
                    logger.info("Watchtower: Auto-releasing stale lock from previous run")
                    self._is_running = False
                    self._run_started_at = None
                else:
                    logger.info("Watchtower: Skipping scan - another scan is already in progress")
                    return []
            else:
                return []

        # Acquire lock
        self._is_running = True
        self._run_started_at = datetime.now(timezone.utc)

        try:
            # Build query
            query = db.query(Jurisdiction).filter(
                Jurisdiction.auto_sync_enabled == True,
                Jurisdiction.court_website.isnot(None)
            )

            if frequency:
                query = query.filter(Jurisdiction.sync_frequency == frequency)

            jurisdictions = query.all()

            if not jurisdictions:
                return []

            logger.info(f"Watchtower: Starting {frequency or 'all'} scan for {len(jurisdictions)} jurisdictions")

            results: List[WatchtowerCheckResult] = []

            for jurisdiction in jurisdictions:
                try:
                    # Add random jitter (0-60s) to stagger checks
                    import random
                    jitter = random.uniform(0, 60)
                    await asyncio.sleep(jitter)

                    result = await self.check_for_updates(jurisdiction.id, db)
                    results.append(result)

                    # Create inbox item if relevant changes detected
                    if result.relevant_update and result.has_changes:
                        await self._create_change_inbox_item(
                            jurisdiction.id,
                            result.change_description,
                            db
                        )

                    # Rate limit between checks
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"Watchtower: Failed to check {jurisdiction.id}: {e}")

            # Log summary
            changes_detected = sum(1 for r in results if r.has_changes)
            relevant_changes = sum(1 for r in results if r.relevant_update)

            logger.info(
                f"Watchtower scan complete: {len(results)} checked, "
                f"{changes_detected} changes, {relevant_changes} relevant"
            )

            return results

        finally:
            # Release lock
            self._is_running = False
            self._run_started_at = None

    async def handle_rule_change(
        self,
        rule_id: str,
        new_raw_text: str,
        change_description: Optional[str],
        db: Session
    ) -> None:
        """
        Handle a detected rule change - store previous version and create inbox item.

        Args:
            rule_id: The rule UUID
            new_raw_text: The new rule text
            change_description: Description of what changed
            db: Database session
        """
        rule = db.query(AuthorityRule).filter(
            AuthorityRule.id == rule_id
        ).first()

        if not rule:
            logger.warning(f"Watchtower: Rule {rule_id} not found")
            return

        previous_raw_text = rule.source_text

        # Generate diff if we have previous text
        if previous_raw_text and new_raw_text:
            has_significant_changes = self._has_significant_changes(
                previous_raw_text,
                new_raw_text
            )

            if not has_significant_changes:
                logger.info(f"Watchtower: Skipping minor change for {rule.rule_name}")
                return

        # Update rule with previous text and increment version
        rule.previous_raw_text = previous_raw_text
        rule.source_text = new_raw_text
        rule.version = (rule.version or 1) + 1

        # Create history record
        history = AuthorityRuleHistory(
            rule_id=rule_id,
            version=rule.version,
            changed_by=None,  # System change
            change_type="watchtower_update",
            previous_data={"source_text": previous_raw_text},
            new_data={"source_text": new_raw_text},
            changed_fields=["source_text"],
            change_reason=change_description or "Detected by Watchtower"
        )
        db.add(history)

        logger.info(f"Watchtower: Rule {rule.rule_name} updated to version {rule.version}")

        # Check if inbox item already exists
        existing_item = db.query(InboxItem).filter(
            and_(
                InboxItem.type == InboxItemType.WATCHTOWER_CHANGE,
                InboxItem.rule_id == rule_id,
                InboxItem.status == InboxStatus.PENDING
            )
        ).first()

        if not existing_item:
            # Create inbox item
            inbox_item = InboxItem(
                type=InboxItemType.WATCHTOWER_CHANGE,
                status=InboxStatus.PENDING,
                title=f"Rule Change Detected: {rule.rule_name}",
                description=change_description or "Watchtower detected changes to this rule",
                rule_id=rule_id,
                confidence=None,
                source_url=rule.source_url,
                metadata={
                    "rule_code": rule.rule_code,
                    "previous_version": rule.version - 1,
                    "new_version": rule.version,
                    "change_description": change_description
                }
            )
            db.add(inbox_item)

        db.commit()

    async def _create_change_inbox_item(
        self,
        jurisdiction_id: str,
        change_description: Optional[str],
        db: Session
    ) -> None:
        """
        Create inbox item for detected changes.

        Args:
            jurisdiction_id: Jurisdiction UUID
            change_description: Description of changes
            db: Database session
        """
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            return

        # Check if recent inbox item exists (within last 24 hours)
        from datetime import timedelta
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        existing = db.query(InboxItem).filter(
            and_(
                InboxItem.type == InboxItemType.WATCHTOWER_CHANGE,
                InboxItem.jurisdiction_id == jurisdiction_id,
                InboxItem.created_at >= recent_cutoff
            )
        ).first()

        if existing:
            logger.info(f"Watchtower: Recent inbox item already exists for {jurisdiction.name}")
            return

        # Create new inbox item
        inbox_item = InboxItem(
            type=InboxItemType.WATCHTOWER_CHANGE,
            status=InboxStatus.PENDING,
            title=f"Rule Changes Detected: {jurisdiction.name}",
            description=change_description or "Watchtower detected changes to court rules",
            jurisdiction_id=jurisdiction_id,
            metadata={
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "change_description": change_description
            }
        )
        db.add(inbox_item)
        db.commit()

        logger.info(f"Watchtower: Created inbox item for {jurisdiction.name}")

    def _has_significant_changes(
        self,
        old_text: str,
        new_text: str
    ) -> bool:
        """
        Determine if changes between two texts are significant.

        Args:
            old_text: Previous text
            new_text: New text

        Returns:
            True if changes are significant
        """
        # Simple heuristic: check if difference is > 5%
        import difflib

        matcher = difflib.SequenceMatcher(None, old_text, new_text)
        ratio = matcher.ratio()

        # If more than 5% different, consider significant
        return ratio < 0.95


# Singleton instance
watchtower_service = WatchtowerService()
