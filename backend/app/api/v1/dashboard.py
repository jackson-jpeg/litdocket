"""
Dashboard API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.dashboard_service import dashboard_service
from app.services.morning_report_service import MorningReportService

router = APIRouter()


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
    dashboard_data = await dashboard_service.get_dashboard_data(
        user_id=current_user.id,
        db=db
    )

    return dashboard_data


@router.get("/morning-report")
def get_morning_report(
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

    morning_service = MorningReportService(db)

    report = morning_service.generate_morning_report(
        user_id=str(current_user.id),
        last_login=current_user.last_login
    )

    return report
