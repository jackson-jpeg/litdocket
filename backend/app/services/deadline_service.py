"""
Deadline Service - Implements Jackson's Legal Docketing Methodology
Extracts and calculates deadlines from legal documents with comprehensive Florida/Federal rules support
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
import re

from app.services.ai_service import AIService
from app.utils.florida_holidays import is_business_day, adjust_to_business_day, get_all_court_holidays
from app.utils.florida_jurisdictions import identify_jurisdiction, get_applicable_rules
from app.services.rules_engine import rules_engine, TriggerType


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

        # Get service info from metadata
        service_date = filing_date  # Default to filing date if no service date
        service_method = 'electronic'  # Default assumption

        prompt = f"""You are an expert Florida legal docketing assistant following Jackson's comprehensive methodology.

CRITICAL PRINCIPLES:
1. COMPREHENSIVE OVER SELECTIVE - Capture EVERY potential deadline, obligation, or court-required action
2. SHOW YOUR WORK - Always explain how you calculated each deadline with full rule citations
3. ACCURACY THROUGH VERIFICATION - Cross-check calculations and verify applicable rules
4. USE ACTUAL DATES FROM THE DOCUMENT - Don't assume today's date!

DOCUMENT ANALYSIS:
Document Type: {document_type}
Jurisdiction: {jurisdiction}
Court: {court}
Filing/Service Date: {filing_date or 'MUST extract from document text'}
Service Method: {service_method or 'MUST extract from certificate of service'}

CRITICAL FOR DISCOVERY DOCUMENTS (MOST COMMON):
- Request for Production → 30 days to respond (Fla. R. Civ. P. 1.350) [HIGH PRIORITY]
- Interrogatories → 30 days to respond (Fla. R. Civ. P. 1.340) [HIGH PRIORITY]
- Request for Admissions → 30 days to respond (Fla. R. Civ. P. 1.370) [CRITICAL - deemed admitted if not answered]
- If served by mail → ADD 5 additional days to the deadline
- If served by email/electronic → NO additional days (since Jan 1, 2019)

MOTION PRACTICE:
- Response to Motion for Summary Judgment → 20 days (HIGH PRIORITY)
- Response to general motion → varies by local rules (typically 10-20 days)
- Reply to response → typically 10 days

PLEADING DEADLINES:
- Answer to Complaint → 20 days after service (Fla. R. Civ. P. 1.140(a)) [CRITICAL]
- Amended Answer → 20 days after amended complaint served
- Counterclaim Answer → 20 days after counterclaim served

TRIAL DEADLINES:
- Pretrial Stipulation → typically 10-15 days before trial per local rules [HIGH]
- Witness List → varies by local rules (often 30-45 days before trial)
- Exhibit List → varies by local rules
- Jury Instructions → typically 15 days before trial

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
1. WHO the obligation applies to - MUST use professional format:
   - "Plaintiff, [Full Name]" NOT "plaintiff" or "Plaintiff" alone
   - "Defendant, [Full Name]" NOT "defendant" or "Defendant" alone
   - "Plaintiffs, [Name 1] and [Name 2]" for multiple parties
   - "All Parties" when obligation applies to everyone (BOTH words capitalized)
   Examples: "Plaintiff, Robert Becker", "Defendant, Jane Doe", "All Parties"
2. WHAT action is required (be specific, use professional terminology)
3. WHEN it's due (CALCULATE THE ACTUAL DATE - do not return null unless absolutely unavoidable)
4. HOW you calculated it - Professional format with full formula:
   - Show complete calculation: "triggered 1 Court Day plus 30 Days after service date"
   - Include all rule citations in full: "Fla. R. Civ. P. 1.350(a)" not just "RCP 1.350"
   - Source attribution: [per MM/DD/YYYY Document Type; via MM/DD/YYYY ECR]
5. SOURCE document with date and service method

CRITICAL CALCULATION INSTRUCTIONS:
- If this is a Request for Production/Interrogatories/RFA: Response deadline = service date + 30 days + (5 days if mail)
- ALWAYS extract the service/filing date from the document text if not provided above
- Look in certificate of service, heading, footer, or anywhere dates appear
- Count calendar days, adjust if deadline falls on weekend/holiday
- Show complete calculation: "30 days from [service date] = [calculated date], plus 5 days for mail service = [final date]"

DATE EXTRACTION INSTRUCTIONS (CRITICAL):
1. Check "Certificate of Service" at the end of document - this is THE authoritative date
2. Check document header/caption for "Filed:" or "Served:" date
3. Check footer or signature block for dates
4. Common date formats to recognize:
   - "12/31/2024", "December 31, 2024", "Dec. 31, 2024"
   - "Filed: January 5, 2025", "Served: 1/5/25"
   - In certificate: "I HEREBY CERTIFY that on January 5, 2025..."
