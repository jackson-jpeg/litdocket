from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, func, JSON
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    context_documents = Column(JSON)  # Array of document IDs used for RAG
    context_rules = Column(JSON)  # Array of rule citations used
    tokens_used = Column(Integer)
    model_used = Column(String(100))  # claude-sonnet-4, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case = relationship("Case", back_populates="chat_messages")
    user = relationship("User", back_populates="chat_messages")
