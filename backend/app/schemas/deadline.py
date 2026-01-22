"""
Pydantic schemas for deadline API endpoints.
"""
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List, Dict, Any
from enum import Enum


class DeadlineCreate(BaseModel):
    """Schema for creating a new deadline manually"""
    case_id: str = Field(..., description="ID of the case this deadline belongs to")
    title: str = Field(..., min_length=1, max_length=500, description="Deadline title")
    deadline_date: date = Field(..., description="Due date for the deadline")
    description: Optional[str] = Field(None, description="Detailed description")
    priority: str = Field("standard", description="Priority level: informational, standard, important, critical, fatal")
    deadline_type: Optional[str] = Field(None, description="Type: response, hearing, filing, discovery, etc.")
    applicable_rule: Optional[str] = Field(None, description="Rule citation (e.g., 'Fla. R. Civ. P. 1.140(a)')")
    party_role: Optional[str] = Field(None, description="Who must take action (e.g., 'Plaintiff', 'Defendant')")
    action_required: Optional[str] = Field(None, description="What action is required")

    class Config:
        json_schema_extra = {
            "example": {
                "case_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "File Motion for Summary Judgment",
                "deadline_date": "2026-02-15",
                "description": "Must file MSJ before discovery cutoff",
                "priority": "critical",
                "deadline_type": "filing",
                "applicable_rule": "Fla. R. Civ. P. 1.510",
                "party_role": "Plaintiff",
                "action_required": "Draft and file motion with supporting affidavits"
            }
        }


class DeadlineReschedule(BaseModel):
    """Schema for rescheduling a deadline (drag-drop or manual edit)"""
    new_date: date = Field(..., description="New deadline date")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for rescheduling")

    class Config:
        json_schema_extra = {
            "example": {
                "new_date": "2026-02-20",
                "reason": "Opposing counsel requested extension"
            }
        }


class DeadlineUpdate(BaseModel):
    """Schema for updating deadline fields"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    deadline_date: Optional[date] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    deadline_type: Optional[str] = None
    applicable_rule: Optional[str] = None
    party_role: Optional[str] = None
    action_required: Optional[str] = None


class DeadlineResponse(BaseModel):
    """Schema for deadline response with case info (for calendar view)"""
    id: str
    case_id: str
    case_number: str  # Joined from case table
    case_title: str   # Joined from case table
    title: str
    description: Optional[str]
    deadline_date: Optional[date]
    deadline_type: Optional[str]
    priority: str
    status: str
    party_role: Optional[str]
    action_required: Optional[str]
    applicable_rule: Optional[str]
    is_manually_overridden: bool
    is_calculated: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# =============================================================
# CONVERSATIONAL INTAKE SCHEMAS
# =============================================================

class DeadlineCreationStatus(str, Enum):
    """Status of deadline creation - supports conversational intake"""
    SUCCESS = "success"
    NEEDS_CLARIFICATION = "needs_clarification"
    PARTIAL_MATCH = "partial_match"
    ERROR = "error"


class ClarificationRequest(BaseModel):
    """A question the system needs answered before creating deadlines"""
    field_name: str = Field(..., description="Internal field name")
    question_text: str = Field(..., description="Question to display to user")
    field_type: str = Field(..., description="Expected answer type: boolean, integer, enum, text, date")
    options: Optional[List[str]] = Field(None, description="Options for enum fields")
    default_value: Optional[Any] = Field(None, description="Default value if user doesn't provide one")
    affects_deadlines: Optional[List[str]] = Field(None, description="Which deadlines depend on this field")

    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "jury_status",
                "question_text": "Is this a jury trial?",
                "field_type": "boolean",
                "options": None,
                "default_value": True,
                "affects_deadlines": ["Proposed Jury Instructions Due", "Proposed Verdict Form Due"]
            }
        }


class DeadlineCreateResponseData(BaseModel):
    """Data returned on successful deadline creation"""
    deadline: Optional[Dict[str, Any]] = None
    trigger_id: Optional[str] = None
    trigger_type: Optional[str] = None
    dependent_deadlines_created: Optional[int] = None
    deadlines: Optional[List[Dict[str, Any]]] = None


class DeadlineCreateResponse(BaseModel):
    """
    Response for deadline creation with conversational intake support.

    Flow:
    1. LLM calls tool with available data
    2. If missing required fields -> status=NEEDS_CLARIFICATION, return missing_fields
    3. LLM sees this, asks user the questions
    4. User answers
    5. LLM calls tool again with context containing answers
    6. If all fields present -> status=SUCCESS, return deadline data
    """
    status: DeadlineCreationStatus = Field(..., description="Creation status")
    message: str = Field(..., description="Human-readable message")

    # SUCCESS fields
    success: Optional[bool] = Field(None, description="Legacy success flag (for backward compatibility)")
    data: Optional[DeadlineCreateResponseData] = Field(None, description="Deadline data on success")

    # NEEDS_CLARIFICATION fields
    missing_fields: Optional[List[ClarificationRequest]] = Field(
        None,
        description="Questions to ask user (returned when status=NEEDS_CLARIFICATION)"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="ID for tracking multi-turn conversations (optional)"
    )

    # PARTIAL_MATCH fields
    detected_trigger: Optional[str] = Field(None, description="Detected trigger type")
    confidence: Optional[float] = Field(None, description="Confidence in trigger detection (0-1)")

    # ERROR fields
    error: Optional[str] = Field(None, description="Error message if status=ERROR")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "status": "needs_clarification",
                    "message": "I detected a trial_date event. I need a few more details.",
                    "missing_fields": [
                        {
                            "field_name": "jury_status",
                            "question_text": "Is this a jury trial?",
                            "field_type": "boolean"
                        }
                    ],
                    "detected_trigger": "trial_date"
                },
                {
                    "status": "success",
                    "message": "Created trial_date with 25 dependent deadlines",
                    "success": True,
                    "data": {
                        "trigger_id": "abc-123",
                        "trigger_type": "trial_date",
                        "dependent_deadlines_created": 25
                    }
                }
            ]
        }
