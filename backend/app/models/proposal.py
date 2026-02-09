"""
Phase 7 Step 11: Proposal Model for AI Safety Rails

This model implements a proposal/approval workflow to prevent AI from writing
directly to the database. AI creates proposals that users must approve before
changes are committed.

Safety Benefits:
- Prevents AI from corrupting data with incorrect actions
- Provides undo capability (reject proposal)
- Creates audit trail of AI actions
- Gives user final control over database changes
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, func, Enum as SQLEnum
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.database import Base
from app.models.enums import ProposalStatus, ProposalActionType


class Proposal(Base):
    """
    Represents an AI-proposed action awaiting user approval.

    Workflow:
    1. AI wants to create/update/delete data
    2. AI calls power tool which creates Proposal (not actual data)
    3. Frontend shows proposal to user with [Approve] [Reject] buttons
    4. User approves → API executes action and marks proposal approved
    5. User rejects → API marks proposal rejected (no action taken)
    """
    __tablename__ = "proposals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # What action is being proposed
    action_type = Column(SQLEnum(ProposalActionType), nullable=False, index=True)
    action_data = Column(JSON, nullable=False)  # The proposed changes (deadline data, case updates, etc.)

    # AI reasoning and context
    ai_reasoning = Column(Text)  # Why AI proposed this action
    ai_message_id = Column(String(36))  # Reference to the chat message that triggered this
    conversation_context = Column(JSON)  # Relevant context from the conversation

    # Approval workflow
    status = Column(SQLEnum(ProposalStatus), nullable=False, default=ProposalStatus.PENDING, index=True)

    # Resolution tracking
    resolved_by = Column(String(36), ForeignKey("users.id"))  # User who approved/rejected
    resolved_at = Column(DateTime(timezone=True))  # When was it resolved
    resolution_notes = Column(Text)  # Optional user notes on approval/rejection

    # Result tracking (for approved proposals)
    executed_successfully = Column(String(10))  # "true"/"false"/"null" (string to avoid DB boolean type issues)
    execution_error = Column(Text)  # Error message if execution failed
    created_resource_id = Column(String(36))  # ID of created deadline/document/etc (if applicable)

    # Preview data (shown to user before approval)
    preview_summary = Column(Text)  # Human-readable summary: "Create Trial Date deadline on June 15, 2026"
    affected_items = Column(JSON)  # List of items that will be affected (e.g., cascaded deadlines)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    case = relationship("Case", back_populates="proposals")
    user = relationship("User", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

    def __repr__(self):
        return f"<Proposal {self.id} - {self.action_type.value} - {self.status.value}>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "action_type": self.action_type.value,
            "action_data": self.action_data,
            "ai_reasoning": self.ai_reasoning,
            "status": self.status.value,
            "preview_summary": self.preview_summary,
            "affected_items": self.affected_items,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "executed_successfully": self.executed_successfully,
            "execution_error": self.execution_error,
            "created_resource_id": self.created_resource_id
        }
