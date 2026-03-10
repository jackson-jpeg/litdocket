from sqlalchemy import Column, String, Date, DateTime, ForeignKey, func, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.event import listens_for
import uuid

from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    case_number = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    court = Column(String(255))
    judge = Column(String(255))
    status = Column(String(50), default="active")
    case_type = Column(String(100))  # civil, criminal, appellate
    jurisdiction = Column(String(100))  # state, federal
    district = Column(String(100))  # Northern, Middle, Southern
    circuit = Column(String(50))  # 1st-20th for circuit courts
    filing_date = Column(Date)
    parties = Column(JSON)  # Array of party objects
    case_metadata = Column(JSON)  # Flexible metadata storage
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="cases")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="case", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="case", cascade="all, delete-orphan")
    calendar_events = relationship("CalendarEvent", back_populates="case", cascade="all, delete-orphan")

    # V3.0 Enhancements - RAG and dependency tracking
    document_embeddings = relationship("DocumentEmbedding", back_populates="case", cascade="all, delete-orphan")
    deadline_chains = relationship("DeadlineChain", back_populates="case", cascade="all, delete-orphan")
    ai_feedback = relationship("AIExtractionFeedback", back_populates="case", cascade="all, delete-orphan")

    # Phase 3 - Multi-user collaboration
    access_grants = relationship("CaseAccess", back_populates="case", cascade="all, delete-orphan")

    # AI Agent analytics
    agent_analytics = relationship("AgentAnalytics", back_populates="case", cascade="all, delete-orphan")

    # Phase 7 Step 11: AI Proposals for Safety Rails
    proposals = relationship("Proposal", back_populates="case", cascade="all, delete-orphan")

    # Unique constraint on user_id + case_number
    __table_args__ = (
        UniqueConstraint('user_id', 'case_number', name='uq_user_case_number'),
    )


@listens_for(Case, 'before_update')
def cascade_case_soft_delete(mapper, connection, target):
    """Cascade soft-delete to related models when a case is soft-deleted."""
    # Check if this is a soft-delete operation (deleted_at is being set)
    from sqlalchemy import inspect
    state = inspect(target)
    
    # Get the deleted_at attribute history
    deleted_at_history = state.attrs.get('deleted_at')
    if deleted_at_history is None:
        return
        
    # Check if deleted_at is being set for the first time (soft-delete)
    if deleted_at_history.history.has_changes() and deleted_at_history.value is not None:
        # Import here to avoid circular imports
        from app.models.deadline import Deadline
        from app.models.document import Document
        from app.models.chat_message import ChatMessage
        
        # Cascade soft-delete to related models
        connection.execute(
            Deadline.__table__.update().where(
                Deadline.__table__.c.case_id == target.id
            ).values(deleted_at=func.now())
        )
        
        connection.execute(
            Document.__table__.update().where(
                Document.__table__.c.case_id == target.id
            ).values(deleted_at=func.now())
        )
        
        connection.execute(
            ChatMessage.__table__.update().where(
                ChatMessage.__table__.c.case_id == target.id
            ).values(deleted_at=func.now())
        )
