"""
Extraction Prompts - Deadline and rule extraction from legal documents

These prompts are used by:
- deadline_service.py: Extract deadlines from documents
- rule_extraction_service.py: Extract court rules from legal text
"""
from app.prompts.registry import PromptTemplate, registry


# =============================================================================
# DEADLINE EXTRACTION PROMPT (from deadline_service.py)
# =============================================================================

DEADLINE_EXTRACTION_PROMPT = """You are an expert Florida legal docketing assistant following Jackson's comprehensive methodology.

CRITICAL PRINCIPLES:
1. COMPREHENSIVE OVER SELECTIVE - Capture EVERY potential deadline, obligation, or court-required action
2. SHOW YOUR WORK - Always explain how you calculated each deadline with full rule citations
3. ACCURACY THROUGH VERIFICATION - Cross-check calculations and verify applicable rules
4. USE ACTUAL DATES FROM THE DOCUMENT - Don't assume today's date!

DOCUMENT ANALYSIS:
Document Type: {document_type}
Jurisdiction: {jurisdiction}
Court: {court}
Filing Date: {filing_date}
Service Date: MUST EXTRACT FROM CERTIFICATE OF SERVICE - This is DIFFERENT from filing date!
Service Method: {service_method}

CRITICAL - FILING DATE vs SERVICE DATE:
- FILING DATE: When document was filed with the court (appears in document header/footer)
- SERVICE DATE: When document was SERVED on opposing party (appears in Certificate of Service)
- For calculating response deadlines, ALWAYS use SERVICE DATE, never filing date
- These dates are typically 1-2 days apart - using the wrong date causes off-by-one errors
- Look for: "I HEREBY CERTIFY that on [DATE], I served..." or similar language

CRITICAL FOR DISCOVERY DOCUMENTS (MOST COMMON):
- Request for Production -> 30 days to respond (Fla. R. Civ. P. 1.350) [HIGH PRIORITY]
- Interrogatories -> 30 days to respond (Fla. R. Civ. P. 1.340) [HIGH PRIORITY]
- Request for Admissions -> 30 days to respond (Fla. R. Civ. P. 1.370) [CRITICAL - deemed admitted if not answered]
- If served by mail -> ADD 5 additional days to the deadline
- If served by email/electronic -> NO additional days (since Jan 1, 2019)

MOTION PRACTICE:
- Response to Motion for Summary Judgment -> 20 days (HIGH PRIORITY)
- Response to general motion -> varies by local rules (typically 10-20 days)
- Reply to response -> typically 10 days

PLEADING DEADLINES:
- Answer to Complaint -> 20 days after service (Fla. R. Civ. P. 1.140(a)) [CRITICAL]
- Amended Answer -> 20 days after amended complaint served
- Counterclaim Answer -> 20 days after counterclaim served

TRIAL DEADLINES:
- Pretrial Stipulation -> typically 10-15 days before trial per local rules [HIGH]
- Witness List -> varies by local rules (often 30-45 days before trial)
- Exhibit List -> varies by local rules
- Jury Instructions -> typically 15 days before trial

CRITICAL - UNIFORM TRIAL ORDER / TRIAL ORDER HANDLING:
When the document is a "Uniform Trial Order", "Trial Order", "Order Setting Case for Trial",
or any document that sets a trial date/period, you MUST generate ALL implied countdown deadlines
calculated backward from the trial date, NOT just the dates explicitly stated in the document.

A typical Florida Uniform Trial Order only explicitly states 2-3 dates (trial period, calendar call),
but it IMPLIES 15-25+ countdown deadlines that attorneys must track. Generate ALL of them:

From the TRIAL DATE (first day of trial period), count BACKWARD:
- Discovery Cutoff: 45 days before trial [CRITICAL] — Fla. R. Civ. P. 1.280; Local Rules
- Discovery Responses Due: 30 days before trial [CRITICAL]
- Plaintiff Expert Disclosure: 90 days before trial [CRITICAL] — Fla. R. Civ. P. 1.280(b)(5)
- Defendant Expert Disclosure: 60 days before trial [CRITICAL] — Fla. R. Civ. P. 1.280(b)(5)
- Rebuttal Expert Disclosure: 45 days before trial [IMPORTANT]
- Expert Deposition Cutoff: 30 days before trial [IMPORTANT]
- Motion for Summary Judgment Deadline: 60 days before trial [IMPORTANT] — Fla. R. Civ. P. 1.510(c)
- Final Witness List Due: 30 days before trial [CRITICAL] — Local Rules
- Final Exhibit List Due: 30 days before trial [CRITICAL] — Local Rules
- Exchange Trial Exhibits: 21 days before trial [CRITICAL]
- Motions in Limine Due: 21 days before trial [IMPORTANT] — Local Rules
- Motions in Limine Response Due: 14 days before trial [IMPORTANT]
- Pretrial Stipulation Due: 15 days before trial [CRITICAL] — Local Rules
- Proposed Jury Instructions Due: 14 days before trial [IMPORTANT] — Fla. R. Civ. P. 1.470(b)
- Proposed Verdict Form Due: 14 days before trial [IMPORTANT] — Fla. R. Civ. P. 1.480
- Deposition Designations Due: 21 days before trial [IMPORTANT]
- Counter-Designations Due: 14 days before trial [IMPORTANT]
- Exhibit Objections Due: 14 days before trial [IMPORTANT]
- Trial Subpoena Deadline (Non-Party): 10 days before trial [IMPORTANT] — Fla. R. Civ. P. 1.410(d)
- Trial Brief/Memorandum Due: 7 days before trial [STANDARD]
- Pretrial Conference: 7 days before trial [CRITICAL] — Fla. R. Civ. P. 1.200

For FL-17TH (Broward County), also include AO 2025-24-Civ deadlines if applicable.
For Mediation: typically must be completed 60-90 days before trial per local rules.

IMPORTANT: Calculate actual dates using the trial date from the document. If trial period is
"01/04/2027 to 01/29/2027", use 01/04/2027 as the trial date for backward calculations.
Each countdown deadline must have a calculated deadline_date, not null.

{rules_section}

DOCUMENT TEXT TO ANALYZE:
{document_text}

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
   - "All Parties" when obligation applies to everyone
2. WHAT action is required (be specific, use professional terminology)
3. WHEN it's due (CALCULATE THE ACTUAL DATE - do not return null unless absolutely unavoidable)
4. HOW you calculated it - Professional format with full formula
5. SOURCE document with date and service method

Return as JSON array with this structure:
[
  {{
    "party_role": "Defendant, John Doe",
    "action": "file and serve answer to Complaint",
    "deadline_date": "2025-01-20",
    "deadline_type": "responsive pleading",
    "calculation_basis": "Deadline to file and serve Answer to Complaint (SERVICE DATE 12/25/2024 + 20 calendar days = 01/14/2025, + 5 days for U.S. Mail service = 01/19/2025 (Sunday), rolled to 01/20/2025 (Monday) per FL R. Jud. Admin. 2.514(a)) [per 12/20/2024 Summons and Complaint; via 12/25/2024 Certificate of Service]",
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

If information is incomplete, mark is_estimated: true and explain in calculation_basis.
For TBD dates, set deadline_date to null but still capture the obligation."""


