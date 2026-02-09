"""
Self-Healing Scraper Service - Autonomous Recovery System

Phase 6: Advanced Intelligence & Self-Healing

Automatically detects and fixes broken scrapers without manual intervention:
1. Monitor consecutive failures (threshold: 3)
2. Auto-disable failing scraper
3. Trigger Cartographer rediscovery
4. Update scraper config if confidence ≥70%
5. Re-enable and retry
6. Notify admin of auto-fix or escalate for manual intervention

Success Rate Target: 80% auto-fix without human intervention
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import logging
import asyncio

from app.models.jurisdiction import Jurisdiction
from app.models.authority_core import AuthorityRule
from app.models.enums import InboxItemType
from app.services.ai_scraper_service import AIScraperService
from app.services.authority_core_service import AuthorityCoreService
from app.services.inbox_service import InboxService
from app.services.scraper_templates import ScraperTemplateLibrary

logger = logging.getLogger(__name__)


class SelfHealingScraperService:
    """
    Autonomous scraper recovery system.

    Monitors scraper health and automatically attempts to fix failures
    by re-discovering scraper configurations and updating database.
    """

    # Configuration
    FAILURE_THRESHOLD = 3  # Failures before auto-disable
    AUTO_FIX_CONFIDENCE_THRESHOLD = 0.70  # Minimum confidence for auto-fix
    RETRY_DELAY_HOURS = 24  # Wait time before retry after fix
    MAX_AUTO_FIX_ATTEMPTS = 3  # Maximum auto-fix attempts before manual escalation

    def __init__(self, db: Session):
        self.db = db
        self.ai_scraper = AIScraperService(db)
        self.authority_service = AuthorityCoreService(db)
        self.inbox_service = InboxService(db)
        self.template_library = ScraperTemplateLibrary()

    async def check_and_heal_scrapers(self) -> Dict[str, Any]:
        """
        Main entry point: Check all scrapers and heal failing ones.

        This should be called by scheduled job (e.g., daily).

        Returns:
            Healing report with successes, failures, and manual escalations
        """
        logger.info("Starting self-healing scraper check")

        report = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "total_checked": 0,
            "healing_attempted": 0,
            "auto_fixed": 0,
            "manual_escalation": 0,
            "healthy": 0,
            "details": []
        }

        # Get all active jurisdictions
        jurisdictions = self.db.query(Jurisdiction).filter(
            Jurisdiction.auto_sync_enabled == True
        ).all()

        report["total_checked"] = len(jurisdictions)

        for jurisdiction in jurisdictions:
            # Check if scraper needs healing
            if jurisdiction.consecutive_scrape_failures >= self.FAILURE_THRESHOLD:
                logger.warning(
                    f"Jurisdiction {jurisdiction.name} has {jurisdiction.consecutive_scrape_failures} "
                    f"consecutive failures. Attempting self-heal..."
                )

                report["healing_attempted"] += 1

                # Attempt healing
                heal_result = await self.heal_scraper(jurisdiction.id)

                report["details"].append({
                    "jurisdiction_id": jurisdiction.id,
                    "jurisdiction_name": jurisdiction.name,
                    "failures": jurisdiction.consecutive_scrape_failures,
                    "heal_result": heal_result
                })

                if heal_result["success"]:
                    report["auto_fixed"] += 1
                else:
                    report["manual_escalation"] += 1
            else:
                report["healthy"] += 1

        report["completed_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Self-healing check complete: {report['auto_fixed']} fixed, "
            f"{report['manual_escalation']} escalated, {report['healthy']} healthy"
        )

        return report

    async def heal_scraper(self, jurisdiction_id: str) -> Dict[str, Any]:
        """
        Attempt to heal a single failing scraper.

        Auto-healing workflow:
        1. Disable scraper temporarily
        2. Check auto-fix attempt count
        3. Try template library first (instant)
        4. If no template, try Cartographer rediscovery
        5. Validate new config
        6. If confidence ≥70%, apply fix and re-enable
        7. If confidence <70%, escalate to manual intervention

        Args:
            jurisdiction_id: Jurisdiction with failing scraper

        Returns:
            Healing result with success status and details
        """
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            return {"success": False, "error": "Jurisdiction not found"}

        healing_log = {
            "jurisdiction_id": jurisdiction_id,
            "jurisdiction_name": jurisdiction.name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "steps": [],
            "success": False
        }

        try:
            # Step 1: Check auto-fix attempt count
            auto_fix_attempts = jurisdiction.metadata.get("auto_fix_attempts", 0) if jurisdiction.metadata else 0

            if auto_fix_attempts >= self.MAX_AUTO_FIX_ATTEMPTS:
                healing_log["steps"].append("Max auto-fix attempts reached")
                healing_log["escalation_reason"] = "Exceeded maximum auto-fix attempts"
                await self._escalate_to_manual(jurisdiction, healing_log)
                return healing_log

            # Step 2: Disable scraper temporarily
            jurisdiction.auto_sync_enabled = False
            jurisdiction.metadata = jurisdiction.metadata or {}
            jurisdiction.metadata["healing_started_at"] = datetime.now(timezone.utc).isoformat()
            self.db.commit()

            healing_log["steps"].append("Scraper disabled for healing")

            # Step 3: Try template library first (fast, free)
            template_config = None
            if jurisdiction.court_website:
                template_name = self.template_library.detect_template(jurisdiction.court_website)

                if template_name:
                    template_config = self.template_library.apply_template(
                        template_name,
                        jurisdiction.court_website
                    )
                    healing_log["steps"].append(f"Template '{template_name}' detected")

            # Step 4: If no template, use Cartographer
            if not template_config or template_config.get("confidence", 0) < self.AUTO_FIX_CONFIDENCE_THRESHOLD:
                healing_log["steps"].append("No suitable template found, trying Cartographer")

                # Get rules URL from previous config or use court_website
                rules_url = None
                if jurisdiction.scraper_config:
                    rules_url = jurisdiction.scraper_config.get("url")
                if not rules_url:
                    rules_url = jurisdiction.court_website

                if not rules_url:
                    healing_log["steps"].append("No URL available for rediscovery")
                    healing_log["escalation_reason"] = "Missing URL for rediscovery"
                    await self._escalate_to_manual(jurisdiction, healing_log)
                    return healing_log

                # Trigger Cartographer rediscovery
                try:
                    new_config = await self.ai_scraper.discover_scraper_config(
                        url=rules_url,
                        jurisdiction_id=jurisdiction_id
                    )

                    if new_config:
                        template_config = new_config
                        healing_log["steps"].append("Cartographer rediscovery successful")
                    else:
                        healing_log["steps"].append("Cartographer rediscovery failed")
                        healing_log["escalation_reason"] = "Cartographer could not rediscover config"
                        await self._escalate_to_manual(jurisdiction, healing_log)
                        return healing_log

                except Exception as e:
                    logger.error(f"Cartographer rediscovery failed: {str(e)}")
                    healing_log["steps"].append(f"Cartographer error: {str(e)}")
                    healing_log["escalation_reason"] = f"Cartographer error: {str(e)}"
                    await self._escalate_to_manual(jurisdiction, healing_log)
                    return healing_log

            # Step 5: Validate confidence
            confidence = template_config.get("confidence", 0)
            healing_log["new_config_confidence"] = confidence

            if confidence < self.AUTO_FIX_CONFIDENCE_THRESHOLD:
                healing_log["steps"].append(f"Confidence {confidence:.1%} below threshold {self.AUTO_FIX_CONFIDENCE_THRESHOLD:.1%}")
                healing_log["escalation_reason"] = "Low confidence rediscovery"
                await self._escalate_to_manual(jurisdiction, healing_log)
                return healing_log

            # Step 6: Apply fix - update scraper config
            old_config = jurisdiction.scraper_config
            jurisdiction.scraper_config = template_config
            jurisdiction.consecutive_scrape_failures = 0  # Reset failure count
            jurisdiction.metadata["auto_fix_attempts"] = auto_fix_attempts + 1
            jurisdiction.metadata["last_auto_fix"] = datetime.now(timezone.utc).isoformat()
            jurisdiction.metadata["old_config_backup"] = old_config  # Backup for rollback

            healing_log["steps"].append("Updated scraper config")

            # Step 7: Re-enable scraper
            jurisdiction.auto_sync_enabled = True
            self.db.commit()

            healing_log["steps"].append("Scraper re-enabled")
            healing_log["success"] = True
            healing_log["completed_at"] = datetime.now(timezone.utc).isoformat()

            # Step 8: Notify admin of successful auto-fix
            await self._notify_auto_fix_success(jurisdiction, healing_log)

            logger.info(f"Successfully healed scraper for {jurisdiction.name}")

            return healing_log

        except Exception as e:
            logger.error(f"Healing failed for {jurisdiction.name}: {str(e)}")
            healing_log["steps"].append(f"Error: {str(e)}")
            healing_log["escalation_reason"] = f"Exception during healing: {str(e)}"
            await self._escalate_to_manual(jurisdiction, healing_log)
            return healing_log

    async def _escalate_to_manual(self, jurisdiction: Jurisdiction, healing_log: Dict[str, Any]) -> None:
        """
        Escalate to manual intervention by creating inbox item.

        Args:
            jurisdiction: Jurisdiction that failed auto-healing
            healing_log: Healing attempt log for context
        """
        try:
            # Create inbox item for manual intervention
            self.inbox_service.create_scraper_failure_item(
                jurisdiction_id=jurisdiction.id,
                title=f"Scraper Auto-Heal Failed: {jurisdiction.name}",
                description=f"Self-healing attempted but failed. Manual intervention required.\n\n"
                           f"Escalation reason: {healing_log.get('escalation_reason', 'Unknown')}\n\n"
                           f"Steps attempted:\n" + "\n".join(f"- {step}" for step in healing_log.get("steps", [])),
                metadata={
                    "healing_log": healing_log,
                    "consecutive_failures": jurisdiction.consecutive_scrape_failures,
                    "last_scraped_at": jurisdiction.last_scraped_at.isoformat() if jurisdiction.last_scraped_at else None,
                    "requires_manual_config": True
                }
            )

            logger.info(f"Escalated {jurisdiction.name} to manual intervention inbox")

        except Exception as e:
            logger.error(f"Failed to create escalation inbox item: {str(e)}")

    async def _notify_auto_fix_success(self, jurisdiction: Jurisdiction, healing_log: Dict[str, Any]) -> None:
        """
        Notify admin of successful auto-fix.

        Args:
            jurisdiction: Jurisdiction that was healed
            healing_log: Healing success log
        """
        try:
            # Create informational inbox item
            self.inbox_service.create_inbox_item(
                type="CONFIG_WARNING",
                title=f"✅ Scraper Auto-Fixed: {jurisdiction.name}",
                description=f"Self-healing successfully repaired scraper configuration.\n\n"
                           f"New config confidence: {healing_log.get('new_config_confidence', 0):.1%}\n\n"
                           f"Steps completed:\n" + "\n".join(f"- {step}" for step in healing_log.get("steps", [])),
                jurisdiction_id=jurisdiction.id,
                metadata={
                    "healing_log": healing_log,
                    "auto_fix_success": True,
                    "review_in_24h": True
                },
                priority="low"  # Low priority since it's fixed
            )

            logger.info(f"Created success notification for {jurisdiction.name}")

        except Exception as e:
            logger.error(f"Failed to send auto-fix notification: {str(e)}")

    def rollback_config(self, jurisdiction_id: str) -> Dict[str, Any]:
        """
        Rollback to previous scraper config if auto-fix made things worse.

        Args:
            jurisdiction_id: Jurisdiction to rollback

        Returns:
            Rollback result
        """
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            return {"success": False, "error": "Jurisdiction not found"}

        if not jurisdiction.metadata or "old_config_backup" not in jurisdiction.metadata:
            return {"success": False, "error": "No backup config available"}

        try:
            old_config = jurisdiction.metadata["old_config_backup"]
            current_config = jurisdiction.scraper_config

            # Restore old config
            jurisdiction.scraper_config = old_config
            jurisdiction.metadata["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
            jurisdiction.metadata["rolled_back_from"] = current_config

            self.db.commit()

            logger.info(f"Rolled back scraper config for {jurisdiction.name}")

            return {
                "success": True,
                "message": "Config rolled back to previous version",
                "jurisdiction_name": jurisdiction.name
            }

        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            return {"success": False, "error": str(e)}

    async def test_healed_scraper(self, jurisdiction_id: str) -> Dict[str, Any]:
        """
        Test a healed scraper to verify it's working.

        Args:
            jurisdiction_id: Jurisdiction to test

        Returns:
            Test result with success status
        """
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            return {"success": False, "error": "Jurisdiction not found"}

        if not jurisdiction.scraper_config:
            return {"success": False, "error": "No scraper config to test"}

        try:
            # Get rules URL
            rules_url = jurisdiction.scraper_config.get("url") or jurisdiction.court_website

            if not rules_url:
                return {"success": False, "error": "No URL to test"}

            # Attempt extraction (don't create proposals)
            harvest_result = await self.authority_service.harvest_rules_from_url(
                jurisdiction_id=jurisdiction_id,
                url=rules_url,
                use_extended_thinking=False,
                auto_approve_high_confidence=False
            )

            if harvest_result and harvest_result.get("success"):
                # Test passed - reset failure count
                jurisdiction.consecutive_scrape_failures = 0
                jurisdiction.last_scraped_at = datetime.now(timezone.utc)
                self.db.commit()

                return {
                    "success": True,
                    "rules_found": harvest_result.get("rules_found", 0),
                    "average_confidence": harvest_result.get("average_confidence", 0),
                    "message": "Healed scraper is working correctly"
                }
            else:
                return {
                    "success": False,
                    "error": harvest_result.get("error", "Unknown error"),
                    "message": "Healed scraper still failing - consider manual intervention"
                }

        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_healing_history(self, jurisdiction_id: str) -> List[Dict[str, Any]]:
        """
        Get healing history for a jurisdiction.

        Args:
            jurisdiction_id: Jurisdiction to get history for

        Returns:
            List of healing attempts with outcomes
        """
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction or not jurisdiction.metadata:
            return []

        # Extract healing history from metadata
        history = []

        if "last_auto_fix" in jurisdiction.metadata:
            history.append({
                "timestamp": jurisdiction.metadata["last_auto_fix"],
                "type": "auto_fix",
                "attempts": jurisdiction.metadata.get("auto_fix_attempts", 0),
                "success": True
            })

        if "rolled_back_at" in jurisdiction.metadata:
            history.append({
                "timestamp": jurisdiction.metadata["rolled_back_at"],
                "type": "rollback",
                "reason": "Auto-fix made situation worse"
            })

        return sorted(history, key=lambda x: x["timestamp"], reverse=True)


# =========================================================================
# SCHEDULED JOB INTEGRATION
# =========================================================================

async def run_self_healing_check(db: Session) -> Dict[str, Any]:
    """
    Entry point for scheduled job (called daily by APScheduler).

    Args:
        db: Database session

    Returns:
        Healing report
    """
    service = SelfHealingScraperService(db)
    return await service.check_and_heal_scrapers()
