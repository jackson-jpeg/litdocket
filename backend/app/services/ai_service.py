from anthropic import Anthropic
from typing import Dict, List, Optional
import json
import re
from app.config import settings


class AIService:
    """Service for Claude AI integration"""

    def __init__(self, model: Optional[str] = None):
        self.anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model or settings.DEFAULT_AI_MODEL

    async def analyze_legal_document(self, text: str, document_type: Optional[str] = None) -> Dict:
        """
        Comprehensive legal document analysis using Claude.

        Args:
            text: Extracted text from the legal document
            document_type: Optional hint about document type

        Returns:
            Dictionary with extracted case information
        """

        system_prompt = """You are an expert Florida legal assistant with deep knowledge of:
- Florida Rules of Civil Procedure
- Florida Rules of Criminal Procedure
- Florida Rules of Appellate Procedure
- Federal Rules of Civil Procedure
- All Florida judicial circuit rules

Analyze legal documents with precision and extract all relevant case information."""

        user_prompt = f"""Analyze this legal document and extract structured information.

Document Text:
{text[:15000]}

Extract and return as valid JSON (no markdown formatting):
{{
  "case_number": "string or null",
  "court": "string or null",
  "judge": "string or null",
  "document_type": "string (motion, order, notice, complaint, answer, etc.)",
  "filing_date": "YYYY-MM-DD or null",
  "parties": [
    {{"name": "string", "role": "plaintiff|defendant|appellant|appellee|etc"}}
  ],
  "jurisdiction": "state|federal|null",
  "district": "Northern|Middle|Southern|null",
  "case_type": "civil|criminal|appellate|null",
  "summary": "brief 2-3 sentence summary of document",
  "key_dates": [
    {{"date": "YYYY-MM-DD", "description": "string"}}
  ],
  "relief_sought": "string or null",
  "deadlines_mentioned": [
    {{"deadline_type": "string", "date": "YYYY-MM-DD or null", "description": "string"}}
  ]
}}

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
            except json.JSONDecodeError:
                pass

        # Fallback
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
