from sqlalchemy import Column, String, BigInteger, Date, DateTime, ForeignKey, Text, func, JSON
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(50))  # pdf, jpg, png
    file_size_bytes = Column(BigInteger)
    storage_path = Column(String(1000), nullable=False)  # S3 path
    storage_url = Column(String(1000))  # Presigned URL
    document_type = Column(String(100))  # motion, order, notice, etc.
    filing_date = Column(Date)
    received_date = Column(Date)
    analysis_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    extracted_text = Column(Text)
    ai_summary = Column(Text)
    extracted_metadata = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    case = relationship("Case", back_populates="documents")
    user = relationship("User", back_populates="documents")
    deadlines = relationship("Deadline", back_populates="document")
