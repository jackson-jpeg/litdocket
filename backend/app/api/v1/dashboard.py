"""
Dashboard API endpoints
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.dashboard_service import dashboard_service
from app.services.morning_report_service import MorningReportService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_default_dashboard_data() -> Dict[str, Any]:
    """Return safe default values for dashboard data"""
    return {
        "case_statistics": {
            "total_cases": 0,
            "total_documents": 0,
            "total_pending_deadlines": 0,
            "by_jurisdiction": {"state": 0, "federal": 0, "unknown": 0},
            "by_case_type": {"civil": 0, "criminal": 0, "appellate": 0, "other": 0}
        },
        "deadline_alerts": {
            "overdue": {"count": 0, "deadlines": []},
            "urgent": {"count": 0, "deadlines": []},
            "upcoming_week": {"count": 0, "deadlines": []},
            "upcoming_month": {"count": 0, "deadlines": []}
        },
        "recent_activity": [],
        "critical_cases": [],
        "upcoming_deadlines": [],
        "heat_map": None,
        "matter_health_cards": []
    }


def get_default_morning_report() -> Dict[str, Any]:
    """Return safe default values for morning report"""
    from datetime import datetime
    return {
        "greeting": "Good morning",
        "summary": "Welcome to LitDocket. Add cases and documents to get started.",
        "high_risk_alerts": [],
        "new_filings": [],
        "upcoming_deadlines": [],
        "actionable_insights": [],
        "case_overview": {
            "total_cases": 0,
            "cases_needing_attention": 0,
            "total_pending_deadlines": 0
        },
        "week_stats": {
            "completed_this_week": 0,
            "due_this_week": 0,
            "day_of_week": datetime.now().strftime('%A')
        },
        "milestones": [],
        "workload_level": "clear",
        "generated_at": datetime.now().isoformat()
    }


@router.get("")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard data for the current user

    Returns:
        - Case statistics
        - Deadline alerts (overdue, urgent, upcoming)
        - Recent activity feed
        - Critical cases needing attention
        - Upcoming deadlines (next 30 days)
    """
    try:
        dashboard_data = await dashboard_service.get_dashboard_data(
            user_id=current_user.id,
            db=db
        )

        # Validate response structure - ensure required fields exist
        if not dashboard_data:
            logger.warning(f"Dashboard service returned empty data for user {current_user.id}")
            return get_default_dashboard_data()

        # Ensure all required keys exist with defaults
        defaults = get_default_dashboard_data()
        for key, default_value in defaults.items():
            if key not in dashboard_data or dashboard_data[key] is None:
                dashboard_data[key] = default_value

        return dashboard_data

    except Exception as e:
        logger.error(f"Error fetching dashboard data for user {current_user.id}: {str(e)}", exc_info=True)
        # Return default data instead of raising error for better UX
        # This allows the page to render with empty state rather than showing error
        raise HTTPException(
            status_code=500,
            detail="Unable to load dashboard data. Please try again."
        )


@router.get("/morning-report")
async def get_morning_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    MODULE 1: Get Morning Agent Report (Intelligence Briefing)

    Generates an AI-powered daily briefing including:
    - Natural language summary of the day's landscape
    - High-risk alerts (Fatal deadlines, new filings)
    - Actionable insights and next steps
    - Case overview

    This is the "War Room" Intelligence Briefing that appears upon login
    """
    try:
        morning_service = MorningReportService(db)

        report = morning_service.generate_morning_report(
            user_id=str(current_user.id),
            last_login=current_user.last_login
        )

        # Check if service returned an error
        if report and "error" in report:
            logger.warning(f"Morning report service returned error for user {current_user.id}: {report['error']}")
            raise HTTPException(
                status_code=404,
                detail=report["error"]
            )

        # Validate response structure
        if not report:
            logger.warning(f"Morning report service returned empty data for user {current_user.id}")
            return get_default_morning_report()

        # Ensure all required keys exist
        defaults = get_default_morning_report()
        for key, default_value in defaults.items():
            if key not in report or report[key] is None:
                report[key] = default_value

        return report

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        logger.error(f"Error generating morning report for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Unable to load morning briefing. Please try again."
        )
