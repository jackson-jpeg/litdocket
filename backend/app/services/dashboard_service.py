"""
Dashboard Service - War Room Intelligence for Legal Practice

Provides intelligent overview of all cases and deadlines with:
- Database-optimized queries (SQL-side filtering)
- Zombie case detection (malpractice risk)
- Workload saturation index (calendar hotspots)
- Recent velocity metrics (productivity trends)
- Judge-specific analytics
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case
from collections import defaultdict
import logging

from app.models.case import Case
from app.models.document import Document
from app.models.deadline import Deadline

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for generating dashboard data and analytics"""

    async def get_dashboard_data(self, user_id: str, db: Session) -> Dict[str, Any]:
        """
        Generate comprehensive War Room dashboard data for a user

        Returns:
            - case_statistics: Total cases, active cases, etc.
            - deadline_alerts: Overdue, urgent, upcoming deadlines (DB-optimized)
            - recent_activity: Latest documents and case updates
            - critical_cases: Cases needing attention
            - zombie_cases: Active cases with ZERO future deadlines (RISK!)
            - calendar_hotspots: Workload saturation index for next 7 days
            - velocity_metrics: Productivity trend (completed vs added)
            - heat_map_flat: Flattened heat map for frontend
            - judge_analytics: Judge-specific case statistics
        """
        today = date.today()

        # Get all user's cases (needed for several calculations)
        cases = db.query(Case).filter(
            Case.user_id == user_id,
            Case.status != 'deleted'
        ).all()
        total_cases = len(cases)

        # ═══════════════════════════════════════════════════════════════════════
        # DATABASE-OPTIMIZED DEADLINE ALERTS (Improvement #7)
        # Move filtering to SQL instead of Python loops
        # ═══════════════════════════════════════════════════════════════════════
        deadline_alerts = self._calculate_deadline_alerts_optimized(user_id, db, today)

        # Get case statistics
        case_stats = self._calculate_case_statistics(cases, user_id, db)

        # Get recent activity
        recent_activity = await self._get_recent_activity(user_id, db)

        # Get critical cases (cases with urgent deadlines)
        critical_cases = self._identify_critical_cases_optimized(user_id, db, today)

        # Get upcoming deadlines (next 30 days) - DB optimized
        upcoming_deadlines = self._get_upcoming_deadlines_optimized(user_id, db, today, days=30)

        # ═══════════════════════════════════════════════════════════════════════
        # ZOMBIE CASE DETECTION (Improvement #2)
        # Active cases with ZERO future deadlines = malpractice risk
        # ═══════════════════════════════════════════════════════════════════════
        zombie_cases = self._detect_zombie_cases(cases, user_id, db, today)

        # ═══════════════════════════════════════════════════════════════════════
        # WORKLOAD SATURATION INDEX (Improvement #4)
        # Calendar hotspots for next 7 days
        # ═══════════════════════════════════════════════════════════════════════
        calendar_hotspots = self._calculate_calendar_hotspots(user_id, db, today)

        # ═══════════════════════════════════════════════════════════════════════
        # VELOCITY METRICS (Improvement #6)
        # Productivity trend: completed vs added this week
        # ═══════════════════════════════════════════════════════════════════════
        velocity_metrics = self._calculate_velocity_metrics(user_id, db, today)

        # ═══════════════════════════════════════════════════════════════════════
        # FLATTENED HEAT MAP (Improvement #9)
        # Frontend-friendly flat structure instead of nested dict
        # ═══════════════════════════════════════════════════════════════════════
        heat_map_flat = self._generate_heat_map_flat(user_id, db, today)

        # ═══════════════════════════════════════════════════════════════════════
        # JUDGE-SPECIFIC ANALYTICS (Improvement #10)
        # Strategic view of judge workload
        # ═══════════════════════════════════════════════════════════════════════
        judge_analytics = self._calculate_judge_analytics(cases, user_id, db, today)

        # Matter health cards (enhanced with judge stats)
        matter_health_cards = self._generate_matter_health_cards_enhanced(cases, user_id, db, today)

        return {
            "case_statistics": case_stats,
            "deadline_alerts": deadline_alerts,
            "recent_activity": recent_activity,
            "critical_cases": critical_cases,
            "upcoming_deadlines": upcoming_deadlines,
            "total_cases": total_cases,
            # War Room Intelligence enhancements
            "zombie_cases": zombie_cases,
            "calendar_hotspots": calendar_hotspots,
            "velocity_metrics": velocity_metrics,
            "heat_map_flat": heat_map_flat,
            "judge_analytics": judge_analytics,
            "matter_health_cards": matter_health_cards,
            "generated_at": datetime.now().isoformat()
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # IMPROVEMENT #7: DATABASE-SIDE FILTERING FOR ALERTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _calculate_deadline_alerts_optimized(
        self,
        user_id: str,
        db: Session,
        today: date
    ) -> Dict[str, Any]:
        """
        Calculate deadline alerts using SQL-side filtering.
        Much faster than fetching all deadlines and filtering in Python.
        """
        three_days = today + timedelta(days=3)
        seven_days = today + timedelta(days=7)
        thirty_days = today + timedelta(days=30)

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

        return {
            "overdue": {
                "count": len(overdue),
                "deadlines": sorted(
                    [self._serialize_deadline(d, "overdue", today) for d in overdue],
                    key=lambda x: x['deadline_date']
                )
            },
            "urgent": {
                "count": len(urgent),
                "deadlines": sorted(
                    [self._serialize_deadline(d, "urgent", today) for d in urgent],
                    key=lambda x: x['deadline_date']
                )
            },
            "upcoming_week": {
                "count": len(upcoming_week),
                "deadlines": sorted(
                    [self._serialize_deadline(d, "upcoming-week", today) for d in upcoming_week],
                    key=lambda x: x['deadline_date']
                )
            },
            "upcoming_month": {
                "count": len(upcoming_month),
                "deadlines": sorted(
                    [self._serialize_deadline(d, "upcoming-month", today) for d in upcoming_month],
                    key=lambda x: x['deadline_date']
                )
            }
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # IMPROVEMENT #2: ZOMBIE CASE DETECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _detect_zombie_cases(
        self,
        cases: List[Case],
        user_id: str,
        db: Session,
        today: date
    ) -> List[Dict]:
        """
        Detect active cases with ZERO future deadlines.
        MALPRACTICE RISK - cases falling through the cracks.
        OPTIMIZED: Uses SQL subquery instead of N+1 pattern.
        """
        # OPTIMIZATION: Use SQL to find zombie cases directly
        # Active cases WITHOUT any future pending deadlines
        from sqlalchemy import text

        zombie_query = text("""
            SELECT
                c.id as case_id,
                c.case_number,
                c.title,
                c.court,
                c.judge,
                c.status,
                MAX(d.deadline_date) as last_deadline,
                MAX(doc.created_at) as last_document
            FROM cases c
            LEFT JOIN deadlines d ON d.case_id = c.id
            LEFT JOIN documents doc ON doc.case_id = c.id
            WHERE c.user_id = :user_id
              AND c.status = 'active'
              AND NOT EXISTS (
                  SELECT 1 FROM deadlines d2
                  WHERE d2.case_id = c.id
                    AND d2.status = 'pending'
                    AND d2.deadline_date >= :today
              )
            GROUP BY c.id, c.case_number, c.title, c.court, c.judge, c.status
        """)

        zombie_results = db.execute(zombie_query, {'user_id': user_id, 'today': today}).fetchall()

        zombie_cases = []
        for row in zombie_results:
            last_activity = None
            if row.last_deadline:
                last_activity = row.last_deadline.isoformat()
            elif row.last_document:
                last_activity = row.last_document.isoformat()

            zombie_cases.append({
                'case_id': str(row.case_id),
                'case_number': row.case_number,
                'title': row.title,
                'court': row.court,
                'judge': row.judge,
                'last_activity': last_activity,
                'risk_level': 'high',
                'recommended_action': 'Add deadlines or close case'
            })

        logger.info(f"Detected {len(zombie_cases)} zombie cases for user {user_id}")
        return zombie_cases

    # ═══════════════════════════════════════════════════════════════════════════
    # IMPROVEMENT #4: WORKLOAD SATURATION INDEX
    # ═══════════════════════════════════════════════════════════════════════════

    def _calculate_calendar_hotspots(
        self,
        user_id: str,
        db: Session,
        today: date
    ) -> Dict[str, Any]:
        """
        Calculate workload saturation for next 7 days.

        Identifies "hot" days where the attorney has too many deadlines.
        Helps with workload planning and delegation decisions.
        """
        hotspots = {}
        seven_days = today + timedelta(days=7)

        # Query deadlines for next 7 days with counts per day
        deadlines = db.query(Deadline).filter(
            Deadline.user_id == user_id,
            Deadline.status == 'pending',
            Deadline.deadline_date >= today,
            Deadline.deadline_date <= seven_days
        ).all()

        # Group by date
        deadlines_by_date = defaultdict(list)
        for d in deadlines:
            if d.deadline_date:
                deadlines_by_date[d.deadline_date.isoformat()].append({
                    'id': str(d.id),
                    'title': d.title,
                    'priority': d.priority,
                    'case_id': str(d.case_id)
                })

        # Calculate saturation levels
        total_deadlines = 0
        high_load_days = 0
        critical_days = 0

        for i in range(7):
            check_date = today + timedelta(days=i)
            date_str = check_date.isoformat()
            day_deadlines = deadlines_by_date.get(date_str, [])
            count = len(day_deadlines)
            total_deadlines += count

            # Determine load level
            if count == 0:
                load_level = 'clear'
            elif count <= 2:
                load_level = 'light'
            elif count <= 4:
                load_level = 'normal'
            elif count <= 6:
                load_level = 'high'
                high_load_days += 1
            else:
                load_level = 'critical'
                critical_days += 1

            # Check for fatal/critical priority deadlines
            has_fatal = any(d['priority'] in ['fatal', 'critical'] for d in day_deadlines)

            hotspots[date_str] = {
                'date': date_str,
                'day_name': check_date.strftime('%A'),
                'count': count,
                'load_level': load_level,
                'has_fatal': has_fatal,
                'deadlines': day_deadlines[:5]  # Limit to first 5 for preview
            }

        # Overall saturation score (0-100)
        max_healthy = 3 * 7  # 3 deadlines per day is healthy
        saturation_score = min(100, int((total_deadlines / max_healthy) * 100))

        return {
            'hotspots': hotspots,
            'summary': {
                'total_next_7_days': total_deadlines,
                'high_load_days': high_load_days,
                'critical_days': critical_days,
                'saturation_score': saturation_score,
                'saturation_level': 'critical' if saturation_score > 80 else 'high' if saturation_score > 60 else 'normal' if saturation_score > 30 else 'light'
            }
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # IMPROVEMENT #6: VELOCITY METRICS
    # ═══════════════════════════════════════════════════════════════════════════

    def _calculate_velocity_metrics(
        self,
        user_id: str,
        db: Session,
        today: date
    ) -> Dict[str, Any]:
        """
        Calculate productivity trend: completed vs added deadlines.

        If Completed > Added: "On Track" (green)
        If Added > Completed: "Falling Behind" (red)
        """
        week_ago = today - timedelta(days=7)

        # Deadlines completed this week
        completed_this_week = db.query(func.count(Deadline.id)).filter(
            Deadline.user_id == user_id,
            Deadline.status == 'completed',
            Deadline.updated_at >= week_ago
        ).scalar() or 0

        # Deadlines added this week
        added_this_week = db.query(func.count(Deadline.id)).filter(
            Deadline.user_id == user_id,
            Deadline.created_at >= week_ago
        ).scalar() or 0

        # Calculate net velocity
        net_velocity = completed_this_week - added_this_week

        # Determine trend
        if net_velocity > 0:
            trend = 'ahead'
            trend_message = f"Great work! {net_velocity} more completed than added"
        elif net_velocity < 0:
            trend = 'behind'
            trend_message = f"Warning: {abs(net_velocity)} more added than completed"
        else:
            trend = 'even'
            trend_message = "Balanced: same number completed as added"

        # Calculate completion rate
        total_pending = db.query(func.count(Deadline.id)).filter(
            Deadline.user_id == user_id,
            Deadline.status == 'pending'
        ).scalar() or 0

        total_completed = db.query(func.count(Deadline.id)).filter(
            Deadline.user_id == user_id,
            Deadline.status == 'completed'
        ).scalar() or 0

        overall_completion_rate = int(
            (total_completed / (total_completed + total_pending) * 100)
        ) if (total_completed + total_pending) > 0 else 0

        return {
            'this_week': {
                'completed': completed_this_week,
                'added': added_this_week,
                'net_velocity': net_velocity
            },
            'trend': trend,
            'trend_message': trend_message,
            'overall': {
                'total_pending': total_pending,
                'total_completed': total_completed,
                'completion_rate': overall_completion_rate
            }
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # IMPROVEMENT #9: FLATTENED HEAT MAP
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_heat_map_flat(
        self,
        user_id: str,
        db: Session,
        today: date
    ) -> List[Dict]:
        """
        Generate flattened heat map structure for frontend.

        Returns list of objects instead of nested dict:
        [{"severity": "fatal", "urgency": "today", "count": 2, "case_ids": [...]}]
        """
        thirty_days = today + timedelta(days=30)

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

        return flat_list

    # ═══════════════════════════════════════════════════════════════════════════
    # IMPROVEMENT #10: JUDGE-SPECIFIC ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════════

    def _calculate_judge_analytics(
        self,
        cases: List[Case],
        user_id: str,
        db: Session,
        today: date
    ) -> List[Dict]:
        """
        Calculate judge-specific case statistics.

        Helps attorneys see workload distribution by judge
        and identify if they're overloaded before a specific judge.
        """
        judge_stats = defaultdict(lambda: {
            'judge': None,
            'active_cases': 0,
            'total_pending_deadlines': 0,
            'urgent_deadlines': 0,
            'case_ids': [],
            'courts': set()
        })

        three_days = today + timedelta(days=3)

        for case in cases:
            if case.status != 'active':
                continue

            judge = case.judge or 'Unassigned'
            judge_stats[judge]['judge'] = judge
            judge_stats[judge]['active_cases'] += 1
            judge_stats[judge]['case_ids'].append(str(case.id))
            if case.court:
                judge_stats[judge]['courts'].add(case.court)

        # Get deadline counts per judge's cases
        for judge, stats in judge_stats.items():
            if stats['case_ids']:
                # Total pending
                pending_count = db.query(func.count(Deadline.id)).filter(
                    Deadline.case_id.in_(stats['case_ids']),
                    Deadline.status == 'pending'
                ).scalar() or 0

                # Urgent (next 3 days)
                urgent_count = db.query(func.count(Deadline.id)).filter(
                    Deadline.case_id.in_(stats['case_ids']),
                    Deadline.status == 'pending',
                    Deadline.deadline_date >= today,
                    Deadline.deadline_date <= three_days
                ).scalar() or 0

                stats['total_pending_deadlines'] = pending_count
                stats['urgent_deadlines'] = urgent_count

        # Convert to list and sort by active cases
        result = []
        for judge, stats in judge_stats.items():
            result.append({
                'judge': judge,
                'active_cases': stats['active_cases'],
                'total_pending_deadlines': stats['total_pending_deadlines'],
                'urgent_deadlines': stats['urgent_deadlines'],
                'courts': list(stats['courts']),
                'workload_level': 'high' if stats['active_cases'] > 5 else 'normal' if stats['active_cases'] > 2 else 'light'
            })

        result.sort(key=lambda x: x['active_cases'], reverse=True)
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # ENHANCED MATTER HEALTH CARDS (with judge stats)
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_matter_health_cards_enhanced(
        self,
        cases: List[Case],
        user_id: str,
        db: Session,
        today: date
    ) -> List[Dict]:
        """
        Generate Matter Health Cards with enhanced judge information.
        OPTIMIZED: Uses bulk queries instead of N+1 pattern.
        """
        # Filter active/pending cases upfront
        active_cases = [c for c in cases if c.status in ['active', 'pending']]
        if not active_cases:
            return []

        case_ids = [c.id for c in active_cases]

        # OPTIMIZATION 1: Get ALL deadline counts in ONE query using aggregation
        deadline_stats = db.query(
            Deadline.case_id,
            func.count(Deadline.id).label('total_count'),
            func.sum(case((Deadline.status == 'completed', 1), else_=0)).label('completed_count')
        ).filter(
            Deadline.case_id.in_(case_ids)
        ).group_by(Deadline.case_id).all()

        # Build lookup dict
        deadline_counts = {
            str(stat.case_id): {
                'total': int(stat.total_count),
                'completed': int(stat.completed_count or 0),
                'pending': int(stat.total_count - (stat.completed_count or 0))
            }
            for stat in deadline_stats
        }

        # OPTIMIZATION 2: Get ALL next deadlines in ONE query using window functions
        # For each case, get the earliest pending deadline
        from sqlalchemy import literal
        next_deadlines_query = db.query(
            Deadline.case_id,
            Deadline.title,
            Deadline.deadline_date,
            Deadline.priority
        ).filter(
            Deadline.case_id.in_(case_ids),
            Deadline.status == 'pending',
            Deadline.deadline_date >= today
        ).order_by(
            Deadline.case_id,
            Deadline.deadline_date
        ).distinct(Deadline.case_id).all()

        # Build next deadline lookup
        next_deadlines_map = {
            str(nd.case_id): nd for nd in next_deadlines_query
        }

        # OPTIMIZATION 3: Get ALL document counts in ONE query
        doc_counts = db.query(
            Document.case_id,
            func.count(Document.id).label('doc_count')
        ).filter(
            Document.case_id.in_(case_ids)
        ).group_by(Document.case_id).all()

        doc_count_map = {str(dc.case_id): int(dc.doc_count) for dc in doc_counts}

        # OPTIMIZATION 4: Pre-compute ALL judge case counts in ONE query
        # This eliminates the N+1 query pattern for judge stats
        judge_counts = db.query(
            Case.judge,
            func.count(Case.id).label('count')
        ).filter(
            Case.user_id == user_id,
            Case.status == 'active',
            Case.judge.isnot(None)
        ).group_by(Case.judge).all()
        judge_count_map = {jc.judge: int(jc.count) for jc in judge_counts}

        # Now build health cards using pre-fetched data (NO MORE QUERIES IN LOOP!)
        health_cards = []
        for case_obj in active_cases:
            case_id_str = str(case_obj.id)

            # Get counts from pre-fetched data
            counts = deadline_counts.get(case_id_str, {'total': 0, 'completed': 0, 'pending': 0})
            total_deadlines = counts['total']
            completed_deadlines = counts['completed']
            pending_deadlines = counts['pending']

            progress_percentage = int((completed_deadlines / total_deadlines * 100)) if total_deadlines > 0 else 0

            # Get next deadline from pre-fetched data
            next_deadline = None
            next_deadline_urgency = 'normal'
            next_deadline_obj = next_deadlines_map.get(case_id_str)

            if next_deadline_obj and next_deadline_obj.deadline_date:
                days_until = (next_deadline_obj.deadline_date - today).days
                next_deadline = {
                    'title': next_deadline_obj.title,
                    'date': next_deadline_obj.deadline_date.isoformat(),
                    'days_until': days_until,
                    'priority': next_deadline_obj.priority
                }

                if days_until <= 1 or next_deadline_obj.priority == 'fatal':
                    next_deadline_urgency = 'critical'
                elif days_until <= 3 or next_deadline_obj.priority == 'critical':
                    next_deadline_urgency = 'urgent'
                elif days_until <= 7:
                    next_deadline_urgency = 'attention'

            # Health status
            health_status = 'healthy'
            if next_deadline_urgency == 'critical':
                health_status = 'critical'
            elif next_deadline_urgency == 'urgent':
                health_status = 'needs_attention'
            elif pending_deadlines > completed_deadlines:
                health_status = 'busy'

            # Document count from pre-fetched data
            doc_count = doc_count_map.get(case_id_str, 0)

            # Judge stats from pre-fetched data (no more N+1 query!)
            judge_case_count = judge_count_map.get(case_obj.judge, 0) if case_obj.judge else 0

            health_cards.append({
                'case_id': str(case_obj.id),
                'case_number': case_obj.case_number,
                'title': case_obj.title,
                'court': case_obj.court or 'Unknown Court',
                'judge': case_obj.judge or 'Unassigned',
                'judge_stats': {
                    'total_cases_with_judge': judge_case_count
                },
                'jurisdiction': case_obj.jurisdiction,
                'case_type': case_obj.case_type,
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
                'filing_date': case_obj.filing_date.isoformat() if case_obj.filing_date else None
            })

        # Sort by health status priority
        status_order = {'critical': 0, 'needs_attention': 1, 'busy': 2, 'healthy': 3}
        health_cards.sort(key=lambda x: (
            status_order.get(x['health_status'], 99),
            (x.get('next_deadline') or {}).get('days_until', 999)
        ))

        return health_cards

    # ═══════════════════════════════════════════════════════════════════════════
    # OPTIMIZED HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _calculate_case_statistics(
        self,
        cases: List[Case],
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Calculate case statistics"""
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

    async def _get_recent_activity(
        self,
        user_id: str,
        db: Session,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent activity across all cases"""
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

        return activities

    def _identify_critical_cases_optimized(
        self,
        user_id: str,
        db: Session,
        today: date
    ) -> List[Dict]:
        """Identify cases with deadlines in next 7 days"""
        seven_days = today + timedelta(days=7)

        # Get deadlines in next 7 days with case info
        critical_deadlines = db.query(Deadline).filter(
            Deadline.user_id == user_id,
            Deadline.status == 'pending',
            Deadline.deadline_date >= today,
            Deadline.deadline_date <= seven_days
        ).order_by(Deadline.deadline_date).all()

        # Group by case
        cases_seen = {}
        for deadline in critical_deadlines:
            case_id = str(deadline.case_id)
            if case_id not in cases_seen:
                case = db.query(Case).filter(Case.id == deadline.case_id).first()
                if case:
                    days_until = (deadline.deadline_date - today).days
                    pending_count = db.query(func.count(Deadline.id)).filter(
                        Deadline.case_id == case.id,
                        Deadline.status == 'pending'
                    ).scalar() or 0

                    cases_seen[case_id] = {
                        "case_id": case_id,
                        "case_number": case.case_number,
                        "title": case.title,
                        "court": case.court,
                        "next_deadline_date": deadline.deadline_date.isoformat(),
                        "next_deadline_title": deadline.title,
                        "days_until_deadline": days_until,
                        "urgency_level": "critical" if days_until <= 3 else "high",
                        "total_pending_deadlines": pending_count
                    }

        return list(cases_seen.values())

    def _get_upcoming_deadlines_optimized(
        self,
        user_id: str,
        db: Session,
        today: date,
        days: int = 30
    ) -> List[Dict]:
        """Get upcoming deadlines using DB query"""
        end_date = today + timedelta(days=days)

        deadlines = db.query(Deadline).filter(
            Deadline.user_id == user_id,
            Deadline.status == 'pending',
            Deadline.deadline_date >= today,
            Deadline.deadline_date <= end_date
        ).order_by(Deadline.deadline_date).all()

        return [self._serialize_deadline(d, self._calculate_urgency_level(d, today), today) for d in deadlines]

    def _serialize_deadline(self, deadline: Deadline, urgency_level: str, today: date) -> Dict:
        """Serialize deadline to dict with urgency info"""
        days_until = (deadline.deadline_date - today).days if deadline.deadline_date else None

        return {
            "id": str(deadline.id),
            "case_id": str(deadline.case_id),
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

    def _calculate_urgency_level(self, deadline: Deadline, today: date) -> str:
        """Calculate urgency level for a deadline"""
        if not deadline.deadline_date:
            return "unknown"

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
