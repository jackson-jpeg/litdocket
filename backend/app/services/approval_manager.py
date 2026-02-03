"""
Approval Manager for Tool Execution

Manages interactive approval flow for destructive AI tool calls.
Uses asyncio.Event to pause/resume async generators without polling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call awaiting approval."""
    id: str
    name: str
    input: Dict
    rationale: Optional[str] = None


@dataclass
class Approval:
    """Result of an approval decision."""
    approved: bool
    reason: Optional[str] = None
    modifications: Optional[Dict] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ApprovalEvent:
    """Internal state for pending approval."""
    tool_call: ToolCall
    event: asyncio.Event
    user_id: str  # Track which user owns this approval
    result: Optional[Approval] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ApprovalManager:
    """
    Manages tool approval flow with pause/resume pattern.

    Flow:
    1. Streaming service yields tool_use event with approval_required=True
    2. Frontend displays ProposalCard
    3. User clicks approve/reject
    4. POST /approve/{approval_id} or /reject/{approval_id}
    5. submit_approval() calls event.set() to resume generator
    6. Tool executes and stream continues

    Example:
        # In streaming service
        approval = await approval_manager.request_approval(tool_call)
        if approval.approved:
            result = execute_tool(...)
    """

    def __init__(self):
        self.pending_approvals: Dict[str, ApprovalEvent] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def request_approval(
        self,
        tool_call: ToolCall,
        user_id: str,
        timeout: float = 60.0
    ) -> Approval:
        """
        Pause generator and wait for user approval.

        Args:
            tool_call: The tool call requiring approval
            timeout: Max wait time in seconds (default: 60s)

        Returns:
            Approval object with approved=True/False

        Raises:
            No exceptions - returns Approval with approved=False on timeout
        """
        # Generate approval ID
        approval_id = str(uuid.uuid4())

        # Create event for this approval
        event = asyncio.Event()

        approval_event = ApprovalEvent(
            tool_call=tool_call,
            event=event,
            user_id=user_id,
            result=None
        )

        self.pending_approvals[approval_id] = approval_event

        logger.info(
            f"Approval requested: {approval_id} for tool '{tool_call.name}'. "
            f"Waiting up to {timeout}s..."
        )

        try:
            # Wait for approval (with timeout)
            await asyncio.wait_for(event.wait(), timeout=timeout)

            # Get result
            result = approval_event.result

            if result and result.approved:
                logger.info(f"Approval {approval_id} APPROVED by user")
            else:
                logger.info(
                    f"Approval {approval_id} REJECTED: "
                    f"{result.reason if result else 'Unknown'}"
                )

            return result

        except asyncio.TimeoutError:
            logger.warning(
                f"Approval timeout for {approval_id} after {timeout}s. "
                f"Tool '{tool_call.name}' will be skipped."
            )

            return Approval(
                approved=False,
                reason=f"Approval timeout after {timeout} seconds"
            )

        finally:
            # Clean up
            if approval_id in self.pending_approvals:
                del self.pending_approvals[approval_id]

    def submit_approval(
        self,
        approval_id: str,
        approved: bool,
        reason: Optional[str] = None,
        modifications: Optional[Dict] = None
    ) -> bool:
        """
        Submit approval decision to resume generator.

        Args:
            approval_id: The approval ID from tool_use event
            approved: True to approve, False to reject
            reason: Optional reason for rejection
            modifications: Optional modifications to tool input

        Returns:
            True if approval was pending, False if not found
        """
        if approval_id not in self.pending_approvals:
            logger.warning(f"Unknown approval_id: {approval_id}")
            return False

        approval_event = self.pending_approvals[approval_id]

        # Set result
        approval_event.result = Approval(
            approved=approved,
            reason=reason,
            modifications=modifications
        )

        # RESUME THE GENERATOR
        approval_event.event.set()

        action = "APPROVED" if approved else "REJECTED"
        logger.info(
            f"Approval {approval_id} {action} for tool '{approval_event.tool_call.name}'"
        )

        return True

    def get_pending_approvals(self, user_id: Optional[str] = None) -> Dict[str, ToolCall]:
        """
        Get pending approvals, optionally filtered by user.

        Args:
            user_id: If provided, only return approvals for this user

        Returns:
            Dict mapping approval_id to ToolCall
        """
        if user_id:
            return {
                approval_id: event.tool_call
                for approval_id, event in self.pending_approvals.items()
                if event.user_id == user_id
            }
        return {
            approval_id: event.tool_call
            for approval_id, event in self.pending_approvals.items()
        }

    def verify_approval_ownership(self, approval_id: str, user_id: str) -> bool:
        """
        Verify that an approval belongs to a specific user.

        Args:
            approval_id: The approval ID to check
            user_id: The user ID to verify against

        Returns:
            True if approval exists and belongs to user, False otherwise
        """
        if approval_id not in self.pending_approvals:
            return False
        return self.pending_approvals[approval_id].user_id == user_id

    def cancel_approval(self, approval_id: str) -> bool:
        """
        Cancel a pending approval (treat as rejected).

        Args:
            approval_id: The approval ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        return self.submit_approval(
            approval_id=approval_id,
            approved=False,
            reason="Cancelled by user or system"
        )

    async def cleanup_stale_approvals(self, max_age_seconds: int = 300):
        """
        Background task to clean up stale approvals (older than 5 minutes).

        This prevents memory leaks if approvals are never responded to.
        Should be called periodically or on app shutdown.
        """
        now = datetime.utcnow()
        stale_ids = []

        for approval_id, approval_event in self.pending_approvals.items():
            age = (now - approval_event.timestamp).total_seconds()
            if age > max_age_seconds:
                stale_ids.append(approval_id)

        for approval_id in stale_ids:
            logger.warning(
                f"Cleaning up stale approval {approval_id} "
                f"(age: {age:.0f}s)"
            )
            self.cancel_approval(approval_id)

        if stale_ids:
            logger.info(f"Cleaned up {len(stale_ids)} stale approvals")


# Global singleton instance
approval_manager = ApprovalManager()
