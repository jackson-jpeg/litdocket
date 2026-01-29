"""
AI Model Configuration and Task Routing

This module defines the model selection strategy for different AI tasks:
- Opus 4.5: Quality-critical tasks (document analysis, chat, rule validation)
- Haiku: High-volume tasks (rules scraping, preprocessing, simple extraction)
- Sonnet: Balanced tasks (fallback, medium complexity)

The routing ensures optimal cost/quality tradeoff for each use case.
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class AITask(Enum):
    """Enumeration of AI task types with model routing"""

    # Quality-Critical Tasks → Opus 4.5
    DOCUMENT_ANALYSIS = "document_analysis"
    DEADLINE_CALCULATION = "deadline_calculation"
    CHAT_RESPONSE = "chat_response"
    RULE_VALIDATION = "rule_validation"
    CASE_SUMMARY = "case_summary"
    LEGAL_RESEARCH = "legal_research"
    COMPLIANCE_CHECK = "compliance_check"

    # High-Volume Tasks → Haiku
    RULES_SCRAPING = "rules_scraping"
    TEXT_EXTRACTION = "text_extraction"
    CLASSIFICATION = "classification"
    SIMPLE_PARSING = "simple_parsing"
    METADATA_EXTRACTION = "metadata_extraction"
    BATCH_PROCESSING = "batch_processing"

    # Balanced Tasks → Sonnet (or configurable)
    GENERAL_QUERY = "general_query"
    EMBEDDINGS_PREP = "embeddings_prep"


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    model_id: str
    max_tokens: int
    cost_tier: str  # "high", "medium", "low"
    latency_tier: str  # "high", "medium", "low"
    quality_tier: str  # "highest", "high", "medium"


# Model configurations
MODELS = {
    "opus": ModelConfig(
        model_id=settings.AI_MODEL_OPUS,
        max_tokens=4096,
        cost_tier="high",
        latency_tier="medium",
        quality_tier="highest"
    ),
    "haiku": ModelConfig(
        model_id=settings.AI_MODEL_HAIKU,
        max_tokens=4096,
        cost_tier="low",
        latency_tier="low",
        quality_tier="medium"
    ),
    "sonnet": ModelConfig(
        model_id=settings.AI_MODEL_SONNET,
        max_tokens=4096,
        cost_tier="medium",
        latency_tier="medium",
        quality_tier="high"
    ),
}

# Task to model mapping
TASK_MODEL_MAPPING: dict[AITask, str] = {
    # Opus 4.5 - Quality-critical
    AITask.DOCUMENT_ANALYSIS: "opus",
    AITask.DEADLINE_CALCULATION: "opus",
    AITask.CHAT_RESPONSE: "opus",
    AITask.RULE_VALIDATION: "opus",
    AITask.CASE_SUMMARY: "opus",
    AITask.LEGAL_RESEARCH: "opus",
    AITask.COMPLIANCE_CHECK: "opus",

    # Haiku - High-volume
    AITask.RULES_SCRAPING: "haiku",
    AITask.TEXT_EXTRACTION: "haiku",
    AITask.CLASSIFICATION: "haiku",
    AITask.SIMPLE_PARSING: "haiku",
    AITask.METADATA_EXTRACTION: "haiku",
    AITask.BATCH_PROCESSING: "haiku",

    # Sonnet - Balanced
    AITask.GENERAL_QUERY: "sonnet",
    AITask.EMBEDDINGS_PREP: "haiku",  # Use Haiku for cost efficiency
}


def get_model_for_task(task: AITask) -> ModelConfig:
    """
    Get the appropriate model configuration for a given task.

    Args:
        task: The AI task type

    Returns:
        ModelConfig with the appropriate model settings
    """
    model_key = TASK_MODEL_MAPPING.get(task, "opus")
    config = MODELS[model_key]

    logger.debug(f"Task {task.value} routed to model {config.model_id}")
    return config


def get_model_id(task: AITask) -> str:
    """
    Get just the model ID string for a task.

    Args:
        task: The AI task type

    Returns:
        Model ID string (e.g., "claude-opus-4-5-20251101")
    """
    return get_model_for_task(task).model_id


class ModelRouter:
    """
    Centralized model routing with usage tracking and fallback handling.
    """

    def __init__(self):
        self.usage_stats: dict[str, int] = {
            "opus": 0,
            "haiku": 0,
            "sonnet": 0
        }

    def get_model(
        self,
        task: AITask,
        override_model: Optional[str] = None
    ) -> str:
        """
        Get the model ID for a task with optional override.

        Args:
            task: The AI task type
            override_model: Optional model override ("opus", "haiku", "sonnet")

        Returns:
            Model ID string
        """
        if override_model and override_model in MODELS:
            model_key = override_model
            logger.info(f"Using override model '{override_model}' for task {task.value}")
        else:
            model_key = TASK_MODEL_MAPPING.get(task, "opus")

        self.usage_stats[model_key] += 1
        return MODELS[model_key].model_id

    def get_stats(self) -> dict[str, int]:
        """Get usage statistics for model routing"""
        return self.usage_stats.copy()

    def reset_stats(self) -> None:
        """Reset usage statistics"""
        self.usage_stats = {key: 0 for key in self.usage_stats}


# Singleton router instance
model_router = ModelRouter()


# Convenience functions
def opus_model() -> str:
    """Get Opus 4.5 model ID"""
    return settings.AI_MODEL_OPUS


def haiku_model() -> str:
    """Get Haiku model ID"""
    return settings.AI_MODEL_HAIKU


def sonnet_model() -> str:
    """Get Sonnet model ID"""
    return settings.AI_MODEL_SONNET
