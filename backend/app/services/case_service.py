"""
Case Service - Business logic for case management operations

Extracted from cases.py router to follow single-responsibility principle.
Handles field-by-field updates with change tracking and audit logging.

Usage:
    service = CaseService(db)
    result = await service.update_case(case, update_data, current_user)
"""
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.user import User
from app.services.case_summary_service import CaseSummaryService

logger = logging.getLogger(__name__)


class CaseService:
    """
    Service for case management operations.

    Handles:
    - Field-by-field updates with change tracking
    - Audit trail logging
    - Summary service integration
    """

    def __init__(self, db: Session):
        self.db = db
        self.summary_service = CaseSummaryService()

    async def update_case(
        self,
        case: Case,
        update_data: Dict[str, Any],
        current_user: User
    ) -> Dict[str, Any]:
        """
        Update case fields with change tracking.

        This method implements field-by-field updates with:
        - Change tracking for audit trail
        - Detailed logging of modifications
        - Automatic summary service updates

        Args:
            case: The case to update
            update_data: Dictionary of fields to update (typically from CaseUpdate.model_dump)
            current_user: The authenticated user making the update

        Returns:
            Dict with success status, case_id, changes list, and message
        """
        case_id = str(case.id)
        changes: List[str] = []

        # Field-by-field update with change tracking
        if 'title' in update_data and update_data['title'] is not None:
            old_title = case.title
            case.title = update_data['title']
            changes.append(f"title: '{old_title}' -> '{update_data['title']}'")

        if 'court' in update_data and update_data['court'] is not None:
            old_court = case.court
            case.court = update_data['court']
            changes.append(f"court: '{old_court}' -> '{update_data['court']}'")

        if 'judge' in update_data and update_data['judge'] is not None:
            old_judge = case.judge
            case.judge = update_data['judge']
            changes.append(f"judge: '{old_judge}' -> '{update_data['judge']}'")

        if 'case_type' in update_data and update_data['case_type'] is not None:
            old_type = case.case_type
            case.case_type = update_data['case_type']
            changes.append(f"case_type: '{old_type}' -> '{update_data['case_type']}'")

        if 'jurisdiction' in update_data and update_data['jurisdiction'] is not None:
            old_jurisdiction = case.jurisdiction
            case.jurisdiction = update_data['jurisdiction']
            changes.append(f"jurisdiction: '{old_jurisdiction}' -> '{update_data['jurisdiction']}'")

        if 'district' in update_data and update_data['district'] is not None:
            case.district = update_data['district']
            changes.append("district updated")

        if 'circuit' in update_data and update_data['circuit'] is not None:
            case.circuit = update_data['circuit']
            changes.append("circuit updated")

        if 'parties' in update_data and update_data['parties'] is not None:
            case.parties = update_data['parties']
            changes.append(f"parties updated ({len(update_data['parties'])} parties)")

        if 'case_metadata' in update_data and update_data['case_metadata'] is not None:
            case.case_metadata = update_data['case_metadata']
            changes.append("case_metadata updated")

        if 'filing_date' in update_data and update_data['filing_date'] is not None:
            case.filing_date = update_data['filing_date']
            changes.append(f"filing_date: {update_data['filing_date']}")

        # Commit changes
        self.db.commit()
        self.db.refresh(case)

        # Log the changes
        if changes:
            logger.info(f"Case {case_id} updated by user {current_user.id}: {changes}")

        # Update case summary to reflect changes
        await self._update_summary_on_change(case_id, changes)

        return {
            'success': True,
            'case_id': case_id,
            'changes': changes,
            'message': "Case updated successfully"
        }

    async def _update_summary_on_change(
        self,
        case_id: str,
        changes: List[str]
    ) -> None:
        """
        Update case summary after changes.

        This is called internally after successful case update.
        Failures are logged but don't propagate to avoid breaking
        the main update flow.
        """
        if not changes:
            return

        try:
            await self.summary_service.update_summary_on_event(
                case_id=case_id,
                event_type="case_updated",
                event_details={
                    "changes": changes
                },
                db=self.db
            )
        except Exception as e:
            logger.warning(f"Failed to update case summary for {case_id}: {e}")

    def update_status(
        self,
        case: Case,
        new_status: str,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Update case status with validation.

        Valid statuses: active, pending, closed, archived

        Args:
            case: The case to update
            new_status: The new status value
            current_user: The authenticated user

        Returns:
            Dict with success status and case_id

        Raises:
            ValueError: If status is invalid
        """
        valid_statuses = ['active', 'pending', 'closed', 'archived']

        if new_status not in valid_statuses:
            raise ValueError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        old_status = case.status
        case.status = new_status
        self.db.commit()

        logger.info(
            f"Case {case.id} status changed by user {current_user.id}: "
            f"'{old_status}' -> '{new_status}'"
        )

        return {
            'success': True,
            'case_id': str(case.id),
            'old_status': old_status,
            'new_status': new_status
        }

    def add_note(
        self,
        case: Case,
        note_content: str,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Add a note to case metadata.

        Notes are stored in case_metadata['notes'] array.

        Args:
            case: The case to add note to
            note_content: The note text
            current_user: The authenticated user

        Returns:
            Dict with success status and note count
        """
        from datetime import datetime

        if not case.case_metadata:
            case.case_metadata = {}

        if 'notes' not in case.case_metadata:
            case.case_metadata['notes'] = []

        note = {
            'content': note_content,
            'author_id': str(current_user.id),
            'author_email': current_user.email,
            'created_at': datetime.utcnow().isoformat()
        }

        case.case_metadata['notes'].append(note)

        # Mark the dict as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(case, 'case_metadata')

        self.db.commit()

        logger.info(f"Note added to case {case.id} by user {current_user.id}")

        return {
            'success': True,
            'case_id': str(case.id),
            'note_count': len(case.case_metadata['notes'])
        }


# Convenience function for dependency injection
def get_case_service(db: Session) -> CaseService:
    """Get a CaseService instance for the given database session."""
    return CaseService(db)
