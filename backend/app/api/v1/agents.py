"""
AI Agents API Endpoints

Endpoints for managing AI agent selection and preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.database import get_db
from app.models.user import User
from app.services.agent_service import get_agent_service
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


class AgentResponse(BaseModel):
    """Response model for an AI agent."""
    id: str
    slug: str
    name: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    primary_tools: List[str]
    triggering_phrases: List[str]
    is_active: bool
    display_order: int


class AgentListResponse(BaseModel):
    """Response model for list of agents."""
    success: bool
    data: List[AgentResponse]


class SetDefaultAgentRequest(BaseModel):
    """Request to set default agent."""
    agent_slug: str


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""
    success: bool
    default_agent: Optional[AgentResponse]


class AgentSuggestionResponse(BaseModel):
    """Response model for agent suggestion."""
    success: bool
    suggested_agent: Optional[AgentResponse]
    reason: Optional[str]


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all available AI agents.

    Returns active agents ordered by display_order.
    """
    agent_service = get_agent_service(db)
    agents = agent_service.get_active_agents()

    return {
        "success": True,
        "data": [
            AgentResponse(
                id=agent.id,
                slug=agent.slug,
                name=agent.name,
                description=agent.description,
                icon=agent.icon,
                color=agent.color,
                primary_tools=agent.primary_tools or [],
                triggering_phrases=agent.triggering_phrases or [],
                is_active=agent.is_active,
                display_order=agent.display_order
            )
            for agent in agents
        ]
    }


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's agent preferences.

    Returns the user's default agent if set.
    """
    agent_service = get_agent_service(db)
    default_agent = agent_service.get_user_default_agent(str(current_user.id))

    return {
        "success": True,
        "default_agent": AgentResponse(
            id=default_agent.id,
            slug=default_agent.slug,
            name=default_agent.name,
            description=default_agent.description,
            icon=default_agent.icon,
            color=default_agent.color,
            primary_tools=default_agent.primary_tools or [],
            triggering_phrases=default_agent.triggering_phrases or [],
            is_active=default_agent.is_active,
            display_order=default_agent.display_order
        ) if default_agent else None
    }


@router.post("/preferences/default")
async def set_default_agent(
    request: SetDefaultAgentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set user's default AI agent.

    Args:
        request: Contains the agent_slug to set as default
    """
    agent_service = get_agent_service(db)
    success = agent_service.set_user_default_agent(
        user_id=str(current_user.id),
        agent_slug=request.agent_slug
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{request.agent_slug}' not found"
        )

    return {
        "success": True,
        "message": f"Default agent set to {request.agent_slug}"
    }


@router.get("/suggest", response_model=AgentSuggestionResponse)
async def suggest_agent(
    message: str = Query(..., description="Message to analyze for agent suggestion"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Suggest an agent based on message content.

    Analyzes the message for triggering phrases and suggests
    the most appropriate agent.
    """
    agent_service = get_agent_service(db)
    suggested = agent_service.detect_suggested_agent(message)

    if suggested:
        return {
            "success": True,
            "suggested_agent": AgentResponse(
                id=suggested.id,
                slug=suggested.slug,
                name=suggested.name,
                description=suggested.description,
                icon=suggested.icon,
                color=suggested.color,
                primary_tools=suggested.primary_tools or [],
                triggering_phrases=suggested.triggering_phrases or [],
                is_active=suggested.is_active,
                display_order=suggested.display_order
            ),
            "reason": f"Message contains keywords matching {suggested.name}"
        }
    else:
        return {
            "success": True,
            "suggested_agent": None,
            "reason": "No specific agent matches the message content"
        }


@router.get("/stats")
async def get_agent_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get agent usage statistics for the current user.

    Returns session counts, message counts, and token usage by agent.
    """
    agent_service = get_agent_service(db)
    stats = agent_service.get_agent_stats(str(current_user.id))

    return {
        "success": True,
        "data": stats
    }


@router.get("/{agent_slug}")
async def get_agent(
    agent_slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific agent by slug.
    """
    agent_service = get_agent_service(db)
    agent = agent_service.get_agent_by_slug(agent_slug)

    if not agent:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_slug}' not found"
        )

    return {
        "success": True,
        "data": AgentResponse(
            id=agent.id,
            slug=agent.slug,
            name=agent.name,
            description=agent.description,
            icon=agent.icon,
            color=agent.color,
            primary_tools=agent.primary_tools or [],
            triggering_phrases=agent.triggering_phrases or [],
            is_active=agent.is_active,
            display_order=agent.display_order
        )
    }
