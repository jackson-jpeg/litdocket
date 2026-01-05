"""
Deadline Service - Implements Jackson's Legal Docketing Methodology
Extracts and calculates deadlines from legal documents with comprehensive Florida/Federal rules support
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
import re

from app.services.ai_service import AIService


class DeadlineService:
    """
    Service for extracting and calculating legal deadlines
    Implements Jackson's comprehensive docketing methodology
    """

    def __init__(self):
        self.ai_service = AIService()

    async def extract_deadlines_from_document(
        self,
        document_text: str,
        document_metadata: Dict[str, Any],
        case_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract all deadlines from a legal document using Claude AI
        Follows Jackson's "comprehensive over selective" principle

        Returns list of deadline objects with Jackson's 3-line format:
        - Line 1: Date and Action
        - Line 2: Calculation Explanation
        - Line 3: Source Documentation
        """

        # Determine jurisdiction and applicable rules
        jurisdiction = document_metadata.get('jurisdiction', 'state')
        court = document_metadata.get('court', '')
        document_type = document_metadata.get('document_type', '')
        filing_date = document_metadata.get('filing_date')

        # Build comprehensive prompt following Jackson's methodology
        prompt = self._build_deadline_extraction_prompt(
            document_text=document_text,
            jurisdiction=jurisdiction,
            court=court,
            document_type=document_type,
            filing_date=filing_date
        )

        # Use Claude to extract deadlines
        try:
            response = await self.ai_service.analyze_with_prompt(prompt, max_tokens=4096)

            # Parse JSON response
            import json
            import re
            # Remove markdown code blocks if present
            response = re.sub(r'```json\s*', '', response)
            response = re.sub(r'```\s*', '', response)
            response = response.strip()

            # Try to find JSON array in response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                raw_deadlines = json.loads(json_match.group())
            else:
                raw_deadlines = []

            # Parse and format deadlines in Jackson's format
            deadlines = self._format_deadlines_jackson_style(
                raw_deadlines=raw_deadlines,
                case_id=case_id,
                user_id=user_id,
                document_metadata=document_metadata
            )

            return deadlines

        except Exception as e:
            print(f"Error extracting deadlines: {e}")
            return []

    def _build_deadline_extraction_prompt(
        self,
        document_text: str,
        jurisdiction: str,
        court: str,
        document_type: str,
        filing_date: Optional[str]
    ) -> str:
        """Build comprehensive deadline extraction prompt following Jackson's methodology"""

        # Determine which rules to apply
        if jurisdiction == 'federal' or 'federal' in court.lower():
            rules_section = self._get_federal_rules_guidance()
        else:
            rules_section = self._get_florida_state_rules_guidance()

        prompt = f"""You are an expert Florida legal docketing assistant following Jackson's comprehensive methodology.

CRITICAL PRINCIPLES:
1. COMPREHENSIVE OVER SELECTIVE - Capture EVERY potential deadline, obligation, or court-required action
2. SHOW YOUR WORK - Always explain how you calculated each deadline with full rule citations
3. ACCURACY THROUGH VERIFICATION - Cross-check calculations and verify applicable rules

DOCUMENT ANALYSIS:
Document Type: {document_type}
Jurisdiction: {jurisdiction}
Court: {court}
Filing Date: {filing_date or 'Not specified'}

{rules_section}

DOCUMENT TEXT TO ANALYZE:
{document_text[:15000]}

EXTRACT ALL DEADLINES INCLUDING:
- Responsive pleadings (answers, replies, responses)
- Motion practice deadlines (responses, replies, hearings)
- Discovery deadlines (responses to interrogatories, RFPs, RFAs, depositions)
- Expert witness deadlines (designations, reports)
- Mediation/ADR deadlines
- Pretrial deadlines (statements, witness lists, exhibits, jury instructions)
- Trial dates and calendar calls
- Post-trial deadlines (new trial motions, appeals)
- Court-ordered compliance deadlines

For EACH deadline, provide:
1. WHO the obligation applies to (Plaintiff, Defendant, All Parties, specific party names in Title Case)
2. WHAT action is required (be specific)
3. WHEN it's due (calculate if relative, state if fixed)
4. HOW you calculated it (trigger event + time period + applicable rule + service additions)
5. SOURCE document with date and service method

Return as JSON array with this structure:
[
  {{
    "party_role": "Defendant, John Doe",
    "action": "file and serve answer to Complaint",
    "deadline_date": "2025-01-15",
    "deadline_type": "responsive pleading",
    "calculation_basis": "20 days after service on 12/25/2024 (Fla. R. Civ. P. 1.140(a)(1)) + 5 days for mail service",
    "trigger_event": "service of complaint",
    "trigger_date": "2024-12-25",
    "applicable_rule": "Fla. R. Civ. P. 1.140(a)(1)",
    "service_method": "U.S. Mail",
    "source_document": "12/20/2024 Summons and Complaint",
    "priority": "high",
    "is_estimated": false
  }}
]

If information is incomplete, mark is_estimated: true and explain in calculation_basis.
For TBD dates, set deadline_date to null but still capture the obligation.
"""
        return prompt

    def _get_florida_state_rules_guidance(self) -> str:
        """Florida state court rules guidance"""
        return """
FLORIDA STATE COURT RULES (Circuit/County Courts):

PRIMARY RULE: Fla. R. Civ. P. 1.090 → defers to Fla. R. Jud. Admin. 2.514

COUNTING METHOD:
- Count EVERY calendar day (including weekends and holidays)
- If last day falls on weekend/holiday → extend to NEXT business day
- Exception: If rule states "business days" or "court days" → skip weekends/holidays

SERVICE TIME ADDITIONS (CRITICAL):
- Email/E-Portal service: NO additional days (effective January 1, 2019)
- U.S. Mail service: ADD 5 days to the deadline
- Personal service: NO additional days

COMMON FLORIDA DEADLINES:
- Answer to complaint: 20 days after service (Fla. R. Civ. P. 1.140(a))
- Response to motion for summary judgment: 20 days (varies by amended rules)
- Discovery responses: 30 days (Fla. R. Civ. P. 1.340, 1.350, 1.370)
- Interrogatories: 30 days to respond
- Requests for production: 30 days to respond
- Requests for admission: 30 days to respond

ALWAYS check certificate of service to determine service method!
"""

    def _get_federal_rules_guidance(self) -> str:
        """Federal court rules guidance (S.D. Fla., M.D. Fla., N.D. Fla.)"""
        return """
FEDERAL COURT RULES (S.D. Fla., M.D. Fla., N.D. Fla.):

PRIMARY RULE: Federal Rules of Civil Procedure, especially Rule 6

COUNTING METHOD:
- Count all days (similar to Florida state)
- Extend deadline if it lands on weekend/holiday to next weekday
- ADD 3 days for service by mail or electronic means under FRCP 6(d)

COMMON FEDERAL DEADLINES:
- Answer to complaint: 21 days after service (FRCP 12(a)(1)(A))
- Answer if service waived: 60 days (FRCP 12(a)(1)(A)(ii))
- Response to motion: typically 14 or 21 days depending on motion type
- Discovery responses: 30 days (FRCP 33, 34, 36)

LOCAL RULES: Always check district-specific local rules for variations!
"""

    def _format_deadlines_jackson_style(
        self,
        raw_deadlines: List[Dict],
        case_id: str,
        user_id: str,
        document_metadata: Dict
    ) -> List[Dict[str, Any]]:
        """
        Format deadlines following Jackson's 3-line standard:

        Line 1: MM/DD/YYYY Deadline for [Party] to [Action]
        Line 2: (Calculated: [Explicit calculation basis])
        Line 3: [per DATE Document; via DATE Service Method; REF#]
        """

        formatted_deadlines = []

        for raw in raw_deadlines:
            # Line 1: Date and Action
            deadline_date = raw.get('deadline_date')
            party = raw.get('party_role', 'Unknown Party')
            action = raw.get('action', 'Complete required action')

            if deadline_date:
                title = f"Deadline for {party} to {action}"
            else:
                title = f"TBD: Deadline for {party} to {action}"

            # Line 2: Calculation Explanation
            calculation = raw.get('calculation_basis', 'Fixed date as stated')
            description = f"(Calculated: {calculation})"

            # Line 3: Source Documentation
            source_doc = raw.get('source_document', 'Document')
            service_method = raw.get('service_method', '')
            source_citation = f"[per {source_doc}"
            if service_method:
                source_citation += f"; via {service_method}"
            source_citation += "]"

            # Combine into full description
            full_description = f"{description}\n\n{source_citation}"

            formatted_deadline = {
                'case_id': case_id,
                'user_id': user_id,
                'title': title,
                'description': full_description,
                'deadline_date': deadline_date,
                'deadline_type': raw.get('deadline_type', 'general'),
                'applicable_rule': raw.get('applicable_rule'),
                'rule_citation': raw.get('calculation_basis'),
                'calculation_basis': raw.get('calculation_basis'),
                'priority': raw.get('priority', 'medium'),
                'status': 'pending',
                'party_role': party,
                'action_required': action,
                'trigger_event': raw.get('trigger_event'),
                'trigger_date': raw.get('trigger_date'),
                'is_estimated': raw.get('is_estimated', False),
                'source_document': source_doc,
                'service_method': service_method
            }

            formatted_deadlines.append(formatted_deadline)

        return formatted_deadlines

    def calculate_florida_deadline(
        self,
        trigger_date: date,
        days_to_add: int,
        service_method: str = 'email',
        skip_weekends: bool = False
    ) -> date:
        """
        Calculate deadline following Florida rules

        Args:
            trigger_date: The starting date
            days_to_add: Number of days to add
            service_method: 'email', 'mail', or 'personal'
            skip_weekends: If True, skip weekends and holidays (for "business days")
        """

        # Add service method days
        if service_method.lower() in ['mail', 'u.s. mail', 'usps']:
            days_to_add += 5
        elif service_method.lower() in ['email', 'e-portal', 'electronic']:
            pass  # No additional days since Jan 1, 2019

        # Calculate deadline
        current = trigger_date
        days_counted = 0

        while days_counted < days_to_add:
            current += timedelta(days=1)

            # If skip_weekends, only count business days
            if skip_weekends and current.weekday() >= 5:  # Saturday=5, Sunday=6
                continue

            days_counted += 1

        # If deadline falls on weekend/holiday, extend to next business day
        while current.weekday() >= 5:  # Weekend
            current += timedelta(days=1)

        # TODO: Check federal/state holidays and extend if needed

        return current

    async def create_deadline_from_chat(
        self,
        deadline_info: Dict[str, Any],
        case_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Create a deadline from chatbot interaction
        Allows users to manually add/update deadlines via chat
        """

        # Format in Jackson's style
        title = deadline_info.get('title', 'New Deadline')
        description = deadline_info.get('description', '')

        deadline = {
            'case_id': case_id,
            'user_id': user_id,
            'title': title,
            'description': description,
            'deadline_date': deadline_info.get('deadline_date'),
            'deadline_type': deadline_info.get('deadline_type', 'general'),
            'applicable_rule': deadline_info.get('applicable_rule'),
            'priority': deadline_info.get('priority', 'medium'),
            'status': 'pending',
            'party_role': deadline_info.get('party_role'),
            'action_required': deadline_info.get('action_required'),
            'created_via_chat': True
        }

        return deadline
