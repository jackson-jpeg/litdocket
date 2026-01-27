"""
RAG-Powered Semantic Search API
Enables natural language questions across all case documents
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.document import Document
from app.utils.auth import get_current_user
from app.services.rag_service import rag_service
from app.services.ai_service import ai_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    """Request model for semantic search"""
    query: str = Field(..., min_length=3, max_length=500, description="Natural language question")
    case_id: str = Field(..., description="Case ID to search within")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of relevant chunks to return")


class SemanticSearchResponse(BaseModel):
    """Response model for semantic search"""
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    case_id: str
    total_chunks_searched: int


class RAGAnswerRequest(BaseModel):
    """Request model for RAG-powered Q&A"""
    question: str = Field(..., min_length=3, max_length=500, description="Question about the case documents")
    case_id: str = Field(..., description="Case ID context")
    include_sources: bool = Field(default=True, description="Include source citations")


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Semantic search across case documents using vector embeddings

    Returns the most relevant document chunks based on meaning, not just keywords.

    Example queries:
    - "What was the service date for the complaint?"
    - "Find all mentions of expert witness deadlines"
    - "What did the judge say about summary judgment?"
    """

    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == request.case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Perform semantic search
    try:
        results = await rag_service.semantic_search(
            query=request.query,
            case_id=request.case_id,
            db=db,
            top_k=request.top_k
        )

        if not results:
            return SemanticSearchResponse(
                query=request.query,
                answer="No relevant information found in the case documents.",
                sources=[],
                case_id=request.case_id,
                total_chunks_searched=0
            )

        # Format sources with document information
        enriched_sources = []
        for result in results:
            # Get document info
            doc = db.query(Document).filter(Document.id == result['document_id']).first()

            enriched_sources.append({
                "chunk_text": result['chunk_text'],
                "similarity": result['similarity'],
                "document_id": result['document_id'],
                "document_name": doc.file_name if doc else "Unknown",
                "document_type": doc.document_type if doc else None,
                "chunk_index": result['chunk_index'],
                "metadata": result.get('metadata', {})
            })

        # Generate a simple summary of findings
        top_result = enriched_sources[0]
        answer = f"Found {len(enriched_sources)} relevant sections. Most relevant: {top_result['chunk_text'][:200]}..."

        return SemanticSearchResponse(
            query=request.query,
            answer=answer,
            sources=enriched_sources,
            case_id=request.case_id,
            total_chunks_searched=len(results)
        )

    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/ask")
async def ask_question(
    request: RAGAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ask a question about case documents and get an AI-generated answer with citations

    Uses RAG (Retrieval Augmented Generation):
    1. Finds relevant document chunks via semantic search
    2. Sends chunks + question to Claude
    3. Returns answer with source citations

    Example questions:
    - "Summarize the key arguments in the motion to dismiss"
    - "What evidence does the plaintiff have for their negligence claim?"
    - "List all discovery deadlines mentioned in court orders"
    """

    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == request.case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        # Step 1: Semantic search for relevant chunks
        relevant_chunks = await rag_service.semantic_search(
            query=request.question,
            case_id=request.case_id,
            db=db,
            top_k=5
        )

        if not relevant_chunks:
            return {
                "success": True,
                "data": {
                    "question": request.question,
                    "answer": "I couldn't find any relevant information in the case documents to answer this question. Please try rephrasing or upload more documents.",
                    "sources": [],
                    "confidence": "low"
                }
            }

        # Step 2: Build context for Claude
        context_parts = []
        sources_metadata = []

        for i, chunk in enumerate(relevant_chunks):
            # Get document info
            doc = db.query(Document).filter(Document.id == chunk['document_id']).first()
            doc_name = doc.file_name if doc else "Unknown Document"

            context_parts.append(
                f"[Source {i+1}: {doc_name}]\n{chunk['chunk_text']}\n"
            )

            sources_metadata.append({
                "source_number": i + 1,
                "document_id": chunk['document_id'],
                "document_name": doc_name,
                "document_type": doc.document_type if doc else None,
                "chunk_text": chunk['chunk_text'][:300] + "..." if len(chunk['chunk_text']) > 300 else chunk['chunk_text'],
                "similarity": chunk['similarity']
            })

        context = "\n\n".join(context_parts)

        # Step 3: Generate answer with Claude
        system_prompt = """You are a legal research assistant helping attorneys analyze case documents.

IMPORTANT RULES:
1. Answer questions based ONLY on the provided document excerpts
2. Always cite your sources using [Source X] format
3. If the answer isn't in the documents, explicitly say so
4. Be precise with dates, names, and legal citations
5. Use clear, professional legal language
6. If documents conflict, note the discrepancy"""

        user_prompt = f"""Question: {request.question}

Relevant Document Excerpts:
{context}

Please answer the question based on the excerpts above. Always cite your sources."""

        response = ai_service.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": user_prompt
            }]
        )

        answer = response.content[0].text

        # Determine confidence based on similarity scores
        avg_similarity = sum(c['similarity'] for c in relevant_chunks) / len(relevant_chunks)
        confidence = "high" if avg_similarity > 0.7 else "medium" if avg_similarity > 0.5 else "low"

        return {
            "success": True,
            "data": {
                "question": request.question,
                "answer": answer,
                "sources": sources_metadata if request.include_sources else [],
                "confidence": confidence,
                "total_sources": len(relevant_chunks)
            },
            "message": "Question answered successfully"
        }

    except Exception as e:
        logger.error(f"RAG Q&A error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to answer question: {str(e)}")


@router.post("/embed/{document_id}")
async def generate_embeddings(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate embeddings for a specific document

    This endpoint manually triggers embedding generation for a document.
    Normally this happens automatically on upload, but this allows re-processing.
    """

    # Verify document ownership
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.extracted_text:
        raise HTTPException(status_code=400, detail="Document has no extracted text")

    try:
        # Generate embeddings
        chunks_created = await rag_service.embed_document(
            document=document,
            case_id=document.case_id,
            db=db
        )

        return {
            "success": True,
            "data": {
                "document_id": document_id,
                "chunks_created": chunks_created,
                "document_name": document.file_name
            },
            "message": f"Generated {chunks_created} embeddings for document"
        }

    except Exception as e:
        logger.error(f"Embedding generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings: {str(e)}")


@router.get("/stats/{case_id}")
async def get_rag_stats(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get RAG statistics for a case (how many documents have embeddings)
    """

    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get document counts
    from app.models.document_embedding import DocumentEmbedding

    total_documents = db.query(Document).filter(Document.case_id == case_id).count()

    documents_with_embeddings = db.query(Document).filter(
        Document.case_id == case_id,
        Document.id.in_(
            db.query(DocumentEmbedding.document_id).filter(
                DocumentEmbedding.case_id == case_id
            )
        )
    ).count()

    total_chunks = db.query(DocumentEmbedding).filter(
        DocumentEmbedding.case_id == case_id
    ).count()

    return {
        "success": True,
        "data": {
            "case_id": case_id,
            "total_documents": total_documents,
            "documents_with_embeddings": documents_with_embeddings,
            "documents_pending_embedding": total_documents - documents_with_embeddings,
            "total_embedding_chunks": total_chunks,
            "rag_enabled": documents_with_embeddings > 0
        }
    }
