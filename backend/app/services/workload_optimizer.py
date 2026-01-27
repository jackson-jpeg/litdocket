"""
Workload Optimizer Service
Analyzes calendar workload, identifies saturation risks, and suggests AI-powered rebalancing
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from collections import defaultdict
import logging

from app.models.deadline import Deadline
from app.models.case import Case
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


class WorkloadOptimizer:
    """
    Intelligent workload management for attorneys

    Features:
    - Calendar saturation analysis (detect high-risk days)
    - AI-powered deadline rebalancing suggestions
    - Burnout prevention alerts
    - Workload heatmap data generation
    """

    # Risk scoring weights
    WEIGHT_TOTAL_DEADLINES = 1.0
    WEIGHT_FATAL = 10.0  # FATAL deadlines are critical
    WEIGHT_CRITICAL = 5.0
    WEIGHT_IMPORTANT = 3.0

    # Thresholds
    SATURATION_THRESHOLD = 10.0  # Risk score above this = saturated
    BURNOUT_THRESHOLD_DAYS = 5  # Consecutive saturated days = burnout risk

    def __init__(self):
        pass

    async def analyze_calendar_saturation(
        self,
        user_id: str,
        db: Session,
        days_ahead: int = 60
    ) -> Dict[str, Any]:
        """
        Analyze calendar for workload saturation and high-risk days

        Args:
            user_id: User ID
            db: Database session
            days_ahead: How many days to analyze (default 60)

        Returns:
            Dictionary with saturation analysis:
            {
                "risk_days": [...],
                "burnout_alerts": [...],
                "workload_heatmap": {...},
                "statistics": {...}
            }
        """

        end_date = date.today() + timedelta(days=days_ahead)

        # Get all pending deadlines in the date range
        deadlines = db.query(Deadline).filter(
            Deadline.user_id == user_id,
            Deadline.status == 'pending',
            Deadline.deadline_date >= date.today(),
            Deadline.deadline_date <= end_date
        ).all()

        # Group deadlines by date
        daily_workload = defaultdict(list)
        for deadline in deadlines:
            if deadline.deadline_date:
                daily_workload[deadline.deadline_date].append(deadline)

        # Calculate risk scores for each day
        risk_days = []
        heatmap = {}

        for day, items in daily_workload.items():
            risk_score, breakdown = self._calculate_risk_score(items)

            heatmap[day.isoformat()] = {
                "risk_score": risk_score,
                "deadline_count": len(items),
                "intensity": self._get_intensity_level(risk_score)
            }

            if risk_score >= self.SATURATION_THRESHOLD:
                risk_days.append({
                    "date": day.isoformat(),
                    "risk_score": risk_score,
                    "deadline_count": len(items),
                    "fatal_count": breakdown['fatal_count'],
                    "critical_count": breakdown['critical_count'],
                    "important_count": breakdown['important_count'],
                    "deadlines": [
                        {
                            "id": str(d.id),
                            "title": d.title,
                            "priority": d.priority,
                            "case_id": d.case_id,
                            "is_moveable": self._is_deadline_moveable(d)
                        }
                        for d in items
                    ],
                    "intensity": self._get_intensity_level(risk_score)
                })

        # Sort risk days by risk score (highest first)
        risk_days.sort(key=lambda x: x['risk_score'], reverse=True)

        # Detect burnout risk (consecutive saturated days)
        burnout_alerts = self._detect_burnout_risk(daily_workload)

        # Generate AI suggestions for top 3 risk days
        suggestions = []
        for risk_day in risk_days[:3]:
            suggestion = await self._generate_rebalance_suggestion(
                risk_day,
                daily_workload,
                db
            )
            suggestions.append(suggestion)

        # Calculate statistics
        stats = self._calculate_workload_statistics(daily_workload, days_ahead)

        return {
            "risk_days": risk_days,
            "burnout_alerts": burnout_alerts,
            "ai_suggestions": suggestions,
            "workload_heatmap": heatmap,
            "statistics": stats
        }

    def _calculate_risk_score(self, deadlines: List[Deadline]) -> tuple[float, Dict]:
        """
        Calculate risk score for a day based on deadlines

        Returns: (risk_score, breakdown_dict)
        """

        fatal_count = sum(1 for d in deadlines if d.priority == 'FATAL')
        critical_count = sum(1 for d in deadlines if d.priority == 'CRITICAL')
        important_count = sum(1 for d in deadlines if d.priority == 'IMPORTANT')

        risk_score = (
            len(deadlines) * self.WEIGHT_TOTAL_DEADLINES +
            fatal_count * self.WEIGHT_FATAL +
            critical_count * self.WEIGHT_CRITICAL +
            important_count * self.WEIGHT_IMPORTANT
        )

        breakdown = {
            "total_deadlines": len(deadlines),
            "fatal_count": fatal_count,
            "critical_count": critical_count,
            "important_count": important_count
        }

        return risk_score, breakdown

    def _get_intensity_level(self, risk_score: float) -> str:
        """Convert risk score to intensity level for visualization"""
        if risk_score >= 20:
            return "extreme"
        elif risk_score >= 15:
            return "very_high"
        elif risk_score >= 10:
            return "high"
        elif risk_score >= 5:
            return "medium"
        else:
            return "low"

    def _is_deadline_moveable(self, deadline: Deadline) -> bool:
        """
        Determine if a deadline can be moved

        Cannot move:
        - FATAL deadlines (jurisdictional)
        - Court-ordered deadlines
        - Dependent deadlines (part of trigger chain)
        """

        if deadline.priority == 'FATAL':
            return False

        if deadline.is_dependent:
            return False

        # Check if it's a court-ordered deadline (heuristic)
        if deadline.trigger_event and 'hearing' in deadline.trigger_event.lower():
            return False

        return True

    def _detect_burnout_risk(self, daily_workload: Dict[date, List[Deadline]]) -> List[Dict]:
        """
        Detect consecutive saturated days (burnout risk)

        Returns: List of burnout alert periods
        """

        alerts = []
        sorted_dates = sorted(daily_workload.keys())

        consecutive_saturated = []

        for day in sorted_dates:
            items = daily_workload[day]
            risk_score, _ = self._calculate_risk_score(items)

            if risk_score >= self.SATURATION_THRESHOLD:
                consecutive_saturated.append(day)
            else:
                # Check if we had a streak
                if len(consecutive_saturated) >= self.BURNOUT_THRESHOLD_DAYS:
                    alerts.append({
                        "type": "burnout_risk",
                        "start_date": consecutive_saturated[0].isoformat(),
                        "end_date": consecutive_saturated[-1].isoformat(),
                        "consecutive_days": len(consecutive_saturated),
                        "message": f"⚠️ {len(consecutive_saturated)} consecutive high-workload days detected. Consider redistributing deadlines to prevent burnout.",
                        "severity": "high"
                    })

                consecutive_saturated = []

        # Check final streak
        if len(consecutive_saturated) >= self.BURNOUT_THRESHOLD_DAYS:
            alerts.append({
                "type": "burnout_risk",
                "start_date": consecutive_saturated[0].isoformat(),
                "end_date": consecutive_saturated[-1].isoformat(),
                "consecutive_days": len(consecutive_saturated),
                "message": f"⚠️ {len(consecutive_saturated)} consecutive high-workload days detected. Consider redistributing deadlines to prevent burnout.",
                "severity": "high"
            })

        return alerts

    async def _generate_rebalance_suggestion(
        self,
        risk_day: Dict,
        daily_workload: Dict[date, List[Deadline]],
        db: Session
    ) -> Dict[str, Any]:
        """
        Use AI to suggest smart deadline rescheduling

        Considers:
        - Which deadlines can be moved
        - Available capacity on adjacent days
        - Logical task sequencing
        - Case context
        """

        try:
            overloaded_date = date.fromisoformat(risk_day['date'])

            # Get moveable deadlines
            moveable = [d for d in risk_day['deadlines'] if d['is_moveable']]

            if not moveable:
                return {
                    "date": risk_day['date'],
                    "suggestion": "No deadlines can be moved (all are court-ordered or jurisdictional)",
                    "alternative_actions": [
                        "Consider delegating work to associates",
                        "Block focus time for critical tasks",
                        "Request continuance if possible"
                    ]
                }

            # Analyze adjacent days capacity
            adjacent_days = []
            for offset in [-2, -1, 1, 2]:
                check_date = overloaded_date + timedelta(days=offset)
                if check_date < date.today():
                    continue

                items = daily_workload.get(check_date, [])
                risk_score, _ = self._calculate_risk_score(items)

                adjacent_days.append({
                    "date": check_date.isoformat(),
                    "current_deadlines": len(items),
                    "risk_score": risk_score,
                    "available_capacity": max(0, self.SATURATION_THRESHOLD - risk_score)
                })

            # Build prompt for Claude
            prompt = f"""You are a workload management expert for attorneys.

