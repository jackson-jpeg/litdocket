"""
Notification Service - Handles creation, delivery, and management of notifications
Supports in-app notifications, email alerts, and deadline reminders
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import asyncio

from app.models.notification import (
    Notification,
    NotificationPreferences,
    NotificationType,
    NotificationPriority
)
from app.models.deadline import Deadline
from app.models.case import Case
from app.models.user import User
from app.models.document import Document
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Comprehensive notification service for DocketAssist

    Handles:
    - In-app notifications (bell icon, notification center)
    - Deadline reminders (approaching, overdue, fatal)
    - Document alerts (upload complete, analysis done)
    - Email notifications (critical deadlines, digests)
    """

    def __init__(self, db: Session):
        self.db = db

    # ==========================================
    # NOTIFICATION CREATION
    # ==========================================

    def create_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        case_id: Optional[str] = None,
        deadline_id: Optional[str] = None,
        document_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        send_email: bool = False
    ) -> Notification:
        """
        Create a new notification for a user

        Args:
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            priority: Priority level
            case_id: Related case (optional)
            deadline_id: Related deadline (optional)
            document_id: Related document (optional)
            metadata: Additional context
            action_url: Deep link URL
            action_label: Button text
            send_email: Whether to also send email

        Returns:
            Created Notification object
        """
        # Check user preferences
        prefs = self._get_user_preferences(user_id)

        # Skip if in-app notifications disabled (except fatal)
        if not prefs.in_app_enabled and priority != NotificationPriority.FATAL:
            logger.info(f"Skipping notification for user {user_id} - in-app disabled")
            return None

        # Check type-specific preferences
        if not self._should_send_notification(prefs, notification_type, priority):
            logger.info(f"Skipping notification type {notification_type} for user {user_id}")
            return None

        notification = Notification(
            user_id=user_id,
            type=notification_type,
            priority=priority,
            title=title,
            message=message,
            case_id=case_id,
            deadline_id=deadline_id,
            document_id=document_id,
            extra_data=metadata or {},
            action_url=action_url,
            action_label=action_label
        )

        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        logger.info(f"Created notification {notification.id} for user {user_id}: {title}")

        # Send email if requested and enabled (fire-and-forget background task)
        if send_email and prefs.email_enabled:
            try:
                # Get or create event loop for background task
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._queue_email_notification(notification, prefs))
                else:
                    # If no running loop, run synchronously
                    loop.run_until_complete(self._queue_email_notification(notification, prefs))
            except RuntimeError:
                # No event loop - skip email for now (will be handled by scheduled job)
                logger.debug("No event loop available - email will be sent by scheduled job")

        return notification

    def create_deadline_notification(
        self,
        deadline: Deadline,
        notification_type: NotificationType,
        days_until: int = None
    ) -> Optional[Notification]:
        """
        Create a deadline-related notification

        Args:
            deadline: Deadline object
            notification_type: Type of deadline notification
            days_until: Days until deadline (for reminders)

        Returns:
            Created Notification or None
        """
        # Build notification content based on type
        if notification_type == NotificationType.DEADLINE_FATAL:
            if days_until is not None and days_until <= 0:
                title = f"FATAL DEADLINE OVERDUE: {deadline.title}"
                message = f"The fatal deadline '{deadline.title}' is now OVERDUE. Immediate action required to avoid malpractice liability."
                priority = NotificationPriority.FATAL
            else:
                title = f"FATAL DEADLINE ALERT: {deadline.title}"
                message = f"Fatal deadline '{deadline.title}' is due in {days_until} day(s). This is a malpractice-risk deadline."
                priority = NotificationPriority.FATAL

        elif notification_type == NotificationType.DEADLINE_OVERDUE:
            days_overdue = abs(days_until) if days_until is not None else 0
            title = f"Overdue: {deadline.title}"
            message = f"The deadline '{deadline.title}' is {days_overdue} day(s) overdue. Please address or update status."
            priority = NotificationPriority.URGENT

        elif notification_type == NotificationType.DEADLINE_APPROACHING:
            title = f"Deadline Approaching: {deadline.title}"
            message = f"The deadline '{deadline.title}' is due in {days_until} day(s)."
            priority = NotificationPriority.HIGH if days_until <= 3 else NotificationPriority.MEDIUM

        elif notification_type == NotificationType.DEADLINE_CREATED:
            title = f"New Deadline: {deadline.title}"
            message = f"A new deadline has been created: '{deadline.title}'"
            if deadline.deadline_date:
                message += f" due on {deadline.deadline_date.strftime('%B %d, %Y')}"
            priority = NotificationPriority.MEDIUM

        elif notification_type == NotificationType.DEADLINE_COMPLETED:
            title = f"Deadline Completed: {deadline.title}"
            message = f"The deadline '{deadline.title}' has been marked as completed."
            priority = NotificationPriority.LOW

        else:
            title = f"Deadline Update: {deadline.title}"
            message = f"The deadline '{deadline.title}' has been updated."
            priority = NotificationPriority.MEDIUM

        # Build action URL
        action_url = f"/cases/{deadline.case_id}?tab=deadlines&highlight={deadline.id}"
        action_label = "View Deadline"

        # Build metadata
        metadata = {
            "deadline_date": deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            "days_until": days_until,
            "priority": deadline.priority,
            "calculation_basis": deadline.calculation_basis
        }

        # Determine if email should be sent
        send_email = notification_type in [
            NotificationType.DEADLINE_FATAL,
            NotificationType.DEADLINE_OVERDUE
        ]

        return self.create_notification(
            user_id=deadline.user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            case_id=deadline.case_id,
            deadline_id=str(deadline.id),
            metadata=metadata,
            action_url=action_url,
            action_label=action_label,
            send_email=send_email
        )

    def create_document_notification(
        self,
        document: Document,
        notification_type: NotificationType,
        extra_info: Optional[Dict] = None
    ) -> Optional[Notification]:
        """
        Create a document-related notification

        Args:
            document: Document object
            notification_type: Type of document notification
            extra_info: Additional context (deadlines_found, etc.)

        Returns:
            Created Notification or None
        """
        if notification_type == NotificationType.DOCUMENT_UPLOADED:
            title = f"Document Uploaded: {document.file_name}"
            message = f"Document '{document.file_name}' has been uploaded and is being analyzed."
            priority = NotificationPriority.LOW

        elif notification_type == NotificationType.DOCUMENT_ANALYZED:
            deadlines_count = extra_info.get("deadlines_found", 0) if extra_info else 0
            title = f"Analysis Complete: {document.file_name}"
            message = f"Document '{document.file_name}' has been analyzed."
            if deadlines_count > 0:
                message += f" {deadlines_count} deadline(s) were extracted."
            priority = NotificationPriority.MEDIUM

        elif notification_type == NotificationType.DOCUMENT_FAILED:
            title = f"Analysis Failed: {document.file_name}"
            message = f"Failed to analyze document '{document.file_name}'. Please try re-uploading."
            priority = NotificationPriority.HIGH

        else:
            title = f"Document Update: {document.file_name}"
            message = f"Document '{document.file_name}' has been updated."
            priority = NotificationPriority.LOW

        action_url = f"/cases/{document.case_id}?tab=documents&highlight={document.id}"
        action_label = "View Document"

        return self.create_notification(
            user_id=document.user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            case_id=document.case_id,
            document_id=str(document.id),
            metadata=extra_info,
            action_url=action_url,
            action_label=action_label
        )

    # ==========================================
    # DEADLINE REMINDER ENGINE
    # ==========================================

    def process_deadline_reminders(self, user_id: Optional[str] = None) -> Dict[str, int]:
        """
        Process deadline reminders for all users (or specific user)
        Creates notifications for approaching and overdue deadlines

        Should be called by a scheduled job (cron/celery)

        Args:
            user_id: Optional - process only for this user

        Returns:
            Dict with counts: {"fatal": X, "overdue": Y, "approaching": Z}
        """
        today = date.today()
        counts = {"fatal": 0, "overdue": 0, "approaching": 0}

        # Build base query
        query = self.db.query(Deadline).join(Case).filter(
            Deadline.status == "pending",
            Case.status == "active"
        )

        if user_id:
            query = query.filter(Deadline.user_id == user_id)

        deadlines = query.all()

        for deadline in deadlines:
            if not deadline.deadline_date:
                continue

            days_until = (deadline.deadline_date - today).days
            prefs = self._get_user_preferences(deadline.user_id)

            # Check if we should create a reminder based on preferences
            if deadline.priority == "fatal":
                remind_days = prefs.remind_days_before_fatal or [7, 3, 1, 0]
            else:
                remind_days = prefs.remind_days_before_standard or [3, 1]

            # Skip if not a reminder day (unless overdue)
            if days_until >= 0 and days_until not in remind_days:
                continue

            # Check if we already sent this notification today
            existing = self._check_existing_notification(
                user_id=deadline.user_id,
                deadline_id=str(deadline.id),
                today=today
            )
            if existing:
                continue

            # Create appropriate notification
            if deadline.priority == "fatal":
                self.create_deadline_notification(
                    deadline,
                    NotificationType.DEADLINE_FATAL,
                    days_until
                )
                counts["fatal"] += 1

            elif days_until < 0:
                self.create_deadline_notification(
                    deadline,
                    NotificationType.DEADLINE_OVERDUE,
                    days_until
                )
                counts["overdue"] += 1

            else:
                self.create_deadline_notification(
                    deadline,
                    NotificationType.DEADLINE_APPROACHING,
                    days_until
                )
                counts["approaching"] += 1

        logger.info(f"Processed deadline reminders: {counts}")
        return counts

    # ==========================================
    # NOTIFICATION RETRIEVAL
    # ==========================================

    def get_user_notifications(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False,
        include_dismissed: bool = False
    ) -> List[Dict]:
        """
        Get notifications for a user

        Args:
            user_id: User ID
            limit: Max notifications to return
            offset: Pagination offset
            unread_only: Only return unread notifications
            include_dismissed: Include dismissed notifications

        Returns:
            List of notification dicts
        """
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id
        )

        if unread_only:
            query = query.filter(Notification.is_read == False)

        if not include_dismissed:
            query = query.filter(Notification.is_dismissed == False)

        # Filter out expired notifications
        query = query.filter(
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.now()
            )
        )

        notifications = query.order_by(
            Notification.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [n.to_dict() for n in notifications]

    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for a user"""
        return self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_dismissed == False
        ).count()

    # ==========================================
    # NOTIFICATION ACTIONS
    # ==========================================

    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if not notification:
            return False

        notification.is_read = True
        notification.read_at = datetime.now()
        self.db.commit()
        return True

    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        count = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            "is_read": True,
            "read_at": datetime.now()
        })
        self.db.commit()
        return count

    def dismiss_notification(self, notification_id: str, user_id: str) -> bool:
        """Dismiss a notification"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if not notification:
            return False

        notification.is_dismissed = True
        notification.dismissed_at = datetime.now()
        self.db.commit()
        return True

    def delete_old_notifications(self, days_old: int = 30) -> int:
        """Delete notifications older than specified days"""
        cutoff = datetime.now() - timedelta(days=days_old)
        count = self.db.query(Notification).filter(
            Notification.created_at < cutoff,
            Notification.is_read == True
        ).delete()
        self.db.commit()
        return count

    # ==========================================
    # PREFERENCES MANAGEMENT
    # ==========================================

    def get_user_preferences(self, user_id: str) -> Dict:
        """Get notification preferences for a user"""
        prefs = self._get_user_preferences(user_id)
        return prefs.to_dict()

    def update_user_preferences(self, user_id: str, updates: Dict) -> Dict:
        """Update notification preferences for a user"""
        prefs = self._get_user_preferences(user_id)

        # Update allowed fields
        allowed_fields = [
            "in_app_enabled", "in_app_deadline_reminders", "in_app_document_updates",
            "in_app_case_updates", "in_app_ai_insights", "email_enabled",
            "email_fatal_deadlines", "email_deadline_reminders", "email_daily_digest",
            "email_weekly_digest", "remind_days_before_fatal", "remind_days_before_standard",
            "quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end"
        ]

        for field in allowed_fields:
            if field in updates:
                setattr(prefs, field, updates[field])

        self.db.commit()
        self.db.refresh(prefs)
        return prefs.to_dict()

    # ==========================================
    # PRIVATE HELPER METHODS
    # ==========================================

    def _get_user_preferences(self, user_id: str) -> NotificationPreferences:
        """Get or create notification preferences for user"""
        prefs = self.db.query(NotificationPreferences).filter(
            NotificationPreferences.user_id == user_id
        ).first()

        if not prefs:
            prefs = NotificationPreferences(user_id=user_id)
            self.db.add(prefs)
            self.db.commit()
            self.db.refresh(prefs)

        return prefs

    def _should_send_notification(
        self,
        prefs: NotificationPreferences,
        notification_type: NotificationType,
        priority: NotificationPriority
    ) -> bool:
        """Check if notification should be sent based on preferences"""
        # Always send fatal priority
        if priority == NotificationPriority.FATAL:
            return True

        # Check type-specific preferences
        if notification_type in [
            NotificationType.DEADLINE_APPROACHING,
            NotificationType.DEADLINE_OVERDUE,
            NotificationType.DEADLINE_FATAL
        ]:
            return prefs.in_app_deadline_reminders

        if notification_type in [
            NotificationType.DOCUMENT_UPLOADED,
            NotificationType.DOCUMENT_ANALYZED,
            NotificationType.DOCUMENT_FAILED
        ]:
            return prefs.in_app_document_updates

        if notification_type in [
            NotificationType.CASE_CREATED,
            NotificationType.CASE_UPDATED
        ]:
            return prefs.in_app_case_updates

        if notification_type == NotificationType.AI_INSIGHT:
            return prefs.in_app_ai_insights

        return True  # Default to sending

    def _check_existing_notification(
        self,
        user_id: str,
        deadline_id: str,
        today: date
    ) -> bool:
        """Check if a notification was already sent today for this deadline"""
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())

        existing = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.deadline_id == deadline_id,
            Notification.created_at.between(start_of_day, end_of_day)
        ).first()

        return existing is not None

    async def _queue_email_notification(
        self,
        notification: Notification,
        prefs: NotificationPreferences
    ) -> None:
        """
        Send email notification via email service (SendGrid).

        Checks user preferences before sending.
        """
        # Check if email should be sent based on type
        if notification.type == NotificationType.DEADLINE_FATAL and not prefs.email_fatal_deadlines:
            logger.debug(f"Skipping fatal deadline email - user has email_fatal_deadlines disabled")
            return

        if notification.type in [
            NotificationType.DEADLINE_APPROACHING,
            NotificationType.DEADLINE_OVERDUE
        ] and not prefs.email_deadline_reminders:
            logger.debug(f"Skipping deadline reminder email - user has email_deadline_reminders disabled")
            return

        # Get user info for email
        user = self.db.query(User).filter(User.id == notification.user_id).first()
        if not user or not user.email:
            logger.warning(f"Cannot send email - user {notification.user_id} not found or no email")
            return

        user_name = user.name or user.full_name or user.email.split('@')[0]

        # Get case info if available
        case = None
        if notification.case_id:
            case = self.db.query(Case).filter(Case.id == notification.case_id).first()

        # Build action URL (use production URL if available)
        from app.config import settings
        import os
        base_url = os.getenv("FRONTEND_URL", "https://litdocket.com")
        action_url = f"{base_url}{notification.action_url}" if notification.action_url else base_url

        # Send email based on notification type
        email_sent = False
        try:
            if notification.type == NotificationType.DEADLINE_FATAL:
                # Get deadline info
                deadline = None
                if notification.deadline_id:
                    deadline = self.db.query(Deadline).filter(Deadline.id == notification.deadline_id).first()

                days_until = notification.extra_data.get("days_until", 0) if notification.extra_data else 0
                deadline_date = notification.extra_data.get("deadline_date", "Unknown") if notification.extra_data else "Unknown"

                email_sent = await email_service.send_fatal_deadline_alert(
                    to_email=user.email,
                    user_name=user_name,
                    deadline_title=deadline.title if deadline else notification.title,
                    deadline_date=deadline_date,
                    days_until=days_until,
                    case_number=case.case_number if case else "N/A",
                    case_title=case.title if case else "Unknown Case",
                    action_url=action_url
                )

            elif notification.type in [NotificationType.DEADLINE_APPROACHING, NotificationType.DEADLINE_OVERDUE]:
                days_until = notification.extra_data.get("days_until", 0) if notification.extra_data else 0
                deadline_date = notification.extra_data.get("deadline_date", "Unknown") if notification.extra_data else "Unknown"
                priority = notification.extra_data.get("priority", "standard") if notification.extra_data else "standard"

                email_sent = await email_service.send_deadline_reminder(
                    to_email=user.email,
                    user_name=user_name,
                    deadline_title=notification.title.replace("Deadline Approaching: ", "").replace("Overdue: ", ""),
                    deadline_date=deadline_date,
                    days_until=days_until,
                    case_number=case.case_number if case else "N/A",
                    priority=priority,
                    action_url=action_url
                )

            if email_sent:
                notification.email_sent = True
                notification.email_sent_at = datetime.now()
                self.db.commit()
                logger.info(f"Email sent for notification {notification.id} to {user.email}")
            else:
                logger.warning(f"Email not sent for notification {notification.id}")

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
