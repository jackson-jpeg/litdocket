"""
Confidence Scoring Service for Case OS

Calculates confidence scores (0-100) for AI-extracted deadlines
based on multiple factors including rule matching, date clarity,
context keywords, and calculation consistency.
"""

import re
from typing import Dict, List, Optional
from datetime import date


class ConfidenceScorer:
    """Calculate confidence scores for deadline extractions"""

    # Keywords that indicate strong deadline language
    STRONG_KEYWORDS = {
        'shall': 10,
        'must': 10,
        'required': 8,
        'deadline': 10,
        'due': 9,
        'file': 7,
        'respond': 8,
        'answer': 7,
        'serve': 7,
        'submit': 6,
    }

    # Keywords that indicate weaker/ambiguous language
    WEAK_KEYWORDS = {
        'may': -5,
        'could': -5,
        'suggested': -3,
        'approximately': -3,
        'about': -3,
        'around': -3,
    }

    # Date pattern regexes (ordered by clarity)
    DATE_PATTERNS = [
        (r'\d{1,2}/\d{1,2}/\d{4}', 20, 'Explicit MM/DD/YYYY'),
        (r'\d{4}-\d{2}-\d{2}', 20, 'Explicit YYYY-MM-DD'),
        (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', 18, 'Month DD, YYYY'),
        (r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}', 18, 'DD Month YYYY'),
        (r'within\s+\d+\s+(days?|weeks?|months?)', 15, 'Relative period (within X days)'),
        (r'\d+\s+(days?|weeks?|months?)\s+(after|before|from)', 15, 'Relative period (X days after)'),
        (r'(before|after|on)\s+\d{1,2}/\d{1,2}/\d{4}', 17, 'Before/after explicit date'),
        (r'no\s+later\s+than\s+\d{1,2}/\d{1,2}/\d{4}', 19, 'No later than explicit date'),
    ]

    @staticmethod
    def calculate_confidence(
        extraction: Dict,
        source_text: str,
        rule_match: Optional[Dict] = None,
        document_type: Optional[str] = None
    ) -> Dict:
        """
        Calculate confidence score for a deadline extraction

        Args:
            extraction: Extracted deadline data
            source_text: Text from PDF where deadline was found
            rule_match: Matched rule template (if any)
            document_type: Type of document (motion, order, etc.)

        Returns:
            {
                "confidence_score": int (0-100),
                "confidence_level": str (high/medium/low),
                "factors": List[Dict],
                "requires_review": bool
            }
        """
        score = 0
        factors = []

        # Factor 1: Rule Match Confidence (40% weight)
        rule_score, rule_factor = ConfidenceScorer._calculate_rule_match_score(rule_match)
        score += rule_score
        factors.append(rule_factor)

        # Factor 2: Date Format Clarity (20% weight)
        date_score, date_factor = ConfidenceScorer._calculate_date_clarity_score(
            extraction, source_text
        )
        score += date_score
        factors.append(date_factor)

        # Factor 3: Context Keywords (20% weight)
        keyword_score, keyword_factor = ConfidenceScorer._calculate_keyword_score(source_text)
        score += keyword_score
        factors.append(keyword_factor)

        # Factor 4: Calculation Consistency (20% weight)
        calc_score, calc_factor = ConfidenceScorer._calculate_calculation_score(extraction)
        score += calc_score
        factors.append(calc_factor)

        # Bonus factors
        bonus_score, bonus_factors = ConfidenceScorer._calculate_bonus_factors(
            extraction, document_type, source_text
        )
        score += bonus_score
        factors.extend(bonus_factors)

        # Normalize to 0-100
        final_score = min(100, max(0, score))

        # Determine confidence level
        confidence_level = ConfidenceScorer._get_confidence_level(final_score)

        return {
            "confidence_score": final_score,
            "confidence_level": confidence_level,
            "factors": factors,
            "requires_review": final_score < 70,
            "auto_approve_eligible": final_score >= 90
        }

    @staticmethod
    def _calculate_rule_match_score(rule_match: Optional[Dict]) -> tuple:
        """Calculate score based on rule matching (40% weight)"""
        if rule_match and rule_match.get('confidence') == 'high':
            return 40, {
                "factor": "Rule Match",
                "score": 40,
                "max_score": 40,
                "evidence": f"Strong match: {rule_match.get('citation', 'Unknown rule')}",
                "weight": "40%"
            }
        elif rule_match and rule_match.get('confidence') == 'medium':
            return 30, {
                "factor": "Rule Match",
                "score": 30,
                "max_score": 40,
                "evidence": f"Partial match: {rule_match.get('citation', 'Unknown rule')}",
                "weight": "40%"
            }
        elif rule_match:
            return 20, {
                "factor": "Rule Match",
                "score": 20,
                "max_score": 40,
                "evidence": f"Weak match: {rule_match.get('citation', 'Unknown rule')}",
                "weight": "40%"
            }
        else:
            return 10, {
                "factor": "Rule Match",
                "score": 10,
                "max_score": 40,
                "evidence": "No specific rule matched (generic extraction)",
                "weight": "40%"
            }

    @staticmethod
    def _calculate_date_clarity_score(extraction: Dict, source_text: str) -> tuple:
        """Calculate score based on date format clarity (20% weight)"""
        if not extraction.get('deadline_date'):
            return 0, {
                "factor": "Date Clarity",
                "score": 0,
                "max_score": 20,
                "evidence": "No date found",
                "weight": "20%"
            }

        # Check source text for date pattern
        date_source = extraction.get('date_source_text', source_text)

        for pattern, base_score, description in ConfidenceScorer.DATE_PATTERNS:
            if re.search(pattern, date_source, re.IGNORECASE):
                return base_score, {
                    "factor": "Date Clarity",
                    "score": base_score,
                    "max_score": 20,
                    "evidence": f"{description}: '{date_source[:50]}'",
                    "weight": "20%"
                }

        # Default if no pattern matched
        return 8, {
            "factor": "Date Clarity",
            "score": 8,
            "max_score": 20,
            "evidence": f"Unclear date format: '{date_source[:50]}'",
            "weight": "20%"
        }

    @staticmethod
    def _calculate_keyword_score(source_text: str) -> tuple:
        """Calculate score based on context keywords (20% weight)"""
        text_lower = source_text.lower()

        score = 0
        found_keywords = []

        # Check for strong keywords
        for keyword, points in ConfidenceScorer.STRONG_KEYWORDS.items():
            if keyword in text_lower:
                score += points
                found_keywords.append(f"+{points}: '{keyword}'")

        # Check for weak keywords (negative)
        for keyword, points in ConfidenceScorer.WEAK_KEYWORDS.items():
            if keyword in text_lower:
                score += points  # Already negative
                found_keywords.append(f"{points}: '{keyword}'")

        # Normalize to 0-20 range
        final_score = min(20, max(0, score))

        evidence = ", ".join(found_keywords) if found_keywords else "No strong deadline keywords found"

        return final_score, {
            "factor": "Context Keywords",
            "score": final_score,
            "max_score": 20,
            "evidence": evidence,
            "weight": "20%"
        }

    @staticmethod
    def _calculate_calculation_score(extraction: Dict) -> tuple:
        """Calculate score based on calculation consistency (20% weight)"""
        has_basis = bool(extraction.get('calculation_basis'))
        has_rule = bool(extraction.get('rule_citation'))
        has_trigger = bool(extraction.get('trigger_event'))
        is_calculated = extraction.get('is_calculated', False)

        score = 0
        evidence_parts = []

        if has_basis:
            score += 8
            evidence_parts.append("Has calculation basis")

        if has_rule:
            score += 7
            evidence_parts.append("Has rule citation")

        if has_trigger:
            score += 3
            evidence_parts.append("Has trigger event")

        if is_calculated:
            score += 2
            evidence_parts.append("Auto-calculated")

        evidence = "; ".join(evidence_parts) if evidence_parts else "No calculation metadata"

        return score, {
            "factor": "Calculation Consistency",
            "score": score,
            "max_score": 20,
            "evidence": evidence,
            "weight": "20%"
        }

    @staticmethod
    def _calculate_bonus_factors(
        extraction: Dict,
        document_type: Optional[str],
        source_text: str
    ) -> tuple:
        """Calculate bonus/penalty factors"""
        bonus_score = 0
        bonus_factors = []

        # Bonus: Priority level indicates importance
        priority = extraction.get('priority')
        if priority in ['fatal', 'critical']:
            bonus_score += 5
            bonus_factors.append({
                "factor": "High Priority",
                "score": 5,
                "max_score": 5,
                "evidence": f"Priority level: {priority}",
                "weight": "bonus"
            })

        # Bonus: Document type is known and relevant
        if document_type in ['motion', 'order', 'complaint', 'summons']:
            bonus_score += 3
            bonus_factors.append({
                "factor": "Document Type",
                "score": 3,
                "max_score": 3,
                "evidence": f"Known document type: {document_type}",
                "weight": "bonus"
            })

        # Bonus: Source text is substantial
        if len(source_text) > 100:
            bonus_score += 2
            bonus_factors.append({
                "factor": "Source Context",
                "score": 2,
                "max_score": 2,
                "evidence": f"Substantial context ({len(source_text)} chars)",
                "weight": "bonus"
            })

        # Penalty: Very short source text
        if len(source_text) < 30:
            bonus_score -= 5
            bonus_factors.append({
                "factor": "Insufficient Context",
                "score": -5,
                "max_score": 0,
                "evidence": f"Very short context ({len(source_text)} chars)",
                "weight": "penalty"
            })

        return bonus_score, bonus_factors

    @staticmethod
    def _get_confidence_level(score: int) -> str:
        """Convert numeric score to confidence level"""
        if score >= 90:
            return "high"
        elif score >= 70:
            return "medium"
        else:
            return "low"

    @staticmethod
    def get_review_priority(confidence_level: str, priority: str) -> str:
        """
        Determine review priority based on confidence and deadline priority

        Returns: 'immediate', 'high', 'normal', 'low'
        """
        if priority in ['fatal', 'critical']:
            # Always review fatal/critical deadlines if not high confidence
            if confidence_level == "low":
                return "immediate"
            elif confidence_level == "medium":
                return "high"
            else:
                return "normal"
        else:
            # For standard deadlines
            if confidence_level == "low":
                return "high"
            elif confidence_level == "medium":
                return "normal"
            else:
                return "low"


# Singleton instance
confidence_scorer = ConfidenceScorer()