5. If multiple dates appear, use the SERVICE date (not filing date) for calculating response deadlines
6. If document says "filed" but no service info, assume service same day for electronic filing
7. NEVER use today's date - extract actual dates from the document text
8. If truly no date found, set deadline_date to null and is_estimated to true

Return as JSON array with this structure:
[
  {{
    "party_role": "Defendant, John Doe",
    "action": "file and serve answer to Complaint",
    "deadline_date": "2025-01-15",
    "deadline_type": "responsive pleading",
    "calculation_basis": "Deadline to file and serve Answer to Complaint (triggered 20 calendar days after service date 12/25/2024 plus 5 days for U.S. Mail service = 01/19/2025, moved to 01/20/2025 next business day) [per 12/20/2024 Summons and Complaint; via 12/25/2024 Certificate of Service]",
    "description": "Deadline to file and serve Answer to Complaint",
    "trigger_event": "service of complaint",
    "trigger_date": "2024-12-25",
    "applicable_rule": "Fla. R. Civ. P. 1.140(a)(1)",
    "service_method": "U.S. Mail",
    "source_document": "12/20/2024 Summons and Complaint",
    "priority": "high",
    "is_estimated": false
  }}
]

PROFESSIONAL FORMATTING EXAMPLES:

Example 1 - Discovery Response:
{{
  "party_role": "Defendant, Jane Smith",
  "action": "respond to Plaintiff's First Request for Production of Documents",
  "deadline_date": "2024-12-31",
  "deadline_type": "Deadline",
  "calculation_basis": "Deadline to respond to Plaintiff's First Request for Production of Documents (triggered 30 calendar days from service on 12/01/2024 per Fla. R. Civ. P. 1.350(a), no extension for electronic service = 12/31/2024) [per 12/01/2024 Plaintiff's First Request for Production; via 12/01/2024 E-Portal]",
  "description": "Deadline to respond to Plaintiff's First Request for Production of Documents",
  "trigger_event": "service of request for production",
  "trigger_date": "2024-12-01",
  "applicable_rule": "Fla. R. Civ. P. 1.350(a)",
  "service_method": "electronic",
  "priority": "high"
}}

Example 2 - Multiple Parties (use "Plaintiffs" or "Defendants" when multiple):
{{
  "party_role": "Plaintiffs, Robert Becker and Alycia Alford",
  "action": "notify court that parties cannot agree on a mediator",
  "deadline_date": "2025-09-02",
  "deadline_type": "Deadline",
  "calculation_basis": "Plaintiffs, Robert Becker and Alycia Alford to notify court that parties cannot agree on a mediator (triggered 1 Court Day plus 19 Days after Order/Referral to Mediation) [per 08/12/2025 Order/Referral to Mediation; via 10/27/2025 ECR]",
  "description": "Plaintiffs, Robert Becker and Alycia Alford to notify court that parties cannot agree on a mediator",
  "trigger_event": "date of order/referral to mediation",
  "trigger_date": "2025-08-12",
  "applicable_rule": "RCP 1.720(j)(2)",
  "service_method": "electronic",
  "priority": "standard"
}}

