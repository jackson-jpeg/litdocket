from anthropic import Anthropic
from typing import Dict, List, Optional
import json
import re
import logging
from app.config import settings
from app.services.ai_models import AITask, get_model_id, model_router

logger = logging.getLogger(__name__)


class AIService:
    """
    Service for Claude AI integration with intelligent model routing.

    Model Selection Strategy:
    - Opus 4.5: Document analysis, chat, deadline calculation, legal research
    - Haiku: Rules scraping, batch processing, simple extraction
    - Sonnet: Fallback for balanced tasks

    Usage:
        # Default (uses task-based routing)
        ai = AIService()
        result = await ai.analyze_legal_document(text)  # Uses Opus 4.5

        # Override for specific use case
        ai = AIService(model="haiku")  # Force Haiku for all calls
    """

    def __init__(self, model: Optional[str] = None, task: Optional[AITask] = None):
        # RESILIENCE FIX: Sanitize API key to remove accidental whitespace/newlines
        api_key = settings.ANTHROPIC_API_KEY.strip()

        # Debug logging: Show first 8 chars of key (masked) to verify it loaded correctly
        logger.info(f"AI Service initialized with key: {api_key[:8]}...")

        # RESILIENCE FIX: Add retry logic to handle minor network blips
        self.anthropic = Anthropic(api_key=api_key, max_retries=3)

        # Model selection: explicit override > task-based routing > default
        if model:
            # Direct model override (e.g., "haiku", "opus", or full model ID)
            if model in ["opus", "haiku", "sonnet"]:
                from app.services.ai_models import MODELS
                self.model = MODELS[model].model_id
            else:
                self.model = model
            logger.info(f"AI Service using override model: {self.model}")
        elif task:
            # Task-based routing
            self.model = get_model_id(task)
            logger.info(f"AI Service using task-based model for {task.value}: {self.model}")
        else:
            # Default to Opus 4.5 (highest quality for legal work)
            self.model = settings.DEFAULT_AI_MODEL
            logger.info(f"AI Service using default model: {self.model}")

    def _get_model_for_task(self, task: AITask) -> str:
        """Get the appropriate model for a specific task (instance method)"""
        return model_router.get_model(task)

    async def analyze_legal_document(self, text: str, document_type: Optional[str] = None) -> Dict:
        """
        Comprehensive legal document analysis using Claude.

        Enhanced in Phase 1 to support "soft ingestion" - extracts additional
        context for documents that don't match standard trigger patterns.

        Args:
            text: Extracted text from the legal document
            document_type: Optional hint about document type

        Returns:
            Dictionary with extracted case information including:
            - Standard fields (case_number, court, parties, etc.)
            - Phase 1 fields (procedural_posture, potential_trigger_event, response_required)
        """

        system_prompt = """You are an expert Florida legal assistant with deep knowledge of:
- Florida Rules of Civil Procedure
- Florida Rules of Criminal Procedure
- Florida Rules of Appellate Procedure
- Federal Rules of Civil Procedure
- All Florida judicial circuit rules

Analyze legal documents with precision and extract all relevant case information.

You are particularly skilled at:
1. Identifying what procedural stage a case is in
2. Determining whether a document requires a response from opposing parties
3. Recognizing unusual or specialized motions and their deadline implications
4. Detecting urgency indicators that may affect deadline priority"""

        user_prompt = f"""Analyze this legal document and extract structured information.

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
{text[:15000]}

Extract and return as valid JSON (no markdown formatting):
{{
  "case_number": "string or null",
  "court": "string or null",
  "judge": "string or null",
  "document_type": "string - Be very specific (e.g., 'Motion for Sanctions Under Rule 11', 'Motion to Strike Affirmative Defenses', 'Motion for Protective Order', not just 'motion')",
  "document_category": "motion|order|notice|pleading|discovery|subpoena|correspondence|other",
  "filing_date": "YYYY-MM-DD (CRITICAL: Extract from document text - look for 'filed', date at top, or certificate of service)",
  "service_date": "YYYY-MM-DD or null (from certificate of service)",
  "service_method": "email|mail|personal|electronic|null (from certificate of service)",
  "parties": [
    {{"name": "string", "role": "plaintiff|defendant|appellant|appellee|movant|respondent|petitioner|etc"}}
  ],
  "jurisdiction": "state|federal|null",
  "district": "Northern|Middle|Southern|null",
  "case_type": "civil|criminal|appellate|null",
  "summary": "brief 2-3 sentence summary of document",
  "key_dates": [
    {{"date": "YYYY-MM-DD", "description": "CRITICAL: Be specific - use phrases like 'Hearing scheduled', 'Trial date set', 'Mediation conference', 'Deposition of John Doe', etc."}}
  ],
  "relief_sought": "string or null - What is the filing party asking the court to do?",
  "deadlines_mentioned": [
    {{"deadline_type": "string", "date": "YYYY-MM-DD or null", "description": "string"}}
  ],

  "procedural_posture": "string - What stage is the case in? (e.g., 'Pre-Answer', 'Discovery Phase', 'Post-Discovery/Pre-Trial', 'Trial Pending', 'Post-Judgment', 'On Appeal')",
  "potential_trigger_event": "string or null - If this document is NOT a standard pleading (Complaint, Answer, Motion to Dismiss), what deadline event might it trigger? (e.g., 'Receipt of Rule 11 Motion', 'Service of Subpoena Duces Tecum', 'Entry of Sanctions Order')",
  "response_required": true/false,
  "response_party": "plaintiff|defendant|both|third_party|null - Who must respond to this document?",
  "response_deadline_days": "number or null - If you can determine the standard response deadline from the document type, provide the number of days",
  "urgency_indicators": ["array of strings - Any keywords suggesting urgency: 'emergency', 'expedited', 'shortened time', 'ex parte', 'TRO', 'immediate', 'time-sensitive'"],
  "rule_references": ["array of strings - Any rule citations mentioned in the document (e.g., 'Fla. R. Civ. P. 1.380', 'FRCP 37', 'Local Rule 7.1')"]
}}

IMPORTANT:
- If you see ANY date in the document, try to determine if it's the filing date or service date
- Look in the certificate of service section for service date and method
- Extract the service method (email, mail, personal delivery, electronic filing, etc.)
- Be VERY specific about document type - this helps the system find applicable rules
- **CRITICAL**: If the document mentions a hearing date, trial date, mediation date, or any scheduled event,
  you MUST include it in the "key_dates" array with a clear description

**PHASE 1 FIELDS - CRITICAL FOR UNRECOGNIZED DOCUMENTS:**
- If the document is NOT a standard Complaint, Answer, or Motion to Dismiss, you MUST fill in:
  - "procedural_posture": What stage is the case in?
  - "potential_trigger_event": What deadline event might this trigger?
  - "response_required": Does this require a response?
  - "response_party": Who must respond?
  - "urgency_indicators": Any urgency keywords found
  - "rule_references": Any rules cited in the document

Return ONLY the JSON object, no additional text."""

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_prompt}]
        )

        return self._parse_json_response(response.content[0].text)

    async def calculate_deadlines(
        self,
        document_analysis: Dict,
        applicable_rules: List[Dict]
    ) -> List[Dict]:
        """
        Calculate deadlines based on document analysis and Florida rules.

        Args:
            document_analysis: Analysis from analyze_legal_document
            applicable_rules: Relevant rules retrieved from RAG

        Returns:
            List of calculated deadlines
        """

        rules_text = "\n\n".join([
            f"Rule {rule.get('section', 'N/A')}: {rule.get('text', '')}"
            for rule in applicable_rules
        ])

        prompt = f"""Based on this document and applicable Florida court rules, calculate all deadlines.

Document Type: {document_analysis.get('document_type')}
Filing Date: {document_analysis.get('filing_date')}
Court: {document_analysis.get('court')}
Case Type: {document_analysis.get('case_type')}
Jurisdiction: {document_analysis.get('jurisdiction')}

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

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{'role': 'user', 'content': prompt}]
        )

        result = self._parse_json_response(response.content[0].text)

        # Handle case where result is a dict instead of list
        if isinstance(result, dict):
            return [result]
        return result if isinstance(result, list) else []

    async def chat_with_context(
        self,
        user_message: str,
        conversation_history: List[Dict],
        case_context: Dict,
        relevant_rules: List[Dict],
        relevant_documents: List[Dict]
    ) -> Dict:
        """
        Generate chat response with full case and rules context.

        Args:
            user_message: The user's question/message
            conversation_history: Previous messages in this conversation
            case_context: Information about the current case
            relevant_rules: Retrieved court rules from RAG
            relevant_documents: Retrieved case documents from RAG

        Returns:
            Dictionary with response and metadata
        """

        rules_context = "\n\n".join([
            f"Rule {rule.get('section', 'N/A')}: {rule.get('text', '')[:500]}"
            for rule in relevant_rules[:5]
        ])

        docs_context = "\n\n".join([
            f"Document ({doc.get('document_type', 'Unknown')}): {doc.get('text', '')[:500]}"
            for doc in relevant_documents[:3]
        ])

        system_prompt = f"""You are an expert Florida legal assistant specializing in docketing and case management.
