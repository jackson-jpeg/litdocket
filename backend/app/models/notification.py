"""
Notification Model - In-app notifications and alerts for users
"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum, JSON, func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.database import Base


class NotificationType(str, enum.Enum):
    """Types of notifications"""
    # Deadline-related
    DEADLINE_APPROACHING = "deadline_approaching"  # Deadline is coming up
    DEADLINE_OVERDUE = "deadline_overdue"  # Deadline is past due
    DEADLINE_FATAL = "deadline_fatal"  # Fatal deadline alert
    DEADLINE_COMPLETED = "deadline_completed"  # Deadline was marked complete
    DEADLINE_CREATED = "deadline_created"  # New deadline created
    DEADLINE_MODIFIED = "deadline_modified"  # Deadline was modified

    # Document-related
    DOCUMENT_UPLOADED = "document_uploaded"  # New document uploaded
    DOCUMENT_ANALYZED = "document_analyzed"  # Document analysis complete
    DOCUMENT_FAILED = "document_failed"  # Document analysis failed

    # Case-related
    CASE_CREATED = "case_created"  # New case created
    CASE_UPDATED = "case_updated"  # Case was updated

    # System
    SYSTEM_ALERT = "system_alert"  # System-wide alerts
    AI_INSIGHT = "ai_insight"  # AI-generated insight

    # Collaboration (future)
    USER_MENTIONED = "user_mentioned"  # User was mentioned
    CASE_SHARED = "case_shared"  # Case was shared with user


class NotificationPriority(str, enum.Enum):
    """Priority levels for notifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    FATAL = "fatal"  # Malpractice-risk level


class Notification(Base):
    """
    In-app notification model
    Stores notifications for user alerts, deadline reminders, document updates, etc.
    """
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Recipient
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Notification content
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    priority = Column(SQLEnum(NotificationPriority), default=NotificationPriority.MEDIUM, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Related entities (optional - for navigation)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)

    # Additional data (note: 'metadata' is reserved by SQLAlchemy)
    extra_data = Column(JSON, default=dict)  # Extra context (days_until, deadline_date, etc.)
    action_url = Column(String(500))  # Deep link to relevant page
    action_label = Column(String(100))  # Button text ("View Deadline", "Open Case", etc.)

    # Status tracking
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True))
    is_dismissed = Column(Boolean, default=False, index=True)
    dismissed_at = Column(DateTime(timezone=True))

    # Email notification tracking
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))  # Optional expiration

    # Relationships
    user = relationship("User", backref="notifications")
    case = relationship("Case", backref="notifications")
    deadline = relationship("Deadline", backref="notifications")
    document = relationship("Document", backref="notifications")

    def to_dict(self):
        """Convert notification to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value if self.type else None,
            "priority": self.priority.value if self.priority else None,
            "title": self.title,
            "message": self.message,
            "case_id": self.case_id,
            "deadline_id": self.deadline_id,
            "document_id": self.document_id,
            "extra_data": self.extra_data or {},
            "action_url": self.action_url,
            "action_label": self.action_label,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "is_dismissed": self.is_dismissed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NotificationPreferences(Base):
    """
    User notification preferences
    Controls what notifications a user receives and how
    """
    __tablename__ = "notification_preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # In-app notifications
    in_app_enabled = Column(Boolean, default=True)
    in_app_deadline_reminders = Column(Boolean, default=True)
    in_app_document_updates = Column(Boolean, default=True)
    in_app_case_updates = Column(Boolean, default=True)
    in_app_ai_insights = Column(Boolean, default=True)

    # Email notifications
    email_enabled = Column(Boolean, default=True)
    email_fatal_deadlines = Column(Boolean, default=True)  # ALWAYS ON for malpractice protection
    email_deadline_reminders = Column(Boolean, default=True)
    email_daily_digest = Column(Boolean, default=False)  # Daily summary email
    email_weekly_digest = Column(Boolean, default=True)  # Weekly summary email

    # Reminder timing
    remind_days_before_fatal = Column(JSON, default=lambda: [7, 3, 1, 0])  # Days before fatal deadline to remind
    remind_days_before_standard = Column(JSON, default=lambda: [3, 1])  # Days before standard deadline

    # Quiet hours (don't send non-urgent notifications)
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String(5), default="22:00")  # HH:MM format
    quiet_hours_end = Column(String(5), default="07:00")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", backref="notification_preferences")

    def to_dict(self):
        """Convert preferences to dictionary"""
        return {
            "in_app_enabled": self.in_app_enabled,
            "in_app_deadline_reminders": self.in_app_deadline_reminders,
            "in_app_document_updates": self.in_app_document_updates,
            "in_app_case_updates": self.in_app_case_updates,
            "in_app_ai_insights": self.in_app_ai_insights,
            "email_enabled": self.email_enabled,
            "email_fatal_deadlines": self.email_fatal_deadlines,
            "email_deadline_reminders": self.email_deadline_reminders,
            "email_daily_digest": self.email_daily_digest,
            "email_weekly_digest": self.email_weekly_digest,
            "remind_days_before_fatal": self.remind_days_before_fatal,
            "remind_days_before_standard": self.remind_days_before_standard,
            "quiet_hours_enabled": self.quiet_hours_enabled,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
        }