Example 3 - All Parties (BOTH words capitalized):
{{
  "party_role": "All Parties",
  "action": "complete fact and expert discovery",
  "deadline_date": "2026-06-01",
  "deadline_type": "Deadline",
  "calculation_basis": "Deadline for All Parties to complete fact and expert discovery (Calculated: fixed date provided in Case Management Plan, 05/31/26, moved to next business day) [per 08/12/2025 Court Ordered Case Management Plan General; via 10/27/2025 ECR]",
  "description": "Deadline for All Parties to complete fact and expert discovery",
  "trigger_event": "court ordered case management plan",
  "trigger_date": "2025-08-12",
  "applicable_rule": "Set by Court Order",
  "service_method": "electronic",
  "priority": "high"
}}

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

    def _parse_date_to_object(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to Python date object"""
        if not date_str:
            return None

        try:
            # Handle ISO format: YYYY-MM-DD
            if isinstance(date_str, str):
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            elif isinstance(date_str, date):
                return date_str
            else:
                return None
        except (ValueError, TypeError):
            return None

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
            deadline_date_str = raw.get('deadline_date')
            deadline_date = self._parse_date_to_object(deadline_date_str)

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

            # Parse trigger_date as well
            trigger_date_str = raw.get('trigger_date')
            trigger_date = self._parse_date_to_object(trigger_date_str)

            # Smart priority assignment based on deadline type and keywords
            raw_priority = raw.get('priority', 'medium')
            priority = self._calculate_smart_priority(
                deadline_type=raw.get('deadline_type', 'general'),
                action=action,
                raw_priority=raw_priority,
                deadline_date=deadline_date
            )

            formatted_deadline = {
                'case_id': case_id,
                'user_id': user_id,
                'title': title,
                'description': full_description,
                'deadline_date': deadline_date,  # Now a date object
                'deadline_type': raw.get('deadline_type', 'general'),
                'applicable_rule': raw.get('applicable_rule'),
                'rule_citation': raw.get('calculation_basis'),
                'calculation_basis': raw.get('calculation_basis'),
                'priority': priority,  # Now uses smart calculation
                'status': 'pending',
                'party_role': party,
                'action_required': action,
                'trigger_event': raw.get('trigger_event'),
                'trigger_date': trigger_date,  # Now a date object
                'is_estimated': raw.get('is_estimated', False),
                'source_document': source_doc,
                'service_method': service_method
            }

            formatted_deadlines.append(formatted_deadline)

        return formatted_deadlines

    def _calculate_smart_priority(
        self,
        deadline_type: str,
        action: str,
        raw_priority: str,
        deadline_date: Optional[date]
    ) -> str:
        """
        Calculate intelligent priority based on deadline characteristics

        Priority levels (from highest to lowest):
        - fatal: Missing this has case-ending consequences (RFA responses, dispositive motions)
        - critical: High stakes but not case-ending (Answer, MSJ response)
        - important: Significant impact (discovery responses, trial prep)
        - standard: Normal deadlines (routine motions, non-critical filings)
        - informational: Nice to know but flexible (status conferences, informal deadlines)
        """

        action_lower = action.lower()

        # FATAL PRIORITY - Case-ending consequences
        fatal_keywords = [
            'request for admission', 'admission', 'deemed admitted',
            'default', 'dismissal', 'summary judgment response',
            'appeal deadline', 'notice of appeal'
        ]
        if any(keyword in action_lower for keyword in fatal_keywords):
            return 'fatal'

        # CRITICAL PRIORITY - Answer, responsive pleadings, MSJ
        critical_keywords = [
            'answer to complaint', 'answer complaint',
            'respond to motion for summary judgment',
            'opposition to motion for summary judgment',
            'response to summary judgment',
            'notice to appear', 'initial appearance'
        ]
        if any(keyword in action_lower for keyword in critical_keywords):
            return 'critical'

        # Check deadline type
        if deadline_type in ['responsive pleading', 'answer']:
            return 'critical'

        # IMPORTANT PRIORITY - Discovery, significant motions
        important_keywords = [
            'discovery response', 'interrogator', 'request for production',
            'respond to motion', 'reply to', 'pretrial',
            'witness list', 'exhibit list', 'deposition'
        ]
        if any(keyword in action_lower for keyword in important_keywords):
            return 'important'

        if deadline_type in ['discovery response', 'motion response', 'pretrial']:
            return 'important'

        # Check if deadline is within 7 days - bump up priority
        if deadline_date:
            from datetime import datetime
            days_until = (deadline_date - datetime.now().date()).days
            if days_until <= 7 and raw_priority in ['medium', 'standard']:
                return 'important'
            elif days_until <= 3:
                return 'critical'

        # STANDARD PRIORITY - Routine matters
        if deadline_type in ['hearing', 'status conference', 'case management']:
            return 'standard'

        # Default to raw priority or standard
        priority_map = {
            'low': 'informational',
            'medium': 'standard',
            'high': 'important',
            'critical': 'critical',
            'fatal': 'fatal'
        }

        return priority_map.get(raw_priority.lower(), 'standard')

    def calculate_florida_deadline(
        self,
        trigger_date: date,
        days_to_add: int,
        service_method: str = 'email',
        skip_weekends: bool = False
    ) -> date:
        """
        Calculate deadline following Florida rules with proper holiday handling

        Args:
            trigger_date: The starting date
            days_to_add: Number of days to add
            service_method: 'email', 'mail', or 'personal'
            skip_weekends: If True, skip weekends and holidays (for "business days")
        """

        # Add service method days (CRITICAL for Florida practice)
        if service_method.lower() in ['mail', 'u.s. mail', 'usps']:
            days_to_add += 5  # Add 5 days for mail service
        elif service_method.lower() in ['email', 'e-portal', 'electronic']:
            pass  # No additional days since Jan 1, 2019

        # Calculate deadline
        current = trigger_date
        days_counted = 0

        # Count calendar days or business days
        while days_counted < days_to_add:
            current += timedelta(days=1)

            # If skip_weekends mode, only count business days
            if skip_weekends:
                if is_business_day(current):
                    days_counted += 1
            else:
                # Count all calendar days (Florida default)
                days_counted += 1

        # CRITICAL: If deadline falls on weekend/holiday, extend to next business day
        # This applies regardless of skip_weekends setting
        current = adjust_to_business_day(current)

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

    async def generate_deadline_chains(
        self,
        trigger_event: str,
        trigger_date: date,
        jurisdiction: str,
        court_type: str,
        case_id: str,
        user_id: str,
        service_method: str = "electronic"
    ) -> List[Dict[str, Any]]:
        """
        Generate deadline chains using the rules engine
        Automatic deadline generation from triggers

        Args:
            trigger_event: Type of trigger (e.g., "service of complaint", "trial date set")
            trigger_date: Date of the trigger event
            jurisdiction: "florida_state" or "federal"
            court_type: "civil", "criminal", or "appellate"
            case_id: Case ID
            user_id: User ID
            service_method: "electronic", "mail", or "personal"

        Returns:
            List of generated deadline dictionaries
        """

        # Map trigger event to TriggerType enum
        trigger_mapping = {
            "service of complaint": TriggerType.COMPLAINT_SERVED,
            "complaint served": TriggerType.COMPLAINT_SERVED,
            "trial date set": TriggerType.TRIAL_DATE,
            "trial date": TriggerType.TRIAL_DATE,
            "case filed": TriggerType.CASE_FILED,
            "motion filed": TriggerType.MOTION_FILED,
            "hearing scheduled": TriggerType.HEARING_SCHEDULED,
        }

        trigger_type = None
        trigger_lower = trigger_event.lower()
        for key, value in trigger_mapping.items():
            if key in trigger_lower:
                trigger_type = value
                break

        if not trigger_type:
            # No matching rule template
            return []

        # Find applicable rules from rules engine
        applicable_rules = rules_engine.get_applicable_rules(
            jurisdiction=jurisdiction,
            court_type=court_type,
            trigger_type=trigger_type
        )

        generated_deadlines = []

        for rule_template in applicable_rules:
            # Calculate all dependent deadlines for this rule
            deadlines = rules_engine.calculate_dependent_deadlines(
                trigger_date=trigger_date,
                rule_template=rule_template,
                service_method=service_method
            )

            # Add case_id and user_id to each deadline
            for deadline in deadlines:
                deadline['case_id'] = case_id
                deadline['user_id'] = user_id
                deadline['deadline_type'] = rule_template.court_type
                generated_deadlines.append(deadline)

        return generated_deadlines

    def detect_trigger_from_document(
        self,
        document_type: str,
        document_analysis: Dict[str, Any],
        court_info: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if a document represents a trigger event
        Returns trigger info if detected, None otherwise

        Args:
            document_type: Type of document (e.g., "complaint", "summons")
            document_analysis: AI analysis of the document
            court_info: Court information string

        Returns:
            Dict with trigger_event, trigger_date, jurisdiction info or None
        """

        # Identify jurisdiction
        jurisdiction_info = identify_jurisdiction(court_info)

        # Map to our jurisdiction format
        if jurisdiction_info.get("type") == "federal":
            jurisdiction = "federal"
        elif jurisdiction_info.get("type") in ["state_circuit", "state_county"]:
            jurisdiction = "florida_state"
        else:
            jurisdiction = "florida_state"  # Default

        # Detect trigger events based on document type
        doc_type_lower = document_type.lower() if document_type else ""

        trigger_event = None
        court_type = "civil"  # Default assumption

        # Complaint/Summons triggers Answer deadline
        if any(word in doc_type_lower for word in ["complaint", "summons", "petition"]):
            trigger_event = "service of complaint"

        # Trial Notice triggers trial prep deadlines
        elif any(word in doc_type_lower for word in ["trial notice", "trial order", "notice of trial"]):
            trigger_event = "trial date set"

        # Motion triggers response deadline
        elif "motion" in doc_type_lower and "response" not in doc_type_lower:
            trigger_event = "motion filed"

        if trigger_event:
            # Try to extract trigger date from analysis
            trigger_date_str = document_analysis.get('filing_date') or document_analysis.get('service_date')
            trigger_date = self._parse_date_to_object(trigger_date_str) if trigger_date_str else None

            if not trigger_date:
                trigger_date = datetime.now().date()  # Fallback to today

            return {
                'trigger_event': trigger_event,
                'trigger_date': trigger_date,
                'jurisdiction': jurisdiction,
                'court_type': court_type,
                'jurisdiction_info': jurisdiction_info,
                'document_type': document_type
            }

        return None
