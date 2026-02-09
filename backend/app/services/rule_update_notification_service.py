"""
Rule Update Notification Service

Phase 6: Advanced Intelligence & Self-Healing

Manages subscriptions to jurisdiction/rule updates and delivers notifications:
- Subscribe to specific jurisdictions or rules
- Watchtower detects changes → notify subscribers
- Email + in-app notifications with diff view
- Configurable notification preferences (immediate, daily digest, weekly)
- Action-required tagging for high-impact changes

Success Target: <5% missed critical rule changes
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
import json

from app.models.user import User
from app.models.jurisdiction import Jurisdiction
from app.models.authority_core import AuthorityRule
from app.models.watchtower_hash import WatchtowerHash
from app.services.inbox_service import InboxService
from app.services.authority_notification_service import AuthorityNotificationService

logger = logging.getLogger(__name__)


class RuleUpdateNotificationService:
    """
    Manages rule update subscriptions and notifications.

    Integrates with Watchtower to deliver timely notifications
    when court rules change.
    """

    def __init__(self, db: Session):
        self.db = db
        self.inbox_service = InboxService(db)
        self.notification_service = AuthorityNotificationService()

    async def subscribe_to_jurisdiction(
        self,
        user_id: str,
        jurisdiction_id: str,
        notification_preference: str = "immediate"
    ) -> Dict[str, Any]:
        """
        Subscribe user to all rule updates for a jurisdiction.

        Args:
            user_id: User UUID
            jurisdiction_id: Jurisdiction UUID
            notification_preference: "immediate", "daily", or "weekly"

        Returns:
            Subscription confirmation
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        jurisdiction = self.db.query(Jurisdiction).filter(
            Jurisdiction.id == jurisdiction_id
        ).first()

        if not user or not jurisdiction:
            return {"success": False, "error": "User or jurisdiction not found"}

        # Store subscription in user metadata
        if not user.metadata:
            user.metadata = {}

        if "rule_subscriptions" not in user.metadata:
            user.metadata["rule_subscriptions"] = {
                "jurisdictions": [],
                "rules": []
            }

        # Add jurisdiction subscription
        jurisdiction_sub = {
            "jurisdiction_id": jurisdiction_id,
            "jurisdiction_name": jurisdiction.name,
            "notification_preference": notification_preference,
            "subscribed_at": datetime.now(timezone.utc).isoformat()
        }

        # Remove existing subscription if present
        user.metadata["rule_subscriptions"]["jurisdictions"] = [
            sub for sub in user.metadata["rule_subscriptions"]["jurisdictions"]
            if sub["jurisdiction_id"] != jurisdiction_id
        ]

        # Add new subscription
        user.metadata["rule_subscriptions"]["jurisdictions"].append(jurisdiction_sub)

        self.db.commit()

        logger.info(f"User {user_id} subscribed to jurisdiction {jurisdiction.name}")

        return {
            "success": True,
            "jurisdiction": jurisdiction.name,
            "notification_preference": notification_preference,
            "message": f"You'll receive {notification_preference} notifications for {jurisdiction.name} rule changes"
        }

    async def subscribe_to_rule(
        self,
        user_id: str,
        rule_id: str,
        notification_preference: str = "immediate"
    ) -> Dict[str, Any]:
        """
        Subscribe user to updates for a specific rule.

        Args:
            user_id: User UUID
            rule_id: AuthorityRule UUID
            notification_preference: "immediate", "daily", or "weekly"

        Returns:
            Subscription confirmation
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        rule = self.db.query(AuthorityRule).filter(
            AuthorityRule.id == rule_id
        ).first()

        if not user or not rule:
            return {"success": False, "error": "User or rule not found"}

        # Store subscription in user metadata
        if not user.metadata:
            user.metadata = {}

        if "rule_subscriptions" not in user.metadata:
            user.metadata["rule_subscriptions"] = {
                "jurisdictions": [],
                "rules": []
            }

        # Add rule subscription
        rule_sub = {
            "rule_id": rule_id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "notification_preference": notification_preference,
            "subscribed_at": datetime.now(timezone.utc).isoformat()
        }

        # Remove existing subscription if present
        user.metadata["rule_subscriptions"]["rules"] = [
            sub for sub in user.metadata["rule_subscriptions"]["rules"]
            if sub["rule_id"] != rule_id
        ]

        # Add new subscription
        user.metadata["rule_subscriptions"]["rules"].append(rule_sub)

        self.db.commit()

        logger.info(f"User {user_id} subscribed to rule {rule.rule_code}")

        return {
            "success": True,
            "rule": f"{rule.rule_code}: {rule.rule_name}",
            "notification_preference": notification_preference,
            "message": f"You'll receive {notification_preference} notifications for this rule"
        }

    async def unsubscribe_from_jurisdiction(
        self,
        user_id: str,
        jurisdiction_id: str
    ) -> Dict[str, Any]:
        """
        Unsubscribe user from jurisdiction updates.

        Args:
            user_id: User UUID
            jurisdiction_id: Jurisdiction UUID

        Returns:
            Unsubscribe confirmation
        """
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user or not user.metadata or "rule_subscriptions" not in user.metadata:
            return {"success": False, "error": "No subscriptions found"}

        # Remove jurisdiction subscription
        user.metadata["rule_subscriptions"]["jurisdictions"] = [
            sub for sub in user.metadata["rule_subscriptions"]["jurisdictions"]
            if sub["jurisdiction_id"] != jurisdiction_id
        ]

        self.db.commit()

        logger.info(f"User {user_id} unsubscribed from jurisdiction {jurisdiction_id}")

        return {
            "success": True,
            "message": "Unsubscribed successfully"
        }

    async def unsubscribe_from_rule(
        self,
        user_id: str,
        rule_id: str
    ) -> Dict[str, Any]:
        """
        Unsubscribe user from rule updates.

        Args:
            user_id: User UUID
            rule_id: AuthorityRule UUID

        Returns:
            Unsubscribe confirmation
        """
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user or not user.metadata or "rule_subscriptions" not in user.metadata:
            return {"success": False, "error": "No subscriptions found"}

        # Remove rule subscription
        user.metadata["rule_subscriptions"]["rules"] = [
            sub for sub in user.metadata["rule_subscriptions"]["rules"]
            if sub["rule_id"] != rule_id
        ]

        self.db.commit()

        logger.info(f"User {user_id} unsubscribed from rule {rule_id}")

        return {
            "success": True,
            "message": "Unsubscribed successfully"
        }

    def get_user_subscriptions(self, user_id: str) -> Dict[str, Any]:
        """
        Get all subscriptions for a user.

        Args:
            user_id: User UUID

        Returns:
            User's subscriptions
        """
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user or not user.metadata or "rule_subscriptions" not in user.metadata:
            return {
                "jurisdictions": [],
                "rules": []
            }

        return user.metadata["rule_subscriptions"]

    async def notify_rule_change(
        self,
        rule_id: str,
        change_details: Dict[str, Any],
        old_version: Optional[Dict[str, Any]] = None,
        new_version: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Notify all subscribers of a rule change.

        Called by Watchtower when it detects a rule update.

        Args:
            rule_id: Changed rule UUID
            change_details: Description of changes
            old_version: Previous rule data (for diff)
            new_version: Updated rule data (for diff)

        Returns:
            Notification delivery report
        """
        rule = self.db.query(AuthorityRule).filter(
            AuthorityRule.id == rule_id
        ).first()

        if not rule:
            return {"success": False, "error": "Rule not found"}

        logger.info(f"Notifying subscribers of rule change: {rule.rule_code}")

        # Find all users subscribed to this rule or its jurisdiction
        users = self.db.query(User).all()
        subscribers = []

        for user in users:
            if not user.metadata or "rule_subscriptions" not in user.metadata:
                continue

            # Check rule-specific subscription
            rule_subscribed = any(
                sub["rule_id"] == rule_id
                for sub in user.metadata["rule_subscriptions"].get("rules", [])
            )

            # Check jurisdiction subscription
            jurisdiction_subscribed = any(
                sub["jurisdiction_id"] == rule.jurisdiction_id
                for sub in user.metadata["rule_subscriptions"].get("jurisdictions", [])
            )

            if rule_subscribed or jurisdiction_subscribed:
                # Get notification preference
                preference = "immediate"  # Default

                if rule_subscribed:
                    pref_sub = next(
                        (sub for sub in user.metadata["rule_subscriptions"]["rules"]
                         if sub["rule_id"] == rule_id),
                        None
                    )
                    if pref_sub:
                        preference = pref_sub["notification_preference"]
                elif jurisdiction_subscribed:
                    pref_sub = next(
                        (sub for sub in user.metadata["rule_subscriptions"]["jurisdictions"]
                         if sub["jurisdiction_id"] == rule.jurisdiction_id),
                        None
                    )
                    if pref_sub:
                        preference = pref_sub["notification_preference"]

                subscribers.append({
                    "user_id": user.id,
                    "email": user.email,
                    "preference": preference
                })

        logger.info(f"Found {len(subscribers)} subscribers for rule {rule.rule_code}")

        # Deliver notifications based on preference
        immediate_count = 0
        digest_count = 0

        for subscriber in subscribers:
            if subscriber["preference"] == "immediate":
                # Send immediate notification
                await self._send_immediate_notification(
                    subscriber["user_id"],
                    rule,
                    change_details,
                    old_version,
                    new_version
                )
                immediate_count += 1
            else:
                # Queue for digest (daily/weekly)
                await self._queue_for_digest(
                    subscriber["user_id"],
                    rule,
                    change_details,
                    subscriber["preference"]
                )
                digest_count += 1

        return {
            "success": True,
            "subscribers_notified": len(subscribers),
            "immediate_notifications": immediate_count,
            "queued_for_digest": digest_count,
            "rule": f"{rule.rule_code}: {rule.rule_name}"
        }

    async def _send_immediate_notification(
        self,
        user_id: str,
        rule: AuthorityRule,
        change_details: Dict[str, Any],
        old_version: Optional[Dict[str, Any]],
        new_version: Optional[Dict[str, Any]]
    ) -> None:
        """
        Send immediate notification for rule change.

        Creates inbox item and sends email.

        Args:
            user_id: User to notify
            rule: Changed rule
            change_details: Change description
            old_version: Previous rule data
            new_version: Updated rule data
        """
        try:
            # Determine impact level
            impact = self._assess_change_impact(old_version, new_version)

            # Create inbox item
            self.inbox_service.create_inbox_item(
                type="WATCHTOWER_CHANGE",
                title=f"Rule Updated: {rule.rule_code}",
                description=f"""The following rule has been updated:

**{rule.rule_code}: {rule.rule_name}**

**Change Type:** {change_details.get('change_type', 'Modified')}
**Impact Level:** {impact}

**Changes Detected:**
{self._format_changes(old_version, new_version)}

**Action Required:** {'Yes - Review deadlines' if impact == 'HIGH' else 'Review recommended'}

Please review this change and update your cases accordingly.
""",
                jurisdiction_id=rule.jurisdiction_id,
                metadata={
                    "rule_id": rule.id,
                    "rule_code": rule.rule_code,
                    "change_details": change_details,
                    "old_version": old_version,
                    "new_version": new_version,
                    "impact": impact,
                    "action_required": impact == "HIGH"
                },
                priority="high" if impact == "HIGH" else "medium",
                user_id=user_id  # User-specific inbox item
            )

            # Send email notification
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.email:
                await self.notification_service.send_rule_update_alert(
                    to_email=user.email,
                    rule_code=rule.rule_code,
                    rule_name=rule.rule_name,
                    change_summary=change_details.get('summary', 'Rule has been modified'),
                    impact=impact
                )

            logger.info(f"Sent immediate notification to user {user_id} for rule {rule.rule_code}")

        except Exception as e:
            logger.error(f"Failed to send immediate notification: {str(e)}")

    async def _queue_for_digest(
        self,
        user_id: str,
        rule: AuthorityRule,
        change_details: Dict[str, Any],
        digest_frequency: str
    ) -> None:
        """
        Queue rule change for digest notification.

        Args:
            user_id: User to notify
            rule: Changed rule
            change_details: Change description
            digest_frequency: "daily" or "weekly"
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()

            if not user:
                return

            # Store pending notification in user metadata
            if not user.metadata:
                user.metadata = {}

            if "pending_rule_notifications" not in user.metadata:
                user.metadata["pending_rule_notifications"] = []

            # Add to pending notifications
            user.metadata["pending_rule_notifications"].append({
                "rule_id": rule.id,
                "rule_code": rule.rule_code,
                "rule_name": rule.rule_name,
                "change_details": change_details,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "digest_frequency": digest_frequency
            })

            self.db.commit()

            logger.info(f"Queued rule change for {digest_frequency} digest: user {user_id}, rule {rule.rule_code}")

        except Exception as e:
            logger.error(f"Failed to queue digest notification: {str(e)}")

    def _assess_change_impact(
        self,
        old_version: Optional[Dict[str, Any]],
        new_version: Optional[Dict[str, Any]]
    ) -> str:
        """
        Assess the impact level of a rule change.

        Args:
            old_version: Previous rule data
            new_version: Updated rule data

        Returns:
            Impact level: "HIGH", "MEDIUM", or "LOW"
        """
        if not old_version or not new_version:
            return "MEDIUM"

        # Check for deadline changes (high impact)
        old_deadlines = old_version.get("deadlines", [])
        new_deadlines = new_version.get("deadlines", [])

        if old_deadlines != new_deadlines:
            # Deadline changes are HIGH impact
            return "HIGH"

        # Check for trigger type changes
        if old_version.get("trigger_type") != new_version.get("trigger_type"):
            return "HIGH"

        # Check for rule code changes (medium impact)
        if old_version.get("rule_code") != new_version.get("rule_code"):
            return "MEDIUM"

        # Minor changes (citation, description)
        return "LOW"

    def _format_changes(
        self,
        old_version: Optional[Dict[str, Any]],
        new_version: Optional[Dict[str, Any]]
    ) -> str:
        """
        Format changes as human-readable diff.

        Args:
            old_version: Previous rule data
            new_version: Updated rule data

        Returns:
            Formatted diff string
        """
        if not old_version or not new_version:
            return "Complete rule replacement detected"

        changes = []

        # Compare key fields
        fields_to_check = ["rule_code", "rule_name", "trigger_type", "deadlines", "citation"]

        for field in fields_to_check:
            old_val = old_version.get(field)
            new_val = new_version.get(field)

            if old_val != new_val:
                changes.append(f"- **{field}**: Changed from `{old_val}` to `{new_val}`")

        if not changes:
            return "Minor updates detected (metadata or text changes)"

        return "\n".join(changes)


# =========================================================================
# DIGEST NOTIFICATION HELPERS
# =========================================================================

async def send_daily_rule_update_digest(db: Session) -> Dict[str, Any]:
    """
    Send daily digest of rule changes to users who opted for daily notifications.

    Called by scheduled job.

    Args:
        db: Database session

    Returns:
        Delivery report
    """
    logger.info("Starting daily rule update digest")

    users = db.query(User).all()
    digests_sent = 0

    for user in users:
        if not user.metadata or "pending_rule_notifications" not in user.metadata:
            continue

        # Filter for daily digest notifications
        daily_notifications = [
            notif for notif in user.metadata["pending_rule_notifications"]
            if notif.get("digest_frequency") == "daily"
        ]

        if daily_notifications:
            # Send digest email
            await _send_digest_email(user, daily_notifications, "daily")

            # Clear sent notifications
            user.metadata["pending_rule_notifications"] = [
                notif for notif in user.metadata["pending_rule_notifications"]
                if notif.get("digest_frequency") != "daily"
            ]

            db.commit()
            digests_sent += 1

    logger.info(f"Sent {digests_sent} daily rule update digests")

    return {
        "digests_sent": digests_sent,
        "frequency": "daily"
    }


async def send_weekly_rule_update_digest(db: Session) -> Dict[str, Any]:
    """
    Send weekly digest of rule changes to users who opted for weekly notifications.

    Called by scheduled job (Sundays).

    Args:
        db: Database session

    Returns:
        Delivery report
    """
    logger.info("Starting weekly rule update digest")

    users = db.query(User).all()
    digests_sent = 0

    for user in users:
        if not user.metadata or "pending_rule_notifications" not in user.metadata:
            continue

        # Filter for weekly digest notifications
        weekly_notifications = [
            notif for notif in user.metadata["pending_rule_notifications"]
            if notif.get("digest_frequency") == "weekly"
        ]

        if weekly_notifications:
            # Send digest email
            await _send_digest_email(user, weekly_notifications, "weekly")

            # Clear sent notifications
            user.metadata["pending_rule_notifications"] = [
                notif for notif in user.metadata["pending_rule_notifications"]
                if notif.get("digest_frequency") != "weekly"
            ]

            digests_sent += 1

    logger.info(f"Sent {digests_sent} weekly rule update digests")

    return {
        "digests_sent": digests_sent,
        "frequency": "weekly"
    }


async def _send_digest_email(
    user: User,
    notifications: List[Dict[str, Any]],
    frequency: str
) -> None:
    """
    Send digest email with multiple rule changes.

    Args:
        user: User to notify
        notifications: List of pending notifications
        frequency: "daily" or "weekly"
    """
    try:
        notification_service = AuthorityNotificationService()

        # Format digest content
        summary = f"You have {len(notifications)} rule update(s) from the past {frequency} period:\n\n"

        for notif in notifications:
            summary += f"- {notif['rule_code']}: {notif['rule_name']}\n"

        await notification_service.send_rule_update_digest(
            to_email=user.email,
            frequency=frequency,
            notification_count=len(notifications),
            summary=summary
        )

        logger.info(f"Sent {frequency} digest to {user.email} with {len(notifications)} notifications")

    except Exception as e:
        logger.error(f"Failed to send digest email: {str(e)}")
