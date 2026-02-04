"""
Legal Analysis Prompts - Document analysis and deadline calculation

These prompts are used by ai_service.py for:
- Comprehensive legal document analysis
- Deadline calculation based on rules
- Chat with case context
"""
from app.prompts.registry import PromptTemplate, registry


# =============================================================================
# DOCUMENT ANALYSIS PROMPTS
# =============================================================================

DOCUMENT_ANALYSIS_SYSTEM = """You are an expert Florida legal assistant with deep knowledge of:
- Florida Rules of Civil Procedure
- Florida Rules of Criminal Procedure
- Florida Rules of Appellate Procedure
- Federal Rules of Civil Procedure
- All Florida judicial circuit rules

Analyze legal documents with precision and extract all relevant case information."""

DOCUMENT_ANALYSIS_USER = """Analyze this legal document and extract structured information.

CRITICAL: Look carefully for dates in the document, especially:
- Filing date (when this document was filed with the court)
- Service date (when this document was served on parties)
- Date at the top of the document
- Date in certificate of service
- Any dates mentioned in the heading or footer
- **HEARING DATES** - Any date when a hearing, trial, mediation, or conference is scheduled
- **TRIAL DATES** - Any date when trial is set or scheduled
- **MEDIATION DATES** - Any scheduled mediation or settlement conference
- **DEPOSITION DATES** - Any scheduled depositions

Document Text:
{document_text}

Extract and return as valid JSON (no markdown formatting):
{{
  "case_number": "string or null",
  "court": "string or null",
  "judge": "string or null",
  "document_type": "string (motion, order, notice, complaint, answer, interrogatories, request for production, request for admissions, notice of hearing, order setting hearing, etc.)",
  "filing_date": "YYYY-MM-DD (CRITICAL: Extract from document text - look for 'filed', date at top, or certificate of service)",
  "service_date": "YYYY-MM-DD or null (from certificate of service)",
  "service_method": "email|mail|personal|electronic|null (from certificate of service)",
  "parties": [
    {{"name": "string", "role": "plaintiff|defendant|appellant|appellee|etc"}}
  ],
  "jurisdiction": "state|federal|null",
  "district": "Northern|Middle|Southern|null",
  "case_type": "civil|criminal|appellate|null",
  "summary": "brief 2-3 sentence summary of document",
  "key_dates": [
    {{"date": "YYYY-MM-DD", "description": "CRITICAL: Be specific - use phrases like 'Hearing scheduled', 'Trial date set', 'Mediation conference', 'Deposition of John Doe', etc."}}
  ],
  "relief_sought": "string or null",
  "deadlines_mentioned": [
    {{"deadline_type": "string", "date": "YYYY-MM-DD or null", "description": "string"}}
  ]
}}

IMPORTANT:
- If you see ANY date in the document, try to determine if it's the filing date or service date
- Look in the certificate of service section for service date and method
- Extract the service method (email, mail, personal delivery, electronic filing, etc.)
- Be specific about document type (e.g., "Plaintiff's First Request for Production" not just "motion")
- **CRITICAL**: If the document mentions a hearing date, trial date, mediation date, or any scheduled event,
  you MUST include it in the "key_dates" array with a clear description (e.g., "Hearing scheduled", "Trial date set", "Mediation conference")

Return ONLY the JSON object, no additional text."""


# =============================================================================
# DEADLINE CALCULATION PROMPTS
# =============================================================================

DEADLINE_CALCULATION_USER = """Based on this document and applicable Florida court rules, calculate all deadlines.

Document Type: {document_type}
Filing Date: {filing_date}
Court: {court}
Case Type: {case_type}
Jurisdiction: {jurisdiction}

Applicable Rules:
{rules_text}

Calculate deadlines considering:
1. Service method (personal, mail, electronic)
2. Weekends and holidays
3. Additional time for mail service (typically +3 days in Florida)
4. Court-specific local rules

Return as valid JSON array (no markdown formatting):
[
  {{
    "deadline_type": "response|hearing|filing|etc",
    "deadline_date": "YYYY-MM-DD",
    "deadline_time": "HH:MM or null",
    "applicable_rule": "rule citation",
    "calculation_explanation": "how deadline was calculated",
    "priority": "low|medium|high|critical"
  }}
]

Return ONLY the JSON array, no additional text."""


# =============================================================================
# CHAT CONTEXT PROMPTS
# =============================================================================

CHAT_CONTEXT_SYSTEM = """You are an expert Florida legal assistant specializing in docketing and case management.
You have access to Florida court rules and case documents.

CASE CONTEXT:
- Case Number: {case_number}
- Court: {court}
- Case Type: {case_type}
- Jurisdiction: {jurisdiction}

RELEVANT FLORIDA COURT RULES:
{rules_context}

RELEVANT CASE DOCUMENTS:
{docs_context}

Provide accurate, actionable legal information based on Florida law and the case context.
Always cite specific rules when providing deadline calculations or procedural guidance.
Be conversational but professional."""


# =============================================================================
# REGISTER PROMPTS
# =============================================================================

registry.register(PromptTemplate(
    name="document_analysis",
    version="1.0",
    description="Comprehensive legal document analysis extracting case info, dates, and deadlines",
    category="legal_analysis",
    system_prompt=DOCUMENT_ANALYSIS_SYSTEM,
    user_prompt=DOCUMENT_ANALYSIS_USER,
    required_variables=("document_text",),
    max_tokens=4096,
))

registry.register(PromptTemplate(
    name="deadline_calculation",
    version="1.0",
    description="Calculate deadlines based on document analysis and applicable rules",
    category="legal_analysis",
    user_prompt=DEADLINE_CALCULATION_USER,
    required_variables=("document_type", "filing_date", "court", "case_type", "jurisdiction", "rules_text"),
    max_tokens=2048,
))

registry.register(PromptTemplate(
    name="chat_context",
    version="1.0",
    description="System prompt for chat with case and rules context",
    category="legal_analysis",
    system_prompt=CHAT_CONTEXT_SYSTEM,
    user_prompt="{user_message}",
    required_variables=("case_number", "court", "case_type", "jurisdiction", "rules_context", "docs_context", "user_message"),
    max_tokens=4096,
))
