"""
Dashboard Service - Provides intelligent overview of all cases and deadlines
"""
from typing import Dict, List, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.case import Case
from app.models.document import Document
from app.models.deadline import Deadline


class DashboardService:
    """Service for generating dashboard data and analytics"""

    async def get_dashboard_data(self, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Generate comprehensive dashboard data for a user

        Returns:
            - case_statistics: Total cases, active cases, etc.
            - deadline_alerts: Overdue, urgent, upcoming deadlines
            - recent_activity: Latest documents and case updates
            - critical_cases: Cases needing attention
        """

        # Get all user's cases
        cases = db.query(Case).filter(Case.userId == user_id).all()
        total_cases = len(cases)

        # Get all deadlines
        all_deadlines = db.query(Deadline).filter(Deadline.userId == user_id).all()

        # Calculate deadline alerts
        deadline_alerts = self._calculate_deadline_alerts(all_deadlines)

        # Get case statistics
        case_stats = self._calculate_case_statistics(cases, db)

        # Get recent activity
        recent_activity = await self._get_recent_activity(user_id, db)

        # Get critical cases (cases with urgent deadlines or recent updates)
        critical_cases = self._identify_critical_cases(cases, all_deadlines, db)

        # Get upcoming deadlines (next 30 days)
        upcoming_deadlines = self._get_upcoming_deadlines(all_deadlines, days=30)

        return {
            "case_statistics": case_stats,
            "deadline_alerts": deadline_alerts,
            "recent_activity": recent_activity,
            "critical_cases": critical_cases,
            "upcoming_deadlines": upcoming_deadlines,
            "total_cases": total_cases,
            "generated_at": datetime.now().isoformat()
        }

    def _calculate_deadline_alerts(self, deadlines: List[Deadline]) -> Dict[str, Any]:
        """Calculate deadline alert levels"""

        today = date.today()

        overdue = []
        urgent = []  # Next 3 days
        upcoming_week = []  # 4-7 days
        upcoming_month = []  # 8-30 days

        pending_deadlines = [d for d in deadlines if d.status == 'pending' and d.deadline_date]

        for deadline in pending_deadlines:
            days_until = (deadline.deadline_date - today).days

            if days_until < 0:
                overdue.append(self._serialize_deadline(deadline, "overdue"))
            elif days_until <= 3:
                urgent.append(self._serialize_deadline(deadline, "urgent"))
            elif days_until <= 7:
                upcoming_week.append(self._serialize_deadline(deadline, "upcoming-week"))
            elif days_until <= 30:
                upcoming_month.append(self._serialize_deadline(deadline, "upcoming-month"))

        return {
            "overdue": {
                "count": len(overdue),
                "deadlines": sorted(overdue, key=lambda x: x['deadline_date'])
            },
            "urgent": {
                "count": len(urgent),
                "deadlines": sorted(urgent, key=lambda x: x['deadline_date'])
            },
            "upcoming_week": {
                "count": len(upcoming_week),
                "deadlines": sorted(upcoming_week, key=lambda x: x['deadline_date'])
            },
            "upcoming_month": {
                "count": len(upcoming_month),
                "deadlines": sorted(upcoming_month, key=lambda x: x['deadline_date'])
            }
        }

    def _calculate_case_statistics(self, cases: List[Case], db: Session) -> Dict[str, Any]:
        """Calculate case statistics"""

        # Count documents
        total_documents = db.query(func.count(Document.id)).filter(
            Document.userId == cases[0].userId if cases else None
        ).scalar() or 0

        # Count pending deadlines
        total_pending_deadlines = db.query(func.count(Deadline.id)).filter(
            Deadline.userId == cases[0].userId if cases else None,
            Deadline.status == 'pending'
        ).scalar() or 0

        # Count by jurisdiction
        state_cases = len([c for c in cases if c.jurisdiction == 'state'])
        federal_cases = len([c for c in cases if c.jurisdiction == 'federal'])

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

    async def _get_recent_activity(self, user_id: str, db: Session, limit: int = 10) -> List[Dict]:
        """Get recent activity across all cases"""

        recent_documents = db.query(Document).filter(
            Document.userId == user_id
        ).order_by(desc(Document.created_at)).limit(limit).all()

        activities = []

        for doc in recent_documents:
            # Get case info
            case = db.query(Case).filter(Case.id == doc.caseId).first()

            activities.append({
                "type": "document_uploaded",
                "timestamp": doc.created_at.isoformat(),
                "case_id": doc.caseId,
                "case_number": case.case_number if case else "Unknown",
                "description": f"Uploaded: {doc.file_name}",
                "document_type": doc.document_type,
                "icon": "file-text"
            })

        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)

        return activities[:limit]

    def _identify_critical_cases(
        self,
        cases: List[Case],
        all_deadlines: List[Deadline],
        db: Session
    ) -> List[Dict]:
        """Identify cases that need immediate attention"""

        critical = []
        today = date.today()

        for case in cases:
            # Get case deadlines
            case_deadlines = [d for d in all_deadlines if d.caseId == case.id and d.status == 'pending']

            if not case_deadlines:
                continue

            # Find most urgent deadline
            upcoming_deadlines = [
                d for d in case_deadlines
                if d.deadline_date and d.deadline_date >= today
            ]

            if not upcoming_deadlines:
                continue

            upcoming_deadlines.sort(key=lambda x: x.deadline_date)
            next_deadline = upcoming_deadlines[0]

            days_until = (next_deadline.deadline_date - today).days

            # Critical if deadline within 7 days
            if days_until <= 7:
                critical.append({
                    "case_id": case.id,
                    "case_number": case.case_number,
                    "title": case.title,
                    "court": case.court,
                    "next_deadline_date": next_deadline.deadline_date.isoformat(),
                    "next_deadline_title": next_deadline.title,
                    "days_until_deadline": days_until,
                    "urgency_level": "critical" if days_until <= 3 else "high",
                    "total_pending_deadlines": len(case_deadlines)
                })

        # Sort by urgency
        critical.sort(key=lambda x: x['days_until_deadline'])

        return critical

    def _get_upcoming_deadlines(self, deadlines: List[Deadline], days: int = 30) -> List[Dict]:
        """Get upcoming deadlines sorted by date"""

        today = date.today()
        end_date = today + timedelta(days=days)

        upcoming = [
            self._serialize_deadline(d, self._calculate_urgency_level(d))
            for d in deadlines
            if d.status == 'pending'
            and d.deadline_date
            and today <= d.deadline_date <= end_date
        ]

        upcoming.sort(key=lambda x: x['deadline_date'])

        return upcoming

    def _serialize_deadline(self, deadline: Deadline, urgency_level: str) -> Dict:
        """Serialize deadline to dict with urgency info"""

        today = date.today()
        days_until = (deadline.deadline_date - today).days if deadline.deadline_date else None

        return {
            "id": deadline.id,
            "case_id": deadline.caseId,
            "title": deadline.title,
            "deadline_date": deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            "deadline_time": deadline.deadline_time.isoformat() if deadline.deadline_time else None,
            "priority": deadline.priority,
            "party_role": deadline.party_role,
            "action_required": deadline.action_required,
            "urgency_level": urgency_level,
            "days_until": days_until,
            "rule_citation": deadline.rule_citation
        }

    def _calculate_urgency_level(self, deadline: Deadline) -> str:
        """Calculate urgency level for a deadline"""

        if not deadline.deadline_date:
            return "unknown"

        today = date.today()
        days_until = (deadline.deadline_date - today).days

        if days_until < 0:
            return "overdue"
        elif days_until <= 3:
            return "urgent"
        elif days_until <= 7:
            return "upcoming-week"
        elif days_until <= 30:
            return "upcoming-month"
        else:
            return "future"


# Singleton instance
dashboard_service = DashboardService()
