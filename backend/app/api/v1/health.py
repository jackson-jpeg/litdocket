"""
Health Check Endpoints

Provides health status for various services including email.
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.utils.auth import get_current_user
from app.models.user import User
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class EmailHealthResponse(BaseModel):
    """Response schema for email health check"""
    enabled: bool
    status: str
    message: str


@router.get("/email", response_model=EmailHealthResponse)
async def check_email_health(
    current_user: User = Depends(get_current_user)
):
    """
    Check email service health status.

    Returns whether email notifications are enabled and operational.
    Users can use this to know if their email preferences will work.
    """
    if email_service.enabled:
        return EmailHealthResponse(
            enabled=True,
            status="operational",
            message="Email service is configured and operational."
        )
    else:
        return EmailHealthResponse(
            enabled=False,
            status="disabled",
            message="Email service is not configured. Email notifications will not be sent."
        )
