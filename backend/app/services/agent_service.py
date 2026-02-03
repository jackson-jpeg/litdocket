"""
Agent Service - AI Agent Management and Prompt Building

Handles AI agent selection, system prompt construction,
analytics tracking, and user preference management.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.ai_agent import AIAgent, UserAgentPreferences, AgentAnalytics
from app.models.user import User

logger = logging.getLogger(__name__)


class AgentService:
    """
    Service for managing AI agents and building agent-specific prompts.

    Responsibilities:
    - Get available agents for a user
    - Build system prompts with agent persona additions
    - Track agent usage analytics
    - Manage user agent preferences
    - Detect contextual agent suggestions from message content
    """

    def __init__(self, db: Session):
        self.db = db

    def get_active_agents(self) -> List[AIAgent]:
        """Get all active agents ordered by display_order."""
        return self.db.query(AIAgent).filter(
            AIAgent.is_active == True
        ).order_by(AIAgent.display_order).all()

    def get_agent_by_slug(self, slug: str) -> Optional[AIAgent]:
        """Get a specific agent by its slug."""
        return self.db.query(AIAgent).filter(
            AIAgent.slug == slug,
            AIAgent.is_active == True
        ).first()

    def get_agent_by_id(self, agent_id: str) -> Optional[AIAgent]:
        """Get a specific agent by its ID."""
        return self.db.query(AIAgent).filter(
            AIAgent.id == agent_id,
            AIAgent.is_active == True
        ).first()

    def get_user_default_agent(self, user_id: str) -> Optional[AIAgent]:
        """Get user's default agent preference."""
        prefs = self.db.query(UserAgentPreferences).filter(
            UserAgentPreferences.user_id == user_id
        ).first()

        if prefs and prefs.default_agent_id:
            return self.get_agent_by_id(prefs.default_agent_id)

        return None

    def set_user_default_agent(self, user_id: str, agent_slug: str) -> bool:
        """Set user's default agent preference."""
        agent = self.get_agent_by_slug(agent_slug)
        if not agent:
            return False

        prefs = self.db.query(UserAgentPreferences).filter(
            UserAgentPreferences.user_id == user_id
        ).first()

        if prefs:
            prefs.default_agent_id = agent.id
            prefs.updated_at = datetime.utcnow()
        else:
            prefs = UserAgentPreferences(
                user_id=user_id,
                default_agent_id=agent.id
            )
            self.db.add(prefs)

        self.db.commit()
        return True

    def build_system_prompt(
        self,
        base_prompt: str,
        agent_slug: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Build system prompt with optional agent persona additions.

        Args:
            base_prompt: The base system prompt (case context, etc.)
            agent_slug: Optional agent to apply persona from
            user_id: Optional user ID for fallback to default agent

        Returns:
            Complete system prompt with agent persona if applicable
        """
        agent = None

        # Try explicit agent first
        if agent_slug:
            agent = self.get_agent_by_slug(agent_slug)

        # Fall back to user's default agent
        if not agent and user_id:
            agent = self.get_user_default_agent(user_id)

        # If no agent, return base prompt unchanged
        if not agent:
            return base_prompt

        # Append agent persona to system prompt
        agent_section = f"""

---
ACTIVE AGENT: {agent.name}
---

{agent.system_prompt_additions}

PRIMARY TOOLS FOR THIS AGENT:
{', '.join(agent.primary_tools or [])}
"""

        return base_prompt + agent_section

    def detect_suggested_agent(self, message: str) -> Optional[AIAgent]:
        """
        Analyze message content and suggest an appropriate agent.

        Uses triggering_phrases from agents to detect context.
        Returns the best matching agent or None.
        """
        message_lower = message.lower()

        agents = self.get_active_agents()
        best_match: Optional[AIAgent] = None
        best_score = 0

        for agent in agents:
            phrases = agent.triggering_phrases or []
            score = 0

            for phrase in phrases:
                if phrase.lower() in message_lower:
                    score += 1

            if score > best_score:
                best_score = score
                best_match = agent

        # Only suggest if we have at least one phrase match
        return best_match if best_score > 0 else None

    def track_usage(
        self,
        user_id: str,
        agent_slug: Optional[str],
        case_id: Optional[str],
        session_id: str,
        tokens_used: int = 0,
        tools_used: Optional[List[str]] = None,
        response_time_ms: Optional[int] = None
    ) -> AgentAnalytics:
        """
        Track agent usage for analytics.

        Creates or updates an analytics record for the session.
        """
        # Check for existing record in this session
        existing = self.db.query(AgentAnalytics).filter(
            AgentAnalytics.session_id == session_id,
            AgentAnalytics.user_id == user_id
        ).first()

        if existing:
            # Update existing record
            existing.message_count += 1
            existing.tokens_used += tokens_used
            if tools_used:
                current_tools = existing.tools_used or []
                existing.tools_used = list(set(current_tools + tools_used))
            if response_time_ms:
                # Average response time
                existing.response_time_ms = (
                    (existing.response_time_ms or 0) + response_time_ms
                ) // 2
            return existing
        else:
            # Create new record
            analytics = AgentAnalytics(
                user_id=user_id,
                agent_slug=agent_slug,
                case_id=case_id,
                session_id=session_id,
                message_count=1,
                tokens_used=tokens_used,
                tools_used=tools_used or [],
                response_time_ms=response_time_ms
            )
            self.db.add(analytics)
            self.db.commit()
            return analytics

    def get_agent_stats(self, user_id: str) -> Dict[str, Any]:
        """Get agent usage statistics for a user."""
        analytics = self.db.query(AgentAnalytics).filter(
            AgentAnalytics.user_id == user_id
        ).all()

        # Aggregate stats by agent
        stats_by_agent: Dict[str, Dict[str, int]] = {}
        for record in analytics:
            slug = record.agent_slug or "general"
            if slug not in stats_by_agent:
                stats_by_agent[slug] = {
                    "sessions": 0,
                    "messages": 0,
                    "tokens": 0
                }
            stats_by_agent[slug]["sessions"] += 1
            stats_by_agent[slug]["messages"] += record.message_count
            stats_by_agent[slug]["tokens"] += record.tokens_used

        return {
            "total_sessions": len(analytics),
            "by_agent": stats_by_agent
        }


class AgentPromptBuilder:
    """
    Builds complete system prompts with agent-specific enhancements.

    This is a stateless helper class for constructing prompts
    without needing database access.
    """

    @staticmethod
    def build_agent_section(agent: AIAgent) -> str:
        """Build the agent-specific section of the system prompt."""
        return f"""
---
ACTIVE AGENT: {agent.name}
---

{agent.system_prompt_additions}

Your primary tools are: {', '.join(agent.primary_tools or [])}

When responding as {agent.name}:
- Stay focused on your expertise area
- Use your primary tools proactively
- Maintain your persona throughout the conversation
"""

    @staticmethod
    def get_agent_header(agent: AIAgent) -> str:
        """Get a short header identifying the active agent."""
        return f"[{agent.name}] "


# Singleton-style factory function
def get_agent_service(db: Session) -> AgentService:
    """Get an instance of AgentService."""
    return AgentService(db)
