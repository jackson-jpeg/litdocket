from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.document import Document
from app.models.deadline import Deadline
from app.services.case_summary_service import CaseSummaryService
from app.api.v1.documents import get_current_user

router = APIRouter()


@router.get("/")
async def list_cases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all cases for the current user"""
    cases = db.query(Case).filter(Case.user_id == str(current_user.id)).order_by(Case.created_at.desc()).all()

    return [
        {
            'id': str(case.id),
            'case_number': case.case_number,
            'title': case.title,
            'court': case.court,
            'status': case.status,
            'case_type': case.case_type,
            'created_at': case.created_at.isoformat()
        }
        for case in cases
    ]


@router.get("/{case_id}")
async def get_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get case details by ID"""
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return {
        'id': str(case.id),
        'case_number': case.case_number,
        'title': case.title,
        'court': case.court,
        'judge': case.judge,
        'status': case.status,
        'case_type': case.case_type,
        'jurisdiction': case.jurisdiction,
        'district': case.district,
        'circuit': case.circuit,
        'filing_date': case.filing_date.isoformat() if case.filing_date else None,
        'parties': case.parties,
        'metadata': case.case_metadata,
        'created_at': case.created_at.isoformat(),
        'updated_at': case.updated_at.isoformat()
    }


@router.get("/{case_id}/documents")
async def get_case_documents(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents for a case"""
    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    documents = db.query(Document).filter(
        Document.case_id == case_id
    ).order_by(Document.created_at.desc()).all()

    return [
        {
            'id': str(doc.id),
            'file_name': doc.file_name,
            'document_type': doc.document_type,
            'filing_date': doc.filing_date.isoformat() if doc.filing_date else None,
            'ai_summary': doc.ai_summary,
            'created_at': doc.created_at.isoformat()
        }
        for doc in documents
    ]


@router.get("/{case_id}/summary")
async def get_case_summary(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get auto-updating case summary"""
    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check if summary exists in metadata
    if case.case_metadata and 'auto_summary' in case.case_metadata:
        return case.case_metadata['auto_summary']

    # Generate new summary
    documents = db.query(Document).filter(
        Document.case_id == case_id
    ).order_by(Document.created_at.desc()).all()

    deadlines = db.query(Deadline).filter(
        Deadline.case_id == case_id
    ).order_by(Deadline.deadline_date.asc().nullslast()).all()

    summary_service = CaseSummaryService()
    summary = await summary_service.generate_case_summary(case, documents, deadlines, db)

    return summary
