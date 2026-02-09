"""
Inbox Service - Unified Approval Workflow

Manages all pending approval items in a single queue:
- Jurisdiction approvals (from Cartographer discovery)
- Rule verifications (low confidence extractions)
- Watchtower changes (detected rule updates)
- Scraper failures (requiring manual intervention)
- Conflict resolutions (rule conflicts)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.inbox import InboxItem
from app.models.enums import InboxItemType, InboxStatus

logger = logging.getLogger(__name__)


class InboxService:
    """
    Service for managing the unified inbox approval workflow.

    Provides methods for creating, listing, and reviewing inbox items.
    """

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # CREATE INBOX ITEMS
    # =========================================================================

    def create_jurisdiction_approval_item(
        self,
        jurisdiction_id: str,
        title: str,
        description: Optional[str],
        confidence: float,
        source_url: Optional[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> InboxItem:
        """
        Create inbox item for jurisdiction approval (from Cartographer).

        Args:
            jurisdiction_id: Jurisdiction UUID
            title: Item title
            description: Item description
            confidence: AI confidence score (0-100)
            source_url: Source URL where jurisdiction was discovered
            metadata: Additional metadata

        Returns:
            Created InboxItem
        """
        item = InboxItem(
            type=InboxItemType.JURISDICTION_APPROVAL,
            status=InboxStatus.PENDING,
            title=title,
            description=description,
            jurisdiction_id=jurisdiction_id,
            confidence=confidence,
            source_url=source_url,
            item_metadata=metadata or {}
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        logger.info(f"Created jurisdiction approval inbox item {item.id}")
        return item

    def create_rule_verification_item(
        self,
        rule_id: str,
        title: str,
        description: Optional[str],
        confidence: float,
        source_url: Optional[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> InboxItem:
        """
        Create inbox item for rule verification (low confidence extraction).

        Args:
            rule_id: Rule UUID
            title: Item title
            description: Item description
            confidence: AI confidence score (0-100)
            source_url: Source URL
            metadata: Additional metadata

        Returns:
            Created InboxItem
        """
        item = InboxItem(
            type=InboxItemType.RULE_VERIFICATION,
            status=InboxStatus.PENDING,
            title=title,
            description=description,
            rule_id=rule_id,
            confidence=confidence,
            source_url=source_url,
            item_metadata=metadata or {}
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        logger.info(f"Created rule verification inbox item {item.id}")
        return item

    def create_watchtower_change_item(
        self,
        rule_id: str,
        title: str,
        description: Optional[str],
        jurisdiction_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> InboxItem:
        """
        Create inbox item for watchtower-detected change.

        Args:
            rule_id: Rule UUID that changed
            title: Item title
            description: Change description
            jurisdiction_id: Optional jurisdiction UUID
            metadata: Additional metadata (diff, version info, etc.)

        Returns:
            Created InboxItem
        """
        item = InboxItem(
            type=InboxItemType.WATCHTOWER_CHANGE,
            status=InboxStatus.PENDING,
            title=title,
            description=description,
            rule_id=rule_id,
            jurisdiction_id=jurisdiction_id,
            item_metadata=metadata or {}
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        logger.info(f"Created watchtower change inbox item {item.id}")
        return item

    def create_scraper_failure_item(
        self,
        jurisdiction_id: str,
        title: str,
        description: Optional[str],
        scrape_job_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> InboxItem:
        """
        Create inbox item for scraper failure.

        Args:
            jurisdiction_id: Jurisdiction UUID with failed scraper
            title: Item title
            description: Failure description
            scrape_job_id: Optional scrape job ID
            metadata: Additional metadata (error details, config version, etc.)

        Returns:
            Created InboxItem
        """
        item = InboxItem(
            type=InboxItemType.SCRAPER_FAILURE,
            status=InboxStatus.PENDING,
            title=title,
            description=description,
            jurisdiction_id=jurisdiction_id,
            scrape_job_id=scrape_job_id,
            item_metadata=metadata or {}
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        logger.info(f"Created scraper failure inbox item {item.id}")
        return item

    def create_conflict_resolution_item(
        self,
        conflict_id: str,
        title: str,
        description: Optional[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> InboxItem:
        """
        Create inbox item for rule conflict resolution.

        Args:
            conflict_id: RuleConflict UUID
            title: Item title
            description: Conflict description
            metadata: Additional metadata

        Returns:
            Created InboxItem
        """
        item = InboxItem(
            type=InboxItemType.CONFLICT_RESOLUTION,
            status=InboxStatus.PENDING,
            title=title,
            description=description,
            conflict_id=conflict_id,
            item_metadata=metadata or {}
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        logger.info(f"Created conflict resolution inbox item {item.id}")
        return item

    # =========================================================================
    # QUERY INBOX ITEMS
    # =========================================================================

    def list_inbox_items(
        self,
        item_type: Optional[InboxItemType] = None,
        status: Optional[InboxStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[InboxItem]:
        """
        List inbox items with optional filters.

        Args:
            item_type: Optional filter by item type
            status: Optional filter by status
            limit: Maximum items to return
            offset: Offset for pagination

        Returns:
            List of InboxItem objects
        """
        query = self.db.query(InboxItem)

        if item_type:
            query = query.filter(InboxItem.type == item_type)
        if status:
            query = query.filter(InboxItem.status == status)

        return query.order_by(desc(InboxItem.created_at)).offset(offset).limit(limit).all()

    def get_inbox_item(self, item_id: str) -> Optional[InboxItem]:
        """
        Get a single inbox item by ID.

        Args:
            item_id: Inbox item UUID

        Returns:
            InboxItem or None
        """
        return self.db.query(InboxItem).filter(InboxItem.id == item_id).first()

    def get_pending_count(self, item_type: Optional[InboxItemType] = None) -> int:
        """
        Get count of pending inbox items.

        Args:
            item_type: Optional filter by item type

        Returns:
            Count of pending items
        """
        query = self.db.query(InboxItem).filter(InboxItem.status == InboxStatus.PENDING)

        if item_type:
            query = query.filter(InboxItem.type == item_type)

        return query.count()

    def get_pending_summary(self) -> Dict[str, int]:
        """
        Get summary of pending items by type.

        Returns:
            Dict mapping item type to count
        """
        from sqlalchemy import func

        results = self.db.query(
            InboxItem.type,
            func.count(InboxItem.id).label("count")
        ).filter(
            InboxItem.status == InboxStatus.PENDING
        ).group_by(InboxItem.type).all()

        summary = {item_type.value: 0 for item_type in InboxItemType}

        for item_type, count in results:
            summary[item_type.value] = count

        return summary

    # =========================================================================
    # REVIEW INBOX ITEMS
    # =========================================================================

    def review_item(
        self,
        item_id: str,
        user_id: str,
        resolution: str,
        notes: Optional[str] = None
    ) -> InboxItem:
        """
        Review an inbox item.

        Args:
            item_id: Inbox item UUID
            user_id: User performing the review
            resolution: Resolution (e.g., 'approved', 'rejected', 'deferred')
            notes: Optional review notes

        Returns:
            Updated InboxItem

        Raises:
            ValueError: If item not found
        """
        item = self.get_inbox_item(item_id)

        if not item:
            raise ValueError(f"Inbox item {item_id} not found")

        item.status = InboxStatus.REVIEWED
        item.reviewed_by = user_id
        item.reviewed_at = datetime.now(timezone.utc)
        item.resolution = resolution
        item.resolution_notes = notes

        self.db.commit()
        self.db.refresh(item)

        logger.info(f"Reviewed inbox item {item_id} with resolution: {resolution}")
        return item

    def defer_item(
        self,
        item_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> InboxItem:
        """
        Defer an inbox item for later review.

        Args:
            item_id: Inbox item UUID
            user_id: User performing the deferral
            notes: Optional deferral notes

        Returns:
            Updated InboxItem

        Raises:
            ValueError: If item not found
        """
        item = self.get_inbox_item(item_id)

        if not item:
            raise ValueError(f"Inbox item {item_id} not found")

        item.status = InboxStatus.DEFERRED
        item.reviewed_by = user_id
        item.reviewed_at = datetime.now(timezone.utc)
        item.resolution = "deferred"
        item.resolution_notes = notes

        self.db.commit()
        self.db.refresh(item)

        logger.info(f"Deferred inbox item {item_id}")
        return item

    def bulk_review(
        self,
        item_ids: List[str],
        user_id: str,
        resolution: str,
        notes: Optional[str] = None
    ) -> List[InboxItem]:
        """
        Review multiple inbox items at once.

        Args:
            item_ids: List of inbox item UUIDs
            user_id: User performing the review
            resolution: Resolution for all items
            notes: Optional review notes

        Returns:
            List of updated InboxItem objects
        """
        items = self.db.query(InboxItem).filter(InboxItem.id.in_(item_ids)).all()

        for item in items:
            item.status = InboxStatus.REVIEWED
            item.reviewed_by = user_id
            item.reviewed_at = datetime.now(timezone.utc)
            item.resolution = resolution
            item.resolution_notes = notes

        self.db.commit()

        logger.info(f"Bulk reviewed {len(items)} inbox items with resolution: {resolution}")
        return items

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def exists_for_entity(
        self,
        item_type: InboxItemType,
        entity_id: str
    ) -> bool:
        """
        Check if a pending inbox item already exists for an entity.

        Args:
            item_type: The inbox item type
            entity_id: The entity ID (rule_id, jurisdiction_id, etc.)

        Returns:
            True if pending item exists
        """
        # Build query based on item type
        query = self.db.query(InboxItem).filter(
            and_(
                InboxItem.type == item_type,
                InboxItem.status == InboxStatus.PENDING
            )
        )

        if item_type == InboxItemType.JURISDICTION_APPROVAL:
            query = query.filter(InboxItem.jurisdiction_id == entity_id)
        elif item_type == InboxItemType.RULE_VERIFICATION:
            query = query.filter(InboxItem.rule_id == entity_id)
        elif item_type == InboxItemType.WATCHTOWER_CHANGE:
            query = query.filter(InboxItem.rule_id == entity_id)
        elif item_type == InboxItemType.SCRAPER_FAILURE:
            query = query.filter(InboxItem.jurisdiction_id == entity_id)
        elif item_type == InboxItemType.CONFLICT_RESOLUTION:
            query = query.filter(InboxItem.conflict_id == entity_id)

        return query.first() is not None

    def delete_item(self, item_id: str) -> bool:
        """
        Delete an inbox item.

        Args:
            item_id: Inbox item UUID

        Returns:
            True if deleted, False if not found
        """
        item = self.get_inbox_item(item_id)

        if not item:
            return False

        self.db.delete(item)
        self.db.commit()

        logger.info(f"Deleted inbox item {item_id}")
        return True
