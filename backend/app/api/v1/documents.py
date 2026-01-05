from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid

from app.database import get_db
from app.services.document_service import DocumentService
from app.services.case_summary_service import CaseSummaryService
from app.models.user import User
from app.models.case import Case
from app.models.deadline import Deadline

router = APIRouter()


# Temporary: Mock user for development (replace with Firebase Auth later)
def get_current_user(db: Session = Depends(get_db)) -> User:
    """Get or create demo user for development"""
    demo_email = "demo@docketassist.com"
    user = db.query(User).filter(User.email == demo_email).first()

    if not user:
        user = User(
            email=demo_email,
            password_hash="demo_hash_placeholder",  # Will use Firebase Auth later
            full_name="Demo User",
            firm_name="Demo Law Firm"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


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

    return {
        'id': str(document.id),
        'case_id': str(document.case_id),
        'file_name': document.file_name,
        'document_type': document.document_type,
        'filing_date': document.filing_date.isoformat() if document.filing_date else None,
        'ai_summary': document.ai_summary,
        'extracted_metadata': document.extracted_metadata,
        'created_at': document.created_at.isoformat()
    }
