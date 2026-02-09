"""
Scraper Health Service - Self-Healing Scraper Pipeline

Monitors scraper health and automatically triggers recovery actions:
1. Tracks consecutive failures
2. Auto-disables scrapers after 3 failures
3. Creates inbox items for manual intervention
4. Triggers automatic selector rediscovery
5. Maintains audit trail of health events

Based on patterns from RulesHarvester.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session

from app.models.jurisdiction import Jurisdiction
from app.models.inbox import InboxItem, ScraperHealthLog
from app.models.enums import InboxItemType, InboxStatus
from app.services.inbox_service import InboxService

logger = logging.getLogger(__name__)


class ScraperHealthService:
    """
    Service for monitoring and managing scraper health.

    Provides self-healing capabilities:
    - Failure tracking
    - Auto-disable after consecutive failures
    - Automatic rediscovery
    - Inbox alerts for manual intervention
    """

    # Thresholds
    MAX_CONSECUTIVE_FAILURES = 3
    AUTO_REDISCOVERY_THRESHOLD = 2

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # FAILURE TRACKING
    # =========================================================================

    def record_failure(
        self,
        jurisdiction_id: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a scraper failure.

        Increments failure counter and triggers auto-disable if threshold reached.

        Args:
            jurisdiction_id: Jurisdiction UUID
            error_message: Error message
            metadata: Additional error metadata
        """
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            logger.error(f"Jurisdiction {jurisdiction_id} not found")
            return

        # Increment failure counter
        consecutive_failures = (jurisdiction.consecutive_scrape_failures or 0) + 1
        jurisdiction.consecutive_scrape_failures = consecutive_failures
        jurisdiction.last_scrape_error = error_message

        # Log health event
        self._create_health_log(
            jurisdiction_id=jurisdiction_id,
            event_type="failure",
            error_message=error_message,
            scraper_config_version=jurisdiction.scraper_config_version or 1,
            consecutive_failures=consecutive_failures,
            metadata=metadata or {}
        )

        logger.warning(
            f"Scraper failure #{consecutive_failures} for {jurisdiction.name}: "
            f"{error_message}"
        )

        # Auto-disable after threshold
        if consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            self._auto_disable_scraper(jurisdiction, error_message)

        # Trigger rediscovery after 2 failures (before auto-disable)
        elif consecutive_failures >= self.AUTO_REDISCOVERY_THRESHOLD:
            logger.info(
                f"Marking {jurisdiction.name} for selector rediscovery "
                f"({consecutive_failures} failures)"
            )
            # Note: Actual rediscovery would be triggered asynchronously

        self.db.commit()

    def record_success(self, jurisdiction_id: str) -> None:
        """
        Record a successful scrape.

        Resets failure counter and updates last successful scrape timestamp.

        Args:
            jurisdiction_id: Jurisdiction UUID
        """
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            logger.error(f"Jurisdiction {jurisdiction_id} not found")
            return

        # Check if this is a recovery from failures
        was_failing = (jurisdiction.consecutive_scrape_failures or 0) > 0

        # Reset failure counter
        jurisdiction.consecutive_scrape_failures = 0
        jurisdiction.last_scrape_error = None
        jurisdiction.last_successful_scrape = datetime.now(timezone.utc)

        # Log recovery event if recovering from failures
        if was_failing:
            self._create_health_log(
                jurisdiction_id=jurisdiction_id,
                event_type="recovery",
                error_message=None,
                scraper_config_version=jurisdiction.scraper_config_version or 1,
                consecutive_failures=0,
                metadata={"recovered_from_failures": True}
            )

            logger.info(f"Scraper recovered for {jurisdiction.name}")

            # Re-enable auto-sync if it was disabled
            if not jurisdiction.auto_sync_enabled:
                jurisdiction.auto_sync_enabled = True
                logger.info(f"Re-enabled auto-sync for {jurisdiction.name}")

        self.db.commit()

    # =========================================================================
    # AUTO-DISABLE & ALERTS
    # =========================================================================

    def _auto_disable_scraper(
        self,
        jurisdiction: Jurisdiction,
        error_message: str
    ) -> None:
        """
        Auto-disable scraper after consecutive failures.

        Args:
            jurisdiction: Jurisdiction object
            error_message: Last error message
        """
        # Disable auto-sync
        jurisdiction.auto_sync_enabled = False

        logger.error(
            f"Auto-disabled scraper for {jurisdiction.name} after "
            f"{jurisdiction.consecutive_scrape_failures} consecutive failures"
        )

        # Create inbox item for manual intervention
        inbox_service = InboxService(self.db)

        # Check if inbox item already exists
        if not inbox_service.exists_for_entity(
            InboxItemType.SCRAPER_FAILURE,
            jurisdiction.id
        ):
            inbox_service.create_scraper_failure_item(
                jurisdiction_id=jurisdiction.id,
                title=f"Scraper Disabled: {jurisdiction.name}",
                description=(
                    f"Scraper has failed {jurisdiction.consecutive_scrape_failures} "
                    f"consecutive times and has been auto-disabled. Manual intervention required.\n\n"
                    f"Last error: {error_message}"
                ),
                metadata={
                    "consecutive_failures": jurisdiction.consecutive_scrape_failures,
                    "last_error": error_message,
                    "scraper_config_version": jurisdiction.scraper_config_version,
                    "auto_disabled_at": datetime.now(timezone.utc).isoformat()
                }
            )

    # =========================================================================
    # HEALTH MONITORING
    # =========================================================================

    def get_health_status(self, jurisdiction_id: str) -> Dict[str, Any]:
        """
        Get health status for a jurisdiction's scraper.

        Args:
            jurisdiction_id: Jurisdiction UUID

        Returns:
            Dict with health status information
        """
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            return {"error": "Jurisdiction not found"}

        consecutive_failures = jurisdiction.consecutive_scrape_failures or 0

        # Determine health status
        if consecutive_failures == 0:
            status = "healthy"
        elif consecutive_failures < self.AUTO_REDISCOVERY_THRESHOLD:
            status = "degraded"
        elif consecutive_failures < self.MAX_CONSECUTIVE_FAILURES:
            status = "unhealthy"
        else:
            status = "failed"

        return {
            "jurisdiction_id": jurisdiction_id,
            "jurisdiction_name": jurisdiction.name,
            "status": status,
            "consecutive_failures": consecutive_failures,
            "last_error": jurisdiction.last_scrape_error,
            "last_successful_scrape": (
                jurisdiction.last_successful_scrape.isoformat()
                if jurisdiction.last_successful_scrape
                else None
            ),
            "auto_sync_enabled": jurisdiction.auto_sync_enabled,
            "scraper_config_version": jurisdiction.scraper_config_version,
            "needs_intervention": consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES
        }

    def get_health_dashboard(self) -> Dict[str, Any]:
        """
        Get health dashboard for all jurisdictions.

        Returns:
            Dict with aggregate health statistics
        """
        jurisdictions = self.db.query(Jurisdiction).filter(
            Jurisdiction.court_website.isnot(None)
        ).all()

        healthy = 0
        degraded = 0
        unhealthy = 0
        failed = 0

        failing_jurisdictions = []

        for jurisdiction in jurisdictions:
            failures = jurisdiction.consecutive_scrape_failures or 0

            if failures == 0:
                healthy += 1
            elif failures < self.AUTO_REDISCOVERY_THRESHOLD:
                degraded += 1
            elif failures < self.MAX_CONSECUTIVE_FAILURES:
                unhealthy += 1
            else:
                failed += 1
                failing_jurisdictions.append({
                    "id": jurisdiction.id,
                    "name": jurisdiction.name,
                    "consecutive_failures": failures,
                    "last_error": jurisdiction.last_scrape_error
                })

        return {
            "total_jurisdictions": len(jurisdictions),
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "failed": failed,
            "failing_jurisdictions": failing_jurisdictions,
            "health_percentage": (
                round((healthy / len(jurisdictions)) * 100, 1)
                if jurisdictions
                else 0
            )
        }

    # =========================================================================
    # HEALTH LOGS
    # =========================================================================

    def _create_health_log(
        self,
        jurisdiction_id: str,
        event_type: str,
        error_message: Optional[str],
        scraper_config_version: int,
        consecutive_failures: int,
        metadata: Dict[str, Any]
    ) -> ScraperHealthLog:
        """
        Create a health log entry.

        Args:
            jurisdiction_id: Jurisdiction UUID
            event_type: Type of event (failure, recovery, config_update, rediscovery)
            error_message: Optional error message
            scraper_config_version: Current config version
            consecutive_failures: Current failure count
            metadata: Additional metadata

        Returns:
            Created ScraperHealthLog
        """
        log = ScraperHealthLog(
            jurisdiction_id=jurisdiction_id,
            event_type=event_type,
            error_message=error_message,
            scraper_config_version=scraper_config_version,
            consecutive_failures=consecutive_failures,
            event_metadata=metadata
        )

        self.db.add(log)
        # Note: commit is done by caller
        return log

    def get_health_logs(
        self,
        jurisdiction_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ScraperHealthLog]:
        """
        Get health logs with optional filters.

        Args:
            jurisdiction_id: Optional jurisdiction filter
            event_type: Optional event type filter
            limit: Maximum logs to return
            offset: Pagination offset

        Returns:
            List of ScraperHealthLog objects
        """
        from sqlalchemy import desc

        query = self.db.query(ScraperHealthLog)

        if jurisdiction_id:
            query = query.filter(ScraperHealthLog.jurisdiction_id == jurisdiction_id)
        if event_type:
            query = query.filter(ScraperHealthLog.event_type == event_type)

        return query.order_by(desc(ScraperHealthLog.created_at)).offset(offset).limit(limit).all()

    # =========================================================================
    # CONFIGURATION MANAGEMENT
    # =========================================================================

    def record_config_update(
        self,
        jurisdiction_id: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a scraper configuration update.

        Args:
            jurisdiction_id: Jurisdiction UUID
            reason: Reason for config update
            metadata: Additional metadata
        """
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            logger.error(f"Jurisdiction {jurisdiction_id} not found")
            return

        # Increment config version
        jurisdiction.scraper_config_version = (jurisdiction.scraper_config_version or 0) + 1

        # Log the event
        self._create_health_log(
            jurisdiction_id=jurisdiction_id,
            event_type="config_update",
            error_message=None,
            scraper_config_version=jurisdiction.scraper_config_version,
            consecutive_failures=jurisdiction.consecutive_scrape_failures or 0,
            metadata={
                "reason": reason,
                **(metadata or {})
            }
        )

        logger.info(
            f"Updated scraper config for {jurisdiction.name} to version "
            f"{jurisdiction.scraper_config_version}: {reason}"
        )

        self.db.commit()

    def trigger_rediscovery(
        self,
        jurisdiction_id: str,
        reason: str
    ) -> None:
        """
        Trigger selector rediscovery for a jurisdiction.

        This marks the jurisdiction for rediscovery and logs the event.
        Actual rediscovery would be performed asynchronously.

        Args:
            jurisdiction_id: Jurisdiction UUID
            reason: Reason for rediscovery
        """
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not jurisdiction:
            logger.error(f"Jurisdiction {jurisdiction_id} not found")
            return

        # Clear existing config to force rediscovery
        jurisdiction.scraper_config = None

        # Log the event
        self._create_health_log(
            jurisdiction_id=jurisdiction_id,
            event_type="rediscovery",
            error_message=None,
            scraper_config_version=jurisdiction.scraper_config_version or 1,
            consecutive_failures=jurisdiction.consecutive_scrape_failures or 0,
            metadata={
                "reason": reason,
                "triggered_at": datetime.now(timezone.utc).isoformat()
            }
        )

        logger.info(f"Triggered selector rediscovery for {jurisdiction.name}: {reason}")

        self.db.commit()
