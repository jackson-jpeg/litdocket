"""Case access control model for multi-user collaboration."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class CaseAccess(Base):
    """
    Track user access permissions to cases.

    Enables multi-user collaboration by defining who can view/edit cases.

    Roles:
    - owner: Full control (can share, edit, delete)
    - editor: Can edit case data and deadlines
    - viewer: Read-only access
    """
    __tablename__ = "case_access"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)  # Nullable for pending invites
    role = Column(String(20), nullable=False, default="viewer")  # owner, editor, viewer
    granted_by = Column(String(36), ForeignKey("users.id"))

    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False)  # False = revoked

    # Invitation tracking (for invites before user accepts)
    invited_email = Column(String(255))  # Email for pending invitations
    invitation_accepted_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case", back_populates="access_grants")
    user = relationship("User", foreign_keys=[user_id], backref="case_access_grants")
    granted_by_user = relationship("User", foreign_keys=[granted_by])

    def to_dict(self):
        """Convert to dictionary for API responses."""
        result = {
            "id": str(self.id),
            "case_id": str(self.case_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "role": self.role,
            "is_active": self.is_active,
            "granted_by": str(self.granted_by) if self.granted_by else None,
            "invited_email": self.invited_email,
            "invitation_accepted_at": self.invitation_accepted_at.isoformat() if self.invitation_accepted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include user details if relationship is loaded
        if self.user:
            result["user"] = {
                "id": str(self.user.id),
                "email": self.user.email,
                "name": self.user.name or self.user.full_name,
            }

        return result

    def can_edit(self) -> bool:
        """Check if this access grant allows editing."""
        return self.is_active and self.role in ('owner', 'editor')

    def can_share(self) -> bool:
        """Check if this access grant allows sharing with others."""
        return self.is_active and self.role == 'owner'
