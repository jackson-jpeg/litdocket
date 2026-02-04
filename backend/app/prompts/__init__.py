"""
Prompt Registry - Centralized management of AI prompts

This module provides versioned, testable prompt management for LLM interactions.
All prompts used by the application should be registered here.

Usage:
    from app.prompts import registry

    prompt = registry.get("document_analysis", version="1.0")
    formatted = prompt.format(document_type="motion", text="...")
"""

from app.prompts.registry import PromptTemplate, PromptRegistry, registry

__all__ = ["PromptTemplate", "PromptRegistry", "registry"]
