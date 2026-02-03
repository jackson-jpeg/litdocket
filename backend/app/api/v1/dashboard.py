"""
Dashboard API endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.services.dashboard_service import dashboard_service
from app.services.morning_report_service import MorningReportService

router = APIRouter()


@router.get("")
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive dashboard data for the current user

    Returns:
        - Case statistics
        - Deadline alerts (overdue, urgent, upcoming)
        - Recent activity feed
        - Critical cases needing attention
        - Upcoming deadlines (next 30 days)
    """
    import asyncio

    # Run async service in sync context (FastAPI will run this in thread pool)
    dashboard_data = asyncio.run(dashboard_service.get_dashboard_data(
        user_id=current_user.id,
        db=db
    ))

    return dashboard_data


@router.get("/morning-report")
def get_morning_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    MODULE 1: Get Morning Agent Report (Intelligence Briefing)

    Generates an AI-powered daily briefing including:
    - Natural language summary of the day's landscape
    - High-risk alerts (Fatal deadlines, new filings)
    - Actionable insights and next steps
    - Case overview

    This is the "War Room" Intelligence Briefing that appears upon login
    """

    morning_service = MorningReportService(db)

    report = morning_service.generate_morning_report(
        user_id=str(current_user.id),
        last_login=current_user.last_login
    )

    return report


# ============================================================================
# SPLIT DASHBOARD ENDPOINTS (v2)
# Progressive loading endpoints for better UX - each section loads independently
# ============================================================================


@router.get("/alerts")
def get_dashboard_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get deadline alerts (critical path - loads first).

    Returns overdue, urgent, and upcoming deadline counts and details.
    This is the most critical data and should load immediately.
    """
    from datetime import date, timedelta
    from app.models.deadline import Deadline

    today = date.today()
    three_days = today + timedelta(days=3)
    seven_days = today + timedelta(days=7)
    thirty_days = today + timedelta(days=30)

    user_id = str(current_user.id)

    # Base query for pending deadlines with dates
    base_query = db.query(Deadline).filter(
        Deadline.user_id == user_id,
        Deadline.status == 'pending',
        Deadline.deadline_date.isnot(None)
    )

    # Overdue: deadline_date < today
    overdue = base_query.filter(Deadline.deadline_date < today).all()

    # Urgent: today <= deadline_date <= 3 days
    urgent = base_query.filter(
        Deadline.deadline_date >= today,
        Deadline.deadline_date <= three_days
    ).all()

    # Upcoming week: 4-7 days
    upcoming_week = base_query.filter(
        Deadline.deadline_date > three_days,
        Deadline.deadline_date <= seven_days
    ).all()

    # Upcoming month: 8-30 days
    upcoming_month = base_query.filter(
        Deadline.deadline_date > seven_days,
        Deadline.deadline_date <= thirty_days
    ).all()

    def serialize_deadline(d, urgency_level):
        days_until = (d.deadline_date - today).days if d.deadline_date else None
        return {
            "id": str(d.id),
            "case_id": str(d.case_id),
            "title": d.title,
            "deadline_date": d.deadline_date.isoformat() if d.deadline_date else None,
            "priority": d.priority,
            "party_role": d.party_role,
            "action_required": d.action_required,
            "urgency_level": urgency_level,
            "days_until": days_until,
            "rule_citation": d.rule_citation
        }

    return {
        "overdue": {
            "count": len(overdue),
            "deadlines": sorted(
                [serialize_deadline(d, "overdue") for d in overdue],
                key=lambda x: x['deadline_date'] or ''
            )
        },
        "urgent": {
            "count": len(urgent),
            "deadlines": sorted(
                [serialize_deadline(d, "urgent") for d in urgent],
                key=lambda x: x['deadline_date'] or ''
            )
        },
        "upcoming_week": {
            "count": len(upcoming_week),
            "deadlines": sorted(
                [serialize_deadline(d, "upcoming-week") for d in upcoming_week],
                key=lambda x: x['deadline_date'] or ''
            )
        },
        "upcoming_month": {
            "count": len(upcoming_month),
            "deadlines": sorted(
                [serialize_deadline(d, "upcoming-month") for d in upcoming_month],
                key=lambda x: x['deadline_date'] or ''
            )
        }
    }