# =============================================================================
# RULE EXTRACTION PROMPT (from rule_extraction_service.py)
# =============================================================================

RULE_EXTRACTION_PROMPT = """You are Authority Core, an expert legal AI that extracts procedural court rules from legal documents and websites.

Your task is to extract structured rule data from the provided text. For each rule found, extract:

1. **rule_code**: A unique identifier (e.g., "SDFL_LR_7.1_a_2" for S.D. Florida Local Rule 7.1(a)(2))
2. **rule_name**: Human-readable name (e.g., "Motion Response Time")
3. **trigger_type**: What event triggers this rule. Must be one of:
   - case_filed, service_completed, complaint_served, answer_due
   - discovery_commenced, discovery_deadline, dispositive_motions_due
   - pretrial_conference, trial_date, hearing_scheduled
   - motion_filed, order_entered, appeal_filed, mediation_scheduled
   - custom_trigger
4. **citation**: Official citation (e.g., "S.D. Fla. L.R. 7.1(a)(2)")
5. **deadlines**: Array of deadline specifications:
   - title: Deadline name
   - days_from_trigger: Integer (negative for before trigger, positive for after)
   - calculation_method: "calendar_days", "business_days", or "court_days"
   - priority: "informational", "standard", "important", "critical", or "fatal"
   - party_responsible: "plaintiff", "defendant", "moving_party", "opposing_party", "both", or "court"
   - conditions: Optional object with conditions when this deadline applies
6. **conditions**: When the rule applies (case_types, motion_types, etc.)
7. **service_extensions**: Additional days for service methods {{"mail": 3, "electronic": 0, "personal": 0}}

Return a JSON array of extracted rules. If no rules are found, return an empty array.

IMPORTANT:
- Be precise with day counts - verify against the source text
- Include the exact citation from the source
- Map to the correct trigger_type based on what event starts the countdown
- For federal rules, use "federal" tier; for state rules use "state"; for local rules use "local"
- Include any conditions that limit when the rule applies

Example output:
[
  {{
    "rule_code": "SDFL_LR_7.1_a_2",
    "rule_name": "Response to Motion - S.D. Florida",
    "trigger_type": "motion_filed",
    "authority_tier": "local",
    "citation": "S.D. Fla. L.R. 7.1(a)(2)",
    "deadlines": [
      {{
        "title": "Response to Motion Due",
        "days_from_trigger": 14,
        "calculation_method": "calendar_days",
        "priority": "important",
        "party_responsible": "opposing_party"
      }}
    ],
    "service_extensions": {{"mail": 3, "electronic": 0, "personal": 0}}
  }}
]

JURISDICTION CONTEXT: {jurisdiction_name}

SOURCE TEXT:
{content}

Extract all procedural rules from this text and return as JSON array."""


