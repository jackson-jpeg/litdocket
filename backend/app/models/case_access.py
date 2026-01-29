"""Case access control model for multi-user collaboration."""

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models import Base


def generate_uuid():
    return str(uuid.uuid4())


class CaseAccess(Base):
    """
    Track user access permissions to cases.

    Enables multi-user collaboration by defining who can view/edit cases.
    """
    __tablename__ = "case_access"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")  # owner, editor, viewer
    granted_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case = relationship("Case", back_populates="access_grants")
    user = relationship("User", foreign_keys=[user_id])
    granted_by_user = relationship("User", foreign_keys=[granted_by])

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "case_id": str(self.case_id),
            "user_id": str(self.user_id),
            "role": self.role,
            "granted_by": str(self.granted_by) if self.granted_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
