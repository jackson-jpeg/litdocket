"""
Prompt Registry - Core infrastructure for managing AI prompts

Provides:
- PromptTemplate: Immutable prompt definition with metadata
- PromptRegistry: Central registry for all prompts with version tracking

Benefits over hardcoded prompts:
- Version tracking for A/B testing and rollback
- Centralized management for consistency
- Easier testing and validation
- Clear separation of prompt logic from service code
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptTemplate:
    """
    Immutable prompt template with metadata.

    Attributes:
        name: Unique identifier for the prompt
        version: Semantic version string (e.g., "1.0", "1.1")
        system_prompt: Optional system prompt for Claude
        user_prompt: The user prompt template with {placeholders}
        description: Human-readable description of what this prompt does
        category: Grouping category (e.g., "legal_analysis", "chat", "extraction")
        required_variables: List of variables that must be provided
        max_tokens: Suggested max_tokens for this prompt
        created_at: When this version was created
    """
    name: str
    version: str
    user_prompt: str
    description: str
    category: str
    system_prompt: Optional[str] = None
    required_variables: tuple = field(default_factory=tuple)
    max_tokens: int = 4096
    created_at: datetime = field(default_factory=datetime.now)

    def format(self, **kwargs: Any) -> str:
        """
        Format the user prompt with provided variables.

        Args:
            **kwargs: Variables to substitute into the prompt

        Returns:
            Formatted prompt string

        Raises:
            KeyError: If a required variable is missing
        """
        # Check for required variables
        missing = set(self.required_variables) - set(kwargs.keys())
        if missing:
            raise KeyError(f"Missing required variables: {missing}")

        return self.user_prompt.format(**kwargs)

    def format_system(self, **kwargs: Any) -> Optional[str]:
        """Format the system prompt if it exists."""
        if self.system_prompt is None:
            return None
        return self.system_prompt.format(**kwargs)


class PromptRegistry:
    """
    Central registry for all AI prompts.

    Provides versioned access to prompts with fallback support.
    """

    def __init__(self):
        self._prompts: Dict[str, Dict[str, PromptTemplate]] = {}
        self._default_versions: Dict[str, str] = {}

    def register(
        self,
        template: PromptTemplate,
        set_default: bool = True
    ) -> None:
        """
        Register a prompt template.

        Args:
            template: The PromptTemplate to register
            set_default: If True, set this as the default version
        """
        if template.name not in self._prompts:
            self._prompts[template.name] = {}

        self._prompts[template.name][template.version] = template

        if set_default:
            self._default_versions[template.name] = template.version

        logger.debug(f"Registered prompt: {template.name} v{template.version}")

    def get(
        self,
        name: str,
        version: Optional[str] = None
    ) -> PromptTemplate:
        """
        Get a prompt template by name and optionally version.

        Args:
            name: The prompt name
            version: Specific version, or None for default

        Returns:
            The PromptTemplate

        Raises:
            KeyError: If prompt or version not found
        """
        if name not in self._prompts:
            raise KeyError(f"Prompt not found: {name}")

        versions = self._prompts[name]

        if version is None:
            version = self._default_versions.get(name)
            if version is None:
                # Fall back to latest version
                version = max(versions.keys())

        if version not in versions:
            raise KeyError(f"Version {version} not found for prompt {name}")

        return versions[version]

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all registered prompts with their versions."""
        result = []
        for name, versions in self._prompts.items():
            result.append({
                "name": name,
                "versions": list(versions.keys()),
                "default_version": self._default_versions.get(name),
                "category": next(iter(versions.values())).category
            })
        return result

    def get_by_category(self, category: str) -> List[PromptTemplate]:
        """Get all prompts in a category."""
        result = []
        for versions in self._prompts.values():
            for template in versions.values():
                if template.category == category:
                    result.append(template)
        return result


# Global registry instance
registry = PromptRegistry()


def _register_default_prompts():
    """Register all default prompts on module load."""
    # Import prompt modules to trigger registration
    # Each module registers its prompts when imported
    try:
        from app.prompts import legal_analysis  # noqa: F401
        from app.prompts import extraction  # noqa: F401
        from app.prompts import case_summary  # noqa: F401
    except ImportError as e:
        # Prompts may not be defined yet during initial setup
        logger.debug(f"Some prompt modules not yet available: {e}")


# Register prompts when module is imported
_register_default_prompts()
