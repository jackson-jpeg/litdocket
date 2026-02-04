"""
Parsing Constants - Standard value normalization for LLM and user inputs

These constants define canonical representations for boolean and other values
that may be provided as strings by LLMs or user inputs. Using frozensets
provides O(1) lookup and immutability.
"""

# Boolean-like string values that should normalize to True
TRUTHY_STRINGS = frozenset({
    "true",
    "yes",
    "1",
    "y",
    "on",
    "enabled",
})

# Boolean-like string values that should normalize to False
FALSY_STRINGS = frozenset({
    "false",
    "no",
    "0",
    "n",
    "off",
    "disabled",
})
