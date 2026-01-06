"""
Email Service - Handles email notifications via SendGrid

For fatal deadline alerts and other critical notifications.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import SendGrid
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content, Personalization
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("SendGrid not installed. Email notifications disabled.")


class EmailService:
    """
    Email notification service using SendGrid.

    Handles sending critical alerts including:
    - Fatal deadline reminders
    - Overdue deadline alerts
    - Daily/weekly digest emails
    """

    def __init__(self):
        self.enabled = settings.EMAIL_ENABLED and SENDGRID_AVAILABLE
        self.client = None

        if self.enabled:
            try:
                self.client = SendGridAPIClient(settings.SENDGRID_API_KEY)
                logger.info("Email service initialized with SendGrid")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid client: {e}")
                self.enabled = False
        else:
            if not SENDGRID_AVAILABLE:
                logger.info("Email service disabled: SendGrid not installed")
            else:
                logger.info("Email service disabled: SENDGRID_API_KEY not configured")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Send a single email.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body
            plain_content: Plain text fallback (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug(f"Email not sent (disabled): {subject} -> {to_email}")
            return False

        try:
            message = Mail(
                from_email=Email(settings.EMAIL_FROM_ADDRESS, settings.EMAIL_FROM_NAME),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )

            if plain_content:
                message.add_content(Content("text/plain", plain_content))

            response = self.client.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully: {subject} -> {to_email}")
                return True
            else:
                logger.error(f"Email send failed with status {response.status_code}: {response.body}")
                return False

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_fatal_deadline_alert(
        self,
        to_email: str,
        user_name: str,
        deadline_title: str,
        deadline_date: str,
        days_until: int,
        case_number: str,
        case_title: str,
        action_url: str
    ) -> bool:
        """
        Send a fatal deadline alert email.

        This is a critical notification that bypasses quiet hours.
        """
        subject = f"FATAL DEADLINE ALERT: {deadline_title} - {days_until} day(s) remaining"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .alert-header {{ background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; padding: 24px; border-radius: 12px 12px 0 0; text-align: center; }}
                .alert-header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
                .alert-body {{ background: #fff; border: 1px solid #e2e8f0; border-top: none; padding: 24px; border-radius: 0 0 12px 12px; }}
                .deadline-info {{ background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 16px; margin: 16px 0; }}
                .deadline-info h2 {{ color: #dc2626; margin: 0 0 8px 0; font-size: 18px; }}
                .deadline-info p {{ margin: 4px 0; }}
                .case-info {{ background: #f8fafc; border-radius: 8px; padding: 16px; margin: 16px 0; }}
                .btn {{ display: inline-block; background: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; margin-top: 16px; }}
                .btn:hover {{ background: #b91c1c; }}
                .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="alert-header">
                    <h1>FATAL DEADLINE ALERT</h1>
                </div>
                <div class="alert-body">
                    <p>Hi {user_name},</p>
                    <p>This is a <strong>critical alert</strong> for a fatal deadline that requires immediate attention.</p>

                    <div class="deadline-info">
                        <h2>{deadline_title}</h2>
                        <p><strong>Due Date:</strong> {deadline_date}</p>
                        <p><strong>Time Remaining:</strong> {days_until} day(s)</p>
                    </div>

                    <div class="case-info">
                        <p><strong>Case:</strong> {case_number}</p>
                        <p><strong>Title:</strong> {case_title}</p>
                    </div>

                    <p>Missing this deadline could result in serious consequences including dismissal, default judgment, or malpractice liability.</p>

                    <center>
                        <a href="{action_url}" class="btn">View Deadline Details</a>
                    </center>

                    <div class="footer">
                        <p>This is an automated alert from LitDocket.<br>
                        You received this because you have fatal deadline email alerts enabled.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        plain_content = f"""
FATAL DEADLINE ALERT

Hi {user_name},

This is a critical alert for a fatal deadline that requires immediate attention.

DEADLINE: {deadline_title}
DUE DATE: {deadline_date}
TIME REMAINING: {days_until} day(s)

CASE: {case_number}
TITLE: {case_title}

Missing this deadline could result in serious consequences including dismissal, default judgment, or malpractice liability.

View details: {action_url}

