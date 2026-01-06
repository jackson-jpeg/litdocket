"""Active session tracking for real-time collaboration."""

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models import Base


class ActiveSession(Base):
    """
    Track active WebSocket sessions for presence indicators.

    Shows which users are currently viewing each case.
    """
    __tablename__ = "active_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("Case")
    user = relationship("User")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "case_id": str(self.case_id),
            "user_id": str(self.user_id),
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }
