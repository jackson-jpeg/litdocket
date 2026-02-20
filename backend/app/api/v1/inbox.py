"""
Inbox API Endpoints - Unified Approval Workflow

Provides REST API for managing inbox items:
- List pending approvals
- Review items (approve/reject/defer)
- Get pending counts by type
- Bulk operations
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.utils.auth import get_current_user
from app.models.user import User
from app.models.enums import InboxItemType, InboxStatus
from app.services.inbox_service import InboxService
from app.database import get_db

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class InboxItemResponse(BaseModel):
    """Response schema for inbox item"""
    id: str
    type: str
    status: str
    title: str
    description: Optional[str]
    jurisdiction_id: Optional[str]
    rule_id: Optional[str]
    conflict_id: Optional[str]
    scrape_job_id: Optional[str]
    confidence: Optional[float]
    source_url: Optional[str]
    metadata: dict
    created_at: str
    reviewed_at: Optional[str]
    reviewed_by: Optional[str]
    resolution: Optional[str]
    resolution_notes: Optional[str]

    class Config:
        from_attributes = True


class ReviewItemRequest(BaseModel):
    """Request schema for reviewing an item"""
    resolution: str = Field(..., description="Resolution: 'approved', 'rejected', 'deferred'")
    notes: Optional[str] = Field(None, description="Review notes")


class BulkReviewRequest(BaseModel):
    """Request schema for bulk review"""
    item_ids: List[str] = Field(..., description="List of inbox item IDs")
    resolution: str = Field(..., description="Resolution for all items")
    notes: Optional[str] = Field(None, description="Review notes")


class PendingSummaryResponse(BaseModel):
    """Response schema for pending summary"""
    total: int
    by_type: dict


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/", response_model=List[InboxItemResponse])
async def list_inbox_items(
    type: Optional[str] = Query(None, description="Filter by item type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List inbox items with optional filters.

    Returns inbox items ordered by creation date (newest first).
    """
    service = InboxService(db)

    # Parse enum filters
    item_type_filter = None
    if type:
        try:
            item_type_filter = InboxItemType[type]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid item type: {type}")

    status_filter = None
    if status:
        try:
            status_filter = InboxStatus[status]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    items = service.list_inbox_items(
        user_id=str(current_user.id),
        item_type=item_type_filter,
        status=status_filter,
        limit=limit,
        offset=offset
    )

    return [item.to_dict() for item in items]


@router.get("/pending/summary", response_model=PendingSummaryResponse)
async def get_pending_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get summary of pending inbox items by type.

    Returns count of pending items for each inbox type.
    """
    service = InboxService(db)

    summary = service.get_pending_summary(user_id=str(current_user.id))
    total = sum(summary.values())

    return {
        "total": total,
        "by_type": summary
    }


@router.get("/pending/count")
async def get_pending_count(
    type: Optional[str] = Query(None, description="Filter by item type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get count of pending inbox items.

    Optionally filter by item type.
    """
    service = InboxService(db)

    item_type_filter = None
    if type:
        try:
            item_type_filter = InboxItemType[type]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid item type: {type}")

    count = service.get_pending_count(user_id=str(current_user.id), item_type=item_type_filter)

    return {
        "count": count,
        "type": type
    }


@router.get("/{item_id}", response_model=InboxItemResponse)
async def get_inbox_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single inbox item by ID.
    """
    service = InboxService(db)

    item = service.get_inbox_item(item_id, user_id=str(current_user.id))

    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")

    return item.to_dict()


@router.post("/{item_id}/review", response_model=InboxItemResponse)
async def review_inbox_item(
    item_id: str,
    review: ReviewItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Review an inbox item (approve/reject/defer).

    Valid resolutions: 'approved', 'rejected', 'deferred'
    """
    service = InboxService(db)

    try:
        item = service.review_item(
            item_id=item_id,
            user_id=str(current_user.id),
            resolution=review.resolution,
            notes=review.notes
        )

        return item.to_dict()

    except ValueError:
        raise HTTPException(status_code=404, detail="Inbox item not found")


@router.post("/{item_id}/defer", response_model=InboxItemResponse)
async def defer_inbox_item(
    item_id: str,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Defer an inbox item for later review.
    """
    service = InboxService(db)

    try:
        item = service.defer_item(
            item_id=item_id,
            user_id=str(current_user.id),
            notes=notes
        )

        return item.to_dict()

    except ValueError:
        raise HTTPException(status_code=404, detail="Inbox item not found")


@router.post("/bulk-review", response_model=List[InboxItemResponse])
async def bulk_review_items(
    bulk_review: BulkReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Review multiple inbox items at once.

    Applies the same resolution to all specified items.
    """
    service = InboxService(db)

    items = service.bulk_review(
        item_ids=bulk_review.item_ids,
        user_id=str(current_user.id),
        resolution=bulk_review.resolution,
        notes=bulk_review.notes
    )

    return [item.to_dict() for item in items]


@router.delete("/{item_id}")
async def delete_inbox_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an inbox item.
    """
    service = InboxService(db)

    deleted = service.delete_item(item_id, user_id=str(current_user.id))

    if not deleted:
        raise HTTPException(status_code=404, detail="Inbox item not found")

    return {"success": True, "message": "Inbox item deleted"}
