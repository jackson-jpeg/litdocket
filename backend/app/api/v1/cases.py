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
            'judge': case.judge,
            'status': case.status,
            'case_type': case.case_type,
            'jurisdiction': case.jurisdiction,
            'parties': case.parties,
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


@router.patch("/{case_id}/status")
async def update_case_status(
    case_id: str,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update case status"""
    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Valid statuses
    valid_statuses = ['active', 'pending', 'closed', 'archived']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    case.status = status
    db.commit()

    return {
        'success': True,
        'case_id': case_id,
        'new_status': status
    }


@router.post("/{case_id}/notes")
async def add_case_note(
    case_id: str,
    note: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a note to a case"""
    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Add note to case metadata
    from datetime import datetime
    if not case.case_metadata:
        case.case_metadata = {}

    if 'notes' not in case.case_metadata:
        case.case_metadata['notes'] = []

    new_note = {
        'id': str(len(case.case_metadata['notes']) + 1),
        'content': note.get('content', ''),
        'created_at': datetime.now().isoformat(),
        'created_by': current_user.email
    }

    case.case_metadata['notes'].append(new_note)
    db.commit()

    return {
        'success': True,
        'note': new_note
    }


@router.get("/{case_id}/timeline")
async def get_case_timeline(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get case timeline with all events"""
    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Fetch all related data
    documents = db.query(Document).filter(
        Document.case_id == case_id
    ).order_by(Document.created_at).all()

    deadlines = db.query(Deadline).filter(
        Deadline.case_id == case_id
    ).order_by(Deadline.created_at).all()

    # Build timeline
    timeline = []

    # Add case creation
    timeline.append({
        'type': 'case_created',
        'timestamp': case.created_at.isoformat(),
        'title': 'Case Created',
        'description': f'Case {case.case_number} was created',
        'icon': 'folder-plus'
    })

    # Add document uploads
    for doc in documents:
        timeline.append({
            'type': 'document_uploaded',
            'timestamp': doc.created_at.isoformat(),
            'title': f'Document Uploaded: {doc.file_name}',
            'description': doc.ai_summary or 'Document added to case',
            'document_id': str(doc.id),
            'icon': 'file-text'
        })

    # Add deadlines
    for deadline in deadlines:
        timeline.append({
            'type': 'deadline_added',
            'timestamp': deadline.created_at.isoformat(),
            'title': f'Deadline: {deadline.title}',
            'description': f'Due: {deadline.deadline_date.isoformat() if deadline.deadline_date else "TBD"}',
            'deadline_id': str(deadline.id),
            'icon': 'clock'
        })

    # Add notes
    if case.case_metadata and 'notes' in case.case_metadata:
        for note in case.case_metadata['notes']:
            timeline.append({
                'type': 'note_added',
                'timestamp': note['created_at'],
                'title': 'Note Added',
                'description': note['content'],
                'created_by': note.get('created_by', 'Unknown'),
                'icon': 'message-square'
            })

    # Sort by timestamp
    timeline.sort(key=lambda x: x['timestamp'])

    return {
        'case_id': case_id,
        'case_number': case.case_number,
        'timeline': timeline
    }