SITUATION:
The attorney has {risk_day['deadline_count']} deadlines on {risk_day['date']} (OVERLOADED):
- {risk_day['fatal_count']} FATAL (cannot move)
- {risk_day['critical_count']} CRITICAL
- {risk_day['important_count']} IMPORTANT

MOVEABLE DEADLINES:
{self._format_moveable_deadlines(moveable)}

ADJACENT DAYS CAPACITY:
{self._format_adjacent_days(adjacent_days)}

TASK:
Suggest which specific deadlines to reschedule and to which dates. Prioritize:
1. Moving lower-priority tasks to less busy days
2. Maintaining logical case progression
3. Spreading work evenly
4. Keeping related tasks on the same day when possible

FORMAT:
Return JSON with:
{{
    "recommendations": [
        {{"deadline_title": "X", "move_to_date": "YYYY-MM-DD", "reason": "..."}}
    ],
    "summary": "Brief explanation of the rebalancing strategy"
}}
"""

            # Call Claude for suggestions
            response = ai_service.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system="You are a workload optimization specialist. Return JSON only.",
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse AI response
            import json
            ai_suggestion = json.loads(response.content[0].text)

            return {
                "date": risk_day['date'],
                "risk_score": risk_day['risk_score'],
                "ai_recommendations": ai_suggestion.get('recommendations', []),
                "summary": ai_suggestion.get('summary', ''),
                "adjacent_days": adjacent_days
            }

        except Exception as e:
            logger.error(f"AI rebalance suggestion error: {e}", exc_info=True)
            return {
                "date": risk_day['date'],
                "error": str(e),
                "fallback_suggestion": "Consider moving lower-priority tasks to adjacent days with less workload."
            }

    def _format_moveable_deadlines(self, moveable: List[Dict]) -> str:
        """Format moveable deadlines for AI prompt"""
        lines = []
        for d in moveable:
            lines.append(f"- {d['title']} (Priority: {d['priority']}, ID: {d['id']})")
        return "\n".join(lines)

    def _format_adjacent_days(self, adjacent_days: List[Dict]) -> str:
        """Format adjacent days capacity for AI prompt"""
        lines = []
        for day in adjacent_days:
            lines.append(
                f"- {day['date']}: {day['current_deadlines']} deadlines "
                f"(Risk: {day['risk_score']:.1f}, Capacity: {day['available_capacity']:.1f})"
            )
        return "\n".join(lines)

    def _calculate_workload_statistics(
        self,
        daily_workload: Dict[date, List[Deadline]],
        days_ahead: int
    ) -> Dict[str, Any]:
        """Calculate aggregate workload statistics"""

        if not daily_workload:
            return {
                "average_deadlines_per_day": 0,
                "peak_workload_day": None,
                "saturated_days_count": 0,
                "total_deadlines": 0
            }

        # Calculate averages
        total_deadlines = sum(len(items) for items in daily_workload.values())
        avg_per_day = total_deadlines / days_ahead if days_ahead > 0 else 0

        # Find peak workload day
        peak_day = max(daily_workload.items(), key=lambda x: len(x[1]))
        peak_date, peak_deadlines = peak_day

        # Count saturated days
        saturated_count = sum(
            1 for items in daily_workload.values()
            if self._calculate_risk_score(items)[0] >= self.SATURATION_THRESHOLD
        )

        return {
            "average_deadlines_per_day": round(avg_per_day, 2),
            "peak_workload_day": {
                "date": peak_date.isoformat(),
                "deadline_count": len(peak_deadlines)
            },
            "saturated_days_count": saturated_count,
            "total_deadlines": total_deadlines,
            "analysis_period_days": days_ahead
        }


# Singleton instance
workload_optimizer = WorkloadOptimizer()
