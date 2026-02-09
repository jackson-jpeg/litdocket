"""
AI Scraper Service (Cartographer) - Auto-Discovery of Web Scraping Selectors

Ported from RulesHarvester. Uses Claude to automatically discover CSS selectors
for scraping court rule websites without manual configuration.

Key Features:
1. Auto-discovers CSS selectors from HTML using Claude with tool use
2. Validates discovered selectors against actual page content
3. Caches discovered config in Jurisdiction.scraper_config
4. Falls back to generic config if discovery fails
5. Self-healing: rediscovers selectors when they break
"""
from typing import Dict, Any, Optional, TypedDict
import logging
import re
from bs4 import BeautifulSoup
import httpx

from anthropic import Anthropic
from anthropic.types import ToolUseBlock
from sqlalchemy.orm import Session

from app.config import settings
from app.models.jurisdiction import Jurisdiction

logger = logging.getLogger(__name__)


# =============================================================
# TYPE DEFINITIONS
# =============================================================

class ScraperConfig(TypedDict, total=False):
    """Configuration for web scraping a court website"""
    name: str
    base_url: str
    rule_list_selector: str  # Container holding list of rules
    rule_link_selector: str  # Links to individual rule pages
    rule_content_selector: str  # Main content area on rule pages
    rule_code_selector: Optional[str]  # Element with rule number/code
    rule_title_selector: Optional[str]  # Element with rule title
    pagination_selector: Optional[str]  # Pagination navigation
    rate_limit_ms: int  # Delay between requests (default: 2000)
    discovered_at: str  # ISO timestamp
    confidence: float  # AI confidence (0-100)
    discovery_reasoning: str  # AI's explanation


class SelectorValidationResult(TypedDict):
    """Result from validating discovered selectors"""
    is_valid: bool
    match_counts: Dict[str, int]
    errors: list[str]


# =============================================================
# GENERIC FALLBACK CONFIG
# =============================================================

GENERIC_CONFIG: ScraperConfig = {
    "name": "Generic Court Website",
    "base_url": "",
    "rule_list_selector": "main, article, .content, #content",
    "rule_link_selector": "a[href*='rule'], a[href*='procedure']",
    "rule_content_selector": "main, article, .content, #content",
    "rule_code_selector": None,
    "rule_title_selector": "h1, h2, .title",
    "pagination_selector": ".pagination, nav[aria-label='pagination']",
    "rate_limit_ms": 2000,
    "discovered_at": "",
    "confidence": 0.0,
    "discovery_reasoning": "Generic fallback configuration"
}


# =============================================================
# TOOL DEFINITION
# =============================================================

CARTOGRAPHER_TOOL = {
    "name": "submit_scraper_config",
    "description": "Submit discovered CSS selectors for scraping this court website",
    "input_schema": {
        "type": "object",
        "properties": {
            "rule_list_selector": {
                "type": "string",
                "description": "CSS selector for container holding list of rules (e.g., ul.rules, .rule-list, table.rules)"
            },
            "rule_link_selector": {
                "type": "string",
                "description": "CSS selector for links to individual rule pages (e.g., a[href*='rule'], a.rule-link)"
            },
            "rule_content_selector": {
                "type": "string",
                "description": "CSS selector for main rule content area (e.g., article, .rule-content, #main)"
            },
            "rule_code_selector": {
                "type": "string",
                "description": "CSS selector for rule number/code element (optional)"
            },
            "rule_title_selector": {
                "type": "string",
                "description": "CSS selector for rule title element (optional)"
            },
            "pagination_selector": {
                "type": "string",
                "description": "CSS selector for pagination navigation (optional)"
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": "Confidence in discovered selectors (0-100)"
            },
            "reasoning": {
                "type": "string",
                "description": "Explanation of how selectors were identified"
            }
        },
        "required": ["rule_list_selector", "rule_link_selector", "rule_content_selector", "confidence", "reasoning"]
    }
}

