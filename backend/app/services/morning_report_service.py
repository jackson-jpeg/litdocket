"""
Morning Agent Report Service - Module 1: War Room Dashboard
Generates AI-powered daily briefings for attorneys upon login
"""
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.case import Case
from app.models.deadline import Deadline
from app.models.document import Document
from app.models.user import User


class MorningReportService:
    """
    The "Intelligence Briefing" - AI orchestrator for daily legal landscape

    Upon login, generates a natural language summary including:
    - High-risk alerts (Fatal deadlines, new filings)
    - Actionable insights (next steps)
    - Case status overview
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_morning_report(
        self,
        user_id: str,
        last_login: Optional[datetime] = None
    ) -> Dict:
        """
        Generate comprehensive morning briefing for attorney

        Args:
            user_id: User ID
            last_login: User's last login time (to detect "new since last visit")

        Returns:
            {
                'greeting': str,
                'summary': str,
                'high_risk_alerts': List[Dict],
                'new_filings': List[Dict],
                'actionable_insights': List[Dict],
                'deadline_overview': Dict,
                'case_overview': Dict
            }
        """

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        today = date.today()

        # Calculate "new since last login" threshold
        if last_login:
            new_since = last_login
        else:
            # If no last login, consider "new" as anything in last 24 hours
            new_since = datetime.now() - timedelta(days=1)

        # Gather intelligence
        high_risk_alerts = self._get_high_risk_alerts(user_id, today)
        new_filings = self._get_new_filings(user_id, new_since)
        upcoming_deadlines = self._get_upcoming_deadlines(user_id, today)
        case_overview = self._get_case_overview(user_id)
        actionable_insights = self._generate_actionable_insights(
            high_risk_alerts,
            new_filings,
            upcoming_deadlines
        )

        # Generate natural language summary
        summary = self._generate_summary(
            user_name=user.name or "Counselor",
            high_risk_count=len(high_risk_alerts),
            new_filings_count=len(new_filings),
            upcoming_count=len(upcoming_deadlines),
            total_cases=case_overview['total_cases']
        )

        return {
            'greeting': self._generate_greeting(user.name),
            'summary': summary,
            'high_risk_alerts': high_risk_alerts,
            'new_filings': new_filings,
            'upcoming_deadlines': upcoming_deadlines,
            'actionable_insights': actionable_insights,
            'case_overview': case_overview,
            'generated_at': datetime.now().isoformat()
        }

    def _get_high_risk_alerts(self, user_id: str, today: date) -> List[Dict]:
        """
        Get FATAL priority deadlines and overdue deadlines

        These are the "malpractice risk" items that need immediate attention
        """
        alerts = []

        # Query fatal deadlines (active cases only)
        fatal_deadlines = self.db.query(Deadline).join(Case).filter(
            and_(
                Deadline.user_id == user_id,
                Deadline.priority == "fatal",
                Deadline.status == "pending",
                Case.status == "active"
            )
        ).order_by(Deadline.deadline_date).all()

        for deadline in fatal_deadlines:
            days_until = (deadline.deadline_date - today).days if deadline.deadline_date else None

            alert_level = "CRITICAL"
            if days_until is not None:
                if days_until < 0:
                    alert_level = "OVERDUE"
                elif days_until <= 3:
                    alert_level = "URGENT"

            alerts.append({
                'type': 'fatal_deadline',
                'alert_level': alert_level,
                'deadline_id': str(deadline.id),
                'case_id': str(deadline.case_id),
                'case_title': deadline.case.title if deadline.case else "Unknown",
                'deadline_title': deadline.title,
                'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None,
                'days_until': days_until,
                'action_required': deadline.action_required,
                'message': self._format_alert_message(deadline, days_until)
            })

        # Query overdue deadlines (non-fatal but still critical)
        overdue_deadlines = self.db.query(Deadline).join(Case).filter(
            and_(
                Deadline.user_id == user_id,
                Deadline.deadline_date < today,
                Deadline.status == "pending",
                Deadline.priority != "fatal",  # Don't duplicate fatal ones
                Case.status == "active"
            )
        ).order_by(Deadline.deadline_date).limit(10).all()

        for deadline in overdue_deadlines:
            days_overdue = (today - deadline.deadline_date).days

            alerts.append({
                'type': 'overdue_deadline',
                'alert_level': 'OVERDUE',
                'deadline_id': str(deadline.id),
                'case_id': str(deadline.case_id),
                'case_title': deadline.case.title if deadline.case else "Unknown",
                'deadline_title': deadline.title,
                'deadline_date': deadline.deadline_date.isoformat(),
                'days_overdue': days_overdue,
                'priority': deadline.priority,
                'message': f"⚠️ {deadline.title} is {days_overdue} day{'s' if days_overdue != 1 else ''} overdue"
            })

        return alerts

    def _get_new_filings(self, user_id: str, since: datetime) -> List[Dict]:
        """
        Get documents uploaded/analyzed since last login

        This shows what changed in the docket while attorney was away
        """
        new_docs = self.db.query(Document).join(Case).filter(
            and_(
                Document.user_id == user_id,
                Document.created_at > since,
                Case.status == "active"
            )
        ).order_by(Document.created_at.desc()).limit(20).all()

        filings = []
        for doc in new_docs:
            filings.append({
                'document_id': str(doc.id),
                'case_id': str(doc.case_id),
                'case_title': doc.case.title if doc.case else "Unknown",
                'document_title': doc.file_name,
                'document_type': doc.document_type,
                'uploaded_at': doc.created_at.isoformat(),
                'analysis_status': doc.analysis_status,
                'has_deadlines': doc.extracted_metadata.get('deadlines_found', 0) > 0 if doc.extracted_metadata else False,
                'message': f"📄 New {doc.document_type or 'document'} in {doc.case.title if doc.case else 'Unknown Case'}"
            })

        return filings

    def _get_upcoming_deadlines(self, user_id: str, today: date) -> List[Dict]:
        """
        Get deadlines in next 7 days (for "what's coming up" section)
        """
        week_from_now = today + timedelta(days=7)

        upcoming = self.db.query(Deadline).join(Case).filter(
            and_(
                Deadline.user_id == user_id,
                Deadline.deadline_date.between(today, week_from_now),
                Deadline.status == "pending",
                Case.status == "active"
            )
        ).order_by(Deadline.deadline_date).limit(15).all()

        deadlines = []
        for deadline in upcoming:
            days_until = (deadline.deadline_date - today).days

            urgency = "today" if days_until == 0 else "this_week"
            if days_until <= 1:
                urgency = "urgent"
            elif days_until <= 3:
                urgency = "soon"

            deadlines.append({
                'deadline_id': str(deadline.id),
                'case_id': str(deadline.case_id),
                'case_title': deadline.case.title if deadline.case else "Unknown",
                'deadline_title': deadline.title,
                'deadline_date': deadline.deadline_date.isoformat(),
                'days_until': days_until,
                'priority': deadline.priority,
                'urgency': urgency,
                'action_required': deadline.action_required
            })

        return deadlines

    def _get_case_overview(self, user_id: str) -> Dict:
        """
        Get high-level case statistics for overview
        """
        # Active cases
        active_cases = self.db.query(Case).filter(
            and_(
                Case.user_id == user_id,
                Case.status == "active"
            )
        ).count()

        # Cases with critical deadlines this week
        today = date.today()
        week_from_now = today + timedelta(days=7)

        cases_with_urgent_deadlines = self.db.query(Deadline.case_id).filter(
            and_(
                Deadline.user_id == user_id,
                Deadline.deadline_date.between(today, week_from_now),
                Deadline.status == "pending",
                or_(
                    Deadline.priority == "fatal",
                    Deadline.priority == "critical"
                )
            )
        ).distinct().count()

        # Total pending deadlines across all active cases
        total_pending = self.db.query(Deadline).join(Case).filter(
            and_(
                Deadline.user_id == user_id,
                Deadline.status == "pending",
                Case.status == "active"
            )
        ).count()

        return {
            'total_cases': active_cases,
            'cases_needing_attention': cases_with_urgent_deadlines,
            'total_pending_deadlines': total_pending
        }

    def _generate_actionable_insights(
        self,
        high_risk_alerts: List[Dict],
        new_filings: List[Dict],
        upcoming_deadlines: List[Dict]
    ) -> List[Dict]:
        """
        Generate AI-style actionable insights

        Examples:
        - "You have a Fatal deadline tomorrow in Smith v. Jones. I recommend prioritizing this today."
        - "I've analyzed the new Motion to Compel in the Johnson matter. Would you like me to draft a response?"
        """
        insights = []

        # Insight 1: Fatal deadlines this week
        fatal_this_week = [a for a in high_risk_alerts if a['type'] == 'fatal_deadline' and a.get('days_until', 99) <= 7]
        if fatal_this_week:
            insight = {
                'priority': 'critical',
                'icon': '🚨',
                'title': 'Fatal Deadlines Require Immediate Attention',
                'message': f"You have {len(fatal_this_week)} Fatal deadline{'s' if len(fatal_this_week) != 1 else ''} this week. Missing these could result in malpractice liability.",
                'action': 'Review fatal deadlines',
                'related_items': [a['deadline_id'] for a in fatal_this_week]
            }
            insights.append(insight)

        # Insight 2: Overdue items
        overdue = [a for a in high_risk_alerts if a['alert_level'] == 'OVERDUE']
        if overdue:
            insight = {
                'priority': 'high',
                'icon': '⏰',
                'title': 'Overdue Deadlines Need Resolution',
                'message': f"{len(overdue)} deadline{'s' if len(overdue) != 1 else ''} {'are' if len(overdue) != 1 else 'is'} overdue. Consider filing motions for extension or updating status if completed.",
                'action': 'Review overdue items',
                'related_items': [a['deadline_id'] for a in overdue]
            }
            insights.append(insight)

        # Insight 3: New documents need review
        unanalyzed_docs = [f for f in new_filings if f['analysis_status'] == 'pending']
        if unanalyzed_docs:
            insight = {
                'priority': 'medium',
                'icon': '📄',
                'title': 'New Documents Ready for Analysis',
                'message': f"{len(unanalyzed_docs)} new document{'s' if len(unanalyzed_docs) != 1 else ''} uploaded but not yet analyzed. I can extract deadlines and key information.",
                'action': 'Analyze pending documents',
                'related_items': [f['document_id'] for f in unanalyzed_docs]
            }
            insights.append(insight)

        # Insight 4: Busy day ahead
        urgent_today = [d for d in upcoming_deadlines if d['urgency'] in ['today', 'urgent']]
        if urgent_today:
            insight = {
                'priority': 'high',
                'icon': '📅',
                'title': 'Busy Day Ahead',
                'message': f"{len(urgent_today)} deadline{'s' if len(urgent_today) != 1 else ''} due today or tomorrow. Would you like me to prioritize your task list?",
                'action': 'View today\'s deadlines',
                'related_items': [d['deadline_id'] for d in urgent_today]
            }
            insights.append(insight)

        return insights

    def _format_alert_message(self, deadline: Deadline, days_until: Optional[int]) -> str:
        """Format a human-readable alert message for a deadline"""
        if days_until is None:
            return f"🚨 FATAL: {deadline.title} (date TBD)"

        if days_until < 0:
            days_overdue = abs(days_until)
            return f"🚨 OVERDUE: {deadline.title} was due {days_overdue} day{'s' if days_overdue != 1 else ''} ago"
        elif days_until == 0:
            return f"🚨 FATAL: {deadline.title} is DUE TODAY"
        elif days_until == 1:
            return f"🚨 FATAL: {deadline.title} is due TOMORROW"
        elif days_until <= 3:
            return f"🚨 URGENT: {deadline.title} is due in {days_until} days"
        else:
            return f"⚠️ FATAL: {deadline.title} is due in {days_until} days"

    def _generate_greeting(self, user_name: Optional[str]) -> str:
        """Generate time-appropriate greeting"""
        hour = datetime.now().hour

        if hour < 12:
            time_of_day = "morning"
        elif hour < 17:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"

        name = user_name or "Counselor"
        return f"Good {time_of_day}, {name}"

    def _generate_summary(
        self,
        user_name: str,
        high_risk_count: int,
        new_filings_count: int,
        upcoming_count: int,
        total_cases: int
    ) -> str:
        """
        Generate natural language summary of the day's landscape

        This is the "AI orchestrator" that provides the high-level briefing
        """
        summary_parts = []

        # Opening
        summary_parts.append(f"Here's your briefing for today.")

        # Cases overview
        summary_parts.append(f"You have {total_cases} active case{'s' if total_cases != 1 else ''}.")

        # High-risk alerts
        if high_risk_count > 0:
            summary_parts.append(f"⚠️ **{high_risk_count} high-risk alert{'s' if high_risk_count != 1 else ''}** require immediate attention.")
        else:
            summary_parts.append("✅ No critical alerts at this time.")

        # New filings
        if new_filings_count > 0:
            summary_parts.append(f"📄 {new_filings_count} new document{'s' if new_filings_count != 1 else ''} {'have' if new_filings_count != 1 else 'has'} been filed since your last login.")

        # Upcoming deadlines
        if upcoming_count > 0:
            summary_parts.append(f"📅 You have {upcoming_count} deadline{'s' if upcoming_count != 1 else ''} coming up in the next week.")

        return " ".join(summary_parts)
