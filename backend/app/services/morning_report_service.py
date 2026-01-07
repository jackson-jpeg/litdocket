"""
Morning Agent Report Service - Intelligence Briefing
Professional daily briefings that feel smart, not robotic
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import random

from app.models.case import Case
from app.models.deadline import Deadline
from app.models.document import Document
from app.models.user import User


class MorningReportService:
    """
    Professional intelligence briefing for attorneys.
    Generates contextual, varied content that feels human-written.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_morning_report(
        self,
        user_id: str,
        last_login: Optional[datetime] = None
    ) -> Dict:
        """Generate the complete morning intelligence briefing"""

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        today = date.today()
        now = datetime.now()

        # Calculate "new since last login" threshold
        if last_login:
            new_since = last_login
        else:
            new_since = datetime.now() - timedelta(days=1)

        # Gather all intelligence
        high_risk_alerts = self._get_high_risk_alerts(user_id, today)
        new_filings = self._get_new_filings(user_id, new_since)
        upcoming_deadlines = self._get_upcoming_deadlines(user_id, today)
        case_overview = self._get_case_overview(user_id)
        week_stats = self._get_week_statistics(user_id, today)
        milestones = self._get_upcoming_milestones(user_id, today)

        # Analyze workload
        workload = self._analyze_workload(high_risk_alerts, upcoming_deadlines, today)

        # Generate actionable insights
        actionable_insights = self._generate_actionable_insights(
            high_risk_alerts,
            new_filings,
            upcoming_deadlines,
            week_stats,
            milestones
        )

        # Generate intelligent greeting and summary
        user_name = self._get_first_name(user.name)
        greeting = self._generate_smart_greeting(user_name, now, workload, week_stats)
        summary = self._generate_intelligent_summary(
            user_name=user_name,
            workload=workload,
            case_overview=case_overview,
            week_stats=week_stats,
            high_risk_count=len(high_risk_alerts),
            upcoming_count=len(upcoming_deadlines),
            today=today
        )

        return {
            'greeting': greeting,
            'summary': summary,
            'high_risk_alerts': high_risk_alerts,
            'new_filings': new_filings,
            'upcoming_deadlines': upcoming_deadlines,
            'actionable_insights': actionable_insights,
            'case_overview': case_overview,
            'week_stats': week_stats,
            'milestones': milestones,
            'workload_level': workload['level'],
            'generated_at': datetime.now().isoformat()
        }

    def _get_first_name(self, full_name: Optional[str]) -> str:
        """Extract first name from full name"""
        if not full_name:
            return "Counselor"
        return full_name.split()[0]

    def _analyze_workload(
        self,
        high_risk_alerts: List[Dict],
        upcoming_deadlines: List[Dict],
        today: date
    ) -> Dict:
        """Analyze current workload intensity"""

        overdue_count = len([a for a in high_risk_alerts if a.get('alert_level') == 'OVERDUE'])
        fatal_count = len([a for a in high_risk_alerts if a.get('type') == 'fatal_deadline'])
        today_count = len([d for d in upcoming_deadlines if d.get('days_until', 99) == 0])
        week_count = len([d for d in upcoming_deadlines if d.get('days_until', 99) <= 7])

        # Calculate intensity score
        score = (overdue_count * 10) + (fatal_count * 5) + (today_count * 3) + (week_count * 0.5)

        if score >= 20:
            level = 'heavy'
            description = 'demanding'
        elif score >= 10:
            level = 'moderate'
            description = 'active'
        elif score >= 3:
            level = 'light'
            description = 'manageable'
        else:
            level = 'clear'
            description = 'clear'

        return {
            'level': level,
            'description': description,
            'score': score,
            'overdue': overdue_count,
            'fatal': fatal_count,
            'today': today_count,
            'this_week': week_count
        }

    def _get_week_statistics(self, user_id: str, today: date) -> Dict:
        """Get statistics for the current week"""

        # Start of current week (Monday)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Deadlines completed this week
        completed_this_week = self.db.query(Deadline).filter(
            and_(
                Deadline.user_id == user_id,
                Deadline.status == "completed",
                Deadline.updated_at >= week_start
            )
        ).count()

        # Deadlines due this week
        due_this_week = self.db.query(Deadline).join(Case).filter(
            and_(
                Deadline.user_id == user_id,
                Deadline.deadline_date.between(week_start, week_end),
                Deadline.status == "pending",
                Case.status == "active"
            )
        ).count()

        # Documents processed this week
        docs_this_week = self.db.query(Document).filter(
            and_(
                Document.user_id == user_id,
                Document.created_at >= week_start
            )
        ).count()

        return {
            'completed_this_week': completed_this_week,
            'due_this_week': due_this_week,
            'docs_processed': docs_this_week,
            'week_start': week_start.isoformat(),
            'day_of_week': today.strftime('%A'),
            'is_monday': today.weekday() == 0,
            'is_friday': today.weekday() == 4,
            'is_weekend': today.weekday() >= 5
        }

    def _get_upcoming_milestones(self, user_id: str, today: date) -> List[Dict]:
        """Get notable upcoming case milestones (trials, hearings, etc.)"""

        milestones = []
        next_60_days = today + timedelta(days=60)

        # Look for trial dates, hearings, mediations
        milestone_types = ['trial', 'hearing', 'mediation', 'deposition', 'conference']

        significant_deadlines = self.db.query(Deadline).join(Case).filter(
            and_(
                Deadline.user_id == user_id,
                Deadline.deadline_date.between(today, next_60_days),
                Deadline.status == "pending",
                Case.status == "active",
                or_(*[Deadline.deadline_type.ilike(f"%{t}%") for t in milestone_types])
            )
        ).order_by(Deadline.deadline_date).limit(5).all()

        for deadline in significant_deadlines:
            days_until = (deadline.deadline_date - today).days

            milestones.append({
                'type': deadline.deadline_type,
                'case_title': deadline.case.title if deadline.case else "Unknown",
                'case_id': str(deadline.case_id),
                'date': deadline.deadline_date.isoformat(),
                'days_until': days_until,
                'title': deadline.title
            })

        return milestones

    def _generate_smart_greeting(
        self,
        user_name: str,
        now: datetime,
        workload: Dict,
        week_stats: Dict
    ) -> str:
        """Generate an intelligent, contextual greeting"""

        hour = now.hour
        day_name = week_stats['day_of_week']

        # Time-based prefix
        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"

        # Build contextual greeting based on day and workload
        if week_stats['is_monday']:
            # Monday greetings
            openers = [
                f"{time_greeting}, {user_name}. Let's set the pace for the week.",
                f"{time_greeting}, {user_name}. Here's your week at a glance.",
                f"{time_greeting}, {user_name}. Fresh week, fresh start.",
            ]
        elif week_stats['is_friday']:
            # Friday greetings
            if workload['level'] == 'clear':
                openers = [
                    f"{time_greeting}, {user_name}. Looking good heading into the weekend.",
                    f"{time_greeting}, {user_name}. Strong position for the week's close.",
                ]
            else:
                openers = [
                    f"{time_greeting}, {user_name}. Let's close out the week strong.",
                    f"{time_greeting}, {user_name}. Final push before the weekend.",
                ]
        elif week_stats['is_weekend']:
            openers = [
                f"{time_greeting}, {user_name}. Catching up on the weekend?",
                f"{time_greeting}, {user_name}. Burning the weekend oil, I see.",
            ]
        else:
            # Regular weekday greetings based on workload
            if workload['level'] == 'heavy':
                openers = [
                    f"{time_greeting}, {user_name}. Busy day ahead.",
                    f"{time_greeting}, {user_name}. Let's tackle what matters most.",
                ]
            elif workload['level'] == 'moderate':
                openers = [
                    f"{time_greeting}, {user_name}. Here's what's on deck.",
                    f"{time_greeting}, {user_name}.",
                ]
            elif workload['level'] == 'light':
                openers = [
                    f"{time_greeting}, {user_name}. Manageable day ahead.",
                    f"{time_greeting}, {user_name}. Looking organized today.",
                ]
            else:
                openers = [
                    f"{time_greeting}, {user_name}. You're in good shape.",
                    f"{time_greeting}, {user_name}. Clear skies on the docket.",
                ]

        return random.choice(openers)

    def _generate_intelligent_summary(
        self,
        user_name: str,
        workload: Dict,
        case_overview: Dict,
        week_stats: Dict,
        high_risk_count: int,
        upcoming_count: int,
        today: date
    ) -> str:
        """Generate a natural, intelligent summary paragraph"""

        parts = []

        # Lead with the most important information
        if workload['overdue'] > 0:
            if workload['overdue'] == 1:
                parts.append("You have 1 overdue deadline that needs immediate attention.")
            else:
                parts.append(f"You have {workload['overdue']} overdue deadlines requiring immediate attention.")

        if workload['fatal'] > 0 and workload['overdue'] == 0:
            if workload['fatal'] == 1:
                parts.append("One fatal deadline is approaching.")
            else:
                parts.append(f"{workload['fatal']} fatal deadlines are on the horizon.")

        # Today's workload
        if workload['today'] > 0:
            if workload['today'] == 1:
                parts.append("1 deadline is due today.")
            else:
                parts.append(f"{workload['today']} deadlines are due today.")

        # Week ahead context
        if workload['this_week'] > 0 and workload['today'] == 0:
            if workload['this_week'] == 1:
                parts.append("1 deadline this week.")
            elif workload['this_week'] <= 3:
                parts.append(f"Light week with {workload['this_week']} upcoming deadlines.")
            elif workload['this_week'] <= 7:
                parts.append(f"{workload['this_week']} deadlines on deck this week.")
            else:
                parts.append(f"Busy week ahead with {workload['this_week']} deadlines.")

        # Productivity acknowledgment
        if week_stats['completed_this_week'] > 0:
            if week_stats['completed_this_week'] >= 5:
                parts.append(f"You've cleared {week_stats['completed_this_week']} items this week - strong progress.")
            elif week_stats['completed_this_week'] >= 2:
                parts.append(f"{week_stats['completed_this_week']} deadlines completed this week.")

        # Case context
        if case_overview['total_cases'] > 0:
            if case_overview['cases_needing_attention'] > 0:
                parts.append(f"Across your {case_overview['total_cases']} active cases, {case_overview['cases_needing_attention']} need attention this week.")
            elif len(parts) == 0:  # Only add if we haven't said much yet
                parts.append(f"Managing {case_overview['total_cases']} active cases with {case_overview['total_pending_deadlines']} pending deadlines.")

        # Handle empty state
        if len(parts) == 0:
            if case_overview['total_cases'] == 0:
                return "No active cases on your docket. Ready to add your first case?"
            else:
                return f"All clear. Your {case_overview['total_cases']} active cases are in good standing with no urgent deadlines."

        return " ".join(parts)

    def _get_high_risk_alerts(self, user_id: str, today: date) -> List[Dict]:
        """Get FATAL priority deadlines and overdue deadlines"""
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
                'case_number': deadline.case.case_number if deadline.case else None,
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
                Deadline.priority != "fatal",
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
                'case_number': deadline.case.case_number if deadline.case else None,
                'case_title': deadline.case.title if deadline.case else "Unknown",
                'deadline_title': deadline.title,
                'deadline_date': deadline.deadline_date.isoformat(),
                'days_overdue': days_overdue,
                'priority': deadline.priority,
                'message': self._format_overdue_message(deadline.title, days_overdue)
            })

        return alerts

    def _get_new_filings(self, user_id: str, since: datetime) -> List[Dict]:
        """Get documents uploaded/analyzed since last login"""
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
                'has_deadlines': doc.extracted_metadata.get('deadlines_found', 0) > 0 if doc.extracted_metadata else False
            })

        return filings

    def _get_upcoming_deadlines(self, user_id: str, today: date) -> List[Dict]:
        """Get deadlines in next 7 days"""
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

            urgency = "this_week"
            if days_until == 0:
                urgency = "today"
            elif days_until == 1:
                urgency = "tomorrow"
            elif days_until <= 3:
                urgency = "soon"

            deadlines.append({
                'deadline_id': str(deadline.id),
                'case_id': str(deadline.case_id),
                'case_number': deadline.case.case_number if deadline.case else None,
                'case_title': deadline.case.title if deadline.case else "Unknown",
                'deadline_title': deadline.title,
                'deadline_date': deadline.deadline_date.isoformat(),
                'deadline_date_formatted': deadline.deadline_date.strftime('%b %d'),
                'days_until': days_until,
                'priority': deadline.priority,
                'urgency': urgency,
                'action_required': deadline.action_required
            })

        return deadlines

    def _get_case_overview(self, user_id: str) -> Dict:
        """Get high-level case statistics"""
        active_cases = self.db.query(Case).filter(
            and_(
                Case.user_id == user_id,
                Case.status == "active"
            )
        ).count()

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
        upcoming_deadlines: List[Dict],
        week_stats: Dict,
        milestones: List[Dict]
    ) -> List[Dict]:
        """Generate smart, prioritized actionable insights"""
        insights = []

        # Insight: Fatal deadlines this week
        fatal_this_week = [a for a in high_risk_alerts if a['type'] == 'fatal_deadline' and a.get('days_until', 99) <= 7 and a.get('days_until', -1) >= 0]
        if fatal_this_week:
            count = len(fatal_this_week)
            insights.append({
                'priority': 'critical',
                'icon': '🚨',
                'title': f"Fatal Deadline{'s' if count > 1 else ''} This Week",
                'message': f"{count} non-negotiable deadline{'s' if count > 1 else ''} {'require' if count > 1 else 'requires'} completion this week. These cannot be missed.",
                'action': 'View fatal deadlines',
                'action_type': 'navigate',
                'related_items': [a['deadline_id'] for a in fatal_this_week]
            })

        # Insight: Overdue items
        overdue = [a for a in high_risk_alerts if a['alert_level'] == 'OVERDUE']
        if overdue:
            count = len(overdue)
            insights.append({
                'priority': 'high',
                'icon': '⏰',
                'title': f"{count} Overdue Item{'s' if count > 1 else ''}",
                'message': "Mark as completed if done, or file for an extension if still pending.",
                'action': 'Review overdue',
                'action_type': 'navigate',
                'related_items': [a['deadline_id'] for a in overdue]
            })

        # Insight: Today's deadlines
        due_today = [d for d in upcoming_deadlines if d['urgency'] == 'today']
        if due_today:
            count = len(due_today)
            insights.append({
                'priority': 'high',
                'icon': '📋',
                'title': f"Due Today: {count} Item{'s' if count > 1 else ''}",
                'message': ', '.join([d['deadline_title'][:40] for d in due_today[:3]]) + ('...' if count > 3 else ''),
                'action': 'View today\'s deadlines',
                'action_type': 'navigate',
                'related_items': [d['deadline_id'] for d in due_today]
            })

        # Insight: Upcoming milestone
        if milestones and len(insights) < 4:
            milestone = milestones[0]
            insights.append({
                'priority': 'medium',
                'icon': '📌',
                'title': f"{milestone['type'].title()} in {milestone['days_until']} Days",
                'message': f"{milestone['case_title']}: {milestone['title']}",
                'action': 'View case',
                'action_type': 'navigate',
                'case_id': milestone['case_id']
            })

        # Insight: Weekly productivity (Monday only, positive reinforcement)
        if week_stats['is_monday'] and week_stats.get('completed_last_week', 0) > 0:
            insights.append({
                'priority': 'low',
                'icon': '📈',
                'title': 'Last Week\'s Progress',
                'message': f"You completed {week_stats['completed_last_week']} deadlines last week.",
                'action': None,
                'action_type': 'info'
            })

        # Insight: New documents needing review
        unanalyzed = [f for f in new_filings if f.get('analysis_status') == 'pending']
        if unanalyzed and len(insights) < 5:
            count = len(unanalyzed)
            insights.append({
                'priority': 'medium',
                'icon': '📄',
                'title': f"{count} New Document{'s' if count > 1 else ''} to Review",
                'message': "Documents uploaded but not yet analyzed for deadlines.",
                'action': 'Analyze documents',
                'action_type': 'analyze',
                'related_items': [f['document_id'] for f in unanalyzed]
            })

        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        insights.sort(key=lambda x: priority_order.get(x['priority'], 99))

        return insights[:5]  # Max 5 insights

    def _format_alert_message(self, deadline: Deadline, days_until: Optional[int]) -> str:
        """Format a clear alert message"""
        if days_until is None:
            return f"Fatal deadline: {deadline.title} (date pending)"

        if days_until < 0:
            days_overdue = abs(days_until)
            return f"Overdue by {days_overdue} day{'s' if days_overdue != 1 else ''}"
        elif days_until == 0:
            return "Due today"
        elif days_until == 1:
            return "Due tomorrow"
        elif days_until <= 3:
            return f"Due in {days_until} days"
        else:
            return f"Due in {days_until} days"

    def _format_overdue_message(self, title: str, days_overdue: int) -> str:
        """Format overdue message"""
        if days_overdue == 1:
            return "1 day overdue"
        else:
            return f"{days_overdue} days overdue"
