"""
Global Search API - Search across cases, documents, and deadlines
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.document import Document
from app.models.deadline import Deadline
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/")
async def global_search(
    q: str = Query(..., min_length=2, description="Search query"),
    type_filter: Optional[str] = Query(None, description="Filter by type: cases, documents, deadlines, or all"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results per type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Global search across all user's cases, documents, and deadlines

    Returns results grouped by type with relevance scoring
    """

    search_term = f"%{q.lower()}%"
    results = {
        "query": q,
        "cases": [],
        "documents": [],
        "deadlines": [],
        "total_results": 0
    }

    # Search Cases
    if type_filter in [None, "all", "cases"]:
        cases = db.query(Case).filter(
            Case.user_id == str(current_user.id),
            (
                Case.case_number.ilike(search_term) |
                Case.title.ilike(search_term) |
                Case.court.ilike(search_term) |
                Case.judge.ilike(search_term)
            )
        ).limit(limit).all()

        results["cases"] = [
            {
                "id": str(case.id),
                "case_number": case.case_number,
                "title": case.title,
                "court": case.court,
                "jurisdiction": case.jurisdiction,
                "case_type": case.case_type,
                "filing_date": case.filing_date.isoformat() if case.filing_date else None,
                "match_type": _get_case_match_type(case, q),
                "created_at": case.created_at.isoformat()
            }
            for case in cases
        ]

    # Search Documents
    if type_filter in [None, "all", "documents"]:
        documents = db.query(Document).filter(
            Document.user_id == str(current_user.id),
            (
                Document.file_name.ilike(search_term) |
                Document.document_type.ilike(search_term) |
                Document.ai_summary.ilike(search_term) |
                Document.extracted_text.ilike(search_term)
            )
        ).limit(limit).all()

        # Get case info for each document
        case_map = {}
        for doc in documents:
            if doc.case_id and doc.case_id not in case_map:
                case = db.query(Case).filter(Case.id == doc.case_id).first()
                if case:
                    case_map[doc.case_id] = case.case_number

        results["documents"] = [
            {
                "id": str(doc.id),
                "file_name": doc.file_name,
                "document_type": doc.document_type,
                "ai_summary": doc.ai_summary[:200] if doc.ai_summary else None,
                "case_id": doc.case_id,
                "case_number": case_map.get(doc.case_id),
                "filing_date": doc.filing_date.isoformat() if doc.filing_date else None,
                "match_type": _get_document_match_type(doc, q),
                "created_at": doc.created_at.isoformat()
            }
            for doc in documents
        ]

    # Search Deadlines
    if type_filter in [None, "all", "deadlines"]:
        deadlines = db.query(Deadline).filter(
            Deadline.user_id == str(current_user.id),
            (
                Deadline.title.ilike(search_term) |
                Deadline.description.ilike(search_term) |
                Deadline.party_role.ilike(search_term) |
                Deadline.action_required.ilike(search_term) |
                Deadline.applicable_rule.ilike(search_term)
            )
        ).limit(limit).all()

        # Get case info for each deadline
        case_map = {}
        for deadline in deadlines:
            if deadline.case_id and deadline.case_id not in case_map:
                case = db.query(Case).filter(Case.id == deadline.case_id).first()
                if case:
                    case_map[deadline.case_id] = case.case_number

        results["deadlines"] = [
            {
                "id": str(deadline.id),
                "title": deadline.title,
                "description": deadline.description[:200] if deadline.description else None,
                "deadline_date": deadline.deadline_date.isoformat() if deadline.deadline_date else None,
                "priority": deadline.priority,
                "status": deadline.status,
                "case_id": deadline.case_id,
                "case_number": case_map.get(deadline.case_id),
                "applicable_rule": deadline.applicable_rule,
                "match_type": _get_deadline_match_type(deadline, q),
                "created_at": deadline.created_at.isoformat()
            }
            for deadline in deadlines
        ]

    results["total_results"] = (
        len(results["cases"]) +
        len(results["documents"]) +
        len(results["deadlines"])
    )

    return results


def _get_case_match_type(case: Case, query: str) -> str:
    """Determine what field matched in the case"""
    q = query.lower()
    if case.case_number and q in case.case_number.lower():
        return "case_number"
    elif case.title and q in case.title.lower():
        return "title"
    elif case.court and q in case.court.lower():
        return "court"
    elif case.judge and q in case.judge.lower():
        return "judge"
    return "other"


def _get_document_match_type(document: Document, query: str) -> str:
    """Determine what field matched in the document"""
    q = query.lower()
    if document.file_name and q in document.file_name.lower():
        return "file_name"
    elif document.document_type and q in document.document_type.lower():
        return "document_type"
    elif document.ai_summary and q in document.ai_summary.lower():
        return "summary"
    elif document.extracted_text and q in document.extracted_text.lower():
        return "content"
    return "other"


def _get_deadline_match_type(deadline: Deadline, query: str) -> str:
    """Determine what field matched in the deadline"""
    q = query.lower()
    if deadline.title and q in deadline.title.lower():
        return "title"
    elif deadline.description and q in deadline.description.lower():
        return "description"
    elif deadline.party_role and q in deadline.party_role.lower():
        return "party"
    elif deadline.applicable_rule and q in deadline.applicable_rule.lower():
        return "rule"
    return "other"
