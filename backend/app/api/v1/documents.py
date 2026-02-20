from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from pydantic import BaseModel
import os
import uuid
import logging
import httpx

from app.database import get_db
from app.services.document_service import DocumentService
from app.services.case_summary_service import CaseSummaryService
from app.services.rag_service import rag_service  # Phase 1: RAG integration
from app.models.user import User
from app.models.case import Case
from app.models.deadline import Deadline
from app.models.document import Document
from app.models.document_tag import Tag, DocumentTag
from app.utils.auth import get_current_user
from app.middleware.security import limiter, validate_pdf_magic_number

logger = logging.getLogger(__name__)
router = APIRouter()


# ===================
# PYDANTIC MODELS
# ===================

class TagCreate(BaseModel):
    name: str
    color: str = "#3b82f6"


class TagResponse(BaseModel):
    id: str
    name: str
    color: str

    class Config:
        from_attributes = True


class BulkUploadResult(BaseModel):
    filename: str
    success: bool
    document_id: Optional[str] = None
    case_id: Optional[str] = None
    error: Optional[str] = None
    deadlines_extracted: int = 0


@router.post("/upload")
@limiter.limit("10/minute")  # Rate limit uploads to prevent abuse
async def upload_document(
    request: Request,  # Required for rate limiter
    file: UploadFile = File(...),
    case_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and analyze a PDF document.

    Workflow:
    1. Extract text from PDF
    2. Analyze with Claude to extract case number and metadata
    3. If case_id provided, attach to existing case
    4. If case_id not provided but case_number detected, check if case exists
    5. If case exists, route to existing "Case Room"
    6. If case doesn't exist, create new case and route to new "Case Room"
    """
    pdf_bytes = None
    analysis_result = None
    document = None
    deadlines = []

    try:
        # SECURITY: Verify case ownership if case_id is provided
        if case_id:
            case = db.query(Case).filter(
                Case.id == case_id,
                Case.user_id == str(current_user.id)
            ).first()
            if not case:
                raise HTTPException(status_code=404, detail="Case not found or access denied")

        # Validate file extension (case-insensitive)
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")

        # Read file bytes
        try:
            pdf_bytes = await file.read()
        except Exception as e:
            logger.error(f"Failed to read uploaded file {file.filename}: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to read uploaded file")

        # SECURITY: Enforce file size limit (50MB)
        MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
        if len(pdf_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is 50MB, got {len(pdf_bytes) / (1024*1024):.1f}MB"
            )

        # SECURITY: Validate PDF magic number to prevent malicious file uploads
        if not validate_pdf_magic_number(pdf_bytes):
            logger.warning(f"Invalid PDF magic number for file {file.filename} from user {current_user.id}")
            raise HTTPException(
                status_code=400,
                detail="Invalid file format. File does not appear to be a valid PDF."
            )

        # Analyze document
        doc_service = DocumentService(db)
        analysis_result = await doc_service.analyze_document(
            pdf_bytes=pdf_bytes,
            file_name=file.filename,
            user_id=str(current_user.id),
            case_id=case_id
        )

        if not analysis_result.get('success'):
            error_msg = analysis_result.get('error', 'Analysis failed')
            # Return 422 for validation/configuration errors (like invalid API key)
            # instead of 500 which suggests a server bug
            logger.error(f"Document analysis failed: {error_msg}")
            raise HTTPException(
                status_code=422,
                detail=f"Document analysis failed: {error_msg}"
            )

        # CRITICAL FIX: Use Firebase Storage instead of local /tmp storage
        # This fixes 404 errors and ensures documents persist across deployments
        from app.services.firebase_service import firebase_service

        try:
            logger.info(f"Uploading document to Firebase Storage: {file.filename}")

            # Upload to Firebase Storage (returns storage_path and signed_url)
            storage_path, signed_url = firebase_service.upload_pdf(
                user_id=str(current_user.id),
                file_name=file.filename,
                pdf_bytes=pdf_bytes
            )

            logger.info(f"Document uploaded successfully to Firebase: {storage_path}")

        except Exception as e:
            logger.error(f"Failed to upload document to Firebase Storage: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to upload document to cloud storage"
            )

        # Create document record with Firebase Storage path
        document = doc_service.create_document_record(
            case_id=analysis_result['case_id'],
            user_id=str(current_user.id),
            file_name=file.filename,
            storage_path=storage_path,  # Now a Firebase path like "documents/user_id/timestamp_file.pdf"
            extracted_text=analysis_result['extracted_text'],
            analysis=analysis_result['analysis'],
            file_size_bytes=analysis_result['file_size_bytes'],
            needs_ocr=analysis_result.get('needs_ocr', False)
        )

        # PHASE 1: Generate embeddings for RAG semantic search
        # This runs asynchronously - embeddings will be available for search within seconds
        try:
            if document.extracted_text:
                chunks_created = await rag_service.embed_document(
                    document=document,
                    case_id=analysis_result['case_id'],
                    db=db
                )
                logger.info(f"Generated {chunks_created} embeddings for document {document.id}")
        except Exception as e:
            # Don't fail the upload if embedding generation fails
            logger.error(f"Embedding generation failed for document {document.id}: {e}")

        # Extract deadlines from document (TRIGGER-FIRST ARCHITECTURE)
        # Returns dict with: deadlines, extraction_method, trigger_info, message, count
        extraction_result = await doc_service.extract_and_save_deadlines(
            document=document,
            extracted_text=analysis_result['extracted_text'],
            analysis=analysis_result['analysis']
        )

        deadlines = extraction_result['deadlines']
        extraction_method = extraction_result['extraction_method']
        docketing_message = extraction_result['message']

        # FEATURE 1: Extract deadline suggestions for user review
        # These are potential deadlines that weren't auto-created but may be relevant
        suggestions_created = []
        try:
            suggestions_created = doc_service.extract_deadline_suggestions(
                document=document,
                analysis=analysis_result['analysis']
            )
            if suggestions_created:
                logger.info(f"Created {len(suggestions_created)} deadline suggestions for document {document.id}")
        except Exception as e:
            # Don't fail upload if suggestion extraction fails
            logger.warning(f"Suggestion extraction failed (non-critical): {e}")

        # Auto-update case summary
        case = db.query(Case).filter(Case.id == analysis_result['case_id']).first()
        if case:
            from app.models.document import Document as DocModel
            all_documents = db.query(DocModel).filter(
                DocModel.case_id == analysis_result['case_id']
            ).order_by(DocModel.created_at.desc()).all()

            all_deadlines = db.query(Deadline).filter(
                Deadline.case_id == analysis_result['case_id']
            ).order_by(Deadline.deadline_date.asc().nullslast()).all()

            summary_service = CaseSummaryService()
            await summary_service.generate_case_summary(case, all_documents, all_deadlines, db)

        # Build appropriate message based on case_status
        case_status = analysis_result.get('case_status', 'attached')
        if case_status == 'created':
            status_message = "New case created"
        elif case_status == 'updated':
            status_message = "Document added to existing case"
        else:
            status_message = "Document attached"

        return {
            'success': True,
            'document_id': str(document.id),
            'case_id': analysis_result['case_id'],
            'case_created': analysis_result.get('case_created', False),
            'case_status': case_status,  # NEW: "created" | "updated" | "attached"
            'analysis': analysis_result['analysis'],
            'deadlines_extracted': len(deadlines),
            'extraction_method': extraction_method,  # "trigger" or "manual"
            'docketing_message': docketing_message,  # Message for chatbot
            'trigger_info': extraction_result.get('trigger_info'),  # Trigger details if PATH A
            'suggestions_created': len(suggestions_created),  # Pending suggestions for review
            'redirect_url': f"/cases/{analysis_result['case_id']}",
            'message': docketing_message or f'{status_message}. {len(deadlines)} deadline(s) extracted.'
        }

    except HTTPException:
        # Rollback and re-raise HTTP exceptions
        db.rollback()
        raise
    except Exception as e:
        # Rollback on any unexpected errors
        db.rollback()
        import traceback
        traceback.print_exc()
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document by ID"""
    from app.models.document import Document

    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get tags for document
    doc_tags = db.query(Tag).join(DocumentTag).filter(
        DocumentTag.document_id == document_id
    ).all()

    return {
        'id': str(document.id),
        'case_id': str(document.case_id),
        'file_name': document.file_name,
        'document_type': document.document_type,
        'filing_date': document.filing_date.isoformat() if document.filing_date else None,
        'ai_summary': document.ai_summary,
        'extracted_metadata': document.extracted_metadata,
        'created_at': document.created_at.isoformat(),
        'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in doc_tags]
    }


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download/serve document file via backend proxy.

    CORS FIX: Instead of redirecting to Firebase signed URL (which has CORS issues),
    the backend fetches the file and streams it to the frontend.

    SECURITY: Always verifies document ownership before serving.
    """
    from app.models.document import Document
    from app.services.firebase_service import firebase_service
    from fastapi.responses import StreamingResponse

    # CRITICAL: Verify ownership before serving file
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)  # OWNERSHIP CHECK
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.storage_path:
        raise HTTPException(status_code=404, detail="Document file not found")

    # Check storage type
    if document.storage_path.startswith('documents/'):
        # Firebase Storage - PROXY the file through backend to bypass CORS
        try:
            # Get signed URL (this works server-side, no CORS)
            signed_url = firebase_service.get_download_url(document.storage_path)

            # Fetch the file from Firebase using async httpx client
            async with httpx.AsyncClient() as client:
                response = await client.get(signed_url)

                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail="Failed to fetch document from storage")

                # Stream the file to the client with proper CORS headers
                return StreamingResponse(
                    iter([response.content]),
                    media_type='application/pdf',
                    headers={
                        'Content-Disposition': f'inline; filename="{document.file_name}"',
                        'Cache-Control': 'private, max-age=3600',
                        'Access-Control-Allow-Origin': '*',  # Allow all origins for PDF viewing
                        'Access-Control-Allow-Methods': 'GET, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                    }
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to proxy Firebase document {document_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to download document")
    else:
        # Local file storage - serve directly
        if not os.path.exists(document.storage_path):
            logger.error(f"Local file not found: {document.storage_path}")
            raise HTTPException(status_code=404, detail="Document file not found on server")

        # Serve file with proper content type
        return FileResponse(
            path=document.storage_path,
            media_type='application/pdf',
            filename=document.file_name,
            headers={
                'Content-Disposition': f'inline; filename="{document.file_name}"',
                'Cache-Control': 'private, max-age=3600'
            }
        )


# ===================
# BULK UPLOAD
# ===================

@router.post("/bulk-upload")
async def bulk_upload_documents(
    files: List[UploadFile] = File(...),
    case_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload multiple PDF documents at once.

    All documents will be analyzed sequentially and attached to:
    - The provided case_id if specified
    - Existing cases if case numbers match
    - New cases if no match found
    """
    # SECURITY: Verify case ownership if case_id is provided
    if case_id:
        case = db.query(Case).filter(
            Case.id == case_id,
            Case.user_id == str(current_user.id)
        ).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found or access denied")

    results = []

    for file in files:
        try:
            # Validate file type
            if not file.filename.endswith('.pdf'):
                results.append(BulkUploadResult(
                    filename=file.filename,
                    success=False,
                    error="Only PDF files are accepted"
                ))
                continue

            # Read file bytes
            pdf_bytes = await file.read()

            # Analyze document
            doc_service = DocumentService(db)
            analysis_result = await doc_service.analyze_document(
                pdf_bytes=pdf_bytes,
                file_name=file.filename,
                user_id=str(current_user.id),
                case_id=case_id
            )

            if not analysis_result.get('success'):
                error_msg = analysis_result.get('error', 'Analysis failed')
                logger.error(f"Bulk upload analysis failed for {file.filename}: {error_msg}")
                results.append(BulkUploadResult(
                    filename=file.filename,
                    success=False,
                    error=f"Document analysis failed: {error_msg}"
                ))
                continue

            # CRITICAL FIX: Use Firebase Storage for bulk uploads too
            from app.services.firebase_service import firebase_service

            try:
                logger.info(f"Bulk upload: Uploading to Firebase Storage: {file.filename}")

                # Upload to Firebase Storage
                storage_path, signed_url = firebase_service.upload_pdf(
                    user_id=str(current_user.id),
                    file_name=file.filename,
                    pdf_bytes=pdf_bytes
                )

                logger.info(f"Bulk upload: Document uploaded to Firebase: {storage_path}")

            except Exception as e:
                logger.error(f"Bulk upload: Failed to upload to Firebase: {e}")
                results.append(BulkUploadResult(
                    filename=file.filename,
                    success=False,
                    error="Failed to upload to cloud storage"
                ))
                continue

            # Create document record with Firebase Storage path
            document = doc_service.create_document_record(
                case_id=analysis_result['case_id'],
                user_id=str(current_user.id),
                file_name=file.filename,
                storage_path=storage_path,  # Firebase path
                extracted_text=analysis_result['extracted_text'],
                analysis=analysis_result['analysis'],
                file_size_bytes=analysis_result['file_size_bytes'],
                needs_ocr=analysis_result.get('needs_ocr', False)
            )

            # Extract deadlines (TRIGGER-FIRST ARCHITECTURE)
            extraction_result = await doc_service.extract_and_save_deadlines(
                document=document,
                extracted_text=analysis_result['extracted_text'],
                analysis=analysis_result['analysis']
            )

            results.append(BulkUploadResult(
                filename=file.filename,
                success=True,
                document_id=str(document.id),
                case_id=analysis_result['case_id'],
                deadlines_extracted=extraction_result['count']
            ))

        except Exception as e:
            # Rollback failed transaction before continuing to next file
            db.rollback()
            logger.error(f"Error processing {file.filename}: {e}")
            results.append(BulkUploadResult(
                filename=file.filename,
                success=False,
                error="An internal error occurred during processing"
            ))

    # Summary stats
    successful = sum(1 for r in results if r.success)
    total_deadlines = sum(r.deadlines_extracted for r in results)

    return {
        'success': True,
        'total_files': len(files),
        'successful': successful,
        'failed': len(files) - successful,
        'total_deadlines_extracted': total_deadlines,
        'results': [r.dict() for r in results]
    }


# ===================
# DOCUMENT LIST & SEARCH
# ===================

@router.get("")
async def list_documents(
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    tag_id: Optional[str] = Query(None, description="Filter by tag ID"),
    search: Optional[str] = Query(None, description="Search in filename or summary"),
    sort_by: str = Query("created_at", description="Sort field: created_at, file_name, document_type"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List documents with filtering and search.
    """
    query = db.query(Document).filter(Document.user_id == str(current_user.id))

    # Apply filters
    if case_id:
        query = query.filter(Document.case_id == case_id)

    if document_type:
        query = query.filter(Document.document_type == document_type)

    if tag_id:
        query = query.join(DocumentTag).filter(DocumentTag.tag_id == tag_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Document.file_name.ilike(search_term),
                Document.ai_summary.ilike(search_term),
                Document.document_type.ilike(search_term)
            )
        )

    # Apply sorting
    sort_column = getattr(Document, sort_by, Document.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Get total count
    total = query.count()

    # Paginate
    documents = query.offset(skip).limit(limit).all()

    # Format response
    doc_list = []
    for doc in documents:
        doc_tags = db.query(Tag).join(DocumentTag).filter(
            DocumentTag.document_id == doc.id
        ).all()

        doc_list.append({
            'id': str(doc.id),
            'case_id': str(doc.case_id),
            'file_name': doc.file_name,
            'document_type': doc.document_type,
            'file_size_bytes': doc.file_size_bytes,
            'filing_date': doc.filing_date.isoformat() if doc.filing_date else None,
            'ai_summary': doc.ai_summary,
            'created_at': doc.created_at.isoformat(),
            'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in doc_tags]
        })

    return {
        'total': total,
        'skip': skip,
        'limit': limit,
        'documents': doc_list
    }


# ===================
# TAG MANAGEMENT
# ===================

@router.get("/tags")
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all tags for current user"""
    tags = db.query(Tag).filter(Tag.user_id == str(current_user.id)).all()
    return {
        'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in tags]
    }


@router.post("/tags")
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new tag"""
    # Check if tag with same name exists
    existing = db.query(Tag).filter(
        Tag.user_id == str(current_user.id),
        Tag.name == tag_data.name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Tag with this name already exists")

    try:
        tag = Tag(
            user_id=str(current_user.id),
            name=tag_data.name,
            color=tag_data.color
        )
        db.add(tag)
        db.commit()
        db.refresh(tag)

        return {'id': tag.id, 'name': tag.name, 'color': tag.color}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create tag: {e}")
        raise HTTPException(status_code=500, detail="Failed to create tag")


@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a tag"""
    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.user_id == str(current_user.id)
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    try:
        db.delete(tag)
        db.commit()
        return {'success': True, 'message': 'Tag deleted'}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete tag: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete tag")


@router.post("/{document_id}/tags/{tag_id}")
async def add_tag_to_document(
    document_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a tag to a document"""
    # Verify document belongs to user
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify tag belongs to user
    tag = db.query(Tag).filter(
        Tag.id == tag_id,
        Tag.user_id == str(current_user.id)
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Check if already tagged
    existing = db.query(DocumentTag).filter(
        DocumentTag.document_id == document_id,
        DocumentTag.tag_id == tag_id
    ).first()

    if existing:
        return {'success': True, 'message': 'Tag already applied'}

    try:
        # Create document-tag relationship
        doc_tag = DocumentTag(document_id=document_id, tag_id=tag_id)
        db.add(doc_tag)
        db.commit()
        return {'success': True, 'message': 'Tag added to document'}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add tag to document: {e}")
        raise HTTPException(status_code=500, detail="Failed to add tag")


@router.delete("/{document_id}/tags/{tag_id}")
async def remove_tag_from_document(
    document_id: str,
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a tag from a document"""
    # Verify document belongs to user
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Find and delete the document-tag relationship
    doc_tag = db.query(DocumentTag).filter(
        DocumentTag.document_id == document_id,
        DocumentTag.tag_id == tag_id
    ).first()

    if not doc_tag:
        raise HTTPException(status_code=404, detail="Tag not found on document")

    try:
        db.delete(doc_tag)
        db.commit()
        return {'success': True, 'message': 'Tag removed from document'}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to remove tag from document: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove tag")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document and its associated file.

    Ghost-Safe Deletion:
    - Handles missing files gracefully (ghost documents)
    - Always deletes DB record even if file is missing
    - Logs warnings for missing files but doesn't fail
    """
    doc_service = DocumentService(db)

    try:
        # Use ghost-safe deletion from service layer
        deleted = doc_service.delete_document(
            document_id=document_id,
            user_id=str(current_user.id)
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")

        return {'success': True, 'message': 'Document deleted'}

    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        # Catch any other errors (database errors, etc.)
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


# ============================================================
# Document Intelligence Endpoints
# ============================================================

class DocumentAnalysisRequest(BaseModel):
    extract_entities: bool = True
    extract_dates: bool = True
    extract_amounts: bool = True
    extract_citations: bool = True
    identify_risks: bool = True


@router.get("/{document_id}/analysis")
async def get_document_analysis(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get existing AI analysis for a document.
    """
    # Verify document ownership
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if analysis exists in metadata
    if not document.metadata or 'analysis' not in document.metadata:
        raise HTTPException(status_code=404, detail="No analysis found for this document")

    return document.metadata['analysis']


@router.post("/{document_id}/analyze")
@limiter.limit("5/minute")  # Rate limit AI analysis
async def analyze_document(
    request: Request,
    document_id: str,
    analysis_request: Optional[DocumentAnalysisRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run AI-powered analysis on a document.

    Extracts:
    - Document classification
    - Key entities (persons, organizations, locations)
    - Important dates
    - Monetary amounts
    - Legal citations
    - Risk indicators
    """
    from app.services.ai_service import AIService
    import json

    # Verify document ownership
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get document text
    content = document.extracted_text or ""
    if not content:
        raise HTTPException(status_code=400, detail="Document has no extracted text")

    # Build analysis prompt
    prompt = f"""Analyze this legal document comprehensively.

Document Name: {document.file_name}
Document Type: {document.document_type or 'Unknown'}
Content:
{content[:12000]}

Provide a detailed analysis in JSON format:
{{
    "classification": {{
        "primary_type": "complaint|motion|order|brief|discovery|contract|correspondence|deposition|exhibit|other",
        "confidence": 0.95,
        "secondary_types": ["list", "of", "related", "types"]
    }},
    "summary": "2-3 sentence summary of the document",
    "key_points": ["Important point 1", "Important point 2", "Important point 3"],
    "entities": [
        {{"type": "person|organization|location", "value": "Entity name", "confidence": 0.9, "context": "Where mentioned"}}
    ],
    "dates": [
        {{"date": "2024-01-15", "context": "Filing deadline", "importance": "critical|high|standard"}}
    ],
    "amounts": [
        {{"amount": "$50,000", "currency": "USD", "context": "Damages claimed"}}
    ],
    "parties_mentioned": [
        {{"name": "Party Name", "role": "plaintiff|defendant|witness|counsel|judge", "mentions": 5}}
    ],
    "legal_citations": [
        {{"citation": "Case Name, Reporter Citation", "context": "Used to support argument"}}
    ],
    "risk_indicators": [
        {{"indicator": "Risk type", "severity": "high|medium|low", "explanation": "Why this is a risk"}}
    ]
}}

Be thorough and accurate. Extract all relevant information."""

    try:
        ai_service = AIService()
        response = await ai_service.analyze_with_claude(prompt)

        # Parse JSON response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            analysis_data = json.loads(response[json_start:json_end])
        else:
            analysis_data = {
                "classification": {"primary_type": "unknown", "confidence": 0.5, "secondary_types": []},
                "summary": "Unable to parse analysis",
                "key_points": [],
                "entities": [],
                "dates": [],
                "amounts": [],
                "parties_mentioned": [],
                "legal_citations": [],
                "risk_indicators": []
            }

        # Add analysis metadata
        analysis_data['id'] = str(uuid.uuid4())
        analysis_data['document_id'] = document_id
        analysis_data['document_type'] = document.document_type
        analysis_data['analyzed_at'] = str(datetime.utcnow().isoformat())

        # Store analysis in document metadata
        if not document.metadata:
            document.metadata = {}
        document.metadata['analysis'] = analysis_data

        # Mark document as analyzed
        document.metadata['analyzed'] = True
        document.metadata['analyzed_at'] = analysis_data['analyzed_at']

        # Use flag_modified to tell SQLAlchemy the JSONB column changed
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(document, 'metadata')

        db.commit()

        return analysis_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI analysis response: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse analysis")
    except Exception as e:
        logger.error(f"Document analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Document analysis failed")


@router.get("/{document_id}/summary")
async def get_document_summary(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a quick AI summary of a document.
    """
    from app.services.ai_service import AIService

    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    content = document.extracted_text or ""
    if not content:
        raise HTTPException(status_code=400, detail="Document has no extracted text")

    # Check if we have a cached summary
    if document.metadata and 'summary' in document.metadata:
        return {"summary": document.metadata['summary'], "cached": True}

    prompt = f"""Summarize this legal document in 2-3 concise sentences. Focus on the key purpose, parties involved, and main claims or requests.

Document: {document.file_name}
Type: {document.document_type or 'Unknown'}

Content:
{content[:6000]}

Respond with only the summary, no additional formatting."""

    try:
        ai_service = AIService()
        summary = await ai_service.analyze_with_claude(prompt)

        # Cache the summary
        if not document.metadata:
            document.metadata = {}
        document.metadata['summary'] = summary.strip()

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(document, 'metadata')
        db.commit()

        return {"summary": summary.strip(), "cached": False}

    except Exception as e:
        logger.error(f"Document summarization failed: {e}")
        raise HTTPException(status_code=500, detail="Document summarization failed")


# Add datetime import at top if not present
from datetime import datetime


# ============================================================
# Deadline Suggestion Endpoints
# ============================================================

@router.get("/{document_id}/suggestions")
async def get_document_suggestions(
    document_id: str,
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get deadline suggestions extracted from a document.

    Returns AI-extracted deadline suggestions that can be approved
    and converted to actual deadlines.
    """
    from app.models.document_deadline_suggestion import DocumentDeadlineSuggestion

    # SECURITY: Verify document ownership
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Query suggestions
    query = db.query(DocumentDeadlineSuggestion).filter(
        DocumentDeadlineSuggestion.document_id == document_id,
        DocumentDeadlineSuggestion.user_id == str(current_user.id)
    )

    if status:
        query = query.filter(DocumentDeadlineSuggestion.status == status)

    # Order by confidence score descending
    suggestions = query.order_by(DocumentDeadlineSuggestion.confidence_score.desc()).all()

    # Count pending
    pending_count = db.query(DocumentDeadlineSuggestion).filter(
        DocumentDeadlineSuggestion.document_id == document_id,
        DocumentDeadlineSuggestion.user_id == str(current_user.id),
        DocumentDeadlineSuggestion.status == 'pending'
    ).count()

    return {
        "suggestions": [s.to_dict() for s in suggestions],
        "total": len(suggestions),
        "pending_count": pending_count,
        "document_id": document_id
    }


@router.post("/{document_id}/apply-deadlines")
@limiter.limit("20/minute")
async def apply_deadline_suggestions(
    request: Request,
    document_id: str,
    apply_request: dict,  # Using dict for flexibility
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Apply selected deadline suggestions as actual deadlines.

    Request body:
    {
        "suggestions": [
            {
                "suggestion_id": "uuid",
                "apply_as_trigger": false,  // If true, trigger cascade calculation
                "override_date": "2024-03-15",  // Optional date override
                "override_title": "Custom title"  // Optional title override
            }
        ]
    }
    """
    from app.models.document_deadline_suggestion import DocumentDeadlineSuggestion
    from app.models.deadline import Deadline
    from app.services.deadline_service import DeadlineService

    # SECURITY: Verify document ownership
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    suggestions_to_apply = apply_request.get('suggestions', [])
    if not suggestions_to_apply:
        raise HTTPException(status_code=400, detail="No suggestions provided")

    results = []
    total_deadlines = 0
    total_cascade = 0
    deadline_service = DeadlineService()

    for item in suggestions_to_apply:
        suggestion_id = item.get('suggestion_id')
        apply_as_trigger = item.get('apply_as_trigger', False)
        override_date = item.get('override_date')
        override_title = item.get('override_title')

        # Get suggestion with ownership check
        suggestion = db.query(DocumentDeadlineSuggestion).filter(
            DocumentDeadlineSuggestion.id == suggestion_id,
            DocumentDeadlineSuggestion.user_id == str(current_user.id)
        ).first()

        if not suggestion:
            results.append({
                "suggestion_id": suggestion_id,
                "success": False,
                "error": "Suggestion not found"
            })
            continue

        if suggestion.status != 'pending':
            results.append({
                "suggestion_id": suggestion_id,
                "success": False,
                "error": f"Suggestion already {suggestion.status}"
            })
            continue

        try:
            cascade_count = 0

            # Parse override date if provided
            deadline_date = suggestion.suggested_date
            if override_date:
                try:
                    deadline_date = datetime.strptime(override_date, '%Y-%m-%d').date()
                except ValueError:
                    pass

            if apply_as_trigger and suggestion.matched_trigger_type:
                # Apply as trigger - generate cascade deadlines
                trigger_type = suggestion.matched_trigger_type
                jurisdiction = 'florida_state'  # TODO: Get from case
                court_type = 'civil'

                # Get case for jurisdiction info
                case = db.query(Case).filter(Case.id == suggestion.case_id).first()
                if case:
                    jurisdiction = case.jurisdiction or 'florida_state'
                    court_type = case.case_type or 'civil'

                # Generate deadline chains
                chain_deadlines = await deadline_service.generate_deadline_chains(
                    trigger_event=trigger_type,
                    trigger_date=deadline_date or datetime.now().date(),
                    jurisdiction=jurisdiction,
                    court_type=court_type,
                    case_id=suggestion.case_id,
                    user_id=str(current_user.id),
                    service_method='electronic'
                )

                # Create all chain deadlines
                for chain_dl in chain_deadlines:
                    deadline = Deadline(
                        case_id=chain_dl['case_id'],
                        user_id=chain_dl['user_id'],
                        document_id=document_id,
                        title=chain_dl['title'],
                        description=chain_dl.get('description'),
                        deadline_date=chain_dl.get('deadline_date'),
                        deadline_type=chain_dl.get('deadline_type', 'general'),
                        applicable_rule=chain_dl.get('rule_citation'),
                        rule_citation=chain_dl.get('rule_citation'),
                        calculation_basis=chain_dl.get('calculation_basis'),
                        priority=chain_dl.get('priority', 'medium'),
                        status='pending',
                        trigger_event=trigger_type,
                        trigger_date=deadline_date,
                        is_calculated=True,
                        extraction_method='rule-based',
                        verification_status='pending'
                    )
                    db.add(deadline)
                    cascade_count += 1

                total_cascade += cascade_count

                # Mark suggestion as approved
                suggestion.status = 'approved'
                suggestion.reviewed_at = datetime.utcnow()

                results.append({
                    "suggestion_id": suggestion_id,
                    "success": True,
                    "cascade_count": cascade_count,
                    "message": f"Trigger applied, {cascade_count} deadlines created"
                })
                total_deadlines += cascade_count

            else:
                # Apply as single deadline
                title = override_title or suggestion.title

                deadline = Deadline(
                    case_id=suggestion.case_id,
                    user_id=str(current_user.id),
                    document_id=document_id,
                    title=title,
                    description=suggestion.description,
                    deadline_date=deadline_date,
                    deadline_type=suggestion.deadline_type or 'general',
                    applicable_rule=suggestion.rule_citation,
                    rule_citation=suggestion.rule_citation,
                    priority='medium',
                    status='pending',
                    is_calculated=False,
                    extraction_method='ai',
                    verification_status='pending',
                    confidence_score=suggestion.confidence_score,
                    confidence_level='medium' if suggestion.confidence_score >= 50 else 'low'
                )
                db.add(deadline)
                db.flush()

                # Update suggestion
                suggestion.status = 'approved'
                suggestion.reviewed_at = datetime.utcnow()
                suggestion.created_deadline_id = deadline.id

                results.append({
                    "suggestion_id": suggestion_id,
                    "success": True,
                    "deadline_id": deadline.id,
                    "cascade_count": 0
                })
                total_deadlines += 1

        except Exception as e:
            logger.error(f"Error applying suggestion {suggestion_id}: {e}")
            results.append({
                "suggestion_id": suggestion_id,
                "success": False,
                "error": "Failed to apply suggestion"
            })

    # Commit all changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit deadline suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to apply suggestions")

    successful = sum(1 for r in results if r.get('success'))

    return {
        "success": True,
        "results": results,
        "total_deadlines_created": total_deadlines,
        "total_cascade_deadlines": total_cascade,
        "message": f"Applied {successful} of {len(suggestions_to_apply)} suggestions. {total_deadlines} deadline(s) created."
    }


@router.patch("/suggestions/{suggestion_id}")
async def update_suggestion_status(
    suggestion_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a suggestion's status (reject, etc.).

    Request body:
    {
        "status": "rejected",
        "notes": "Optional rejection reason"
    }
    """
    from app.models.document_deadline_suggestion import DocumentDeadlineSuggestion

    # SECURITY: Verify ownership
    suggestion = db.query(DocumentDeadlineSuggestion).filter(
        DocumentDeadlineSuggestion.id == suggestion_id,
        DocumentDeadlineSuggestion.user_id == str(current_user.id)
    ).first()

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    new_status = update_data.get('status')
    if new_status not in ['pending', 'approved', 'rejected', 'expired']:
        raise HTTPException(status_code=400, detail="Invalid status")

    # Update status
    suggestion.status = new_status
    suggestion.reviewed_at = datetime.utcnow()

    # Store notes in confidence_factors if provided
    notes = update_data.get('notes')
    if notes:
        if not suggestion.confidence_factors:
            suggestion.confidence_factors = {}
        suggestion.confidence_factors['rejection_notes'] = notes

    try:
        db.commit()
        db.refresh(suggestion)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update suggestion: {e}")
        raise HTTPException(status_code=500, detail="Failed to update suggestion")

    return {
        "success": True,
        "suggestion": suggestion.to_dict(),
        "message": f"Suggestion marked as {new_status}"
    }


@router.get("/cases/{case_id}/pending-suggestions")
async def get_case_pending_suggestions(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all pending deadline suggestions for a case.

    Returns suggestions across all documents in the case.
    """
    from app.models.document_deadline_suggestion import DocumentDeadlineSuggestion

    # SECURITY: Verify case ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get all pending suggestions for this case
    suggestions = db.query(DocumentDeadlineSuggestion).filter(
        DocumentDeadlineSuggestion.case_id == case_id,
        DocumentDeadlineSuggestion.user_id == str(current_user.id),
        DocumentDeadlineSuggestion.status == 'pending'
    ).order_by(
        DocumentDeadlineSuggestion.confidence_score.desc()
    ).all()

    # Group by document
    by_document = {}
    for s in suggestions:
        doc_id = s.document_id
        if doc_id not in by_document:
            by_document[doc_id] = []
        by_document[doc_id].append(s.to_dict())

    return {
        "case_id": case_id,
        "total_pending": len(suggestions),
        "suggestions": [s.to_dict() for s in suggestions],
        "by_document": by_document
    }
