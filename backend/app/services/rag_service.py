"""
RAG Service - Retrieval Augmented Generation
Handles document embeddings, semantic search, and context retrieval for chat
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import json
import numpy as np
from anthropic import Anthropic
import logging

from app.models.document import Document
from app.models.document_embedding import DocumentEmbedding
from app.models.deadline import Deadline
from app.models.case import Case
from app.config import settings

logger = logging.getLogger(__name__)

# Try to import OpenAI, but make it optional
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. Using fallback embeddings.")


class RAGService:
    """
    RAG (Retrieval Augmented Generation) Service

    Provides semantic search over case documents and intelligent context retrieval
    for the AI chat assistant.

    Uses OpenAI text-embedding-3-small for production embeddings,
    with fallback to simple TF-IDF-style embeddings if OpenAI is not available.
    """

    def __init__(self):
        self.anthropic_client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY.strip() if settings.ANTHROPIC_API_KEY else None
        )
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks

        # Initialize OpenAI client if available and configured
        self.openai_client = None
        self.use_openai_embeddings = False

        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(
                    api_key=settings.OPENAI_API_KEY.strip() if settings.OPENAI_API_KEY else None
                )
                self.use_openai_embeddings = True
                logger.info("OpenAI embeddings enabled (text-embedding-3-small)")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.info("Using fallback embeddings (OpenAI not configured)")

    def chunk_document(self, text: str, document_id: str, document_type: str = None) -> List[Dict]:
        """
        Split document into overlapping chunks for embedding

        Args:
            text: Full document text
            document_id: Document ID
            document_type: Type of document (motion, order, etc.)

        Returns:
            List of chunks with metadata
        """
        chunks = []
        text_length = len(text)

        # Simple chunking by character count with overlap
        start = 0
        chunk_index = 0

        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunk_text = text[start:end]

            # Try to break at sentence boundary if possible
            if end < text_length:
                # Look for last period, question mark, or exclamation mark
                last_period = max(
                    chunk_text.rfind('.'),
                    chunk_text.rfind('?'),
                    chunk_text.rfind('!')
                )
                if last_period > self.chunk_size * 0.7:  # Only if reasonably close to end
                    end = start + last_period + 1
                    chunk_text = text[start:end]

            chunks.append({
                'document_id': document_id,
                'chunk_index': chunk_index,
                'chunk_text': chunk_text.strip(),
                'chunk_metadata': {
                    'document_type': document_type,
                    'start_char': start,
                    'end_char': end,
                    'length': len(chunk_text)
                }
            })

            chunk_index += 1
            start = end - self.chunk_overlap  # Overlap for context

        return chunks

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text chunks.

        Uses OpenAI text-embedding-3-small when configured (1536 dimensions),
        falls back to simple hash-based embeddings otherwise (768 dimensions).

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (as lists of floats)
        """
        if self.use_openai_embeddings and self.openai_client:
            return self._generate_openai_embeddings(texts)
        else:
            return self._generate_fallback_embeddings(texts)

    def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings using OpenAI text-embedding-3-small model.

        This is the production-quality embedding method.
        Model: text-embedding-3-small (1536 dimensions, high quality, low cost)
        """
        embeddings = []

        # Process in batches to avoid rate limits (max 8191 tokens per request)
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                response = self.openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch,
                    encoding_format="float"
                )

                for item in response.data:
                    embeddings.append(item.embedding)

                logger.debug(f"Generated {len(batch)} embeddings via OpenAI")

            except Exception as e:
                logger.error(f"OpenAI embedding error: {e}")
                # Fallback to simple embeddings for this batch
                fallback = self._generate_fallback_embeddings(batch)
                embeddings.extend(fallback)

        return embeddings

    def _generate_fallback_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate simple hash-based embeddings as fallback.

        This is a placeholder for when OpenAI is not available.
        Uses a simple word-hashing approach (768 dimensions).
        """
        embeddings = []
        for text in texts:
            words = text.lower().split()

            # Create a simple 768-dimensional embedding based on text features
            embedding = [0.0] * 768

            # Hash words into embedding dimensions
            for word in words:
                idx = hash(word) % 768
                embedding[idx] += 1.0

            # Normalize
            magnitude = sum(x ** 2 for x in embedding) ** 0.5
            if magnitude > 0:
                embedding = [x / magnitude for x in embedding]

            embeddings.append(embedding)

        return embeddings

    async def embed_document(
        self,
        document: Document,
        case_id: str,
        db: Session
    ) -> int:
        """
        Chunk and embed a document, store in database

        Args:
            document: Document object
            case_id: Case ID
            db: Database session

        Returns:
            Number of chunks created
        """
        # Skip if no text
        if not document.extracted_text:
            return 0

        # Chunk the document
        chunks = self.chunk_document(
            text=document.extracted_text,
            document_id=str(document.id),
            document_type=document.document_type
        )

        # Generate embeddings for all chunks
        chunk_texts = [chunk['chunk_text'] for chunk in chunks]
        embeddings = self.generate_embeddings(chunk_texts)

        # Store in database
        for chunk, embedding in zip(chunks, embeddings):
            doc_embedding = DocumentEmbedding(
                case_id=case_id,
                document_id=chunk['document_id'],
                chunk_text=chunk['chunk_text'],
                chunk_index=chunk['chunk_index'],
                embedding=embedding,  # Stored as JSON array
                chunk_metadata=chunk['chunk_metadata']
            )
            db.add(doc_embedding)

        db.commit()
        return len(chunks)

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a ** 2 for a in vec1) ** 0.5
        magnitude2 = sum(b ** 2 for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def semantic_search(
        self,
        query: str,
        case_id: str,
        db: Session,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search over case documents

        Uses pgvector's native similarity search when available (O(log n) with HNSW index),
        falls back to manual cosine similarity calculation (O(n)) for SQLite/non-pgvector.

        Args:
            query: Search query
            case_id: Case ID to search within
            db: Database session
            top_k: Number of results to return

        Returns:
            List of relevant document chunks with similarity scores
        """
        # Generate query embedding
        query_embeddings = self.generate_embeddings([query])
        query_embedding = query_embeddings[0]

        # Check if pgvector is available for optimized search
        if DocumentEmbedding.using_pgvector():
            return await self._pgvector_semantic_search(query_embedding, case_id, db, top_k)
        else:
            return await self._fallback_semantic_search(query_embedding, case_id, db, top_k)

    async def _pgvector_semantic_search(
        self,
        query_embedding: List[float],
        case_id: str,
        db: Session,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Optimized semantic search using pgvector's native operators.

        Uses the <=> operator for cosine distance (1 - cosine_similarity).
        With HNSW index, this is O(log n) complexity.
        """
        from sqlalchemy import text

        # pgvector uses cosine distance (<=>), we convert to similarity
        # similarity = 1 - distance
        query = text("""
            SELECT
                id,
                chunk_text,
                chunk_index,
                document_id,
                chunk_metadata,
                1 - (embedding <=> :query_embedding::vector) as similarity
            FROM document_embeddings
            WHERE case_id = :case_id
            ORDER BY embedding <=> :query_embedding::vector
            LIMIT :top_k
        """)

        result = db.execute(query, {
            "query_embedding": str(query_embedding),
            "case_id": case_id,
            "top_k": top_k
        })

        results = []
        for row in result:
            results.append({
                'chunk_text': row.chunk_text,
                'chunk_index': row.chunk_index,
                'document_id': row.document_id,
                'similarity': float(row.similarity),
                'metadata': row.chunk_metadata
            })

        logger.debug(f"pgvector search returned {len(results)} results for case {case_id}")
        return results

    async def _fallback_semantic_search(
        self,
        query_embedding: List[float],
        case_id: str,
        db: Session,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Fallback semantic search using manual cosine similarity.

        Used when pgvector is not available (SQLite, PostgreSQL without pgvector).
        O(n) complexity - fine for < 100k embeddings per case.
        """
        # Get all embeddings for this case
        embeddings = db.query(DocumentEmbedding).filter(
            DocumentEmbedding.case_id == case_id
        ).all()

        if not embeddings:
            return []

        # Calculate similarities manually
        results = []
        for emb in embeddings:
            if not emb.embedding:
                continue

            similarity = self.cosine_similarity(query_embedding, emb.embedding)

            results.append({
                'chunk_text': emb.chunk_text,
                'chunk_index': emb.chunk_index,
                'document_id': emb.document_id,
                'similarity': similarity,
                'metadata': emb.chunk_metadata
            })

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    async def _bm25_search(
        self,
        query: str,
        case_id: str,
        db: Session,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        BM25-style keyword search using PostgreSQL full-text search.

        Uses ts_rank_cd (cover density ranking) for better phrase matching.
        Scores are normalized to [0, 1] range by dividing by max score.

        Args:
            query: Search query text
            case_id: Case ID to search within
            db: Database session
            top_k: Number of results to return

        Returns:
            List of relevant document chunks with BM25 scores
        """
        from sqlalchemy import text

        # Convert query to tsquery format
        # plainto_tsquery handles natural language queries
        search_query = text("""
            WITH ranked AS (
                SELECT
                    id,
                    chunk_text,
                    chunk_index,
                    document_id,
                    chunk_metadata,
                    ts_rank_cd(chunk_text_search, plainto_tsquery('english', :query)) as raw_score
                FROM document_embeddings
                WHERE case_id = :case_id
                    AND chunk_text_search @@ plainto_tsquery('english', :query)
            ),
            max_score AS (
                SELECT COALESCE(MAX(raw_score), 1) as max_val FROM ranked
            )
            SELECT
                r.id,
                r.chunk_text,
                r.chunk_index,
                r.document_id,
                r.chunk_metadata,
                r.raw_score,
                CASE WHEN m.max_val > 0
                    THEN r.raw_score / m.max_val
                    ELSE 0
                END as bm25_score
            FROM ranked r, max_score m
            ORDER BY r.raw_score DESC
            LIMIT :top_k
        """)

        result = db.execute(search_query, {
            "query": query,
            "case_id": case_id,
            "top_k": top_k
        })

        results = []
        for row in result:
            results.append({
                'chunk_text': row.chunk_text,
                'chunk_index': row.chunk_index,
                'document_id': row.document_id,
                'bm25_score': float(row.bm25_score),
                'metadata': row.chunk_metadata
            })

        logger.debug(f"BM25 search returned {len(results)} results for case {case_id}")
        return results

    async def hybrid_search(
        self,
        query: str,
        case_id: str,
        db: Session,
        top_k: int = 5,
        alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic and BM25 keyword search.

        Formula: hybrid_score = alpha * semantic_score + (1 - alpha) * bm25_score

        Args:
            query: Search query text
            case_id: Case ID to search within
            db: Database session
            top_k: Number of final results to return
            alpha: Weight for semantic search (0.0 = BM25 only, 1.0 = semantic only)

        Returns:
            List of document chunks with hybrid scores, semantic scores, and BM25 scores
        """
        # Fetch 3x top_k from each method to ensure good coverage
        fetch_k = top_k * 3

        # Run semantic search
        semantic_results = await self.semantic_search(
            query=query,
            case_id=case_id,
            db=db,
            top_k=fetch_k
        )

        # Run BM25 search
        bm25_results = await self._bm25_search(
            query=query,
            case_id=case_id,
            db=db,
            top_k=fetch_k
        )

        # Create lookup dictionaries by (document_id, chunk_index)
        semantic_lookup: Dict[tuple, Dict] = {}
        for r in semantic_results:
            key = (r['document_id'], r['chunk_index'])
            semantic_lookup[key] = r

        bm25_lookup: Dict[tuple, Dict] = {}
        for r in bm25_results:
            key = (r['document_id'], r['chunk_index'])
            bm25_lookup[key] = r

        # Get all unique keys
        all_keys = set(semantic_lookup.keys()) | set(bm25_lookup.keys())

        # Merge results
        merged_results = []
        for key in all_keys:
            sem_result = semantic_lookup.get(key)
            bm25_result = bm25_lookup.get(key)

            # Get scores (default to 0 if not found in one method)
            semantic_score = sem_result['similarity'] if sem_result else 0.0
            bm25_score = bm25_result['bm25_score'] if bm25_result else 0.0

            # Calculate hybrid score
            hybrid_score = alpha * semantic_score + (1 - alpha) * bm25_score

            # Use data from whichever result is available (prefer semantic for text)
            base_result = sem_result or bm25_result

            merged_results.append({
                'chunk_text': base_result['chunk_text'],
                'chunk_index': base_result['chunk_index'],
                'document_id': base_result['document_id'],
                'hybrid_score': hybrid_score,
                'semantic_score': semantic_score,
                'bm25_score': bm25_score,
                'metadata': base_result.get('metadata', {})
            })

        # Sort by hybrid score and return top_k
        merged_results.sort(key=lambda x: x['hybrid_score'], reverse=True)

        logger.debug(
            f"Hybrid search (alpha={alpha}) returned {len(merged_results[:top_k])} "
            f"results from {len(semantic_results)} semantic + {len(bm25_results)} BM25"
        )

        return merged_results[:top_k]

    async def get_case_context(
        self,
        case_id: str,
        user_query: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Build comprehensive case context for AI assistant

        Args:
            case_id: Case ID
            user_query: User's question (for semantic search)
            db: Database session

        Returns:
            Comprehensive context dictionary
        """
        # Get case details
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {}

        # Get documents (limit to most recent 20 for performance)
        documents = db.query(Document).filter(
            Document.case_id == case_id
        ).order_by(Document.created_at.desc()).limit(20).all()

        # Get deadlines (only pending and upcoming)
        from datetime import datetime, timedelta
        future_cutoff = datetime.now() + timedelta(days=180)  # 6 months ahead

        deadlines = db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.status.in_(['pending', 'in_progress'])
        ).order_by(Deadline.deadline_date.asc().nullslast()).limit(50).all()

        # Perform semantic search if query provided
        relevant_chunks = []
        if user_query:
            relevant_chunks = await self.semantic_search(
                query=user_query,
                case_id=case_id,
                db=db,
                top_k=5
            )

        # Rank documents by importance (orders, motions > other documents)
        priority_types = ['order', 'motion', 'judgment', 'ruling']
        important_docs = [d for d in documents if any(pt in (d.document_type or '').lower() for pt in priority_types)]
        other_docs = [d for d in documents if d not in important_docs]
        ranked_documents = important_docs[:10] + other_docs[:10]  # Top 20 total

        # Build context
        context = {
            'case': {
                'case_number': case.case_number,
                'title': case.title,
                'court': case.court,
                'judge': case.judge,
                'case_type': case.case_type,
                'jurisdiction': case.jurisdiction,
                'filing_date': case.filing_date.isoformat() if case.filing_date else None,
                'parties': case.parties or []
            },
            'documents': [
                {
                    'id': str(doc.id),
                    'file_name': doc.file_name,
                    'document_type': doc.document_type,
                    'filing_date': doc.filing_date.isoformat() if doc.filing_date else None,
                    'summary': doc.ai_summary,
                    'is_important': doc in important_docs
                }
                for doc in ranked_documents
            ],
            'deadlines': {
                'total': len(deadlines),
                'upcoming': [
                    {
                        'id': str(d.id),
                        'title': d.title,
                        'date': d.deadline_date.isoformat() if d.deadline_date else None,
                        'priority': d.priority,
                        'is_calculated': d.is_calculated,
                        'calculation_basis': d.calculation_basis
                    }
                    for d in deadlines if d.status == 'pending'
                ],
                'trigger_events': [
                    {
                        'id': str(d.id),
                        'title': d.title,
                        'trigger_type': d.trigger_event,
                        'date': d.deadline_date.isoformat() if d.deadline_date else None
                    }
                    for d in deadlines if d.trigger_event and not d.is_dependent
                ]
            },
            'relevant_excerpts': [
                {
                    'text': chunk['chunk_text'][:500],  # Truncate for context
                    'document_id': chunk['document_id'],
                    'similarity': round(chunk['similarity'], 3)
                }
                for chunk in relevant_chunks
            ]
        }

        return context


# Singleton instance
rag_service = RAGService()
