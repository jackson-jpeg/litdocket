"""
Deadline Template Model - User-customizable deadline templates
Trigger templates that users can create and share
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, JSON, func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class DeadlineTemplate(Base):
    """
    Customizable deadline templates for trigger-based generation
    Users can create their own templates or use system templates
    """
    __tablename__ = "deadline_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_by = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Template identification
    name = Column(String(200), nullable=False)
    description = Column(String(500))

    # Jurisdiction and category
    jurisdiction_type = Column(String(20), nullable=False)  # 'federal', 'florida_state', 'florida_local'
    court_type = Column(String(100))  # 'civil', 'criminal', 'appellate', 'bankruptcy', 'family'
    category = Column(String(100))  # 'pretrial', 'discovery', 'appeal', 'trial', etc.

    # Trigger configuration
    trigger_code = Column(String(10))  # $TR, $MC, $PC, $HR, $SD (service date), etc.
    trigger_type = Column(String(50), nullable=False)  # trial_date, service_completed, etc.

    # Template structure (JSON)
    template_json = Column(JSON, nullable=False)
    """
    Structure:
    {
        "dependent_deadlines": [
            {
                "name": "Pretrial Stipulation Due",
                "description": "...",
                "days_from_trigger": -15,
                "priority": "critical",
                "party_responsible": "both",
                "action_required": "...",
                "calculation_method": "calendar_days",
                "add_service_method_days": false,
                "rule_citation": "..."
            },
            ...
        ]
    }
    """

    # Sharing settings
    is_public = Column(Boolean, default=False)  # Can other users see/use this template?
    is_system = Column(Boolean, default=False)  # System-provided template (can't be deleted)

    # Usage statistics
    times_used = Column(String(50), default="0")
    last_used = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", back_populates="deadline_templates")
    chains = relationship("DeadlineChain", back_populates="template")
