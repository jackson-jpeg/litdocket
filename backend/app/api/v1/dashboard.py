"""
Dashboard API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.v1.documents import get_current_user
from app.services.dashboard_service import dashboard_service

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
