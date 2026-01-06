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
        cases = db.query(Case).filter(Case.user_id == user_id).all()
        total_cases = len(cases)

        # Get all deadlines
        all_deadlines = db.query(Deadline).filter(Deadline.user_id == user_id).all()

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

        # MODULE 1: Deadline Heat Map (Fatality x Urgency matrix)
        heat_map = self._generate_heat_map(all_deadlines)

        # MODULE 1: Matter Health Cards
        matter_health_cards = self._generate_matter_health_cards(cases, all_deadlines, db)

        return {
            "case_statistics": case_stats,
            "deadline_alerts": deadline_alerts,
            "recent_activity": recent_activity,
            "critical_cases": critical_cases,
            "upcoming_deadlines": upcoming_deadlines,
            "total_cases": total_cases,
            # MODULE 1: War Room enhancements
            "heat_map": heat_map,
            "matter_health_cards": matter_health_cards,
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
            Document.user_id == cases[0].user_id if cases else None
        ).scalar() or 0

        # Count pending deadlines
        total_pending_deadlines = db.query(func.count(Deadline.id)).filter(
            Deadline.user_id == cases[0].user_id if cases else None,
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
            Document.user_id == user_id
        ).order_by(desc(Document.created_at)).limit(limit).all()

        activities = []

        for doc in recent_documents:
            # Get case info
            case = db.query(Case).filter(Case.id == doc.case_id).first()

            activities.append({
                "type": "document_uploaded",
                "timestamp": doc.created_at.isoformat(),
                "case_id": doc.case_id,
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
            case_deadlines = [d for d in all_deadlines if d.case_id == case.id and d.status == 'pending']

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
            "case_id": deadline.case_id,
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

    def _generate_heat_map(self, deadlines: List[Deadline]) -> Dict[str, Any]:
        """
        MODULE 1: Generate Deadline Heat Map

        Visual matrix categorizing deadlines by:
        - Fatality (Red: Fatal; Orange: Critical; Yellow: Important; Green: Standard)
        - Urgency (Today, 3-Day, 7-Day, 30-Day)

        This provides instant visual triage for attorneys
        """
        today = date.today()

        # Initialize matrix
        heat_map = {
            'fatal': {'today': [], '3_day': [], '7_day': [], '30_day': []},
            'critical': {'today': [], '3_day': [], '7_day': [], '30_day': []},
            'important': {'today': [], '3_day': [], '7_day': [], '30_day': []},
            'standard': {'today': [], '3_day': [], '7_day': [], '30_day': []},
            'informational': {'today': [], '3_day': [], '7_day': [], '30_day': []}
        }

        # Categorize pending deadlines
        pending = [d for d in deadlines if d.status == 'pending' and d.deadline_date]

        for deadline in pending:
            days_until = (deadline.deadline_date - today).days

            # Determine urgency bucket
            if days_until < 0 or days_until == 0:
                urgency_bucket = 'today'
            elif days_until <= 3:
                urgency_bucket = '3_day'
            elif days_until <= 7:
                urgency_bucket = '7_day'
            elif days_until <= 30:
                urgency_bucket = '30_day'
            else:
                continue  # Beyond 30 days, not on heat map

            # Determine fatality level
            fatality = deadline.priority or 'standard'
            if fatality not in heat_map:
                fatality = 'standard'

            # Add to matrix
            heat_map[fatality][urgency_bucket].append({
                'id': str(deadline.id),
                'case_id': str(deadline.case_id),
                'title': deadline.title,
                'deadline_date': deadline.deadline_date.isoformat(),
                'days_until': days_until,
                'action_required': deadline.action_required,
                'case_title': deadline.case.title if deadline.case else "Unknown"
            })

        # Calculate totals for each cell
        summary = {
            'total_deadlines': sum(len(v) for row in heat_map.values() for v in row.values()),
            'by_fatality': {
                'fatal': sum(len(v) for v in heat_map['fatal'].values()),
                'critical': sum(len(v) for v in heat_map['critical'].values()),
                'important': sum(len(v) for v in heat_map['important'].values()),
                'standard': sum(len(v) for v in heat_map['standard'].values()),
                'informational': sum(len(v) for v in heat_map['informational'].values())
            },
            'by_urgency': {
                'today': sum(len(heat_map[f]['today']) for f in heat_map.keys()),
                '3_day': sum(len(heat_map[f]['3_day']) for f in heat_map.keys()),
                '7_day': sum(len(heat_map[f]['7_day']) for f in heat_map.keys()),
                '30_day': sum(len(heat_map[f]['30_day']) for f in heat_map.keys())
            }
        }

        return {
            'matrix': heat_map,
            'summary': summary
        }

    def _generate_matter_health_cards(
        self,
        cases: List[Case],
        all_deadlines: List[Deadline],
        db: Session
    ) -> List[Dict]:
        """
        MODULE 1: Generate Matter Health Cards

        "Loose view" of all cases showing:
        - Progress bar (completed vs pending tasks)
        - Judge name
        - Next deadline
        - Overall health status
        """
        health_cards = []
        today = date.today()

        for case in cases:
            if case.status != 'active':
                continue

            # Get case deadlines
            case_deadlines = [d for d in all_deadlines if d.case_id == case.id]

            if not case_deadlines:
                continue

            # Calculate progress
            total_deadlines = len(case_deadlines)
            completed_deadlines = len([d for d in case_deadlines if d.status == 'completed'])
            pending_deadlines = len([d for d in case_deadlines if d.status == 'pending'])

            progress_percentage = int((completed_deadlines / total_deadlines * 100)) if total_deadlines > 0 else 0

            # Find next deadline
            upcoming = [
                d for d in case_deadlines
                if d.status == 'pending' and d.deadline_date and d.deadline_date >= today
            ]
            upcoming.sort(key=lambda x: x.deadline_date)

            next_deadline = None
            next_deadline_urgency = 'normal'
            if upcoming:
                next_dl = upcoming[0]
                days_until = (next_dl.deadline_date - today).days

                next_deadline = {
                    'title': next_dl.title,
                    'date': next_dl.deadline_date.isoformat(),
                    'days_until': days_until,
                    'priority': next_dl.priority
                }

                # Determine urgency
                if days_until <= 1 or next_dl.priority == 'fatal':
                    next_deadline_urgency = 'critical'
                elif days_until <= 3 or next_dl.priority == 'critical':
                    next_deadline_urgency = 'urgent'
                elif days_until <= 7:
                    next_deadline_urgency = 'attention'

            # Overall health status
            health_status = 'healthy'
            if next_deadline_urgency == 'critical':
                health_status = 'critical'
            elif next_deadline_urgency == 'urgent':
                health_status = 'needs_attention'
            elif pending_deadlines > completed_deadlines:
                health_status = 'busy'

            # Count documents
            doc_count = db.query(func.count(Document.id)).filter(
                Document.case_id == case.id
            ).scalar() or 0

            health_cards.append({
                'case_id': str(case.id),
                'case_number': case.case_number,
                'title': case.title,
                'court': case.court or 'Unknown Court',
                'judge': case.judge or 'Unassigned',
                'jurisdiction': case.jurisdiction,
                'case_type': case.case_type,
                'progress': {
                    'completed': completed_deadlines,
                    'pending': pending_deadlines,
                    'total': total_deadlines,
                    'percentage': progress_percentage
                },
                'next_deadline': next_deadline,
                'next_deadline_urgency': next_deadline_urgency,
                'health_status': health_status,
                'document_count': doc_count,
                'filing_date': case.filing_date.isoformat() if case.filing_date else None
            })

        # Sort by health status priority (critical first, then urgent, etc.)
        status_order = {'critical': 0, 'needs_attention': 1, 'busy': 2, 'healthy': 3}
        health_cards.sort(key=lambda x: (
            status_order.get(x['health_status'], 99),
            (x.get('next_deadline') or {}).get('days_until', 999)
        ))

        return health_cards


# Singleton instance
dashboard_service = DashboardService()
