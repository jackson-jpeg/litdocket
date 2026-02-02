"""
Pydantic Schemas for Document Deadline Suggestions

Defines request/response schemas for the document suggestion endpoints.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum


class SuggestionStatus(str, Enum):
    """Status values for deadline suggestions."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExtractionMethod(str, Enum):
    """How the suggestion was extracted."""
    AI_KEY_DATES = "ai_key_dates"
    AI_DEADLINES_MENTIONED = "ai_deadlines_mentioned"
    TRIGGER_DETECTED = "trigger_detected"


# =============================================================================
# Response Schemas
# =============================================================================

class SuggestionResponse(BaseModel):
    """Response schema for a single deadline suggestion."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    case_id: str
    title: str
    description: Optional[str] = None
    suggested_date: Optional[date] = None
    deadline_type: Optional[str] = None

    # Extraction info
    extraction_method: str
    source_text: Optional[str] = None

    # Rule matching
    matched_trigger_type: Optional[str] = None
    rule_citation: Optional[str] = None

    # Confidence
    confidence_score: int = 50
    confidence_factors: Dict[str, Any] = Field(default_factory=dict)

    # Status
    status: str = "pending"
    reviewed_at: Optional[datetime] = None
    created_deadline_id: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SuggestionListResponse(BaseModel):
    """Response schema for listing suggestions."""
    suggestions: List[SuggestionResponse]
    total: int
    pending_count: int
    document_id: str


# =============================================================================
# Request Schemas
# =============================================================================

class ApplySuggestionItem(BaseModel):
    """Single suggestion to apply."""
    suggestion_id: str
    apply_as_trigger: bool = False  # If true, trigger cascade calculation
    override_date: Optional[date] = None  # Allow user to override suggested date
    override_title: Optional[str] = None  # Allow user to override title


class ApplySuggestionsRequest(BaseModel):
    """Request to apply multiple suggestions as deadlines."""
    suggestions: List[ApplySuggestionItem]


class ApplySuggestionsResult(BaseModel):
    """Result of applying a single suggestion."""
    suggestion_id: str
    success: bool
    deadline_id: Optional[str] = None
    cascade_count: int = 0  # Number of cascade deadlines created
    error: Optional[str] = None


class ApplySuggestionsResponse(BaseModel):
    """Response from applying suggestions."""
    success: bool
    results: List[ApplySuggestionsResult]
    total_deadlines_created: int
    total_cascade_deadlines: int
    message: str


class UpdateSuggestionRequest(BaseModel):
    """Request to update a suggestion's status."""
    status: SuggestionStatus
    notes: Optional[str] = None  # Optional rejection reason


class UpdateSuggestionResponse(BaseModel):
    """Response from updating a suggestion."""
    success: bool
    suggestion: SuggestionResponse
    message: str


# =============================================================================
# Internal Schemas (for service layer)
# =============================================================================

class CreateSuggestionData(BaseModel):
    """Data for creating a new suggestion (internal use)."""
    document_id: str
    case_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    suggested_date: Optional[date] = None
    deadline_type: Optional[str] = None
    extraction_method: str
    source_text: Optional[str] = None
    matched_trigger_type: Optional[str] = None
    rule_citation: Optional[str] = None
    confidence_score: int = 50
    confidence_factors: Dict[str, Any] = Field(default_factory=dict)