---
This is an automated alert from LitDocket.
        """

        return await self.send_email(to_email, subject, html_content, plain_content)

    async def send_deadline_reminder(
        self,
        to_email: str,
        user_name: str,
        deadline_title: str,
        deadline_date: str,
        days_until: int,
        case_number: str,
        priority: str,
        action_url: str
    ) -> bool:
        """
        Send a standard deadline reminder email.
        """
        priority_color = "#f59e0b" if priority in ["urgent", "critical"] else "#3b82f6"
        priority_label = priority.upper() if priority else "STANDARD"

        subject = f"Deadline Reminder: {deadline_title} - {days_until} day(s) remaining"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: {priority_color}; color: white; padding: 20px; border-radius: 12px 12px 0 0; }}
                .header h1 {{ margin: 0; font-size: 20px; }}
                .body {{ background: #fff; border: 1px solid #e2e8f0; border-top: none; padding: 24px; border-radius: 0 0 12px 12px; }}
                .deadline-box {{ background: #f8fafc; border-radius: 8px; padding: 16px; margin: 16px 0; }}
                .badge {{ display: inline-block; background: {priority_color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
                .btn {{ display: inline-block; background: {priority_color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; margin-top: 16px; }}
                .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 24px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Deadline Reminder</h1>
                </div>
                <div class="body">
                    <p>Hi {user_name},</p>
                    <p>You have an upcoming deadline that needs your attention.</p>

                    <div class="deadline-box">
                        <span class="badge">{priority_label}</span>
                        <h3 style="margin: 12px 0 8px 0;">{deadline_title}</h3>
                        <p style="margin: 4px 0;"><strong>Due:</strong> {deadline_date} ({days_until} days)</p>
                        <p style="margin: 4px 0;"><strong>Case:</strong> {case_number}</p>
                    </div>

                    <center>
                        <a href="{action_url}" class="btn">View Details</a>
                    </center>

                    <div class="footer">
                        <p>This is an automated reminder from LitDocket.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(to_email, subject, html_content)

    async def send_daily_digest(
        self,
        to_email: str,
        user_name: str,
        deadlines: List[Dict[str, Any]],
        dashboard_url: str
    ) -> bool:
        """
        Send a daily digest email with upcoming deadlines.
        """
        if not deadlines:
            return True  # Nothing to send

        today = datetime.now().strftime("%B %d, %Y")
        subject = f"LitDocket Daily Digest - {today}"

        deadline_rows = ""
        for d in deadlines[:10]:  # Limit to 10 deadlines
            priority_color = "#dc2626" if d.get("priority") == "fatal" else (
                "#f59e0b" if d.get("priority") in ["urgent", "critical"] else "#3b82f6"
            )
            deadline_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">
                    <span style="display: inline-block; width: 8px; height: 8px; background: {priority_color}; border-radius: 50%; margin-right: 8px;"></span>
                    {d.get('title', 'Untitled')}
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">{d.get('case_number', 'N/A')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">{d.get('deadline_date', 'N/A')}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">{d.get('days_until', '?')} days</td>
            </tr>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; }}
                .container {{ max-width: 650px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 24px; border-radius: 12px 12px 0 0; }}
                .body {{ background: #fff; border: 1px solid #e2e8f0; border-top: none; padding: 24px; border-radius: 0 0 12px 12px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
                th {{ text-align: left; padding: 12px; background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 12px; text-transform: uppercase; color: #64748b; }}
                .btn {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; margin-top: 16px; }}
                .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 24px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">Daily Digest</h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9;">{today}</p>
                </div>
                <div class="body">
                    <p>Good morning {user_name},</p>
                    <p>Here's your daily overview of upcoming deadlines:</p>

                    <table>
                        <thead>
                            <tr>
                                <th>Deadline</th>
                                <th>Case</th>
                                <th>Due Date</th>
                                <th>Remaining</th>
                            </tr>
                        </thead>
                        <tbody>
                            {deadline_rows}
                        </tbody>
                    </table>

                    <center>
                        <a href="{dashboard_url}" class="btn">Open Dashboard</a>
                    </center>

                    <div class="footer">
                        <p>This is your daily digest from LitDocket.<br>
                        Manage your email preferences in Settings.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(to_email, subject, html_content)


# Singleton instance
email_service = EmailService()
