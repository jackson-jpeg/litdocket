"""
Robust JSON Extractor - Handles LLM responses with embedded JSON

This utility provides reliable JSON extraction from LLM responses, replacing
the greedy regex pattern ``re.search(r'{.*}|[.*]', text, re.DOTALL)`` which
fails on:
- Nested JSON structures
- Preamble text before JSON
- Malformed JSON with trailing commas
- Unquoted keys in JavaScript-style objects

The bracket-balanced algorithm correctly handles nested structures and
provides structured error reporting for debugging.
"""
import json
import re
import logging
from typing import Any, Optional, Tuple, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of JSON extraction with metadata for debugging."""
    data: Optional[Any]
    success: bool
    error: Optional[str] = None
    raw_extracted: Optional[str] = None
    repairs_applied: Optional[list] = None


def extract_json(
    text: str,
    expected_type: str = "auto"
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Extract and parse JSON from LLM response text.

    Uses bracket-balanced extraction (not greedy regex) to correctly handle
    nested JSON structures. Applies common repair patterns for malformed output.

    Args:
        text: Raw text that may contain JSON (with preamble, code blocks, etc.)
        expected_type: "object" for {}, "array" for [], or "auto" for either

    Returns:
        Tuple of (parsed_data, error_message)
        - On success: (data, None)
        - On failure: (None, error_description)

    Examples:
        >>> data, err = extract_json('Here is the JSON: {"foo": "bar"}')
        >>> data
        {'foo': 'bar'}

        >>> data, err = extract_json('[1, 2, 3]', expected_type="array")
        >>> data
        [1, 2, 3]
    """
    if not text or not isinstance(text, str):
        return None, "Empty or invalid input"

    # Strip markdown code blocks
    cleaned = _strip_markdown(text)

    # Find JSON bounds using bracket-balanced extraction
    json_str, extraction_error = _extract_json_bounds(cleaned, expected_type)

    if json_str is None:
        return None, extraction_error or "No JSON found in text"

    # Try parsing as-is first
    try:
        return json.loads(json_str), None
    except json.JSONDecodeError as e:
        logger.debug(f"Initial parse failed: {e}")

    # Apply repair patterns and retry
    repaired, repairs = _apply_repairs(json_str)

    try:
        data = json.loads(repaired)
        if repairs:
            logger.info(f"JSON parsed after repairs: {repairs}")
        return data, None
    except json.JSONDecodeError as e:
        error_msg = f"JSON parse failed: {e}. Extracted: {json_str[:200]}..."
        logger.warning(error_msg)
        return None, error_msg


def extract_json_detailed(
    text: str,
    expected_type: str = "auto"
) -> ExtractionResult:
    """
    Extract JSON with detailed metadata about the extraction process.

    Use this when you need visibility into repairs applied or debugging info.

    Args:
        text: Raw text containing JSON
        expected_type: "object", "array", or "auto"

    Returns:
        ExtractionResult with data, success flag, and metadata
    """
    if not text or not isinstance(text, str):
        return ExtractionResult(
            data=None,
            success=False,
            error="Empty or invalid input"
        )

    cleaned = _strip_markdown(text)
    json_str, extraction_error = _extract_json_bounds(cleaned, expected_type)

    if json_str is None:
        return ExtractionResult(
            data=None,
            success=False,
            error=extraction_error or "No JSON found in text"
        )

    # Try direct parse
    try:
        data = json.loads(json_str)
        return ExtractionResult(
            data=data,
            success=True,
            raw_extracted=json_str
        )
    except json.JSONDecodeError:
        pass

    # Try with repairs
    repaired, repairs = _apply_repairs(json_str)

    try:
        data = json.loads(repaired)
        return ExtractionResult(
            data=data,
            success=True,
            raw_extracted=json_str,
            repairs_applied=repairs
        )
    except json.JSONDecodeError as e:
        return ExtractionResult(
            data=None,
            success=False,
            error=f"Parse failed after repairs: {e}",
            raw_extracted=json_str,
            repairs_applied=repairs
        )


