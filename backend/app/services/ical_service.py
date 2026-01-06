"""
iCal Service - Generate .ics files for calendar export
Allows users to export deadlines to Outlook, Google Calendar, Apple Calendar, etc.
"""
from typing import List
from datetime import datetime, timezone
from app.models.deadline import Deadline


class ICalService:
    """Service for generating iCal (.ics) calendar files"""

    def generate_ics_file(self, deadlines: List[Deadline], case_number: str = None) -> str:
        """
        Generate an iCal (.ics) file from deadlines

        Args:
            deadlines: List of Deadline objects
            case_number: Optional case number to include in calendar name

        Returns:
            String content of .ics file
        """

        # Start iCal file
        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Florida Legal Docketing Assistant//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            f"X-WR-CALNAME:Legal Deadlines{f' - {case_number}' if case_number else ''}",
            "X-WR-TIMEZONE:America/New_York",
            "X-WR-CALDESC:Deadlines from Florida Legal Docketing Assistant"
        ]

        # Add each deadline as an event
        for deadline in deadlines:
            if not deadline.deadline_date:
                continue  # Skip deadlines without dates

            event_lines = self._create_event(deadline)
            ics_lines.extend(event_lines)

        # End iCal file
        ics_lines.append("END:VCALENDAR")

        return "\r\n".join(ics_lines)

    def _create_event(self, deadline: Deadline) -> List[str]:
        """
        Create an iCal event (VEVENT) from a deadline

        Returns:
            List of iCal lines for this event
        """

        # Generate unique ID
        event_id = f"{deadline.id}@docketassist.com"

        # Format date (all-day event)
        # iCal format: YYYYMMDD
        date_str = deadline.deadline_date.strftime("%Y%m%d")

        # Generate timestamp for DTSTAMP (when this entry was created)
        now = datetime.now(timezone.utc)
        dtstamp = now.strftime("%Y%m%dT%H%M%SZ")

        # Build title
        title = deadline.title

        # Build description
        description_parts = []

        if deadline.description:
            description_parts.append(deadline.description)

        if deadline.applicable_rule:
            description_parts.append(f"\\n\\nApplicable Rule: {deadline.applicable_rule}")

        if deadline.party_role:
            description_parts.append(f"\\nParty: {deadline.party_role}")

        if deadline.action_required:
            description_parts.append(f"\\nAction Required: {deadline.action_required}")

        description = "".join(description_parts).replace('\n', '\\n')

        # Build categories based on priority
        categories = []
        if deadline.priority:
            categories.append(deadline.priority.upper())
        if deadline.deadline_type:
            categories.append(deadline.deadline_type.replace('_', ' ').title())

        # Set priority (1=high, 5=medium, 9=low)
        ical_priority = "5"  # default medium
        if deadline.priority in ['fatal', 'critical', 'high']:
            ical_priority = "1"
        elif deadline.priority in ['informational', 'low']:
            ical_priority = "9"

        # Build alarm/reminder (remind 3 days before for critical, 1 day for others)
        alarm_days = 3 if deadline.priority in ['fatal', 'critical', 'high'] else 1

        event_lines = [
            "BEGIN:VEVENT",
            f"UID:{event_id}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;VALUE=DATE:{date_str}",
            f"SUMMARY:{self._escape_text(title)}",
            f"DESCRIPTION:{self._escape_text(description)}",
            f"PRIORITY:{ical_priority}",
            f"STATUS:{self._get_status(deadline.status)}",
        ]

        if categories:
            event_lines.append(f"CATEGORIES:{','.join(categories)}")

        # Add alarm/reminder
        event_lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:-P{alarm_days}D",  # Trigger N days before
            "ACTION:DISPLAY",
            f"DESCRIPTION:Reminder: {self._escape_text(title)}",
            "END:VALARM"
        ])

        event_lines.append("END:VEVENT")

        return event_lines

    def _escape_text(self, text: str) -> str:
        """Escape special characters for iCal format"""
        if not text:
            return ""

        # Replace special characters
        text = text.replace("\\", "\\\\")  # Backslash first
        text = text.replace(",", "\\,")
        text = text.replace(";", "\\;")
        text = text.replace("\n", "\\n")

        # Limit length to avoid issues
        if len(text) > 1000:
            text = text[:997] + "..."

        return text

    def _get_status(self, status: str) -> str:
        """Convert deadline status to iCal status"""
        status_map = {
            'pending': 'CONFIRMED',
            'completed': 'COMPLETED',
            'cancelled': 'CANCELLED'
        }
        return status_map.get(status, 'TENTATIVE')


# Singleton instance
ical_service = ICalService()
