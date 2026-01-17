"""
Document Embeddings Model - For RAG (Retrieval Augmented Generation)
Stores vector embeddings of document chunks for semantic search

Supports two modes:
1. pgvector (PostgreSQL) - Uses native Vector type with HNSW index for fast similarity search
2. JSON fallback (SQLite/PostgreSQL without pgvector) - Stores as JSON array with manual similarity

Detection is automatic based on database configuration.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, JSON, Index, event
from sqlalchemy.orm import relationship
from sqlalchemy.engine import Engine
import uuid
import os
import logging

from app.database import Base

logger = logging.getLogger(__name__)

# Try to import pgvector
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
    logger.info("pgvector extension available")
except ImportError:
    PGVECTOR_AVAILABLE = False
    logger.info("pgvector not installed - using JSON fallback for embeddings")


def is_postgres_database():
    """Check if we're using PostgreSQL"""
    db_url = os.getenv("DATABASE_URL", "")
    return "postgresql" in db_url.lower() or "postgres" in db_url.lower()


# Determine embedding column type based on environment
# Use pgvector Vector if PostgreSQL + pgvector available
USE_PGVECTOR = PGVECTOR_AVAILABLE and is_postgres_database()

# Embedding dimensions (OpenAI text-embedding-3-small = 1536)
EMBEDDING_DIMENSIONS = 1536


class DocumentEmbedding(Base):
    """
    Vector embeddings for document chunks - enables semantic search

    When PostgreSQL + pgvector is available:
    - Uses native Vector(1536) type
    - Creates HNSW index for fast approximate nearest neighbor search
    - Uses pgvector's <=> operator for cosine distance

    When using SQLite or PostgreSQL without pgvector:
    - Stores embedding as JSON array
    - Uses manual cosine similarity calculation in Python
    """
    __tablename__ = "document_embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Chunking information
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document
    # chunk_page = Column(Integer)  # REMOVED: Column doesn't exist in production DB
    # Page numbers now stored in chunk_metadata JSON: {"page": 3, ...}

    # Embedding vector - pgvector Vector or JSON depending on environment
    # pgvector: Uses Vector(1536) with HNSW index for O(log n) similarity search
    # JSON: Uses JSON array with O(n) similarity search (fine for < 100k embeddings)
    if USE_PGVECTOR:
        embedding = Column(Vector(EMBEDDING_DIMENSIONS))
    else:
        embedding = Column(JSON)  # Array of floats as JSON

    # Metadata about the chunk
    chunk_metadata = Column(JSON)  # {document_type, section, keywords, etc.}

    # Relationships
    case = relationship("Case", back_populates="document_embeddings")
    document = relationship("Document", back_populates="embeddings")

    # Create indexes
    __table_args__ = (
        Index('idx_case_document', 'case_id', 'document_id'),
        # Note: HNSW index for pgvector is created via migration/SQL
        # CREATE INDEX ON document_embeddings USING hnsw (embedding vector_cosine_ops);
    )

    @classmethod
    def using_pgvector(cls) -> bool:
        """Check if this model is using pgvector"""
        return USE_PGVECTOR


# SQL to create pgvector extension and HNSW index (run manually on PostgreSQL)
PGVECTOR_SETUP_SQL = """
-- Enable pgvector extension (requires superuser or extension granted)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create HNSW index for fast approximate nearest neighbor search
-- This makes similarity queries O(log n) instead of O(n)
CREATE INDEX IF NOT EXISTS idx_embedding_hnsw
ON document_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Alternative: IVFFlat index (faster to build, slightly less accurate)
-- CREATE INDEX IF NOT EXISTS idx_embedding_ivfflat
-- ON document_embeddings
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);
"""