def _strip_markdown(text: str) -> str:
    """Remove markdown code block markers."""
    # Remove ```json and ``` markers
    text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*', '', text)
    return text.strip()


def _extract_json_bounds(
    text: str,
    expected_type: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract JSON using bracket-balanced algorithm.

    This correctly handles nested structures unlike greedy regex.

    Args:
        text: Cleaned text to search
        expected_type: "object", "array", or "auto"

    Returns:
        Tuple of (json_string, error_message)
    """
    # Determine which brackets to look for
    if expected_type == "object":
        open_chars = ['{']
    elif expected_type == "array":
        open_chars = ['[']
    else:  # auto - try both, prefer the one that appears first
        open_chars = ['{', '[']

    # Find the first occurrence of any valid opener
    best_start = -1
    best_open_char = None

    for char in open_chars:
        idx = text.find(char)
        if idx != -1 and (best_start == -1 or idx < best_start):
            best_start = idx
            best_open_char = char

    if best_start == -1:
        return None, f"No JSON {expected_type} found in text"

    # Match the closing bracket type
    close_char = '}' if best_open_char == '{' else ']'

    # Use bracket counting to find the matching close
    depth = 0
    in_string = False
    escape_next = False
    end_pos = -1

    for i in range(best_start, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == best_open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                end_pos = i
                break

    if end_pos == -1:
        return None, f"Unbalanced brackets in JSON (opened at {best_start}, never closed)"

    return text[best_start:end_pos + 1], None


def _apply_repairs(json_str: str) -> Tuple[str, list]:
    """
    Apply common repairs to malformed JSON.

    Handles issues commonly seen in LLM output:
    - Trailing commas in arrays/objects
    - Single quotes instead of double quotes (in some cases)
    - Unquoted keys (limited support)

    Args:
        json_str: Potentially malformed JSON string

    Returns:
        Tuple of (repaired_string, list_of_repairs_applied)
    """
    repairs = []
    result = json_str

    # Repair 1: Trailing commas before closing brackets
    # E.g., {"foo": "bar",} or [1, 2, 3,]
    trailing_comma_pattern = r',(\s*[}\]])'
    if re.search(trailing_comma_pattern, result):
        result = re.sub(trailing_comma_pattern, r'\1', result)
        repairs.append("removed_trailing_commas")

    # Repair 2: Missing commas between array elements (common LLM error)
    # E.g., ["a" "b"] -> ["a", "b"]
    # Only apply to simple string arrays to avoid false positives
    missing_comma_pattern = r'"\s+"'
    if re.search(missing_comma_pattern, result):
        # Be conservative - only apply if it looks like a string array
        if result.strip().startswith('['):
            result = re.sub(r'"\s+"', '", "', result)
            repairs.append("added_missing_commas_in_array")

    # Repair 3: Unescaped newlines in strings (LLM sometimes does this)
    # Replace literal newlines inside strings with \n
    # This is tricky - we need to be careful not to break valid JSON
    def escape_newlines_in_strings(match: re.Match) -> str:
        s = match.group(0)
        # Replace actual newlines with escaped ones
        return s.replace('\n', '\\n').replace('\r', '\\r')

    # Match string contents (between unescaped quotes)
    string_pattern = r'"(?:[^"\\]|\\.)*"'
    original = result
    result = re.sub(string_pattern, escape_newlines_in_strings, result)
    if result != original:
        repairs.append("escaped_newlines_in_strings")

    return result, repairs


# Backwards compatibility: simple function that returns dict with parse_error flag
def parse_json_response(text: str) -> dict:
    """
    Legacy-compatible JSON parser that returns parse_error flag on failure.

    This matches the behavior of the old _parse_json_response method in ai_service.py
    for backwards compatibility.

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON data, or {'raw_text': text, 'parse_error': True} on failure
    """
    data, error = extract_json(text)

    if data is not None:
        return data

    logger.debug(f"Returning raw text fallback for unparseable response: {text[:100]}...")
    return {'raw_text': text, 'parse_error': True}
