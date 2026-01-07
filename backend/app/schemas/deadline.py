"""
Pydantic schemas for deadline API endpoints.
"""
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


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
