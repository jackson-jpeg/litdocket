"""
Document Embeddings Model - For RAG (Retrieval Augmented Generation)
Stores vector embeddings of document chunks for semantic search
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON, Index
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class DocumentEmbedding(Base):
    """Vector embeddings for document chunks - enables semantic search"""
    __tablename__ = "document_embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Chunking information
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    chunk_page = Column(Integer)  # Which page this chunk came from

    # Embedding vector stored as JSON array (compatible with SQLite)
    # OpenAI text-embedding-3-small = 1536 dimensions
    # Claude embeddings = 768 dimensions
    # TODO: Switch to pgvector.Vector type when using PostgreSQL in production
    embedding = Column(JSON)  # Array of floats

    # Metadata about the chunk
    chunk_metadata = Column(JSON)  # {document_type, section, keywords, etc.}

    # Relationships
    case = relationship("Case", back_populates="document_embeddings")
    document = relationship("Document", back_populates="embeddings")

    # Create indexes
    __table_args__ = (
        Index('idx_case_document', 'case_id', 'document_id'),
    )
