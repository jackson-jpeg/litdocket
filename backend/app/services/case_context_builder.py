"""
Case Context Builder - Omniscient Context Architecture for AI Chat

Provides comprehensive, structured case context that gives the AI chatbot
complete awareness of all case elements, enabling it to take action on
deadlines, documents, and case management.

The context is structured in 4 dimensions:
1. LEGAL GRAPH - Case metadata, parties, jurisdiction, applicable rules
2. LIVE DOCKET STATE - All deadlines with IDs, status, priority, dates
3. DOCUMENT INTELLIGENCE - Document summaries, extracted content, embeddings
4. TEMPORAL GRID - Today's date, days until deadlines, calendar awareness
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
import logging

from app.models.case import Case
from app.models.deadline import Deadline
from app.models.document import Document

logger = logging.getLogger(__name__)


class CaseContextBuilder:
    """
    Builds comprehensive, omniscient context for AI chat.

    This replaces the minimal context from RAG service with a
    complete picture of the case that enables Claude to:
    - See ALL deadlines with their IDs (to update/complete them)
    - Understand temporal context (what's due today, this week, overdue)
    - Access document summaries and extracted information
    - Know the case's procedural posture and next steps
    """

    def __init__(self, db: Session):
        self.db = db
        self.today = date.today()
        self.now = datetime.now()

    def build_context(self, case_id: str, user_query: str = None) -> Dict[str, Any]:
        """
        Build complete case context for AI consumption.

        Args:
            case_id: The case to build context for
            user_query: Optional user query for relevance scoring

        Returns:
            Comprehensive context dictionary with all 4 dimensions
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"error": "Case not found"}

        context = {
            "legal_graph": self._build_legal_graph(case),
            "live_docket": self._build_live_docket(case_id),
            "document_intelligence": self._build_document_intelligence(case_id),
            "temporal_grid": self._build_temporal_grid(case_id),
            "ai_action_context": self._build_action_context(case_id),
        }

        # Log for debugging
        deadline_count = len(context["live_docket"]["all_deadlines"])
        logger.info(f"Built omniscient context for case {case_id}: {deadline_count} deadlines")

        return context

    def _build_legal_graph(self, case: Case) -> Dict[str, Any]:
        """
        Dimension 1: Legal Graph
        Case metadata, parties, jurisdiction, and applicable rule sets
        """
        return {
            "case_number": case.case_number,
            "title": case.title,
            "court": case.court,
            "judge": case.judge,
            "case_type": case.case_type,
            "jurisdiction": case.jurisdiction or "florida_state",
            "circuit": getattr(case, 'circuit', None),
            "district": getattr(case, 'district', None),
            "filing_date": case.filing_date.isoformat() if case.filing_date else None,
            "status": case.status or "active",
            "parties": case.parties or [],
            "applicable_rules": self._get_applicable_rules(case),
        }

    def _build_live_docket(self, case_id: str) -> Dict[str, Any]:
        """
        Dimension 2: Live Docket State
        Complete deadline information with IDs, enabling AI actions
        """
        # Get ALL deadlines for this case
        all_deadlines = self.db.query(Deadline).filter(
            Deadline.case_id == case_id
        ).order_by(Deadline.deadline_date.asc().nullslast()).all()

        # Categorize deadlines
        overdue = []
        due_today = []
        due_this_week = []
        upcoming = []
        completed = []
        cancelled = []

        for deadline in all_deadlines:
            deadline_data = self._format_deadline_complete(deadline)

            if deadline.status == "completed":
                completed.append(deadline_data)
            elif deadline.status == "cancelled":
                cancelled.append(deadline_data)
            elif deadline.deadline_date:
                days_until = (deadline.deadline_date - self.today).days
                deadline_data["days_until"] = days_until

                if days_until < 0:
                    deadline_data["days_overdue"] = abs(days_until)
                    overdue.append(deadline_data)
                elif days_until == 0:
                    due_today.append(deadline_data)
                elif days_until <= 7:
                    due_this_week.append(deadline_data)
                else:
                    upcoming.append(deadline_data)
            else:
                # No date set
                upcoming.append(deadline_data)

        return {
            "summary": {
                "total_deadlines": len(all_deadlines),
                "overdue_count": len(overdue),
                "due_today_count": len(due_today),
                "due_this_week_count": len(due_this_week),
                "pending_count": len(overdue) + len(due_today) + len(due_this_week) + len(upcoming),
                "completed_count": len(completed),
            },
            "overdue": overdue,
            "due_today": due_today,
            "due_this_week": due_this_week,
            "upcoming": upcoming[:20],  # Limit for context size
            "recently_completed": completed[:10],  # Last 10 completed
            "all_deadlines": [self._format_deadline_complete(d) for d in all_deadlines],
        }

    def _format_deadline_complete(self, deadline: Deadline) -> Dict[str, Any]:
        """Format a deadline with ALL fields needed for AI actions"""
        return {
            "id": str(deadline.id),
            "title": deadline.title,
            "description": deadline.description,
            "deadline_date": deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            "deadline_date_formatted": deadline.deadline_date.strftime("%B %d, %Y") if deadline.deadline_date else "No date set",
            "priority": deadline.priority,
            "status": deadline.status,
            "party_role": deadline.party_role,
            "action_required": deadline.action_required,
            "applicable_rule": deadline.applicable_rule,
            "calculation_basis": deadline.calculation_basis,
            "is_calculated": deadline.is_calculated,
            "is_dependent": deadline.is_dependent,
            "is_manually_overridden": deadline.is_manually_overridden,
            "trigger_event": deadline.trigger_event,
            "parent_deadline_id": deadline.parent_deadline_id,
            "notes": deadline.notes,
        }

    def _build_document_intelligence(self, case_id: str) -> Dict[str, Any]:
        """
        Dimension 3: Document Intelligence
        Document metadata, AI summaries, and extracted information
        """
        documents = self.db.query(Document).filter(
            Document.case_id == case_id
        ).order_by(Document.created_at.desc()).limit(50).all()

        formatted_docs = []
        for doc in documents:
            formatted_docs.append({
                "id": str(doc.id),
                "file_name": doc.file_name,
                "document_type": doc.document_type,
                "filing_date": doc.filing_date.isoformat() if doc.filing_date else None,
                "upload_date": doc.created_at.isoformat() if doc.created_at else None,
                "ai_summary": doc.ai_summary,
                "extracted_dates": doc.extracted_dates if hasattr(doc, 'extracted_dates') else None,
                "extracted_parties": doc.extracted_parties if hasattr(doc, 'extracted_parties') else None,
            })

        return {
            "total_documents": len(documents),
            "documents": formatted_docs,
            "document_types": self._get_document_type_summary(documents),
        }

    def _get_document_type_summary(self, documents: List[Document]) -> Dict[str, int]:
        """Summarize document types"""
        types = {}
        for doc in documents:
            doc_type = doc.document_type or "unknown"
            types[doc_type] = types.get(doc_type, 0) + 1
        return types

    def _build_temporal_grid(self, case_id: str) -> Dict[str, Any]:
        """
        Dimension 4: Temporal Grid
        Today's date, calendar awareness, deadline clustering
        """
        # Get upcoming deadlines for calendar analysis
        upcoming = self.db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.status == "pending",
            Deadline.deadline_date >= self.today
        ).order_by(Deadline.deadline_date.asc()).limit(30).all()

        # Calculate deadline density (busy periods)
        busy_periods = self._identify_busy_periods(upcoming)

        return {
            "today": self.today.isoformat(),
            "today_formatted": self.today.strftime("%A, %B %d, %Y"),
            "current_time": self.now.strftime("%I:%M %p"),
            "current_week": self._get_week_info(),
            "busy_periods": busy_periods,
            "next_7_days": self._get_next_n_days(upcoming, 7),
            "next_30_days": self._get_next_n_days(upcoming, 30),
        }

    def _get_week_info(self) -> Dict[str, str]:
        """Get current week information"""
        start_of_week = self.today - timedelta(days=self.today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return {
            "start": start_of_week.isoformat(),
            "end": end_of_week.isoformat(),
            "week_number": self.today.isocalendar()[1],
        }

    def _identify_busy_periods(self, deadlines: List[Deadline]) -> List[Dict]:
        """Identify periods with high deadline density"""
        busy = []

        if len(deadlines) < 3:
            return busy

        # Check for clusters (3+ deadlines within 5 days)
        for i, deadline in enumerate(deadlines):
            if not deadline.deadline_date:
                continue

            cluster = [deadline]
            for j in range(i + 1, len(deadlines)):
                other = deadlines[j]
                if not other.deadline_date:
                    continue

                days_diff = (other.deadline_date - deadline.deadline_date).days
                if days_diff <= 5:
                    cluster.append(other)
                else:
                    break

            if len(cluster) >= 3:
                busy.append({
                    "start_date": deadline.deadline_date.isoformat(),
                    "end_date": cluster[-1].deadline_date.isoformat(),
                    "deadline_count": len(cluster),
                    "warning": f"⚠️ {len(cluster)} deadlines in {(cluster[-1].deadline_date - deadline.deadline_date).days + 1} days",
                })

        return busy[:3]  # Top 3 busy periods

    def _get_next_n_days(self, deadlines: List[Deadline], n: int) -> List[Dict]:
        """Get deadlines for next N days"""
        cutoff = self.today + timedelta(days=n)
        result = []

        for d in deadlines:
            if d.deadline_date and d.deadline_date <= cutoff:
                result.append({
                    "id": str(d.id),
                    "title": d.title,
                    "date": d.deadline_date.isoformat(),
                    "priority": d.priority,
                    "days_until": (d.deadline_date - self.today).days,
                })

        return result

    def _build_action_context(self, case_id: str) -> Dict[str, Any]:
        """
        Additional context to help AI understand what actions are available
        and provide quick reference for common operations
        """
        # Get pending deadlines that can be marked complete
        pending = self.db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.status == "pending"
        ).order_by(Deadline.deadline_date.asc().nullslast()).all()

        # Build quick reference for "close/complete" type requests
        completable = []
        for d in pending[:20]:
            completable.append({
                "id": str(d.id),
                "title": d.title,
                "date": d.deadline_date.isoformat() if d.deadline_date else None,
            })

        return {
            "completable_deadlines": completable,
            "hints": [
                "To mark a deadline complete, use update_deadline with new_status='completed'",
                "To delete a deadline, use delete_deadline with deadline_id",
                "To modify a date, use update_deadline with new_date",
            ],
        }

    def _get_applicable_rules(self, case: Case) -> List[str]:
        """Determine which rule sets apply to this case"""
        rules = []

        jurisdiction = case.jurisdiction or "florida_state"
        case_type = case.case_type or "civil"

        if jurisdiction == "florida_state":
            if case_type == "civil":
                rules.append("Florida Rules of Civil Procedure")
            elif case_type == "criminal":
                rules.append("Florida Rules of Criminal Procedure")
            elif case_type == "appellate":
                rules.append("Florida Rules of Appellate Procedure")
            rules.append("Florida Rules of Judicial Administration")

            # Add circuit-specific rules if known
            circuit = getattr(case, 'circuit', None)
            if circuit:
                rules.append(f"{circuit} Judicial Circuit Local Rules")

        elif jurisdiction == "federal":
            rules.append("Federal Rules of Civil Procedure")
            rules.append("Federal Rules of Evidence")

            district = getattr(case, 'district', None)
            if district:
                rules.append(f"Local Rules - {district}")

        return rules

    def get_system_prompt_context(self, case_id: str) -> str:
        """
        Generate XML-structured context for Claude's system prompt.
        This format is optimized for Claude's understanding.
        """
        context = self.build_context(case_id)

        if "error" in context:
            return f"<error>{context['error']}</error>"

        legal = context["legal_graph"]
        docket = context["live_docket"]
        temporal = context["temporal_grid"]
        action = context["ai_action_context"]

        # Build XML-structured context
        xml_context = f"""
<case_context>
    <metadata>
        <case_number>{legal['case_number']}</case_number>
        <title>{legal['title']}</title>
        <court>{legal['court']}</court>
        <judge>{legal['judge'] or 'Not assigned'}</judge>
        <case_type>{legal['case_type']}</case_type>
        <jurisdiction>{legal['jurisdiction']}</jurisdiction>
        <status>{legal['status']}</status>
        <filing_date>{legal['filing_date'] or 'Not set'}</filing_date>
    </metadata>

    <temporal_awareness>
        <today>{temporal['today_formatted']}</today>
        <current_time>{temporal['current_time']}</current_time>
    </temporal_awareness>

    <docket_summary>
        <total_deadlines>{docket['summary']['total_deadlines']}</total_deadlines>
        <overdue>{docket['summary']['overdue_count']}</overdue>
        <due_today>{docket['summary']['due_today_count']}</due_today>
        <due_this_week>{docket['summary']['due_this_week_count']}</due_this_week>
        <pending>{docket['summary']['pending_count']}</pending>
        <completed>{docket['summary']['completed_count']}</completed>
    </docket_summary>
"""

        # Add overdue deadlines (CRITICAL)
        if docket["overdue"]:
            xml_context += "\n    <overdue_deadlines>\n"
            for d in docket["overdue"]:
                xml_context += f"""        <deadline id="{d['id']}">
            <title>{d['title']}</title>
            <date>{d['deadline_date']}</date>
            <days_overdue>{d.get('days_overdue', 0)}</days_overdue>
            <priority>{d['priority']}</priority>
            <status>{d['status']}</status>
        </deadline>
"""
            xml_context += "    </overdue_deadlines>\n"

        # Add due today
        if docket["due_today"]:
            xml_context += "\n    <due_today>\n"
            for d in docket["due_today"]:
                xml_context += f"""        <deadline id="{d['id']}">
            <title>{d['title']}</title>
            <priority>{d['priority']}</priority>
            <status>{d['status']}</status>
        </deadline>
"""
            xml_context += "    </due_today>\n"

        # Add this week
        if docket["due_this_week"]:
            xml_context += "\n    <due_this_week>\n"
            for d in docket["due_this_week"]:
                xml_context += f"""        <deadline id="{d['id']}">
            <title>{d['title']}</title>
            <date>{d['deadline_date']}</date>
            <days_until>{d.get('days_until', 0)}</days_until>
            <priority>{d['priority']}</priority>
            <status>{d['status']}</status>
        </deadline>
"""
            xml_context += "    </due_this_week>\n"

        # Add ALL pending deadlines with IDs for action capability
        xml_context += "\n    <all_pending_deadlines>\n"
        xml_context += "        <!-- These are ALL pending deadlines with IDs. Use these IDs to update/complete/delete deadlines. -->\n"
        for d in action["completable_deadlines"]:
            xml_context += f"""        <deadline id="{d['id']}">
            <title>{d['title']}</title>
            <date>{d['date'] or 'No date'}</date>
        </deadline>
"""
        xml_context += "    </all_pending_deadlines>\n"

        # Add recently completed
        if docket["recently_completed"]:
            xml_context += "\n    <recently_completed>\n"
            for d in docket["recently_completed"][:5]:
                xml_context += f"""        <deadline id="{d['id']}">
            <title>{d['title']}</title>
            <date>{d['deadline_date']}</date>
        </deadline>
"""
            xml_context += "    </recently_completed>\n"

        xml_context += "</case_context>"

        return xml_context


def get_case_context_builder(db: Session) -> CaseContextBuilder:
    """Factory function to create CaseContextBuilder"""
    return CaseContextBuilder(db)
