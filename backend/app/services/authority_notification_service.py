"""
Authority Core Email Notification Service

Dedicated email service for Authority Core automation events:
- Daily inbox digest for rule review
- Scraper failure alerts
- Watchtower change summaries
- Jurisdiction health reports

Extends the existing notification_service.py with Authority Core-specific templates.
Uses SendGrid API for email delivery.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app.config import settings

logger = logging.getLogger(__name__)


class AuthorityNotificationService:
    """
    Email notification service for Authority Core automation.
    Separate from main NotificationService to avoid conflicts.
    """

    def __init__(self):
        """Initialize SendGrid client."""
        self.client = None
        self.from_email = Email("authority-core@litdocket.com", "LitDocket Authority Core")

        # Only initialize SendGrid if API key is configured
        if hasattr(settings, 'SENDGRID_API_KEY') and settings.SENDGRID_API_KEY and settings.SENDGRID_API_KEY != "your_sendgrid_api_key":
            try:
                self.client = SendGridAPIClient(settings.SENDGRID_API_KEY)
                logger.info("SendGrid client initialized for Authority Core notifications")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid client: {str(e)}")
                self.client = None
        else:
            logger.warning("SendGrid API key not configured - Authority Core email notifications disabled")

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send email via SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.client:
            logger.warning(f"SendGrid not configured - skipping email to {to_email}: {subject}")
            return False

        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            response = self.client.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Authority Core email sent successfully to {to_email}: {subject}")
                return True
            else:
                logger.error(f"SendGrid error (status {response.status_code}) for {to_email}: {subject}")
                return False

        except Exception as e:
            logger.error(f"Failed to send Authority Core email to {to_email}: {str(e)}")
            return False

    async def send_inbox_daily_digest(
        self,
        user_email: str,
        pending_count: int,
        pending_items: List[Dict],
        user_timezone: str = "America/New_York"
    ) -> bool:
        """
        Send daily inbox digest summarizing pending review items.

        Args:
            user_email: Attorney email address
            pending_count: Number of pending inbox items
            pending_items: List of pending items with metadata
            user_timezone: User's timezone for scheduling (default: EST)

        Returns:
            bool: True if email sent successfully
        """
        if pending_count == 0:
            logger.info(f"No pending inbox items for {user_email} - skipping daily digest")
            return False

        # Build HTML email
        html_content = self._build_inbox_digest_html(pending_count, pending_items)

        subject = f"LitDocket Inbox: {pending_count} item{'s' if pending_count != 1 else ''} pending review"

        return self._send_email(user_email, subject, html_content)

    def _build_inbox_digest_html(self, pending_count: int, pending_items: List[Dict]) -> str:
        """Build HTML email for inbox daily digest."""
        items_html = ""

        for item in pending_items[:10]:  # Limit to 10 items in email
            item_type = item.get("type", "UNKNOWN")
            title = item.get("title", "Untitled Item")
            created_at = item.get("created_at", "")
            priority = item.get("priority", "medium")

            priority_color = {
                "high": "#DC2626",  # Red
                "medium": "#F59E0B",  # Amber
                "low": "#10B981"  # Green
            }.get(priority, "#6B7280")  # Default gray

            items_html += f"""
            <div style="border-left: 4px solid {priority_color}; padding: 12px; margin-bottom: 12px; background-color: #F9FAFB;">
                <div style="font-weight: 600; color: #111827; margin-bottom: 4px;">{title}</div>
                <div style="font-size: 14px; color: #6B7280;">Type: {item_type} • {created_at}</div>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #F3F4F6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <!-- Header -->
                <div style="background-color: #1E40AF; color: white; padding: 24px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: 600;">Daily Inbox Digest</h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9;">You have {pending_count} item{'s' if pending_count != 1 else ''} pending review</p>
                </div>

                <!-- Content -->
                <div style="padding: 24px;">
                    <p style="color: #374151; margin: 0 0 20px 0;">
                        Your LitDocket inbox has items requiring attorney review.
                    </p>

                    {items_html}

                    {f'<p style="color: #6B7280; font-size: 14px; margin-top: 16px;">...and {pending_count - 10} more items</p>' if pending_count > 10 else ''}

                    <!-- CTA Button -->
                    <div style="margin-top: 24px; text-align: center;">
                        <a href="https://frontend-five-azure-58.vercel.app/inbox" style="display: inline-block; background-color: #1E40AF; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">
                            Review Inbox →
                        </a>
                    </div>
                </div>

                <!-- Footer -->
                <div style="background-color: #F9FAFB; padding: 16px; border-radius: 0 0 8px 8px; text-align: center; color: #6B7280; font-size: 14px;">
                    <p style="margin: 0;">LitDocket • AI-Powered Legal Docketing</p>
                    <p style="margin: 8px 0 0 0;">
                        <a href="https://frontend-five-azure-58.vercel.app/settings" style="color: #1E40AF; text-decoration: none;">Manage notification preferences</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    async def send_scraper_failure_alert(
        self,
        admin_email: str,
        jurisdiction_name: str,
        jurisdiction_id: str,
        error_message: str,
        consecutive_failures: int
    ) -> bool:
        """
        Send alert when scraper fails for a jurisdiction.

        Args:
            admin_email: Administrator email address
            jurisdiction_name: Name of affected jurisdiction
            jurisdiction_id: Jurisdiction UUID
            error_message: Error details
            consecutive_failures: Number of consecutive failures

        Returns:
            bool: True if email sent successfully
        """
        severity = "CRITICAL" if consecutive_failures >= 3 else "WARNING"
        color = "#DC2626" if consecutive_failures >= 3 else "#F59E0B"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #F3F4F6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="background-color: {color}; color: white; padding: 24px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: 600;">🚨 Scraper Failure Alert</h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9;">{severity}</p>
                </div>

                <div style="padding: 24px;">
                    <div style="background-color: #FEF2F2; border-left: 4px solid {color}; padding: 16px; margin-bottom: 20px;">
                        <h2 style="margin: 0 0 8px 0; font-size: 18px; color: #111827;">{jurisdiction_name}</h2>
                        <p style="margin: 0; color: #374151;">Consecutive failures: {consecutive_failures}</p>
                    </div>

                    <h3 style="color: #111827; font-size: 16px; margin: 16px 0 8px 0;">Error Details:</h3>
                    <pre style="background-color: #F9FAFB; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 13px; color: #374151; white-space: pre-wrap; word-wrap: break-word;">{error_message}</pre>

                    {f'<div style="background-color: #FEE2E2; border: 1px solid #FCA5A5; padding: 12px; border-radius: 4px; margin-top: 16px;"><strong>⚠️ Auto-Disable Warning:</strong> This jurisdiction will be automatically disabled if failures continue.</div>' if consecutive_failures >= 2 else ''}

                    <div style="margin-top: 24px; text-align: center;">
                        <a href="https://litdocket-production.up.railway.app/api/v1/authority-core/scraper-health/check/{jurisdiction_id}" style="display: inline-block; background-color: #1E40AF; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; margin-right: 8px;">
                            Run Health Check
                        </a>
                        <a href="https://frontend-five-azure-58.vercel.app/admin/scraper-health" style="display: inline-block; background-color: #6B7280; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">
                            View Dashboard
                        </a>
                    </div>
                </div>

                <div style="background-color: #F9FAFB; padding: 16px; border-radius: 0 0 8px 8px; text-align: center; color: #6B7280; font-size: 14px;">
                    <p style="margin: 0;">LitDocket Authority Core • Automated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        subject = f"[{severity}] Scraper Failure: {jurisdiction_name} ({consecutive_failures} failures)"

        return self._send_email(admin_email, subject, html_content)

    async def send_watchtower_change_summary(
        self,
        admin_email: str,
        jurisdiction_name: str,
        changed_urls: List[Dict],
        total_urls_checked: int
    ) -> bool:
        """
        Send summary when Watchtower detects rule changes.

        Args:
            admin_email: Administrator email address
            jurisdiction_name: Name of affected jurisdiction
            changed_urls: List of URLs with detected changes
            total_urls_checked: Total URLs monitored

        Returns:
            bool: True if email sent successfully
        """
        changes_html = ""
        for url_change in changed_urls[:10]:  # Limit to 10 URLs
            url = url_change.get("url", "Unknown URL")
            changes_html += f"""
            <div style="background-color: #F9FAFB; padding: 12px; margin-bottom: 8px; border-radius: 4px;">
                <div style="font-size: 14px; color: #374151; word-break: break-all;">{url}</div>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #F3F4F6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="background-color: #7C3AED; color: white; padding: 24px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: 600;">👁️ Rule Changes Detected</h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9;">Watchtower Alert</p>
                </div>

                <div style="padding: 24px;">
                    <div style="background-color: #EDE9FE; border-left: 4px solid #7C3AED; padding: 16px; margin-bottom: 20px;">
                        <h2 style="margin: 0 0 8px 0; font-size: 18px; color: #111827;">{jurisdiction_name}</h2>
                        <p style="margin: 0; color: #374151;">{len(changed_urls)} of {total_urls_checked} monitored URLs changed</p>
                    </div>

                    <h3 style="color: #111827; font-size: 16px; margin: 16px 0 8px 0;">Changed URLs:</h3>
                    {changes_html}

                    {f'<p style="color: #6B7280; font-size: 14px; margin-top: 12px;">...and {len(changed_urls) - 10} more URLs</p>' if len(changed_urls) > 10 else ''}

                    <div style="background-color: #FEF3C7; border: 1px solid #FCD34D; padding: 12px; border-radius: 4px; margin-top: 16px;">
                        <strong>⚠️ Action Required:</strong> Review changes in inbox to verify rule updates are reflected in Authority Core.
                    </div>

                    <div style="margin-top: 24px; text-align: center;">
                        <a href="https://frontend-five-azure-58.vercel.app/inbox?type=WATCHTOWER_CHANGE" style="display: inline-block; background-color: #7C3AED; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">
                            Review Changes in Inbox →
                        </a>
                    </div>
                </div>

                <div style="background-color: #F9FAFB; padding: 16px; border-radius: 0 0 8px 8px; text-align: center; color: #6B7280; font-size: 14px;">
                    <p style="margin: 0;">Detected at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        subject = f"Watchtower: {len(changed_urls)} rule changes detected in {jurisdiction_name}"

        return self._send_email(admin_email, subject, html_content)

    async def send_scraper_health_alert(
        self,
        unhealthy_count: int,
        disabled_count: int,
        admin_email: str = "admin@litdocket.com"
    ) -> bool:
        """
        Send daily scraper health summary.

        Args:
            unhealthy_count: Number of unhealthy scrapers
            disabled_count: Number of auto-disabled scrapers
            admin_email: Administrator email address

        Returns:
            bool: True if email sent successfully
        """
        if unhealthy_count == 0 and disabled_count == 0:
            logger.info("All scrapers healthy - skipping health alert email")
            return False

        severity_color = "#DC2626" if disabled_count > 0 else "#F59E0B"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #F3F4F6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="background-color: {severity_color}; color: white; padding: 24px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px; font-weight: 600;">📊 Daily Scraper Health Report</h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9;">Authority Core Monitoring</p>
                </div>

                <div style="padding: 24px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
                        <div style="background-color: #FEF2F2; padding: 16px; border-radius: 4px; text-align: center;">
                            <div style="font-size: 32px; font-weight: 700; color: #DC2626;">{unhealthy_count}</div>
                            <div style="color: #374151; font-size: 14px;">Unhealthy Scrapers</div>
                        </div>
                        <div style="background-color: #FEE2E2; padding: 16px; border-radius: 4px; text-align: center;">
                            <div style="font-size: 32px; font-weight: 700; color: #991B1B;">{disabled_count}</div>
                            <div style="color: #374151; font-size: 14px;">Auto-Disabled</div>
                        </div>
                    </div>

                    {f'<div style="background-color: #FEE2E2; border: 1px solid #FCA5A5; padding: 12px; border-radius: 4px; margin-bottom: 16px;"><strong>⚠️ Critical:</strong> {disabled_count} jurisdiction(s) have been automatically disabled due to consecutive failures.</div>' if disabled_count > 0 else ''}

                    <p style="color: #374151; margin: 16px 0;">
                        Action required to restore full Authority Core coverage.
                    </p>

                    <div style="margin-top: 24px; text-align: center;">
                        <a href="https://frontend-five-azure-58.vercel.app/admin/scraper-health" style="display: inline-block; background-color: #1E40AF; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">
                            View Full Health Report →
                        </a>
                    </div>
                </div>

                <div style="background-color: #F9FAFB; padding: 16px; border-radius: 0 0 8px 8px; text-align: center; color: #6B7280; font-size: 14px;">
                    <p style="margin: 0;">Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        subject = f"[Alert] Scraper Health: {unhealthy_count} unhealthy, {disabled_count} disabled"

        return self._send_email(admin_email, subject, html_content)