You have access to Florida court rules and case documents.

CASE CONTEXT:
- Case Number: {case_context.get('case_number', 'N/A')}
- Court: {case_context.get('court', 'N/A')}
- Case Type: {case_context.get('case_type', 'N/A')}
- Jurisdiction: {case_context.get('jurisdiction', 'N/A')}

RELEVANT FLORIDA COURT RULES:
{rules_context}

RELEVANT CASE DOCUMENTS:
{docs_context}

Provide accurate, actionable legal information based on Florida law and the case context.
Always cite specific rules when providing deadline calculations or procedural guidance.
Be conversational but professional."""

        # Build message history
        messages = []
        for msg in conversation_history[-10:]:  # Last 10 messages
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        messages.append({'role': 'user', 'content': user_message})

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )

        # Extract rule citations mentioned
        rule_citations = self._extract_rule_citations(response.content[0].text)

        return {
            'content': response.content[0].text,
            'model': self.model,
            'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
            'context_rules': rule_citations,
            'context_documents': [doc.get('id') for doc in relevant_documents]
        }

    def _parse_json_response(self, text: str) -> Dict:
        """Extract and parse JSON from Claude response"""
        # Remove markdown code blocks if present
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        # Try to find JSON in response
        json_match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                # Log the parse failure but continue to fallback
                logger.warning(f"JSON parse failed on matched text: {e}. Matched: {json_match.group()[:200]}...")

        # Fallback - return raw text with parse_error flag
        logger.debug(f"Returning raw text fallback for unparseable response: {text[:100]}...")
        return {'raw_text': text, 'parse_error': True}

    def _extract_rule_citations(self, text: str) -> List[str]:
        """Extract rule citations from response text"""
        # Pattern to match common rule citations (e.g., "FRCP 12(a)", "Fla. R. Civ. P. 1.140")
        pattern = r'(?:FRCP|F\.R\.C\.P\.|Fla\.\s*R\.\s*Civ\.\s*P\.|Florida Rule)\s*[\d\.]+(?:\([a-z0-9]+\))*'
        citations = re.findall(pattern, text, re.IGNORECASE)
        return list(set(citations))  # Remove duplicates

    async def analyze_with_prompt(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generic method to analyze with any custom prompt"""
        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{'role': 'user', 'content': prompt}]
        )

        return response.content[0].text


# Singleton instance
ai_service = AIService()