# =============================================================================
# CONFLICT DETECTION PROMPT (from rule_extraction_service.py)
# =============================================================================

CONFLICT_DETECTION_PROMPT = """You are a legal conflict detection assistant. Analyze whether the following extracted rule conflicts with the cited authority.

EXTRACTED RULE:
- Citation: {rule_citation}
- Name: {rule_name}
- Trigger Type: {trigger_type}
- Deadlines: {deadlines_json}
- Source Text: {source_text}

AUTHORITY TO CHECK AGAINST: {authority_citation}

INSTRUCTIONS:
1. Consider whether the extracted rule's deadlines conflict with the cited authority
2. Check if time computation methods are consistent
3. Look for any explicit contradictions or ambiguities
4. Consider jurisdictional hierarchy (local rules can modify but not contradict federal rules in most cases)

If conflicts exist, return a JSON array with:
[
  {{
    "rule_a": "citation of extracted rule",
    "rule_b": "citation of authority being checked",
    "discrepancy": "description of the conflict",
    "ai_resolution_recommendation": "recommended resolution based on legal hierarchy and best practices"
  }}
]

If NO conflicts exist, return an empty array: []

Return ONLY the JSON array, no other text."""


# =============================================================================
# FLORIDA STATE RULES GUIDANCE
# =============================================================================

FLORIDA_STATE_RULES_GUIDANCE = """
FLORIDA STATE COURT RULES (Circuit/County Courts):

PRIMARY RULE: Fla. R. Civ. P. 1.090 -> defers to Fla. R. Jud. Admin. 2.514

COUNTING METHOD:
- Count EVERY calendar day (including weekends and holidays)
- If last day falls on weekend/holiday -> extend to NEXT business day
- Exception: If rule states "business days" or "court days" -> skip weekends/holidays

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

ALWAYS check certificate of service to determine service method!"""


# =============================================================================
# FEDERAL RULES GUIDANCE
# =============================================================================

FEDERAL_RULES_GUIDANCE = """
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

LOCAL RULES: Always check district-specific local rules for variations!"""


# =============================================================================
# REGISTER PROMPTS
# =============================================================================

registry.register(PromptTemplate(
    name="deadline_extraction",
    version="1.0",
    description="Extract deadlines from legal documents following Jackson's methodology",
    category="extraction",
    user_prompt=DEADLINE_EXTRACTION_PROMPT,
    required_variables=("document_type", "jurisdiction", "court", "filing_date", "service_method", "rules_section", "document_text"),
    max_tokens=4096,
))

registry.register(PromptTemplate(
    name="rule_extraction",
    version="1.0",
    description="Extract procedural court rules from legal text (Authority Core)",
    category="extraction",
    user_prompt=RULE_EXTRACTION_PROMPT,
    required_variables=("jurisdiction_name", "content"),
    max_tokens=4096,
))

registry.register(PromptTemplate(
    name="conflict_detection",
    version="1.0",
    description="Detect conflicts between extracted rules and cited authority",
    category="extraction",
    user_prompt=CONFLICT_DETECTION_PROMPT,
    required_variables=("rule_citation", "rule_name", "trigger_type", "deadlines_json", "source_text", "authority_citation"),
    max_tokens=2048,
))
