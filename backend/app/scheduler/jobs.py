"""
Scheduled background jobs for Authority Core automation.

This module contains the actual job implementations that are
scheduled by the APScheduler in __init__.py.
"""

import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.jurisdiction import Jurisdiction
from app.models.inbox import InboxItem
from app.models.enums import SyncFrequency, InboxStatus

logger = logging.getLogger(__name__)


async def run_daily_watchtower():
    """
    Check all DAILY sync jurisdictions for rule changes.

    Runs daily at 6am UTC. Iterates through all jurisdictions with
    auto_sync_enabled=true and sync_frequency=DAILY, triggering
    Watchtower change detection for each.
    """
    logger.info("Starting daily Watchtower check")
    db: Session = SessionLocal()

    try:
        # Get all jurisdictions with daily sync enabled
        jurisdictions = db.query(Jurisdiction).filter(
            Jurisdiction.auto_sync_enabled == True,
            Jurisdiction.sync_frequency == SyncFrequency.DAILY
        ).all()

        logger.info(f"Found {len(jurisdictions)} jurisdictions configured for daily sync")

        # Import here to avoid circular dependency
        from app.services.watchtower_service import WatchtowerService

        watchtower = WatchtowerService(db)
        changes_detected = 0

        for jurisdiction in jurisdictions:
            try:
                logger.info(f"Checking jurisdiction: {jurisdiction.name}")
                result = await watchtower.check_for_changes(jurisdiction.id)

                if result.get("has_changes"):
                    changes_detected += 1
                    logger.info(f"Changes detected in {jurisdiction.name}")

                    # Send notification if configured
                    await _notify_jurisdiction_changes(db, jurisdiction, result)

            except Exception as e:
                logger.error(f"Error checking jurisdiction {jurisdiction.name}: {str(e)}")
                await _create_error_inbox_item(db, jurisdiction, str(e))

        logger.info(f"Daily Watchtower check completed. Changes detected in {changes_detected}/{len(jurisdictions)} jurisdictions")

    except Exception as e:
        logger.error(f"Critical error in daily Watchtower job: {str(e)}")
        raise
    finally:
        db.close()


async def run_weekly_watchtower():
    """
    Check all WEEKLY sync jurisdictions for rule changes.

    Runs weekly on Sunday at 3am UTC. Similar to daily check but
    targets jurisdictions with sync_frequency=WEEKLY.
    """
    logger.info("Starting weekly Watchtower check")
    db: Session = SessionLocal()

    try:
        # Get all jurisdictions with weekly sync enabled
        jurisdictions = db.query(Jurisdiction).filter(
            Jurisdiction.auto_sync_enabled == True,
            Jurisdiction.sync_frequency == SyncFrequency.WEEKLY
        ).all()

        logger.info(f"Found {len(jurisdictions)} jurisdictions configured for weekly sync")

        from app.services.watchtower_service import WatchtowerService

        watchtower = WatchtowerService(db)
        changes_detected = 0

        for jurisdiction in jurisdictions:
            try:
                logger.info(f"Checking jurisdiction: {jurisdiction.name}")
                result = await watchtower.check_for_changes(jurisdiction.id)

                if result.get("has_changes"):
                    changes_detected += 1
                    logger.info(f"Changes detected in {jurisdiction.name}")
                    await _notify_jurisdiction_changes(db, jurisdiction, result)

            except Exception as e:
                logger.error(f"Error checking jurisdiction {jurisdiction.name}: {str(e)}")
                await _create_error_inbox_item(db, jurisdiction, str(e))

        logger.info(f"Weekly Watchtower check completed. Changes detected in {changes_detected}/{len(jurisdictions)} jurisdictions")

    except Exception as e:
        logger.error(f"Critical error in weekly Watchtower job: {str(e)}")
        raise
    finally:
        db.close()


