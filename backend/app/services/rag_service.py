"""
RAG Service - Retrieval Augmented Generation
Handles document embeddings, semantic search, and context retrieval for chat
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
import json
import numpy as np
from anthropic import Anthropic

from app.models.document import Document
from app.models.document_embedding import DocumentEmbedding
from app.models.deadline import Deadline
from app.models.case import Case
from app.config import settings


class RAGService:
    """
    RAG (Retrieval Augmented Generation) Service

    Provides semantic search over case documents and intelligent context retrieval
    for the AI chat assistant
    """

    def __init__(self):
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks

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
        Generate embeddings for text chunks using Claude

        Note: Currently returns dummy embeddings as Claude doesn't have a dedicated
        embeddings API. In production, use OpenAI text-embedding-3-small or similar.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (as lists of floats)
        """
        # TODO: Replace with actual embedding service (OpenAI, Cohere, etc.)
        # For now, using a simple TF-IDF style approach as placeholder

        embeddings = []
        for text in texts:
            # Simple word-based embedding (placeholder)
            # In production, use: openai.embeddings.create(input=text, model="text-embedding-3-small")
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

        # Get all embeddings for this case
        embeddings = db.query(DocumentEmbedding).filter(
            DocumentEmbedding.case_id == case_id
        ).all()

        if not embeddings:
            return []

        # Calculate similarities
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
