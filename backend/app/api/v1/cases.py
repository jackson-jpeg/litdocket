from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.document import Document
from app.models.deadline import Deadline
from app.models.case_template import CaseTemplate
from app.services.case_summary_service import CaseSummaryService
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ===================
# PYDANTIC MODELS
# ===================

class CaseCreate(BaseModel):
    case_number: str
    title: str
    court: Optional[str] = None
    judge: Optional[str] = None
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    district: Optional[str] = None
    circuit: Optional[str] = None
    parties: Optional[List[dict]] = None


class CaseUpdate(BaseModel):
    """Schema for updating case fields"""
    title: Optional[str] = None
    court: Optional[str] = None
    judge: Optional[str] = None
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    district: Optional[str] = None
    circuit: Optional[str] = None
    parties: Optional[List[dict]] = None
    case_metadata: Optional[dict] = None
    filing_date: Optional[str] = None


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    case_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    court: Optional[str] = None
    district: Optional[str] = None
    circuit: Optional[str] = None
    party_roles: Optional[List[dict]] = None
    default_deadlines: Optional[List[dict]] = None


@router.get("")
def list_cases(
    include_archived: bool = Query(True, description="Include archived cases"),
    status: Optional[str] = Query(None, description="Filter by status"),
    case_type: Optional[str] = Query(None, description="Filter by case type"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all cases for the current user with optional filtering"""
    query = db.query(Case).filter(
        Case.user_id == str(current_user.id),
        Case.status != 'deleted'  # Only exclude hard-deleted cases, match dashboard logic
    )

    # Filter archived cases if not requested
    if not include_archived:
        query = query.filter(Case.status != 'archived')

    # Apply optional filters
    if status:
        query = query.filter(Case.status == status)
    if case_type:
        query = query.filter(Case.case_type == case_type)
    if jurisdiction:
        query = query.filter(Case.jurisdiction == jurisdiction)

    cases = query.order_by(Case.created_at.desc()).all()

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
def get_case(
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
def get_case_documents(
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

    from app.services.firebase_service import firebase_service

    return [
        {
            'id': str(doc.id),
            'file_name': doc.file_name,
            'document_type': doc.document_type,
            'filing_date': doc.filing_date.isoformat() if doc.filing_date else None,
            'ai_summary': doc.ai_summary,
            'storage_url': firebase_service.get_download_url(doc.storage_path) if doc.storage_path else None,
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
def update_case_status(
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


@router.patch("/{case_id}")
async def update_case(
    case_id: str,
    update_data: CaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update case fields (title, court, judge, parties, etc.)

    This endpoint allows full editing of case metadata.
    Ownership is verified - users can only update their own cases.
    """
    # Get case with ownership check
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Track what changed for audit
    changes = []

    # Update fields if provided
    if update_data.title is not None:
        old_title = case.title
        case.title = update_data.title
        changes.append(f"title: '{old_title}' → '{update_data.title}'")

    if update_data.court is not None:
        old_court = case.court
        case.court = update_data.court
        changes.append(f"court: '{old_court}' → '{update_data.court}'")

    if update_data.judge is not None:
        old_judge = case.judge
        case.judge = update_data.judge
        changes.append(f"judge: '{old_judge}' → '{update_data.judge}'")

    if update_data.case_type is not None:
        old_type = case.case_type
        case.case_type = update_data.case_type
        changes.append(f"case_type: '{old_type}' → '{update_data.case_type}'")

    if update_data.jurisdiction is not None:
        old_jurisdiction = case.jurisdiction
        case.jurisdiction = update_data.jurisdiction
        changes.append(f"jurisdiction: '{old_jurisdiction}' → '{update_data.jurisdiction}'")

    if update_data.district is not None:
        case.district = update_data.district
        changes.append("district updated")

    if update_data.circuit is not None:
        case.circuit = update_data.circuit
        changes.append("circuit updated")

    if update_data.parties is not None:
        case.parties = update_data.parties
        changes.append(f"parties updated ({len(update_data.parties)} parties)")

    if update_data.case_metadata is not None:
        case.case_metadata = update_data.case_metadata
        changes.append("case_metadata updated")

    if update_data.filing_date is not None:
        case.filing_date = update_data.filing_date
        changes.append(f"filing_date: {update_data.filing_date}")

    db.commit()
    db.refresh(case)

    logger.info(f"Case {case_id} updated by user {current_user.id}: {changes}")

    # Update case summary to reflect changes
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=case_id,
            event_type="case_updated",
            event_details={
                "changes": changes
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'case_id': case_id,
        'changes': changes,
        'message': f"Case updated successfully"
    }


@router.post("/{case_id}/notes")
def add_case_note(
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
def get_case_timeline(
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


# ===================
# CASE ARCHIVE
# ===================

@router.post("/{case_id}/archive")
def archive_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archive a case (hides from main list)"""
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = 'archived'
    db.commit()

    return {
        'success': True,
        'case_id': case_id,
        'message': f'Case {case.case_number} has been archived'
    }


@router.post("/{case_id}/unarchive")
def unarchive_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Restore an archived case"""
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = 'active'
    db.commit()

    return {
        'success': True,
        'case_id': case_id,
        'message': f'Case {case.case_number} has been restored'
    }


@router.delete("/{case_id}")
def delete_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently delete a case and all related data"""
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case_number = case.case_number
    db.delete(case)  # Cascades to documents, deadlines, etc.
    db.commit()

    return {
        'success': True,
        'message': f'Case {case_number} has been permanently deleted'
    }


# ===================
# CASE TEMPLATES
# ===================

@router.get("/templates/")
def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all case templates for current user"""
    templates = db.query(CaseTemplate).filter(
        CaseTemplate.user_id == str(current_user.id)
    ).order_by(CaseTemplate.created_at.desc()).all()

    return [
        {
            'id': str(t.id),
            'name': t.name,
            'description': t.description,
            'case_type': t.case_type,
            'jurisdiction': t.jurisdiction,
            'court': t.court,
            'times_used': t.times_used,
            'created_at': t.created_at.isoformat()
        }
        for t in templates
    ]


@router.post("/templates/")
def create_template(
    template_data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new case template"""
    template = CaseTemplate(
        user_id=str(current_user.id),
        name=template_data.name,
        description=template_data.description,
        case_type=template_data.case_type,
        jurisdiction=template_data.jurisdiction,
        court=template_data.court,
        district=template_data.district,
        circuit=template_data.circuit,
        party_roles=template_data.party_roles,
        default_deadlines=template_data.default_deadlines
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return {
        'id': str(template.id),
        'name': template.name,
        'message': 'Template created successfully'
    }


@router.post("/templates/{template_id}/create-case")
def create_case_from_template(
    template_id: str,
    case_data: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new case from a template"""
    # Get template
    template = db.query(CaseTemplate).filter(
        CaseTemplate.id == template_id,
        CaseTemplate.user_id == str(current_user.id)
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Create case with template defaults + provided data
    new_case = Case(
        user_id=str(current_user.id),
        case_number=case_data.case_number,
        title=case_data.title,
        court=case_data.court or template.court,
        judge=case_data.judge,
        case_type=case_data.case_type or template.case_type,
        jurisdiction=case_data.jurisdiction or template.jurisdiction,
        district=case_data.district or template.district,
        circuit=case_data.circuit or template.circuit,
        parties=case_data.parties or [],
        status='active'
    )
    db.add(new_case)
    db.flush()  # Get case ID

    # Create default deadlines from template
    deadlines_created = 0
    if template.default_deadlines:
        from datetime import datetime, timedelta

        for dl_template in template.default_deadlines:
            deadline_date = None
            if dl_template.get('days_from_filing') and new_case.filing_date:
                deadline_date = new_case.filing_date + timedelta(days=dl_template['days_from_filing'])

            deadline = Deadline(
                case_id=str(new_case.id),
                user_id=str(current_user.id),
                title=dl_template.get('title', 'Deadline'),
                description=dl_template.get('description', ''),
                deadline_date=deadline_date,
                applicable_rule=dl_template.get('rule'),
                priority=dl_template.get('priority', 'medium'),
                status='pending'
            )
            db.add(deadline)
            deadlines_created += 1

    # Update template usage count
    template.times_used = str(int(template.times_used or 0) + 1)

    db.commit()
    db.refresh(new_case)

    return {
        'success': True,
        'case_id': str(new_case.id),
        'case_number': new_case.case_number,
        'deadlines_created': deadlines_created,
        'message': f'Case created from template "{template.name}"'
    }


@router.post("/{case_id}/save-as-template")
def save_case_as_template(
    case_id: str,
    template_name: str = Query(..., description="Name for the template"),
    template_description: Optional[str] = Query(None, description="Template description"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save an existing case as a template"""
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Extract party roles from case parties
    party_roles = []
    if case.parties:
        for party in case.parties:
            party_roles.append({
                'role': party.get('role', 'Party'),
                'name_placeholder': True
            })

    # Create template from case
    template = CaseTemplate(
        user_id=str(current_user.id),
        name=template_name,
        description=template_description or f'Template based on {case.case_number}',
        case_type=case.case_type,
        jurisdiction=case.jurisdiction,
        court=case.court,
        district=case.district,
        circuit=case.circuit,
        party_roles=party_roles
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return {
        'success': True,
        'template_id': str(template.id),
        'template_name': template.name,
        'message': f'Template "{template_name}" created from case {case.case_number}'
    }


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a case template"""
    template = db.query(CaseTemplate).filter(
        CaseTemplate.id == template_id,
        CaseTemplate.user_id == str(current_user.id)
    ).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template_name = template.name
    db.delete(template)
    db.commit()

    return {
        'success': True,
        'message': f'Template "{template_name}" has been deleted'
    }
