"""
Document Tag Model - For organizing and categorizing documents
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Tag(Base):
    """User-defined tags for document organization"""
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(20), default="#3b82f6")  # Default blue
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint: user can't have duplicate tag names
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_tag_name'),
    )

    # Relationships
    user = relationship("User", back_populates="tags")
    document_tags = relationship("DocumentTag", back_populates="tag", cascade="all, delete-orphan")


class DocumentTag(Base):
    """Junction table for document-tag many-to-many relationship"""
    __tablename__ = "document_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint: document can't have same tag twice
    __table_args__ = (
        UniqueConstraint('document_id', 'tag_id', name='uq_document_tag'),
    )

    # Relationships
    document = relationship("Document", back_populates="tags")
    tag = relationship("Tag", back_populates="document_tags")
