"""
Case Summary Prompts - Auto-updating case summary generation

These prompts are used by case_summary_service.py for generating
comprehensive case summaries that update whenever events occur.
"""
from app.prompts.registry import PromptTemplate, registry


# =============================================================================
# CASE SUMMARY GENERATION PROMPT
# =============================================================================

CASE_SUMMARY_PROMPT = """You are an expert legal case analyst. Generate a comprehensive case summary.

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
  "last_updated": "{last_updated}"
}}"""


# =============================================================================
# REGISTER PROMPTS
# =============================================================================

registry.register(PromptTemplate(
    name="case_summary",
    version="1.0",
    description="Generate comprehensive case summary with overview, status, and action items",
    category="case_summary",
    user_prompt=CASE_SUMMARY_PROMPT,
    required_variables=("case_context", "last_updated"),
    max_tokens=4096,
))