CARTOGRAPHER_SYSTEM = """You are an expert web scraper analyst for legal court websites.
Analyze the HTML and identify CSS selectors for extracting legal rules.

Identify:
1. rule_list_selector - Container holding list of rules (e.g., ul.rules, .rule-list, table.rules)
2. rule_link_selector - Links to individual rule pages (e.g., a[href*="rule"], a.rule-link)
3. rule_content_selector - Main content area on rule pages (e.g., article, .rule-content, #main)
4. rule_code_selector (optional) - Element with rule number/code
5. rule_title_selector (optional) - Element with rule title
6. pagination_selector (optional) - Pagination navigation

Prefer:
- Specific selectors (avoid overly broad like "a" or "div")
- Stable selectors (classes/IDs over positional)
- Semantic selectors (meaningful class names)

Use the submit_scraper_config tool to return your analysis."""


# =============================================================
# AI SCRAPER SERVICE
# =============================================================

class AIScraperService:
    """
    Cartographer - AI-powered web scraper configuration discovery.

    Uses Claude to automatically discover CSS selectors for scraping
    court websites without manual configuration.
    """

    def __init__(self):
        api_key = settings.ANTHROPIC_API_KEY.strip()
        self.anthropic = Anthropic(api_key=api_key, max_retries=3)
        self.model = settings.DEFAULT_AI_MODEL

    async def get_scraping_strategy(
        self,
        url: str,
        jurisdiction_id: str,
        db: Session
    ) -> ScraperConfig:
        """
        Get scraping strategy for a court website.

        Checks cache first, then discovers selectors using Claude.

        Args:
            url: The court website URL to analyze
            jurisdiction_id: Jurisdiction UUID
            db: Database session

        Returns:
            ScraperConfig with discovered selectors
        """
        # 1. Check for cached config
        jurisdiction = db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if jurisdiction and jurisdiction.scraper_config:
            logger.info(f"Using cached scraper config for {jurisdiction.name}")
            return jurisdiction.scraper_config

        # 2. Fetch and clean HTML
        logger.info(f"Discovering scraper config for {jurisdiction.name if jurisdiction else jurisdiction_id}...")
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "LitDocket/1.0 (Legal Research Bot)"}
                )
                response.raise_for_status()
                html = response.text
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            return self._get_fallback_config(url)

        cleaned_html = self._clean_html_for_llm(html)

        # 3. Ask Claude to discover selectors
        try:
            config = await self._discover_selectors_with_claude(
                cleaned_html,
                url,
                jurisdiction.name if jurisdiction else "Unknown Court"
            )

            # 4. Save to database
            if jurisdiction:
                jurisdiction.scraper_config = config
                jurisdiction.scraper_config_version = (jurisdiction.scraper_config_version or 0) + 1
                db.commit()

            logger.info(f"Discovered config with {config['confidence']}% confidence")
            return config

        except Exception as e:
            logger.error(f"Cartographer discovery failed: {e}")
            fallback = self._get_fallback_config(url)

            # Save fallback config
            if jurisdiction:
                jurisdiction.scraper_config = fallback
                db.commit()

            return fallback

    async def _discover_selectors_with_claude(
        self,
        cleaned_html: str,
        url: str,
        jurisdiction_name: str
    ) -> ScraperConfig:
        """
        Use Claude to discover CSS selectors from HTML.

        Args:
            cleaned_html: Cleaned HTML content
            url: Source URL
            jurisdiction_name: Name of the jurisdiction

        Returns:
            ScraperConfig with discovered selectors
        """
        from datetime import datetime, timezone

        response = await self.anthropic.messages.create(
            model=self.model,
            max_tokens=1024,
            system=CARTOGRAPHER_SYSTEM,
            tools=[CARTOGRAPHER_TOOL],
            tool_choice={"type": "tool", "name": "submit_scraper_config"},
            messages=[{
                "role": "user",
                "content": f"Analyze this court website HTML for {jurisdiction_name} ({url}):\n\n{cleaned_html}"
            }]
        )

        # Extract tool result
        tool_use = None
        for block in response.content:
            if isinstance(block, ToolUseBlock) and block.name == "submit_scraper_config":
                tool_use = block
                break

        if not tool_use:
            raise ValueError("Claude did not return selector configuration")

        input_data = tool_use.input

        config: ScraperConfig = {
            "name": jurisdiction_name,
            "base_url": self._extract_base_url(url),
            "rule_list_selector": input_data["rule_list_selector"],
            "rule_link_selector": input_data["rule_link_selector"],
            "rule_content_selector": input_data["rule_content_selector"],
            "rule_code_selector": input_data.get("rule_code_selector"),
            "rule_title_selector": input_data.get("rule_title_selector"),
            "pagination_selector": input_data.get("pagination_selector"),
            "rate_limit_ms": 2000,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "confidence": float(input_data["confidence"]),
            "discovery_reasoning": input_data["reasoning"]
        }

        return config

    async def validate_selectors(
        self,
        url: str,
        config: ScraperConfig
    ) -> SelectorValidationResult:
        """
        Validate that discovered selectors actually match elements on the page.

        Args:
            url: The URL to validate against
            config: The scraper configuration to validate

        Returns:
            SelectorValidationResult with validation details
        """
        errors: list[str] = []
        match_counts: Dict[str, int] = {
            "rule_list_selector": 0,
            "rule_link_selector": 0,
            "rule_content_selector": 0,
            "rule_code_selector": 0,
            "rule_title_selector": 0,
            "pagination_selector": 0
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "LitDocket/1.0"}
                )

                if not response.is_success:
                    return {
                        "is_valid": False,
                        "match_counts": match_counts,
                        "errors": [f"Failed to fetch page: {response.status_code}"]
                    }

                soup = BeautifulSoup(response.text, "html.parser")

                # Check required selectors
                match_counts["rule_list_selector"] = len(soup.select(config["rule_list_selector"]))
                if match_counts["rule_list_selector"] == 0:
                    errors.append(f"rule_list_selector '{config['rule_list_selector']}' matches 0 elements")

                match_counts["rule_link_selector"] = len(soup.select(config["rule_link_selector"]))
                if match_counts["rule_link_selector"] == 0:
                    errors.append(f"rule_link_selector '{config['rule_link_selector']}' matches 0 elements")

                match_counts["rule_content_selector"] = len(soup.select(config["rule_content_selector"]))
                if match_counts["rule_content_selector"] == 0:
                    errors.append(f"rule_content_selector '{config['rule_content_selector']}' matches 0 elements")

                # Check optional selectors
                if config.get("rule_code_selector"):
                    match_counts["rule_code_selector"] = len(soup.select(config["rule_code_selector"]))

                if config.get("rule_title_selector"):
                    match_counts["rule_title_selector"] = len(soup.select(config["rule_title_selector"]))

                if config.get("pagination_selector"):
                    match_counts["pagination_selector"] = len(soup.select(config["pagination_selector"]))

                # Valid if all required selectors match at least one element
                is_valid = (
                    match_counts["rule_list_selector"] > 0 and
                    match_counts["rule_link_selector"] > 0 and
                    match_counts["rule_content_selector"] > 0
                )

                return {
                    "is_valid": is_valid,
                    "match_counts": match_counts,
                    "errors": errors
                }

        except Exception as e:
            return {
                "is_valid": False,
                "match_counts": match_counts,
                "errors": [str(e)]
            }

    def _clean_html_for_llm(self, html: str) -> str:
        """
        Clean HTML for LLM processing - remove noise, compress DOM.

        Args:
            html: Raw HTML content

        Returns:
            Cleaned HTML string
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove noise elements
        for tag in soup.select("script, style, svg, noscript, iframe, img, video, audio"):
            tag.decompose()

        for tag in soup.select("nav, footer, header, aside, .nav, .footer, .header, .sidebar"):
            tag.decompose()

        # Remove inline styles and event handlers
        for tag in soup.find_all(True):
            if tag.get("style"):
                del tag["style"]
            for attr in ["onclick", "onload", "onerror"]:
                if tag.get(attr):
                    del tag[attr]

        # Get cleaned HTML
        cleaned = str(soup)

        # Collapse whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'>\s+<', '><', cleaned)

        # Truncate to ~80KB for context window
        if len(cleaned) > 80000:
            cleaned = cleaned[:80000] + "<!-- truncated -->"

        return cleaned

    def _extract_base_url(self, url: str) -> str:
        """Extract base URL from full URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _get_fallback_config(self, url: str) -> ScraperConfig:
        """Get fallback generic config when discovery fails"""
        from datetime import datetime, timezone

        fallback = GENERIC_CONFIG.copy()
        fallback["base_url"] = self._extract_base_url(url)
        fallback["discovered_at"] = datetime.now(timezone.utc).isoformat()
        fallback["discovery_reasoning"] = "Discovery failed. Using generic fallback."

        return fallback


# Singleton instance
ai_scraper_service = AIScraperService()