@router.get("/stats")
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get case statistics (high priority).

    Returns counts of cases, documents, and pending deadlines by category.
    """
    from sqlalchemy import func
    from app.models.case import Case
    from app.models.document import Document
    from app.models.deadline import Deadline

    user_id = str(current_user.id)

    # Get all user's cases
    cases = db.query(Case).filter(
        Case.user_id == user_id,
        Case.status != 'deleted'
    ).all()

    if not cases:
        return {
            "total_cases": 0,
            "total_documents": 0,
            "total_pending_deadlines": 0,
            "by_jurisdiction": {"state": 0, "federal": 0, "unknown": 0},
            "by_case_type": {"civil": 0, "criminal": 0, "appellate": 0, "other": 0}
        }

    # Count documents
    total_documents = db.query(func.count(Document.id)).filter(
        Document.user_id == user_id
    ).scalar() or 0

    # Count pending deadlines
    total_pending_deadlines = db.query(func.count(Deadline.id)).filter(
        Deadline.user_id == user_id,
        Deadline.status == 'pending'
    ).scalar() or 0

    # Count by jurisdiction
    state_cases = len([c for c in cases if c.jurisdiction in ['state', 'florida_state']])
    federal_cases = len([c for c in cases if c.jurisdiction in ['federal', 'florida_federal']])

    # Count by case type
    civil_cases = len([c for c in cases if c.case_type == 'civil'])
    criminal_cases = len([c for c in cases if c.case_type == 'criminal'])
    appellate_cases = len([c for c in cases if c.case_type == 'appellate'])

    return {
        "total_cases": len(cases),
        "total_documents": total_documents,
        "total_pending_deadlines": total_pending_deadlines,
        "by_jurisdiction": {
            "state": state_cases,
            "federal": federal_cases,
            "unknown": len(cases) - state_cases - federal_cases
        },
        "by_case_type": {
            "civil": civil_cases,
            "criminal": criminal_cases,
            "appellate": appellate_cases,
            "other": len(cases) - civil_cases - criminal_cases - appellate_cases
        }
    }


@router.get("/upcoming")
def get_dashboard_upcoming(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30,
    limit: int = 20
):
    """
    Get upcoming deadlines (high priority).

    Returns deadlines for the next N days, sorted by date.
    """
    from datetime import date, timedelta
    from app.models.deadline import Deadline

    today = date.today()
    end_date = today + timedelta(days=days)
    user_id = str(current_user.id)

    deadlines = db.query(Deadline).filter(
        Deadline.user_id == user_id,
        Deadline.status == 'pending',
        Deadline.deadline_date >= today,
        Deadline.deadline_date <= end_date
    ).order_by(Deadline.deadline_date).limit(limit).all()

    def calculate_urgency(d):
        if not d.deadline_date:
            return "unknown"
        days_until = (d.deadline_date - today).days
        if days_until < 0:
            return "overdue"
        elif days_until <= 3:
            return "urgent"
        elif days_until <= 7:
            return "upcoming-week"
        elif days_until <= 30:
            return "upcoming-month"
        return "future"

    return {
        "deadlines": [
            {
                "id": str(d.id),
                "case_id": str(d.case_id),
                "title": d.title,
                "deadline_date": d.deadline_date.isoformat() if d.deadline_date else None,
                "deadline_time": d.deadline_time.isoformat() if d.deadline_time else None,
                "priority": d.priority,
                "party_role": d.party_role,
                "action_required": d.action_required,
                "urgency_level": calculate_urgency(d),
                "days_until": (d.deadline_date - today).days if d.deadline_date else None,
                "rule_citation": d.rule_citation
            }
            for d in deadlines
        ],
        "total_count": len(deadlines),
        "range_days": days
    }


@router.get("/heatmap")
def get_dashboard_heatmap(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get heat map data (lazy loaded - only when tab selected).

    Returns deadline distribution matrix by severity and urgency.
    """
    from datetime import date, timedelta
    from collections import defaultdict
    from app.models.deadline import Deadline

    today = date.today()
    thirty_days = today + timedelta(days=30)
    user_id = str(current_user.id)

    # Query all pending deadlines in range
    deadlines = db.query(Deadline).filter(
        Deadline.user_id == user_id,
        Deadline.status == 'pending',
        Deadline.deadline_date.isnot(None),
        Deadline.deadline_date <= thirty_days
    ).all()

    # Build flat matrix
    matrix_data = defaultdict(lambda: {'count': 0, 'deadlines': []})

    for deadline in deadlines:
        days_until = (deadline.deadline_date - today).days

        # Determine urgency bucket
        if days_until < 0 or days_until == 0:
            urgency = 'today'
        elif days_until <= 3:
            urgency = '3_day'
        elif days_until <= 7:
            urgency = '7_day'
        elif days_until <= 30:
            urgency = '30_day'
        else:
            continue

        # Determine severity
        severity = deadline.priority or 'standard'
        if severity not in ['fatal', 'critical', 'important', 'standard', 'informational']:
            severity = 'standard'

        key = f"{severity}_{urgency}"
        matrix_data[key]['count'] += 1
        matrix_data[key]['deadlines'].append({
            'id': str(deadline.id),
            'case_id': str(deadline.case_id),
            'title': deadline.title,
            'deadline_date': deadline.deadline_date.isoformat(),
            'days_until': days_until
        })

    # Convert to flat list
    flat_list = []
    severities = ['fatal', 'critical', 'important', 'standard', 'informational']
    urgencies = ['today', '3_day', '7_day', '30_day']

    for severity in severities:
        for urgency in urgencies:
            key = f"{severity}_{urgency}"
            data = matrix_data[key]
            flat_list.append({
                'severity': severity,
                'urgency': urgency,
                'count': data['count'],
                'case_ids': list(set(d['case_id'] for d in data['deadlines'])),
                'deadlines': data['deadlines'][:5]  # Limit preview
            })

    # Summary stats
    total_count = sum(d['count'] for d in flat_list)
    critical_count = sum(d['count'] for d in flat_list if d['severity'] in ['fatal', 'critical'])
    today_count = sum(d['count'] for d in flat_list if d['urgency'] == 'today')

    return {
        "matrix": flat_list,
        "summary": {
            "total": total_count,
            "critical": critical_count,
            "today": today_count
        }
    }


