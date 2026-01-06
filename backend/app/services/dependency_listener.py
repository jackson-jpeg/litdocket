"""
Dependency Listener - Advanced Dependency Tracking
Detects when parent (trigger) deadlines change and cascades updates to dependent deadlines

When a trigger changes, all dependent deadlines automatically update
EXCEPT those that were manually overridden by the user.
"""
from typing import Dict, List, Optional
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session

from app.models.deadline import Deadline
from app.models.user import User
from app.utils.florida_holidays import adjust_to_business_day


class DependencyListener:
    """
    Advanced dependency tracking
    Listens for parent deadline changes and cascades updates to children
    """

    def __init__(self, db: Session):
        self.db = db

    def detect_parent_change(
        self,
        parent_deadline_id: str,
        old_date: date,
        new_date: date
    ) -> Dict:
        """
        Detect when a parent (trigger) deadline changes and preview cascade impact

        Args:
            parent_deadline_id: ID of the parent deadline that changed
            old_date: Original date
            new_date: New date

        Returns:
            {
                'is_parent': bool,
                'has_dependents': bool,
                'affected_count': int,
                'overridden_count': int,
                'changes_preview': List[Dict],
                'skipped_deadlines': List[Dict]
            }
        """

        # Find all child deadlines
        dependents = self.db.query(Deadline).filter(
            Deadline.parent_deadline_id == parent_deadline_id
        ).all()

        if not dependents:
            return {
                'is_parent': False,
                'has_dependents': False,
                'affected_count': 0,
                'overridden_count': 0,
                'changes_preview': [],
                'skipped_deadlines': []
            }

        # Calculate date shift
        days_shift = (new_date - old_date).days

        affected = []
        skipped = []

        for child in dependents:
            # PHASE 1 INTEGRATION: Skip manually overridden deadlines!
            if child.is_manually_overridden or not child.auto_recalculate:
                skipped.append({
                    'id': str(child.id),
                    'title': child.title,
                    'current_date': child.deadline_date.isoformat() if child.deadline_date else None,
                    'reason': 'manually_overridden',
                    'override_date': child.override_timestamp.isoformat() if child.override_timestamp else None,
                    'override_reason': child.override_reason
                })
                continue

            # Calculate new date for this child
            if child.deadline_date:
                new_child_date = child.deadline_date + timedelta(days=days_shift)

                # Adjust for business days (weekends/holidays)
                new_child_date = adjust_to_business_day(new_child_date)

                affected.append({
                    'id': str(child.id),
                    'title': child.title,
                    'old_date': child.deadline_date.isoformat(),
                    'new_date': new_child_date.isoformat(),
                    'days_shifted': days_shift,
                    'priority': child.priority,
                    'status': child.status
                })

        return {
            'is_parent': True,
            'has_dependents': True,
            'total_dependents': len(dependents),
            'affected_count': len(affected),
            'overridden_count': len(skipped),
            'days_shift': days_shift,
            'parent_old_date': old_date.isoformat(),
            'parent_new_date': new_date.isoformat(),
            'changes_preview': affected,
            'skipped_deadlines': skipped
        }

    def apply_cascade_update(
        self,
        parent_deadline_id: str,
        new_date: date,
        user_id: str,
        reason: str = "Cascade update from parent trigger change"
    ) -> Dict:
        """
        Apply cascade updates to all dependent deadlines

        This is the actual execution - call this after user approves the preview

        Args:
            parent_deadline_id: ID of parent deadline
            new_date: New date for the parent
            user_id: User making the change
            reason: Reason for cascade

        Returns:
            {
                'success': bool,
                'updated_count': int,
                'skipped_count': int,
                'updated_deadlines': List[str]
            }
        """

        # Get the parent deadline
        parent = self.db.query(Deadline).filter(Deadline.id == parent_deadline_id).first()
        if not parent:
            return {
                'success': False,
                'error': 'Parent deadline not found'
            }

        old_date = parent.deadline_date
        days_shift = (new_date - old_date).days

        # Update parent first
        parent.deadline_date = new_date
        parent.modified_by = user_id
        parent.modification_reason = reason

        # Find all dependents
        dependents = self.db.query(Deadline).filter(
            Deadline.parent_deadline_id == parent_deadline_id
        ).all()

        updated_deadlines = []
        skipped_count = 0

        for child in dependents:
            # PHASE 1 PROTECTION: Skip overridden deadlines
            if child.is_manually_overridden or not child.auto_recalculate:
                skipped_count += 1
                continue

            # Calculate new date
            if child.deadline_date:
                new_child_date = child.deadline_date + timedelta(days=days_shift)
                new_child_date = adjust_to_business_day(new_child_date)

                # Update the child
                child.deadline_date = new_child_date
                child.modified_by = user_id
                child.modification_reason = f"Auto-updated: parent trigger moved by {days_shift} days"

                # Update trigger_date as well since it's dependent
                if child.trigger_date:
                    child.trigger_date = new_date

                updated_deadlines.append({
                    'id': str(child.id),
                    'title': child.title,
                    'new_date': new_child_date.isoformat()
                })

        # Commit all changes
        self.db.commit()

        return {
            'success': True,
            'updated_count': len(updated_deadlines),
            'skipped_count': skipped_count,
            'updated_deadlines': updated_deadlines,
            'message': f"✓ Updated parent and {len(updated_deadlines)} dependent deadline(s). {skipped_count} manually overridden deadline(s) were protected and not changed."
        }

    def get_dependency_tree(self, case_id: str) -> Dict:
        """
        Get the full dependency tree for a case
        Shows which deadlines are parents and which are children

        Useful for visualization and understanding relationships

        Returns:
            {
                'triggers': List[parent deadlines with their children],
                'total_triggers': int,
                'total_dependents': int
            }
        """

        # Find all parent (trigger) deadlines
        parents = self.db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.is_calculated == False,
            Deadline.is_dependent == False
        ).all()

        triggers = []

        for parent in parents:
            # Find children of this parent
            children = self.db.query(Deadline).filter(
                Deadline.parent_deadline_id == str(parent.id)
            ).all()

            triggers.append({
                'trigger_id': str(parent.id),
                'trigger_title': parent.title,
                'trigger_date': parent.deadline_date.isoformat() if parent.deadline_date else None,
                'trigger_event': parent.trigger_event,
                'dependents_count': len(children),
                'dependents': [
                    {
                        'id': str(child.id),
                        'title': child.title,
                        'date': child.deadline_date.isoformat() if child.deadline_date else None,
                        'priority': child.priority,
                        'is_overridden': child.is_manually_overridden,
                        'auto_recalculate': child.auto_recalculate
                    }
                    for child in children
                ]
            })

        total_dependents = sum(t['dependents_count'] for t in triggers)

        return {
            'triggers': triggers,
            'total_triggers': len(triggers),
            'total_dependents': total_dependents
        }

    def check_if_parent(self, deadline_id: str) -> bool:
        """Check if a deadline has any dependents (i.e., is a parent)"""
        count = self.db.query(Deadline).filter(
            Deadline.parent_deadline_id == deadline_id
        ).count()
        return count > 0

    def get_dependents(self, parent_deadline_id: str) -> List[Deadline]:
        """Get all dependent deadlines for a parent"""
        return self.db.query(Deadline).filter(
            Deadline.parent_deadline_id == parent_deadline_id
        ).all()
