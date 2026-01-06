"""
Intelligent Case Insights API
Provides AI-powered analysis and recommendations for cases
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.deadline import Deadline
from app.models.document import Document
from app.utils.auth import get_current_user

router = APIRouter()


class CaseInsightsService:
    """Intelligent case analysis and recommendations"""

    def analyze_case(self, case_id: str, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Comprehensive intelligent case analysis
        Returns proactive insights, warnings, and recommendations
        """
        # Get case
        case = db.query(Case).filter(
            Case.id == case_id,
            Case.user_id == user_id
        ).first()

        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Get deadlines
        deadlines = db.query(Deadline).filter(
            Deadline.case_id == case_id
        ).all()

        # Get documents
        documents = db.query(Document).filter(
            Document.case_id == case_id
        ).all()

        # Run analysis
        insights = {
            'case_health': self._calculate_case_health(deadlines, documents, case),
            'urgent_alerts': self._get_urgent_alerts(deadlines),
            'smart_recommendations': self._get_smart_recommendations(case, deadlines, documents),
            'deadline_analytics': self._analyze_deadlines(deadlines),
            'document_analytics': self._analyze_documents(documents),
            'next_actions': self._suggest_next_actions(case, deadlines, documents),
            'risk_factors': self._identify_risks(deadlines, case),
            'efficiency_score': self._calculate_efficiency(deadlines)
        }

        return insights

    def _calculate_case_health(self, deadlines: List, documents: List, case: Case) -> Dict:
        """Calculate overall case health score (0-100)"""
        score = 100
        issues = []
        now = datetime.now()

        # Check for overdue deadlines (-20 each, max -40)
        overdue = []
        for d in deadlines:
            if d.deadline_date and d.status == 'pending':
                # Handle both date and datetime objects
                if isinstance(d.deadline_date, datetime):
                    deadline_dt = d.deadline_date.replace(tzinfo=None)
                else:
                    deadline_dt = datetime.combine(d.deadline_date, datetime.min.time())

                if deadline_dt < now:
                    overdue.append(d)

        if overdue:
            score -= min(len(overdue) * 20, 40)
            issues.append(f"{len(overdue)} overdue deadline(s)")

        # Check for upcoming critical deadlines (-10 if within 3 days)
        critical_soon = []
        for d in deadlines:
            if d.deadline_date and d.priority in ['fatal', 'critical'] and d.status == 'pending':
                # Handle both date and datetime objects
                if isinstance(d.deadline_date, datetime):
                    deadline_dt = d.deadline_date.replace(tzinfo=None)
                else:
                    deadline_dt = datetime.combine(d.deadline_date, datetime.min.time())

                if now < deadline_dt < now + timedelta(days=3):
                    critical_soon.append(d)

        if critical_soon:
            score -= 10
            issues.append(f"{len(critical_soon)} critical deadline(s) within 3 days")

        # Check for no documents (-15)
        if len(documents) == 0:
            score -= 15
            issues.append("No documents uploaded")

        # Check for missing case info (-5 each)
        if not case.filing_date:
            score -= 5
            issues.append("Filing date not set")

        if not case.judge:
            score -= 5
            issues.append("Judge not assigned")

        # Bonus for having trigger events (+5)
        trigger_events = [d for d in deadlines if d.trigger_event and not d.is_dependent]
        if trigger_events:
            score = min(score + 5, 100)

        # Determine health status
        if score >= 90:
            status = "excellent"
            emoji = "💚"
        elif score >= 75:
            status = "good"
            emoji = "💙"
        elif score >= 60:
            status = "fair"
            emoji = "💛"
        elif score >= 40:
            status = "poor"
            emoji = "🧡"
        else:
            status = "critical"
            emoji = "❤️"

        return {
            'score': max(score, 0),
            'status': status,
            'emoji': emoji,
            'issues': issues or ["No issues detected - great job!"]
        }

    def _get_urgent_alerts(self, deadlines: List) -> List[Dict]:
        """Get time-sensitive alerts"""
        alerts = []
        now = datetime.now()

        for deadline in deadlines:
            if not deadline.deadline_date or deadline.status != 'pending':
                continue

            # Handle both date and datetime objects
            if isinstance(deadline.deadline_date, datetime):
                deadline_dt = deadline.deadline_date.replace(tzinfo=None)
            else:
                deadline_dt = datetime.combine(deadline.deadline_date, datetime.min.time())

            days_until = (deadline_dt - now).days

            if days_until < 0:
                alerts.append({
                    'severity': 'critical',
                    'type': 'overdue',
                    'title': deadline.title,
                    'days_overdue': abs(days_until),
                    'message': f"⚠️ OVERDUE: {deadline.title} was due {abs(days_until)} days ago!",
                    'deadline_id': str(deadline.id)
                })
            elif days_until == 0:
                alerts.append({
                    'severity': 'critical',
                    'type': 'due_today',
                    'title': deadline.title,
                    'message': f"🔴 DUE TODAY: {deadline.title}",
                    'deadline_id': str(deadline.id)
                })
            elif days_until == 1:
                alerts.append({
                    'severity': 'high',
                    'type': 'due_tomorrow',
                    'title': deadline.title,
                    'message': f"🟠 DUE TOMORROW: {deadline.title}",
                    'deadline_id': str(deadline.id)
                })
            elif days_until <= 3 and deadline.priority in ['fatal', 'critical']:
                alerts.append({
                    'severity': 'high',
                    'type': 'critical_soon',
                    'title': deadline.title,
                    'days_until': days_until,
                    'message': f"🟡 CRITICAL DEADLINE in {days_until} days: {deadline.title}",
                    'deadline_id': str(deadline.id)
                })

        # Sort by severity and date
        severity_order = {'critical': 0, 'high': 1, 'medium': 2}
        alerts.sort(key=lambda x: (severity_order.get(x['severity'], 3), x.get('days_overdue', -x.get('days_until', 999))))

        return alerts[:10]  # Top 10 most urgent

    def _get_smart_recommendations(self, case: Case, deadlines: List, documents: List) -> List[str]:
        """AI-powered smart recommendations"""
        recommendations = []

        # Check for trigger events
        trigger_events = [d for d in deadlines if d.trigger_event and not d.is_dependent]
        if not trigger_events and case.case_type in ['civil', 'Civil']:
            recommendations.append("💡 Set up trigger events (trial date, service date) to automatically generate all related deadlines")

        # Check for trial date
        has_trial = any('trial' in d.title.lower() for d in deadlines if d.title)
        if not has_trial and len(deadlines) > 3 and case.case_type in ['civil', 'Civil']:
            recommendations.append("📅 Consider setting a trial date trigger to auto-generate pretrial deadlines")

        # Check for document organization
        if len(documents) > 10:
            doc_types = set(d.document_type for d in documents if d.document_type)
            if len(doc_types) < 3:
                recommendations.append("📁 Categorize your documents by type (motion, order, pleading) for better organization")

        # Check for missing filing date
        if not case.filing_date and len(documents) > 0:
            recommendations.append("📋 Set the case filing date to ensure accurate deadline calculations")

        # Check for deadline density
        now = datetime.now()
        upcoming = []
        for d in deadlines:
            if d.deadline_date and d.status == 'pending':
                # Handle both date and datetime objects
                if isinstance(d.deadline_date, datetime):
                    deadline_dt = d.deadline_date.replace(tzinfo=None)
                else:
                    deadline_dt = datetime.combine(d.deadline_date, datetime.min.time())

                if deadline_dt > now:
                    upcoming.append(d)

        if len(upcoming) > 15:
            # Check for clusters
            dates = sorted([d.deadline_date for d in upcoming[:20] if d.deadline_date])
            if len(dates) >= 5:
                for i in range(len(dates) - 4):
                    # Handle both date and datetime objects for date subtraction
                    date_i = dates[i].date() if isinstance(dates[i], datetime) else dates[i]
                    date_i4 = dates[i+4].date() if isinstance(dates[i+4], datetime) else dates[i+4]
                    if (date_i4 - date_i).days <= 14:
                        display_date = dates[i].date() if isinstance(dates[i], datetime) else dates[i]
                        recommendations.append(f"⚠️ Deadline cluster detected: 5+ deadlines within 2 weeks starting {display_date}. Consider delegating or requesting extensions.")
                        break

        # Check for completed deadlines that should be archived
        completed = [d for d in deadlines if d.status == 'completed']
        if len(completed) > 20:
            recommendations.append("🗄️ You have many completed deadlines. Consider archiving them to declutter your calendar.")

        if not recommendations:
            recommendations.append("✅ Everything looks good! Your case is well-organized.")

        return recommendations

    def _analyze_deadlines(self, deadlines: List) -> Dict:
        """Deadline analytics"""
        total = len(deadlines)
        pending = len([d for d in deadlines if d.status == 'pending'])
        completed = len([d for d in deadlines if d.status == 'completed'])

        # Count overdue with proper datetime handling
        now = datetime.now()
        overdue = 0
        for d in deadlines:
            if d.deadline_date and d.status == 'pending':
                # Handle both date and datetime objects
                if isinstance(d.deadline_date, datetime):
                    deadline_dt = d.deadline_date.replace(tzinfo=None)
                else:
                    deadline_dt = datetime.combine(d.deadline_date, datetime.min.time())

                if deadline_dt < now:
                    overdue += 1

        # Priority breakdown
        by_priority = {}
        for d in deadlines:
            if d.status == 'pending':
                priority = d.priority or 'standard'
                by_priority[priority] = by_priority.get(priority, 0) + 1

        # Auto-calculated vs manual
        auto_calculated = len([d for d in deadlines if d.is_calculated])
        manual = total - auto_calculated

        return {
            'total': total,
            'pending': pending,
            'completed': completed,
            'overdue': overdue,
            'by_priority': by_priority,
            'auto_calculated': auto_calculated,
            'manual': manual,
            'completion_rate': round((completed / total * 100) if total > 0 else 0, 1)
        }

    def _analyze_documents(self, documents: List) -> Dict:
        """Document analytics"""
        total = len(documents)

        # By type
        by_type = {}
        for d in documents:
            doc_type = d.document_type or 'uncategorized'
            by_type[doc_type] = by_type.get(doc_type, 0) + 1

        # Recent uploads (last 30 days)
        recent = len([d for d in documents if d.created_at and (datetime.now() - d.created_at).days <= 30])

        return {
            'total': total,
            'by_type': by_type,
            'recent_uploads': recent,
            'needs_categorization': by_type.get('uncategorized', 0)
        }

    def _suggest_next_actions(self, case: Case, deadlines: List, documents: List) -> List[Dict]:
        """Suggest concrete next actions"""
        actions = []
        now = datetime.now()

        # Most urgent deadline
        upcoming_deadlines = []
        for d in deadlines:
            if d.deadline_date and d.status == 'pending':
                # Handle both date and datetime objects
                if isinstance(d.deadline_date, datetime):
                    deadline_dt = d.deadline_date.replace(tzinfo=None)
                else:
                    deadline_dt = datetime.combine(d.deadline_date, datetime.min.time())

                if deadline_dt > now:
                    upcoming_deadlines.append(d)

        if upcoming_deadlines:
            upcoming_deadlines.sort(key=lambda d: d.deadline_date)
            next_deadline = upcoming_deadlines[0]

            # Handle both date and datetime objects for days_until calculation
            if isinstance(next_deadline.deadline_date, datetime):
                deadline_dt = next_deadline.deadline_date.replace(tzinfo=None)
            else:
                deadline_dt = datetime.combine(next_deadline.deadline_date, datetime.min.time())

            days_until = (deadline_dt - now).days

            # Convert deadline_date to ISO format for JSON serialization
            due_date_iso = next_deadline.deadline_date.isoformat() if isinstance(next_deadline.deadline_date, datetime) else next_deadline.deadline_date.isoformat()

            actions.append({
                'priority': 'high' if days_until <= 7 else 'medium',
                'action': f"Prepare for {next_deadline.title}",
                'due_date': due_date_iso,
                'days_until': days_until,
                'deadline_id': str(next_deadline.id)
            })

        # Upload missing documents
        if len(documents) == 0:
            actions.append({
                'priority': 'medium',
                'action': "Upload initial case documents (complaint, answer, etc.)",
                'category': 'document_management'
            })

        # Set up automation
        trigger_events = [d for d in deadlines if d.trigger_event and not d.is_dependent]
        if not trigger_events:
            actions.append({
                'priority': 'low',
                'action': "Set up trigger events for automatic deadline generation",
                'category': 'automation'
            })

        return actions[:5]  # Top 5 actions

    def _identify_risks(self, deadlines: List, case: Case) -> List[Dict]:
        """Identify potential risks"""
        risks = []
        now = datetime.now()

        # Fatal priority deadlines
        fatal_deadlines = [
            d for d in deadlines
            if d.priority == 'fatal' and d.status == 'pending' and d.deadline_date
        ]
        for deadline in fatal_deadlines:
            # Handle both date and datetime objects
            if isinstance(deadline.deadline_date, datetime):
                deadline_dt = deadline.deadline_date.replace(tzinfo=None)
            else:
                deadline_dt = datetime.combine(deadline.deadline_date, datetime.min.time())

            days_until = (deadline_dt - now).days
            if 0 <= days_until <= 14:
                risks.append({
                    'severity': 'high',
                    'category': 'deadline',
                    'description': f"Fatal deadline '{deadline.title}' in {days_until} days - missing this could result in dismissal or default",
                    'deadline_id': str(deadline.id)
                })

        # Missing case information
        if not case.filing_date:
            risks.append({
                'severity': 'medium',
                'category': 'case_info',
                'description': "Filing date not set - may affect deadline calculations"
            })

        return risks

    def _calculate_efficiency(self, deadlines: List) -> Dict:
        """Calculate deadline management efficiency score"""
        if not deadlines:
            return {'score': 100.0, 'rating': 'N/A', 'on_time': 0, 'late': 0, 'overdue': 0}

        total = len(deadlines)
        completed = len([d for d in deadlines if d.status == 'completed'])
        pending = len([d for d in deadlines if d.status == 'pending'])

        # Count overdue with proper datetime handling
        now = datetime.now()
        overdue_count = 0
        for d in deadlines:
            if d.deadline_date and d.status == 'pending':
                # Handle both date and datetime objects
                if isinstance(d.deadline_date, datetime):
                    deadline_dt = d.deadline_date.replace(tzinfo=None)
                else:
                    deadline_dt = datetime.combine(d.deadline_date, datetime.min.time())

                if deadline_dt < now:
                    overdue_count += 1

        # Calculate score based on completion rate and overdue percentage
        completion_rate = (completed / total * 100) if total > 0 else 0
        overdue_rate = (overdue_count / total * 100) if total > 0 else 0

        # Score: high completion is good, overdue is bad
        score = completion_rate - (overdue_rate * 2)  # Overdue is weighted 2x
        score = max(0, min(100, score))  # Clamp between 0-100

        if score >= 90:
            rating = "Excellent"
        elif score >= 75:
            rating = "Good"
        elif score >= 60:
            rating = "Fair"
        else:
            rating = "Needs Improvement"

        return {
            'score': round(score, 1),
            'rating': rating,
            'on_time': completed,
            'late': 0,  # Can't track without completed_at field
            'overdue': overdue_count
        }


insights_service = CaseInsightsService()


@router.get("/case/{case_id}")
async def get_case_insights(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive intelligent insights for a case

    Returns:
        - Case health score and status
        - Urgent alerts
        - Smart recommendations
        - Analytics and metrics
        - Risk factors
        - Suggested next actions
    """
    insights = insights_service.analyze_case(case_id, str(current_user.id), db)
    return insights
