from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from pydantic import BaseModel
import os
import uuid
import logging

from app.database import get_db
from app.services.document_service import DocumentService
from app.services.case_summary_service import CaseSummaryService
from app.models.user import User
from app.models.case import Case
from app.models.deadline import Deadline
from app.models.document import Document
from app.models.document_tag import Tag, DocumentTag
from app.utils.auth import get_current_user

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
async def upload_document(
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

    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted")

        # Read file bytes
        try:
            pdf_bytes = await file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

        # Analyze document
        doc_service = DocumentService(db)
        analysis_result = await doc_service.analyze_document(
            pdf_bytes=pdf_bytes,
            file_name=file.filename,
            user_id=str(current_user.id),
            case_id=case_id
        )

        if not analysis_result.get('success'):
            raise HTTPException(status_code=500, detail=analysis_result.get('error', 'Analysis failed'))
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch any unexpected errors
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    # For MVP, store files locally (replace with S3 later)
    storage_dir = f"/tmp/docketassist/{current_user.id}"
    os.makedirs(storage_dir, exist_ok=True)
    storage_filename = f"{uuid.uuid4()}.pdf"
    storage_path = f"{storage_dir}/{storage_filename}"

    with open(storage_path, 'wb') as f:
        f.write(pdf_bytes)

    # Create document record
    document = doc_service.create_document_record(
        case_id=analysis_result['case_id'],
        user_id=str(current_user.id),
        file_name=file.filename,
        storage_path=storage_path,
        extracted_text=analysis_result['extracted_text'],
        analysis=analysis_result['analysis'],
        file_size_bytes=analysis_result['file_size_bytes']
    )

    # Extract deadlines from document (Jackson's comprehensive methodology)
    deadlines = await doc_service.extract_and_save_deadlines(
        document=document,
        extracted_text=analysis_result['extracted_text'],
        analysis=analysis_result['analysis']
    )

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

    return {
        'success': True,
        'document_id': str(document.id),
        'case_id': analysis_result['case_id'],
        'case_created': analysis_result.get('case_created', False),
        'analysis': analysis_result['analysis'],
        'deadlines_extracted': len(deadlines),
        'redirect_url': f"/cases/{analysis_result['case_id']}",
        'message': f'Document uploaded, analyzed, and {len(deadlines)} deadline(s) extracted successfully'
    }


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
                results.append(BulkUploadResult(
                    filename=file.filename,
                    success=False,
                    error=analysis_result.get('error', 'Analysis failed')
                ))
                continue

            # Store file locally
            storage_dir = f"/tmp/docketassist/{current_user.id}"
            os.makedirs(storage_dir, exist_ok=True)
            storage_filename = f"{uuid.uuid4()}.pdf"
            storage_path = f"{storage_dir}/{storage_filename}"

            with open(storage_path, 'wb') as f:
                f.write(pdf_bytes)

            # Create document record
            document = doc_service.create_document_record(
                case_id=analysis_result['case_id'],
                user_id=str(current_user.id),
                file_name=file.filename,
                storage_path=storage_path,
                extracted_text=analysis_result['extracted_text'],
                analysis=analysis_result['analysis'],
                file_size_bytes=analysis_result['file_size_bytes']
            )

            # Extract deadlines
            deadlines = await doc_service.extract_and_save_deadlines(
                document=document,
                extracted_text=analysis_result['extracted_text'],
                analysis=analysis_result['analysis']
            )

            results.append(BulkUploadResult(
                filename=file.filename,
                success=True,
                document_id=str(document.id),
                case_id=analysis_result['case_id'],
                deadlines_extracted=len(deadlines)
            ))

        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            results.append(BulkUploadResult(
                filename=file.filename,
                success=False,
                error=str(e)
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

@router.get("/")
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

    tag = Tag(
        user_id=str(current_user.id),
        name=tag_data.name,
        color=tag_data.color
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)

    return {'id': tag.id, 'name': tag.name, 'color': tag.color}


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

    db.delete(tag)
    db.commit()

    return {'success': True, 'message': 'Tag deleted'}


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

    # Create document-tag relationship
    doc_tag = DocumentTag(document_id=document_id, tag_id=tag_id)
    db.add(doc_tag)
    db.commit()

    return {'success': True, 'message': 'Tag added to document'}


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

    db.delete(doc_tag)
    db.commit()

    return {'success': True, 'message': 'Tag removed from document'}


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document and its associated file"""
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == str(current_user.id)
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete the physical file
    if document.storage_path:
        # Check if it's a Firebase Storage path (starts with 'documents/')
        if document.storage_path.startswith('documents/'):
            try:
                from app.services.firebase_service import firebase_service
                firebase_service.delete_file(document.storage_path)
                logger.info(f"Deleted Firebase file: {document.storage_path}")
            except Exception as e:
                logger.warning(f"Failed to delete Firebase file {document.storage_path}: {e}")
        # Local file path
        elif os.path.exists(document.storage_path):
            try:
                os.remove(document.storage_path)
                logger.info(f"Deleted local file: {document.storage_path}")
            except Exception as e:
                logger.warning(f"Failed to delete local file {document.storage_path}: {e}")

    # Delete from database (cascades to document_tags)
    db.delete(document)
    db.commit()

    return {'success': True, 'message': 'Document deleted'}
