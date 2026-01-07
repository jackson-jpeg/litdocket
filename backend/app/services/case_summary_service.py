"""
Case Summary Service - Auto-updating case summaries
Generates comprehensive case summaries that update whenever events occur
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.ai_service import AIService

logger = logging.getLogger(__name__)
from app.models.case import Case
from app.models.document import Document
from app.models.deadline import Deadline


class CaseSummaryService:
    """Service for generating and updating case summaries"""

    def __init__(self):
        self.ai_service = AIService()

    async def generate_case_summary(
        self,
        case: Case,
        documents: List[Document],
        deadlines: List[Deadline],
        db: Session
    ) -> Dict:
        """
        Generate comprehensive case summary using Claude AI
        Updates automatically whenever:
        - New documents are uploaded
        - Deadlines are extracted
        - Case information changes
        """

        # Build context for summary generation
        case_context = self._build_case_context(case, documents, deadlines)

        # Generate summary using Claude
        summary_prompt = f"""You are an expert legal case analyst. Generate a comprehensive case summary.

CASE INFORMATION:
{case_context}

Generate a professional case summary with the following sections:

1. **Case Overview** (2-3 sentences)
   - Case number, court, parties, case type

2. **Current Status** (1-2 sentences)
   - Number of documents filed
   - Upcoming deadlines (next 3 critical deadlines)
   - Current stage of litigation

3. **Key Documents** (bullet list)
   - Most recent 5 documents with dates and types

4. **Critical Deadlines** (bullet list)
   - Next 5 upcoming deadlines with dates and actions required

5. **Timeline** (chronological bullet list)
   - Major events in reverse chronological order (most recent first)

6. **Action Items** (bullet list)
   - What needs to be done immediately
   - What's coming up in the next 30 days

Keep it concise, professional, and focused on actionable information.
Return as JSON with structure:
{{
  "overview": "...",
  "current_status": "...",
  "key_documents": ["...", "..."],
  "critical_deadlines": ["...", "..."],
  "timeline": ["...", "..."],
  "action_items": ["...", "..."],
  "last_updated": "{datetime.now().isoformat()}"
}}
"""

        try:
            response = await self.ai_service.analyze_with_prompt(summary_prompt)

            # Parse JSON response using AI service's parser
            summary_data = self.ai_service._parse_json_response(response)

            # Check if parsing failed
            if summary_data.get('parse_error'):
                raise ValueError("Failed to parse AI response as JSON")

            # Store summary in case metadata
            if case.case_metadata is None:
                case.case_metadata = {}

            case.case_metadata['auto_summary'] = summary_data
            db.commit()

            return summary_data

        except Exception as e:
            logger.error(f"Error generating case summary: {e}")
            return self._generate_fallback_summary(case, documents, deadlines)

    def _build_case_context(
        self,
        case: Case,
        documents: List[Document],
        deadlines: List[Deadline]
    ) -> str:
        """Build context string for case summary generation"""

        context_parts = []

        # Case basics
        context_parts.append(f"Case Number: {case.case_number}")
        context_parts.append(f"Title: {case.title}")

        if case.court:
            context_parts.append(f"Court: {case.court}")
        if case.judge:
            context_parts.append(f"Judge: {case.judge}")
        if case.case_type:
            context_parts.append(f"Case Type: {case.case_type}")
        if case.jurisdiction:
            context_parts.append(f"Jurisdiction: {case.jurisdiction}")

        # Parties
        if case.parties:
            context_parts.append("\nParties:")
            for party in case.parties:
                context_parts.append(f"  - {party.get('role', 'Unknown')}: {party.get('name', 'Unknown')}")

        # Documents
        context_parts.append(f"\n{len(documents)} document(s) filed:")
        for doc in documents[:10]:  # Most recent 10
            # Use filing_date if available, otherwise fall back to created_at
            doc_date = doc.filing_date if doc.filing_date else doc.created_at.date()
            doc_info = f"  - {doc_date.strftime('%Y-%m-%d')}: {doc.file_name}"
            if doc.document_type:
                doc_info += f" ({doc.document_type})"
            if doc.ai_summary:
                doc_info += f"\n    Summary: {doc.ai_summary[:200]}"
            context_parts.append(doc_info)

        # Deadlines
        upcoming_deadlines = [d for d in deadlines if d.deadline_date and d.status == 'pending']
        upcoming_deadlines.sort(key=lambda x: x.deadline_date if x.deadline_date else datetime.max.date())

        context_parts.append(f"\n{len(upcoming_deadlines)} upcoming deadline(s):")
        for deadline in upcoming_deadlines[:10]:  # Next 10
            deadline_info = f"  - {deadline.deadline_date}: {deadline.title}"
            if deadline.priority:
                deadline_info += f" [Priority: {deadline.priority}]"
            if deadline.calculation_basis:
                deadline_info += f"\n    Basis: {deadline.calculation_basis[:150]}"
            context_parts.append(deadline_info)

        return "\n".join(context_parts)

    def _generate_fallback_summary(
        self,
        case: Case,
        documents: List[Document],
        deadlines: List[Deadline]
    ) -> Dict:
        """Generate simple fallback summary if AI fails"""

        upcoming_deadlines = [d for d in deadlines if d.deadline_date and d.status == 'pending']
        upcoming_deadlines.sort(key=lambda x: x.deadline_date if x.deadline_date else datetime.max.date())

        return {
            "overview": f"Case {case.case_number} in {case.court or 'court'}. {len(documents)} documents filed, {len(upcoming_deadlines)} upcoming deadlines.",
            "current_status": f"Active case with {len(documents)} document(s) and {len(upcoming_deadlines)} pending deadline(s).",
            "key_documents": [
                f"{(doc.filing_date if doc.filing_date else doc.created_at.date()).strftime('%Y-%m-%d')}: {doc.file_name}"
                for doc in documents[:5]
            ],
            "critical_deadlines": [
                f"{d.deadline_date}: {d.title}"
                for d in upcoming_deadlines[:5]
            ],
            "timeline": [
                f"{(doc.filing_date if doc.filing_date else doc.created_at.date()).strftime('%Y-%m-%d')}: {doc.file_name} filed"
                for doc in documents[:10]
            ],
            "action_items": [
                f"Review deadline: {d.title} (due {d.deadline_date})"
                for d in upcoming_deadlines[:3]
            ],
            "last_updated": datetime.now().isoformat()
        }

    async def update_summary_on_event(
        self,
        case_id: str,
        event_type: str,
        event_details: Dict,
        db: Session
    ):
        """
        Update case summary when an event occurs
        Events: document_uploaded, deadline_extracted, chat_interaction, etc.
        """

        # Get case with all related data
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return None

        documents = db.query(Document).filter(
            Document.case_id == case_id
        ).order_by(Document.created_at.desc()).all()

        deadlines = db.query(Deadline).filter(
            Deadline.case_id == case_id
        ).order_by(Deadline.deadline_date.asc().nullslast()).all()

        # Regenerate summary
        summary = await self.generate_case_summary(case, documents, deadlines, db)

        return summary
