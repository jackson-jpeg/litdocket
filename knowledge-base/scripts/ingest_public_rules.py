#!/usr/bin/env python3
"""
Sovereign Rule Ingestion Pipeline

"Clean Room" rule extraction from public domain legal texts.

This script:
1. Reads raw legal text files (Federal Rules, State Rules)
2. Chunks by rule number (Rule 1.01, Rule 2.04, etc.)
3. Uses Claude to extract deadline logic
4. Generates SQL INSERT statements for the database

Usage:
    python ingest_public_rules.py --input ./raw_text/ --output ./generated_sql/
    python ingest_public_rules.py --file ./raw_text/frcp.txt --jurisdiction federal

The output is legally defensible because we derive logic from public law,
not from a competitor's proprietary database.
"""

import os
import re
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

# Optional: Use Anthropic SDK if available
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("Warning: anthropic package not installed. LLM extraction disabled.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# DATA STRUCTURES
# ============================================

@dataclass
class ExtractedDeadline:
    """A deadline extracted from legal text."""
    name: str
    description: str
    days_from_trigger: int
    trigger_event: str
    priority: str  # 'informational', 'standard', 'important', 'critical', 'fatal'
    calculation_method: str  # 'calendar_days', 'business_days', 'court_days'
    party_responsible: str  # 'plaintiff', 'defendant', 'both', 'court'
    action_required: str
    add_service_days: bool
    rule_citation: str
    source_text: str
    confidence: float  # 0.0 to 1.0

@dataclass
class ExtractedRule:
    """A complete rule with its deadlines."""
    rule_code: str
    name: str
    description: str
    trigger_type: str
    citation: str
    deadlines: List[ExtractedDeadline]
    source_file: str

@dataclass
class ChunkedRule:
    """A chunk of text representing a single rule."""
    rule_number: str
    title: str
    full_text: str
    source_file: str
    start_line: int
    end_line: int

# ============================================
# TEXT CHUNKING
# ============================================

class RuleChunker:
    """Chunks legal text into individual rules."""

    # Common rule number patterns
    RULE_PATTERNS = [
        # Federal Rules: "Rule 4.", "RULE 4.", "Rule 4 "
        r'^(?:RULE|Rule)\s+(\d+(?:\.\d+)?)\b[.\s]',
        # Florida Rules: "1.140", "RULE 1.140"
        r'^(?:RULE\s+)?(\d+\.\d+)\b[.\s]',
        # Subsection: "(a)", "(b)(1)"
        r'^\(([a-z])\)\s',
    ]

    def __init__(self, jurisdiction_type: str = 'federal'):
        self.jurisdiction_type = jurisdiction_type

    def chunk_file(self, file_path: Path) -> List[ChunkedRule]:
        """Chunk a file into individual rules."""
        logger.info(f"Chunking file: {file_path}")

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        chunks = []
        current_chunk = None
        current_lines = []
        current_start = 0

        for i, line in enumerate(lines):
            # Check if this line starts a new rule
            rule_match = self._match_rule_start(line)

            if rule_match:
                # Save previous chunk if exists
                if current_chunk and current_lines:
                    current_chunk.full_text = ''.join(current_lines).strip()
                    current_chunk.end_line = i - 1
                    chunks.append(current_chunk)

                # Start new chunk
                rule_number, title = rule_match
                current_chunk = ChunkedRule(
                    rule_number=rule_number,
                    title=title,
                    full_text='',
                    source_file=str(file_path),
                    start_line=i,
                    end_line=i
                )
                current_lines = [line]
                current_start = i
            elif current_chunk:
                current_lines.append(line)

        # Don't forget the last chunk
        if current_chunk and current_lines:
            current_chunk.full_text = ''.join(current_lines).strip()
            current_chunk.end_line = len(lines) - 1
            chunks.append(current_chunk)

        logger.info(f"Found {len(chunks)} rule chunks in {file_path}")
        return chunks

    def _match_rule_start(self, line: str) -> Optional[tuple]:
        """Check if line starts a new rule."""
        line = line.strip()
        if not line:
            return None

        for pattern in self.RULE_PATTERNS:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                rule_number = match.group(1)
                # Extract title (rest of the line after the rule number)
                title = line[match.end():].strip().rstrip('.')
                return (rule_number, title)

        return None

# ============================================
# LLM EXTRACTION
# ============================================

class LLMExtractor:
    """Uses Claude to extract deadline logic from legal text."""

    EXTRACTION_PROMPT = """You are a legal deadline extraction system. Analyze the following legal rule text and extract any deadline information.

IMPORTANT: Output ONLY valid JSON. Do not include any explanation or markdown formatting.

For each deadline found, extract:
1. name: Short name for the deadline
2. description: What must be done
3. days_from_trigger: Number of days (positive = after trigger, negative = before trigger)
4. trigger_event: What triggers this deadline (e.g., "complaint_served", "trial_date")
5. priority: One of "informational", "standard", "important", "critical", "fatal"
6. calculation_method: One of "calendar_days", "business_days", "court_days"
7. party_responsible: One of "plaintiff", "defendant", "both", "court"
8. action_required: Specific action that must be taken
9. add_service_days: true if service method days should be added
10. confidence: Your confidence in this extraction (0.0 to 1.0)

Common trigger events:
- case_filed, complaint_served, answer_filed, discovery_commenced
- trial_date, hearing_scheduled, motion_filed, order_entered

Convert text to days:
- "twenty (20) days" = 20
- "within 14 days" = 14
- "not later than 30 days before" = -30
- "at least 21 days prior" = -21

Rule Text:
{rule_text}

Rule Number: {rule_number}
Citation Format: {citation_prefix}

Output a JSON array of deadline objects. If no deadlines found, output an empty array [].
"""

    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if HAS_ANTHROPIC:
            api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                self.client = Anthropic(api_key=api_key)

    def extract_deadlines(
        self,
        chunk: ChunkedRule,
        citation_prefix: str = 'Fed. R. Civ. P.'
    ) -> List[ExtractedDeadline]:
        """Extract deadlines from a rule chunk using Claude."""

        if not self.client:
            logger.warning("LLM client not available, using regex fallback")
            return self._regex_fallback(chunk, citation_prefix)

        prompt = self.EXTRACTION_PROMPT.format(
            rule_text=chunk.full_text[:4000],  # Limit text length
            rule_number=chunk.rule_number,
            citation_prefix=citation_prefix
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse JSON response
            response_text = response.content[0].text.strip()

            # Handle potential markdown code blocks
            if response_text.startswith('```'):
                response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)

            deadlines_data = json.loads(response_text)

            deadlines = []
            for d in deadlines_data:
                deadlines.append(ExtractedDeadline(
                    name=d.get('name', 'Unknown'),
                    description=d.get('description', ''),
                    days_from_trigger=int(d.get('days_from_trigger', 0)),
                    trigger_event=d.get('trigger_event', 'custom_trigger'),
                    priority=d.get('priority', 'standard'),
                    calculation_method=d.get('calculation_method', 'calendar_days'),
                    party_responsible=d.get('party_responsible', 'both'),
                    action_required=d.get('action_required', ''),
                    add_service_days=d.get('add_service_days', False),
                    rule_citation=f"{citation_prefix} {chunk.rule_number}",
                    source_text=chunk.full_text[:500],
                    confidence=float(d.get('confidence', 0.8))
                ))

            return deadlines

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return self._regex_fallback(chunk, citation_prefix)

    def _regex_fallback(
        self,
        chunk: ChunkedRule,
        citation_prefix: str
    ) -> List[ExtractedDeadline]:
        """Fallback regex-based extraction when LLM is unavailable."""

        deadlines = []
        text = chunk.full_text.lower()

        # Common patterns
        patterns = [
            # "within X days"
            (r'within\s+(\w+)\s*\((\d+)\)\s*days?', 'after'),
            (r'within\s+(\d+)\s*days?', 'after'),
            # "not later than X days"
            (r'not\s+later\s+than\s+(\d+)\s*days?', 'after'),
            # "at least X days before"
            (r'at\s+least\s+(\d+)\s*days?\s+(?:before|prior)', 'before'),
            # "X days after"
            (r'(\d+)\s*days?\s+after', 'after'),
            # "X days before"
            (r'(\d+)\s*days?\s+before', 'before'),
        ]

        for pattern, direction in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Handle tuple (word, number) or just number
                if isinstance(match, tuple):
                    days = int(match[-1])
                else:
                    days = int(match)

                if direction == 'before':
                    days = -days

                deadlines.append(ExtractedDeadline(
                    name=f"Rule {chunk.rule_number} Deadline",
                    description=f"Deadline from Rule {chunk.rule_number}",
                    days_from_trigger=days,
                    trigger_event='custom_trigger',
                    priority='standard',
                    calculation_method='calendar_days',
                    party_responsible='both',
                    action_required='See rule text',
                    add_service_days=False,
                    rule_citation=f"{citation_prefix} {chunk.rule_number}",
                    source_text=chunk.full_text[:200],
                    confidence=0.5  # Lower confidence for regex
                ))

        return deadlines

# ============================================
# SQL GENERATION
# ============================================

class SQLGenerator:
    """Generates SQL INSERT statements from extracted rules."""

    TRIGGER_TYPE_MAP = {
        'case_filed': 'case_filed',
        'complaint_served': 'complaint_served',
        'service_completed': 'service_completed',
        'answer_filed': 'answer_due',
        'answer_due': 'answer_due',
        'discovery_commenced': 'discovery_commenced',
        'discovery_deadline': 'discovery_deadline',
        'trial_date': 'trial_date',
        'hearing_scheduled': 'hearing_scheduled',
        'motion_filed': 'motion_filed',
        'order_entered': 'order_entered',
        'appeal_filed': 'appeal_filed',
        'custom_trigger': 'custom_trigger',
    }

    def __init__(self, jurisdiction_id: str, rule_set_id: str):
        self.jurisdiction_id = jurisdiction_id
        self.rule_set_id = rule_set_id

    def generate_rule_template(self, rule: ExtractedRule) -> str:
        """Generate SQL for a rule template and its deadlines."""

        template_id = str(uuid.uuid4())
        trigger_type = self.TRIGGER_TYPE_MAP.get(
            rule.trigger_type, 'custom_trigger'
        )

        sql = f"""
-- Rule: {rule.rule_code} - {rule.name}
-- Source: {rule.source_file}
INSERT INTO rule_templates (
    id, rule_set_id, rule_code, name, description, trigger_type, citation, is_active
) VALUES (
    '{template_id}',
    '{self.rule_set_id}',
    '{self._escape(rule.rule_code)}',
    '{self._escape(rule.name)}',
    '{self._escape(rule.description)}',
    '{trigger_type}',
    '{self._escape(rule.citation)}',
    TRUE
) ON CONFLICT (rule_set_id, rule_code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    citation = EXCLUDED.citation;

"""

        # Generate deadline inserts
        for i, deadline in enumerate(rule.deadlines):
            deadline_id = str(uuid.uuid4())
            sql += f"""
INSERT INTO rule_template_deadlines (
    id, rule_template_id, name, description, days_from_trigger,
    priority, party_responsible, action_required, calculation_method,
    add_service_days, rule_citation, display_order, is_active,
    source_text, ai_extracted, extraction_confidence
) VALUES (
    '{deadline_id}',
    '{template_id}',
    '{self._escape(deadline.name)}',
    '{self._escape(deadline.description)}',
    {deadline.days_from_trigger},
    '{deadline.priority}',
    '{deadline.party_responsible}',
    '{self._escape(deadline.action_required)}',
    '{deadline.calculation_method}',
    {str(deadline.add_service_days).upper()},
    '{self._escape(deadline.rule_citation)}',
    {i + 1},
    TRUE,
    '{self._escape(deadline.source_text[:500])}',
    TRUE,
    {deadline.confidence}
) ON CONFLICT DO NOTHING;

"""

        return sql

    def _escape(self, text: str) -> str:
        """Escape single quotes for SQL."""
        if not text:
            return ''
        return text.replace("'", "''")

# ============================================
# MAIN PIPELINE
# ============================================

class RuleIngestionPipeline:
    """Main orchestration for rule ingestion."""

    # Known jurisdiction configurations
    JURISDICTIONS = {
        'federal': {
            'id': '00000000-0000-0000-0000-000000000001',
            'citation_prefix': 'Fed. R. Civ. P.',
            'rule_set_id': '10000000-0000-0000-0000-000000000001',  # FRCP
        },
        'florida': {
            'id': '00000000-0000-0000-0000-000000000100',
            'citation_prefix': 'Fla. R. Civ. P.',
            'rule_set_id': '20000000-0000-0000-0000-000000000001',  # FL:RCP
        },
        'bankruptcy': {
            'id': '00000000-0000-0000-0000-000000000020',
            'citation_prefix': 'Fed. R. Bankr. P.',
            'rule_set_id': '10000000-0000-0000-0000-000000000003',  # FRBP
        },
    }

    def __init__(
        self,
        jurisdiction: str = 'federal',
        api_key: Optional[str] = None
    ):
        if jurisdiction not in self.JURISDICTIONS:
            raise ValueError(f"Unknown jurisdiction: {jurisdiction}")

        self.jurisdiction = jurisdiction
        self.config = self.JURISDICTIONS[jurisdiction]
        self.chunker = RuleChunker(jurisdiction)
        self.extractor = LLMExtractor(api_key)
        self.generator = SQLGenerator(
            self.config['id'],
            self.config['rule_set_id']
        )

    def process_file(self, file_path: Path) -> str:
        """Process a single file and return SQL."""
        logger.info(f"Processing file: {file_path}")

        # Chunk the file
        chunks = self.chunker.chunk_file(file_path)

        # Extract rules from each chunk
        rules = []
        for chunk in chunks:
            deadlines = self.extractor.extract_deadlines(
                chunk,
                self.config['citation_prefix']
            )

            if deadlines:
                rule = ExtractedRule(
                    rule_code=f"{self.jurisdiction.upper()}-{chunk.rule_number}",
                    name=chunk.title or f"Rule {chunk.rule_number}",
                    description=f"Extracted from {file_path.name}",
                    trigger_type=self._infer_trigger_type(deadlines),
                    citation=f"{self.config['citation_prefix']} {chunk.rule_number}",
                    deadlines=deadlines,
                    source_file=str(file_path)
                )
                rules.append(rule)

        # Generate SQL
        sql = f"""
-- ============================================
-- AUTO-GENERATED RULE DEFINITIONS
-- Source: {file_path}
-- Generated: {datetime.now().isoformat()}
-- Jurisdiction: {self.jurisdiction}
-- ============================================

"""
        for rule in rules:
            sql += self.generator.generate_rule_template(rule)

        return sql

    def process_directory(self, dir_path: Path) -> str:
        """Process all text files in a directory."""
        sql_parts = []

        for file_path in dir_path.glob('*.txt'):
            try:
                sql = self.process_file(file_path)
                sql_parts.append(sql)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")

        return '\n'.join(sql_parts)

    def _infer_trigger_type(self, deadlines: List[ExtractedDeadline]) -> str:
        """Infer the trigger type from extracted deadlines."""
        # Count trigger types
        triggers = {}
        for d in deadlines:
            t = d.trigger_event
            triggers[t] = triggers.get(t, 0) + 1

        if not triggers:
            return 'custom_trigger'

        # Return most common trigger
        return max(triggers, key=triggers.get)

# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description='Sovereign Rule Ingestion Pipeline'
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Input file or directory path'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='./generated_sql',
        help='Output directory for SQL files'
    )
    parser.add_argument(
        '--jurisdiction', '-j',
        type=str,
        default='federal',
        choices=['federal', 'florida', 'bankruptcy'],
        help='Jurisdiction type'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print SQL to stdout instead of writing files'
    )

    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        return

    # Create pipeline
    pipeline = RuleIngestionPipeline(
        jurisdiction=args.jurisdiction,
        api_key=args.api_key
    )

    input_path = Path(args.input)

    if input_path.is_file():
        sql = pipeline.process_file(input_path)
    elif input_path.is_dir():
        sql = pipeline.process_directory(input_path)
    else:
        logger.error(f"Input path not found: {input_path}")
        return

    if args.dry_run:
        print(sql)
    else:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{args.jurisdiction}_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        output_file.write_text(sql)
        logger.info(f"SQL written to: {output_file}")

if __name__ == '__main__':
    main()