async def run_scraper_health_check():
    """
    Verify all jurisdiction scraper configurations are valid.

    Runs daily at 5am UTC. Checks:
    - scraper_config is valid JSON
    - Required fields are present
    - consecutive_scrape_failures threshold monitoring
    - auto_sync_enabled flag consistency
    """
    logger.info("Starting scraper health check")
    db: Session = SessionLocal()

    try:
        # Get all jurisdictions with auto_sync enabled
        jurisdictions = db.query(Jurisdiction).filter(
            Jurisdiction.auto_sync_enabled == True
        ).all()

        logger.info(f"Checking health for {len(jurisdictions)} jurisdictions")

        unhealthy_count = 0
        disabled_count = 0

        for jurisdiction in jurisdictions:
            try:
                # Check 1: Validate scraper_config exists and is valid
                if not jurisdiction.scraper_config:
                    logger.warning(f"Jurisdiction {jurisdiction.name} missing scraper_config")
                    unhealthy_count += 1
                    await _create_config_warning_inbox_item(db, jurisdiction, "Missing scraper configuration")
                    continue

                # Check 2: Monitor consecutive failures (disable after 3 failures)
                if jurisdiction.consecutive_scrape_failures >= 3:
                    logger.warning(f"Jurisdiction {jurisdiction.name} has {jurisdiction.consecutive_scrape_failures} consecutive failures - disabling")
                    jurisdiction.auto_sync_enabled = False
                    disabled_count += 1
                    await _create_failure_inbox_item(db, jurisdiction)

                # Check 3: Validate scraper_config has required fields
                config = jurisdiction.scraper_config
                required_fields = ['base_url', 'selectors']
                missing_fields = [field for field in required_fields if field not in config]

                if missing_fields:
                    logger.warning(f"Jurisdiction {jurisdiction.name} scraper_config missing fields: {missing_fields}")
                    unhealthy_count += 1
                    await _create_config_warning_inbox_item(
                        db,
                        jurisdiction,
                        f"Scraper config missing required fields: {', '.join(missing_fields)}"
                    )

            except Exception as e:
                logger.error(f"Error checking health for jurisdiction {jurisdiction.name}: {str(e)}")
                unhealthy_count += 1

        db.commit()

        logger.info(f"Scraper health check completed. Unhealthy: {unhealthy_count}, Disabled: {disabled_count}")

        # Send summary notification if issues found
        if unhealthy_count > 0 or disabled_count > 0:
            await _send_health_summary_email(unhealthy_count, disabled_count)

    except Exception as e:
        logger.error(f"Critical error in scraper health check job: {str(e)}")
        raise
    finally:
        db.close()


