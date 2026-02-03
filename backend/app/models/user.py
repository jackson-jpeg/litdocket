from sqlalchemy import Column, String, DateTime, JSON, func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Firebase Authentication
    firebase_uid = Column(String(255), unique=True, nullable=True, index=True)  # Firebase user ID

    # Basic Info
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable - Firebase handles auth
    name = Column(String(255))  # Display name
    full_name = Column(String(255))  # Kept for backward compatibility

    # Professional Info
    firm_name = Column(String(255))
    role = Column(String(50), default="attorney")  # attorney, paralegal, assistant, litdocket_admin
    jurisdictions = Column(JSON, default=list)  # List of jurisdiction codes ["FL", "GA", etc.]

    # Account Settings
    subscription_tier = Column(String(50), default="free")
    subscription_status = Column(String(50), default="active")
    preferred_ai_model = Column(String(50), default="claude-sonnet-4")
    settings = Column(JSON, default=dict)  # User preferences (notifications, calendar, etc.)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    cases = relationship("Case", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    # Specify foreign_keys to resolve ambiguity (user_id vs override_user_id)
    deadlines = relationship("Deadline", back_populates="user", cascade="all, delete-orphan", foreign_keys="Deadline.user_id")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="user", cascade="all, delete-orphan")

    # V3.0 Enhancements - Learning and audit trail
    deadline_history_entries = relationship("DeadlineHistory", back_populates="user", cascade="all, delete-orphan")
    ai_feedback = relationship("AIExtractionFeedback", back_populates="user", cascade="all, delete-orphan")
    deadline_templates = relationship("DeadlineTemplate", back_populates="creator", cascade="all, delete-orphan")

    # Document tagging
    tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")

    # Case templates
    case_templates = relationship("CaseTemplate", back_populates="user", cascade="all, delete-orphan")

    # NOTE: created_rules relationship removed - migration 009 (dynamic_rules_engine)
    # was never fully integrated. Current RuleTemplate model (migration 001) doesn't
    # have created_by column. User-created rules feature is not currently active.

    # AI Agent preferences
    agent_preferences = relationship("UserAgentPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    agent_analytics = relationship("AgentAnalytics", back_populates="user", cascade="all, delete-orphan")
