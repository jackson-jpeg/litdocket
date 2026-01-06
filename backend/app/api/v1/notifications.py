"""
Notification API Routes - Handles notification retrieval, actions, and preferences
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ==========================================
# PYDANTIC MODELS
# ==========================================

class NotificationResponse(BaseModel):
    id: str
    type: str
    priority: str
    title: str
    message: str
    case_id: Optional[str] = None
    deadline_id: Optional[str] = None
    document_id: Optional[str] = None
    metadata: dict = Field(default={}, validation_alias="extra_data")  # Maps from SQLAlchemy extra_data
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    is_read: bool
    read_at: Optional[str] = None
    is_dismissed: bool = False
    created_at: str

    class Config:
        from_attributes = True
        populate_by_name = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    unread_count: int
    total: int


class NotificationPreferencesResponse(BaseModel):
    in_app_enabled: bool
    in_app_deadline_reminders: bool
    in_app_document_updates: bool
    in_app_case_updates: bool
    in_app_ai_insights: bool
    email_enabled: bool
    email_fatal_deadlines: bool
    email_deadline_reminders: bool
    email_daily_digest: bool
    email_weekly_digest: bool
    remind_days_before_fatal: List[int]
    remind_days_before_standard: List[int]
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str


class UpdatePreferencesRequest(BaseModel):
    in_app_enabled: Optional[bool] = None
    in_app_deadline_reminders: Optional[bool] = None
    in_app_document_updates: Optional[bool] = None
    in_app_case_updates: Optional[bool] = None
    in_app_ai_insights: Optional[bool] = None
    email_enabled: Optional[bool] = None
    email_fatal_deadlines: Optional[bool] = None
    email_deadline_reminders: Optional[bool] = None
    email_daily_digest: Optional[bool] = None
    email_weekly_digest: Optional[bool] = None
    remind_days_before_fatal: Optional[List[int]] = None
    remind_days_before_standard: Optional[List[int]] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


# ==========================================
# NOTIFICATION ENDPOINTS
# ==========================================

@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get notifications for the current user

    Returns paginated list of notifications with unread count
    """
    service = NotificationService(db)

    notifications = service.get_user_notifications(
        user_id=str(current_user.id),
        limit=limit,
        offset=offset,
        unread_only=unread_only
    )

    unread_count = service.get_unread_count(str(current_user.id))

    return NotificationListResponse(
        notifications=notifications,
        unread_count=unread_count,
        total=len(notifications)
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications"""
    service = NotificationService(db)
    count = service.get_unread_count(str(current_user.id))
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a specific notification as read"""
    service = NotificationService(db)
    success = service.mark_as_read(notification_id, str(current_user.id))

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"success": True, "message": "Notification marked as read"}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    service = NotificationService(db)
    count = service.mark_all_as_read(str(current_user.id))
    return {"success": True, "count": count, "message": f"Marked {count} notifications as read"}


@router.post("/{notification_id}/dismiss")
async def dismiss_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dismiss a notification (hide from list)"""
    service = NotificationService(db)
    success = service.dismiss_notification(notification_id, str(current_user.id))

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"success": True, "message": "Notification dismissed"}


# ==========================================
# PREFERENCES ENDPOINTS
# ==========================================

@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification preferences for current user"""
    service = NotificationService(db)
    prefs = service.get_user_preferences(str(current_user.id))
    return prefs


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    request: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update notification preferences"""
    service = NotificationService(db)

    # Convert request to dict, excluding None values
    updates = {k: v for k, v in request.model_dump().items() if v is not None}

    prefs = service.update_user_preferences(str(current_user.id), updates)
    return prefs


# ==========================================
# ADMIN/SYSTEM ENDPOINTS
# ==========================================

@router.post("/process-reminders")
async def process_deadline_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger deadline reminder processing

    In production, this would be called by a scheduled job.
    For testing, can be triggered manually.
    """
    # Only allow admins or the user to trigger for themselves
    service = NotificationService(db)
    counts = service.process_deadline_reminders(user_id=str(current_user.id))

    return {
        "success": True,
        "message": "Processed deadline reminders",
        "counts": counts
    }