async def cleanup_old_inbox_items():
    """
    Archive reviewed inbox items older than 90 days.

    Runs daily at 2am UTC. Updates status from APPROVED/REJECTED
    to ARCHIVED for items older than 90 days. This keeps the inbox
    clean while preserving audit trail.
    """
    logger.info("Starting inbox cleanup")
    db: Session = SessionLocal()

    try:
        # Calculate cutoff date (90 days ago)
        cutoff_date = datetime.utcnow() - timedelta(days=90)

        # Find old reviewed items
        old_items = db.query(InboxItem).filter(
            InboxItem.status.in_([InboxStatus.APPROVED, InboxStatus.REJECTED]),
            InboxItem.reviewed_at < cutoff_date
        ).all()

        logger.info(f"Found {len(old_items)} inbox items to archive (older than 90 days)")

        # Archive items
        for item in old_items:
            item.status = InboxStatus.ARCHIVED
            item.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Inbox cleanup completed. Archived {len(old_items)} items")

    except Exception as e:
        logger.error(f"Critical error in inbox cleanup job: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


# Helper functions for notifications and error handling

async def _notify_jurisdiction_changes(db: Session, jurisdiction: Jurisdiction, changes: dict):
    """Create inbox item for detected changes."""
    try:
        from app.services.inbox_service import InboxService
        inbox_service = InboxService(db)

        # Create inbox item for attorney review
        await inbox_service.create_inbox_item(
            type="WATCHTOWER_CHANGE",
            title=f"Rule changes detected: {jurisdiction.name}",
            description=f"Watchtower detected changes in {jurisdiction.name} court rules",
            metadata={
                "jurisdiction_id": str(jurisdiction.id),
                "changes": changes.get("changed_urls", []),
                "detected_at": datetime.utcnow().isoformat()
            },
            priority="medium"
        )

        logger.info(f"Created inbox item for changes in {jurisdiction.name}")

    except Exception as e:
        logger.error(f"Error creating change notification: {str(e)}")


async def _create_error_inbox_item(db: Session, jurisdiction: Jurisdiction, error_msg: str):
    """Create inbox item for scraper errors."""
    try:
        from app.services.inbox_service import InboxService
        inbox_service = InboxService(db)

        await inbox_service.create_inbox_item(
            type="SCRAPER_ERROR",
            title=f"Scraper error: {jurisdiction.name}",
            description=f"Failed to check {jurisdiction.name} for changes: {error_msg}",
            metadata={
                "jurisdiction_id": str(jurisdiction.id),
                "error": error_msg,
                "occurred_at": datetime.utcnow().isoformat()
            },
            priority="high"
        )

    except Exception as e:
        logger.error(f"Error creating error inbox item: {str(e)}")


async def _create_config_warning_inbox_item(db: Session, jurisdiction: Jurisdiction, warning_msg: str):
    """Create inbox item for configuration warnings."""
    try:
        from app.services.inbox_service import InboxService
        inbox_service = InboxService(db)

        await inbox_service.create_inbox_item(
            type="CONFIG_WARNING",
            title=f"Configuration issue: {jurisdiction.name}",
            description=warning_msg,
            metadata={
                "jurisdiction_id": str(jurisdiction.id),
                "warning": warning_msg,
                "detected_at": datetime.utcnow().isoformat()
            },
            priority="medium"
        )

    except Exception as e:
        logger.error(f"Error creating config warning inbox item: {str(e)}")


async def _create_failure_inbox_item(db: Session, jurisdiction: Jurisdiction):
    """Create inbox item when jurisdiction is auto-disabled due to failures."""
    try:
        from app.services.inbox_service import InboxService
        inbox_service = InboxService(db)

        await inbox_service.create_inbox_item(
            type="JURISDICTION_DISABLED",
            title=f"Auto-disabled: {jurisdiction.name}",
            description=f"{jurisdiction.name} was automatically disabled after {jurisdiction.consecutive_scrape_failures} consecutive scraper failures",
            metadata={
                "jurisdiction_id": str(jurisdiction.id),
                "consecutive_failures": jurisdiction.consecutive_scrape_failures,
                "disabled_at": datetime.utcnow().isoformat()
            },
            priority="high"
        )

        logger.info(f"Created inbox item for auto-disabled jurisdiction: {jurisdiction.name}")

    except Exception as e:
        logger.error(f"Error creating failure inbox item: {str(e)}")


async def _send_health_summary_email(unhealthy_count: int, disabled_count: int):
    """Send email summary of scraper health issues."""
    try:
        from app.services.authority_notification_service import AuthorityNotificationService

        notification_service = AuthorityNotificationService()
        await notification_service.send_scraper_health_alert(unhealthy_count, disabled_count)

    except Exception as e:
        logger.error(f"Error sending health summary email: {str(e)}")


# =============================================================================
# PHASE 6: SELF-HEALING SCRAPER JOB
# =============================================================================

async def run_self_healing_check():
    """
    Phase 6: Self-healing scraper check (runs daily at 3am UTC).

    Automatically detects and fixes broken scrapers:
    1. Identifies jurisdictions with ≥3 consecutive failures
    2. Attempts auto-fix via template detection or Cartographer rediscovery
    3. Updates scraper config if confidence ≥70%
    4. Re-enables scraper and notifies admin
    5. Escalates to manual intervention if auto-fix fails

    Target: 80% auto-fix success rate
    """
    logger.info("Starting self-healing scraper check (Phase 6)")
    db: Session = SessionLocal()

    try:
        from app.services.self_healing_scraper_service import SelfHealingScraperService

        healing_service = SelfHealingScraperService(db)
        report = await healing_service.check_and_heal_scrapers()

        logger.info(
            f"Self-healing check complete: {report['auto_fixed']} auto-fixed, "
            f"{report['manual_escalation']} escalated, {report['healthy']} healthy"
        )

        # Send notification if any manual escalations
        if report['manual_escalation'] > 0:
            await _notify_manual_escalations(report)

        return report

    except Exception as e:
        logger.error(f"Self-healing check failed: {str(e)}")
        raise
    finally:
        db.close()


async def _notify_manual_escalations(report: dict):
    """Send email notification for manual escalations."""
    try:
        from app.services.authority_notification_service import AuthorityNotificationService

        notification_service = AuthorityNotificationService()

        # Build email content
        escalations = [
            detail for detail in report.get('details', [])
            if not detail['heal_result'].get('success')
        ]

        if escalations:
            await notification_service.send_self_healing_alert(
                auto_fixed=report['auto_fixed'],
                escalated=report['manual_escalation'],
                escalation_details=escalations
            )

    except Exception as e:
        logger.error(f"Error sending escalation notification: {str(e)}")


# =============================================================================
# PHASE 6: AI CONFLICT RESOLUTION JOB
# =============================================================================

async def run_conflict_detection_and_resolution():
    """
    Phase 6: AI-powered rule conflict detection and resolution (runs daily at 4am UTC).

    Automatically detects and resolves conflicts between competing rules:
    1. Detects conflicts (same jurisdiction+trigger, different deadlines)
    2. Uses Claude AI to analyze which rule is authoritative
    3. Auto-resolves if confidence ≥90%
    4. Creates recommendation inbox items if confidence 70-90%
    5. Escalates to manual review if confidence <70%

    Target: 70% auto-resolve without human intervention
    """
    logger.info("Starting AI conflict detection and resolution (Phase 6)")
    db: Session = SessionLocal()

    try:
        from app.services.ai_conflict_resolver import run_conflict_detection_and_resolution as run_resolver

        report = await run_resolver(db)

        logger.info(
            f"Conflict resolution complete: {report['conflicts_detected']} detected, "
            f"{report['resolution_report']['auto_resolved']} auto-resolved, "
            f"{report['resolution_report']['recommendations_created']} recommended, "
            f"{report['resolution_report']['manual_review_required']} require manual review"
        )

        # Send notification if conflicts were found
        if report['conflicts_detected'] > 0:
            await _notify_conflict_resolution_results(report)

        return report

    except Exception as e:
        logger.error(f"Conflict resolution job failed: {str(e)}")
        raise
    finally:
        db.close()


async def _notify_conflict_resolution_results(report: dict):
    """Send email notification for conflict resolution results."""
    try:
        from app.services.authority_notification_service import AuthorityNotificationService

        notification_service = AuthorityNotificationService()

        resolution_data = report['resolution_report']

        # Only send notification if there are manual reviews needed or failures
        if resolution_data['manual_review_required'] > 0 or resolution_data['failed'] > 0:
            await notification_service.send_conflict_resolution_alert(
                conflicts_detected=report['conflicts_detected'],
                auto_resolved=resolution_data['auto_resolved'],
                recommendations=resolution_data['recommendations_created'],
                manual_review=resolution_data['manual_review_required'],
                failed=resolution_data['failed']
            )

    except Exception as e:
        logger.error(f"Error sending conflict resolution notification: {str(e)}")
