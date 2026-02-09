"""
Watchtower Models - Change Detection and Monitoring

Tracks content hashes of court websites to detect rule changes
without expensive full scrapes.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, func, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class WatchtowerHash(Base):
    """
    Content hashes for watchtower change detection.

    Stores SHA-256 hashes of court website content to detect changes.
    Used by the watchtower service to avoid unnecessary full scrapes.
    """
    __tablename__ = "watchtower_hashes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    jurisdiction_id = Column(String(36), ForeignKey("jurisdictions.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)  # The URL that was checked
    content_hash = Column(String(64), nullable=False)  # SHA-256 hash (first 16 chars)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    jurisdiction = relationship("Jurisdiction", foreign_keys=[jurisdiction_id])

    # Constraints
    __table_args__ = (
        UniqueConstraint('jurisdiction_id', 'url', name='unique_watchtower_hash'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "jurisdiction_id": self.jurisdiction_id,
            "url": self.url,
            "content_hash": self.content_hash,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
