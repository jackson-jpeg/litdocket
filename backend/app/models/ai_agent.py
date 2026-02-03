"""
AI Agent Models

Specialized AI agent personas for the chat interface.
Enables different agent personalities (Deadline Sentinel, Rules Oracle, etc.)
for different use cases within the legal docketing workflow.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class AIAgent(Base):
    """
    Specialized AI agent definition.

    Each agent has a unique persona with specific expertise areas,
    primary tools, and system prompt modifications that guide its behavior.

    Attributes:
        id: Unique identifier (UUID)
        slug: URL-safe unique identifier (e.g., 'deadline_sentinel')
        name: Display name (e.g., 'Deadline Sentinel')
        description: Brief description of agent expertise
        system_prompt_additions: Text appended to system prompt when active
        primary_tools: JSON array of tool names this agent primarily uses
        context_enhancers: JSON array of context enhancement strategies
        triggering_phrases: JSON array of phrases that suggest this agent
        icon: Icon identifier for UI (e.g., 'clock', 'book')
        color: Color identifier for UI (e.g., 'red', 'blue')
        is_active: Whether agent is available for use
        display_order: Order in agent selector UI
    """
    __tablename__ = "ai_agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    system_prompt_additions = Column(Text, nullable=False)
    primary_tools = Column(JSONB, default=list)
    context_enhancers = Column(JSONB, default=list)
    triggering_phrases = Column(JSONB, default=list)
    icon = Column(String(50))
    color = Column(String(20))
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_preferences = relationship("UserAgentPreferences", back_populates="default_agent")

    def __repr__(self):
        return f"<AIAgent(slug={self.slug}, name={self.name})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "primary_tools": self.primary_tools or [],
            "triggering_phrases": self.triggering_phrases or [],
            "is_active": self.is_active,
            "display_order": self.display_order,
        }


class UserAgentPreferences(Base):
    """
    Per-user preferences for AI agent selection.

    Stores the user's default agent preference and any
    agent-specific settings they've configured.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Reference to user
        default_agent_id: Reference to their default agent
        agent_settings: JSON object with per-agent settings
    """
    __tablename__ = "user_agent_preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    default_agent_id = Column(String(36), ForeignKey("ai_agents.id", ondelete="SET NULL"))
    agent_settings = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="agent_preferences")
    default_agent = relationship("AIAgent", back_populates="user_preferences")

    def __repr__(self):
        return f"<UserAgentPreferences(user_id={self.user_id}, default_agent_id={self.default_agent_id})>"


class AgentAnalytics(Base):
    """
    Usage analytics for AI agents.

    Tracks which agents are used, by whom, for what cases,
    and performance metrics like tokens used and response time.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Reference to user
        agent_slug: Agent identifier (denormalized for query performance)
        case_id: Optional reference to case
        session_id: Chat session identifier
        message_count: Number of messages in this session
        tools_used: JSON array of tools called
        tokens_used: Total tokens consumed
        response_time_ms: Average response time in milliseconds
    """
    __tablename__ = "agent_analytics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_slug = Column(String(50), index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="SET NULL"), index=True)
    session_id = Column(String(100))
    message_count = Column(Integer, default=1)
    tools_used = Column(JSONB, default=list)
    tokens_used = Column(Integer, default=0)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="agent_analytics")
    case = relationship("Case", back_populates="agent_analytics")

    def __repr__(self):
        return f"<AgentAnalytics(agent_slug={self.agent_slug}, user_id={self.user_id})>"