@router.get("/activity")
def get_dashboard_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    """
    Get recent activity feed (lazy loaded).

    Returns recent documents and case updates.
    """
    from sqlalchemy import desc
    from app.models.case import Case
    from app.models.document import Document

    user_id = str(current_user.id)

    recent_documents = db.query(Document).filter(
        Document.user_id == user_id
    ).order_by(desc(Document.created_at)).limit(limit).all()

    activities = []
    for doc in recent_documents:
        case = db.query(Case).filter(Case.id == doc.case_id).first()
        activities.append({
            "type": "document_uploaded",
            "timestamp": doc.created_at.isoformat(),
            "case_id": str(doc.case_id),
            "case_number": case.case_number if case else "Unknown",
            "description": f"Uploaded: {doc.file_name}",
            "document_type": doc.document_type,
            "icon": "file-text"
        })

    return {
        "activities": activities,
        "total_count": len(activities)
    }


@router.get("/health")
def get_dashboard_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get matter health cards (lazy loaded).

    Returns health status for each active case with progress and next deadline.
    """
    import asyncio

    # Use existing dashboard service for health cards
    data = asyncio.run(dashboard_service.get_dashboard_data(
        user_id=current_user.id,
        db=db
    ))

    return {
        "health_cards": data.get("matter_health_cards", []),
        "critical_cases": data.get("critical_cases", []),
        "zombie_cases": data.get("zombie_cases", [])
    }
