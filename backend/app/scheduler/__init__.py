"""
Background job scheduler for automated Authority Core operations.

This module provides APScheduler integration for:
- Daily/weekly Watchtower change detection
- Scraper health monitoring
- Inbox cleanup
- Automated rule harvesting workflows
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from pytz import utc
from app.config import settings

logger = logging.getLogger(__name__)

# Job store configuration - persists jobs to database for restart resilience
jobstores = {
    'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
}

# Executor configuration - run jobs in thread pool
executors = {
    'default': ThreadPoolExecutor(10)  # Max 10 concurrent jobs
}

# Job defaults
job_defaults = {
    'coalesce': True,  # Combine missed jobs into single run
    'max_instances': 1,  # Prevent concurrent runs of same job
    'misfire_grace_time': 3600  # Allow 1 hour delay before considering job missed
}

# Global scheduler instance
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone=utc
)


def start_scheduler():
    """
    Initialize and start the background job scheduler.
    Called from main.py on application startup.
    """
    try:
        # Import and register jobs
        from app.scheduler.jobs import (
            run_daily_watchtower,
            run_weekly_watchtower,
            run_scraper_health_check,
            cleanup_old_inbox_items,
            run_self_healing_check,  # Phase 6
            run_conflict_detection_and_resolution  # Phase 6
        )

        # Schedule daily Watchtower - check DAILY sync jurisdictions at 6am UTC
        scheduler.add_job(
            run_daily_watchtower,
            'cron',
            hour=6,
            minute=0,
            id='daily_watchtower',
            replace_existing=True,
            name='Daily Watchtower Check'
        )

        # Schedule weekly Watchtower - check WEEKLY sync jurisdictions Sunday 3am UTC
        scheduler.add_job(
            run_weekly_watchtower,
            'cron',
            day_of_week='sun',
            hour=3,
            minute=0,
            id='weekly_watchtower',
            replace_existing=True,
            name='Weekly Watchtower Check'
        )

        # Schedule daily scraper health check - verify all jurisdiction configs daily at 5am UTC
        scheduler.add_job(
            run_scraper_health_check,
            'cron',
            hour=5,
            minute=0,
            id='scraper_health_check',
            replace_existing=True,
            name='Scraper Health Check'
        )

        # Schedule daily inbox cleanup - archive reviewed items older than 90 days at 2am UTC
        scheduler.add_job(
            cleanup_old_inbox_items,
            'cron',
            hour=2,
            minute=0,
            id='inbox_cleanup',
            replace_existing=True,
            name='Inbox Cleanup'
        )

        # Schedule daily self-healing check - Phase 6: auto-fix broken scrapers at 3am UTC
        scheduler.add_job(
            run_self_healing_check,
            'cron',
            hour=3,
            minute=0,
            id='self_healing_check',
            replace_existing=True,
            name='Self-Healing Scraper Check'
        )

        # Schedule daily conflict resolution - Phase 6: AI-powered rule conflict detection at 4am UTC
        scheduler.add_job(
            run_conflict_detection_and_resolution,
            'cron',
            hour=4,
            minute=0,
            id='conflict_resolution',
            replace_existing=True,
            name='AI Conflict Resolution'
        )

        scheduler.start()
        logger.info("APScheduler started successfully with 6 scheduled jobs")
        logger.info(f"Jobs: {[job.id for job in scheduler.get_jobs()]}")

    except Exception as e:
        logger.error(f"Failed to start APScheduler: {str(e)}")
        raise


def shutdown_scheduler():
    """
    Gracefully shutdown the scheduler.
    Called from main.py on application shutdown.
    """
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("APScheduler shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down APScheduler: {str(e)}")


def get_scheduler_status() -> dict:
    """
    Get current scheduler status for health checks.

    Returns:
        dict: Status information including running state and job list
    """
    try:
        jobs = scheduler.get_jobs()
        return {
            "running": scheduler.running,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "pending": job.pending
                }
                for job in jobs
            ]
        }
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        return {"running": False, "error": str(e)}
