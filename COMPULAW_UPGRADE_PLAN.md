# 🎯 CompuLaw-Level Deadline Engine Upgrade Plan

## Current State Analysis

### ✅ What You Already Have (Strong Foundation!)
1. **Trigger & Chain Architecture** - parent_deadline_id, is_dependent, is_calculated ✅
2. **Rule Engine** - 13+ rule templates with dependent deadlines ✅
3. **Holiday Calendar** - Florida + Federal holidays with Easter calculation ✅
4. **Business Day Adjustment** - adjust_to_business_day() function ✅
5. **Service Method Logic** - +5 days for mail, +0 for email ✅
6. **Audit Trail Fields** - original_deadline_date, modified_by, modification_reason ✅
7. **Deadline History** - DeadlineHistory relationship exists ✅
8. **Auto-Recalculate Flag** - auto_recalculate boolean ✅

### ❌ What's Missing (CompuLaw Features)
1. **IsOverridden Flag** - Manual changes should prevent auto-recalculation ❌
2. **Dependency Listener** - Cascade updates when parent trigger changes ❌
3. **Court Days Calculator** - Real court_days calculation (not just calendar_days) ❌
4. **Recalculation Prompt** - "Parent changed, recalculate children?" ❌
5. **Document-to-Deadline Linking** - Many-to-many relationship ❌
6. **Tickler System** - Automated reminders (30, 15, 7, 1 day before) ❌
7. **Batch Event Operations** - Bulk deadline management ❌
8. **Audit Trail UI** - "Who changed what when" visibility ❌
9. **Local Rule Override** - Circuit-specific modifications ❌
10. **Deadline Conflicts** - Detect overlapping deadlines ❌

---

## Implementation Plan - 7 Phases

### **Phase 1: IsOverridden Flag & Manual Change Tracking** (Week 1)

#### Problem Statement
When a user manually changes a calculated deadline, the system should:
1. Mark it as "overridden"
2. NOT recalculate it when the parent trigger changes
3. Show a visual indicator in the UI that it was manually changed

#### Implementation

**A. Database Changes**

Add to `Deadline` model:
```python
# Manual override tracking
is_manually_overridden = Column(Boolean, default=False)
override_timestamp = Column(DateTime(timezone=True))
override_user_id = Column(String(36), ForeignKey("users.id"))
override_reason = Column(Text)  # Why was this manually changed?
```

**B. Business Logic**

Update `/backend/app/services/deadline_service.py`:
```python
def update_deadline(deadline_id: str, new_date: date, user_id: str, reason: str = None):
    """Update a deadline and mark as manually overridden if calculated"""
    deadline = db.query(Deadline).get(deadline_id)

    # If this was an auto-calculated deadline, mark as overridden
    if deadline.is_calculated and not deadline.is_manually_overridden:
        deadline.is_manually_overridden = True
        deadline.override_timestamp = datetime.now()
        deadline.override_user_id = user_id
        deadline.override_reason = reason
        deadline.auto_recalculate = False  # Stop auto-recalc

    # Save original if first change
    if not deadline.original_deadline_date:
        deadline.original_deadline_date = deadline.deadline_date

    deadline.deadline_date = new_date
    deadline.modified_by = user_id
    db.commit()
```

**C. UI Indicators**

Frontend: Show override indicator
```tsx
{deadline.is_manually_overridden && (
  <Badge color="orange">
    <Edit2 size={12} />
    Manually Changed
  </Badge>
)}
```

**D. Chatbot Integration**

Update chat tools to respect override flag:
```python
# In create_trigger_deadline tool
if deadline.is_manually_overridden:
    # Skip this deadline from recalculation
    continue
```

---

### **Phase 2: Dependency Listener & Cascade Updates** (Week 1-2)

#### Problem Statement
When a **parent trigger changes** (e.g., trial date moved), all **dependent deadlines** should:
1. Detect the change
2. Prompt user: "Recalculate all dependent deadlines?"
3. If YES: Recalculate all (except manually overridden ones)
4. If NO: Leave them as-is

#### Implementation

**A. Create Dependency Listener Service**

`/backend/app/services/dependency_listener.py`:
```python
class DependencyListener:
    """
    CompuLaw-inspired dependency tracking
    Listens for parent deadline changes and cascades updates
    """

    def on_parent_deadline_changed(
        self,
        parent_deadline_id: str,
        old_date: date,
        new_date: date,
        db: Session
    ) -> Dict:
        """
        Called when a parent (trigger) deadline changes

        Returns:
            {
                'affected_deadlines': int,
                'overridden_skipped': int,
                'changes_preview': List[Dict]
            }
        """

        # Find all child deadlines
        children = db.query(Deadline).filter(
            Deadline.parent_deadline_id == parent_deadline_id
        ).all()

        affected = []
        skipped = []

        for child in children:
            # Skip manually overridden deadlines
            if child.is_manually_overridden or not child.auto_recalculate:
                skipped.append({
                    'id': str(child.id),
                    'title': child.title,
                    'reason': 'manually_overridden'
                })
                continue

            # Calculate date shift
            days_diff = (new_date - old_date).days
            new_child_date = child.deadline_date + timedelta(days=days_diff)

            # Adjust for business days
            from app.utils.florida_holidays import adjust_to_business_day
            new_child_date = adjust_to_business_day(new_child_date)

            affected.append({
                'id': str(child.id),
                'title': child.title,
                'old_date': child.deadline_date.isoformat(),
                'new_date': new_child_date.isoformat(),
                'days_shifted': days_diff
            })

        return {
            'affected_deadlines': len(affected),
            'overridden_skipped': len(skipped),
            'changes_preview': affected,
            'skipped_deadlines': skipped
        }

    def apply_cascade_update(
        self,
        changes: List[Dict],
        user_id: str,
        db: Session
    ):
        """Apply the cascade updates to all affected deadlines"""
        for change in changes:
            deadline = db.query(Deadline).get(change['id'])
            deadline.deadline_date = datetime.strptime(change['new_date'], '%Y-%m-%d').date()
            deadline.modified_by = user_id
            deadline.modification_reason = f"Cascade update from parent trigger change"

        db.commit()
```

**B. Update Deadline Service**

Modify `update_deadline` to call dependency listener:
```python
def update_deadline(deadline_id: str, new_date: date, user_id: str):
    deadline = db.query(Deadline).get(deadline_id)
    old_date = deadline.deadline_date

    # Check if this is a parent (trigger) deadline
    is_parent = db.query(Deadline).filter(
        Deadline.parent_deadline_id == deadline_id
    ).count() > 0

    if is_parent:
        # Get preview of cascade changes
        listener = DependencyListener()
        preview = listener.on_parent_deadline_changed(
            deadline_id, old_date, new_date, db
        )

        return {
            'success': True,
            'requires_cascade_confirmation': True,
            'cascade_preview': preview
        }

    # Normal update
    deadline.deadline_date = new_date
    db.commit()

    return {'success': True}
```

**C. Chatbot Tool**

Add new tool: `cascade_update_deadlines`
```python
{
    "name": "cascade_update_deadlines",
    "description": "When a parent trigger deadline changes, cascade the update to all dependent deadlines (except manually overridden ones).",
    "input_schema": {
        "type": "object",
        "properties": {
            "parent_deadline_id": {"type": "string"},
            "new_date": {"type": "string"},
            "apply_changes": {"type": "boolean", "description": "Whether to apply or just preview"}
        }
    }
}
```

**D. Frontend UI**

Add confirmation dialog:
```tsx
if (updateResult.requires_cascade_confirmation) {
  const preview = updateResult.cascade_preview;

  showDialog({
    title: "Recalculate Dependent Deadlines?",
    message: `The trigger date has changed. This will affect ${preview.affected_deadlines} deadline(s).`,
    preview: preview.changes_preview,
    actions: [
      { label: "Recalculate All", onClick: () => applyCascade() },
      { label: "Skip", onClick: () => skipCascade() }
    ]
  });
}
```

---

### **Phase 3: Court Days Calculator** (Week 2)

#### Problem Statement
"30 court days" ≠ "30 calendar days"
- Court days = business days (excluding weekends + holidays)
- Many Florida rules use "court days" not "calendar days"

#### Implementation

**A. Add Court Days Calculator**

`/backend/app/utils/florida_holidays.py`:
```python
def add_court_days(start_date: date, num_days: int) -> date:
    """
    Add a specific number of COURT days (business days)

    Args:
        start_date: Starting date
        num_days: Number of court days to add

    Returns:
        Final date after adding N court days

    Example:
        add_court_days(date(2025, 7, 1), 30)
        # Skips weekends, July 4th, etc.
    """
    current = start_date
    days_added = 0

    while days_added < num_days:
        current += timedelta(days=1)
        if is_business_day(current):
            days_added += 1

    return current


def subtract_court_days(start_date: date, num_days: int) -> date:
    """Subtract court days (go backwards)"""
    current = start_date
    days_subtracted = 0

    while days_subtracted < num_days:
        current -= timedelta(days=1)
        if is_business_day(current):
            days_subtracted += 1

    return current
```

**B. Update Rules Engine**

Modify `calculate_dependent_deadlines` to use court days:
```python
# In calculate_dependent_deadlines method

if dependent.calculation_method == "court_days":
    if dependent.days_from_trigger > 0:
        base_date = add_court_days(trigger_date, abs(dependent.days_from_trigger))
    else:
        base_date = subtract_court_days(trigger_date, abs(dependent.days_from_trigger))
elif dependent.calculation_method == "calendar_days":
    base_date = trigger_date + timedelta(days=dependent.days_from_trigger)
elif dependent.calculation_method == "business_days":
    # Alias for court_days
    base_date = add_court_days(trigger_date, abs(dependent.days_from_trigger))
```

**C. Update Rule Templates**

Change applicable rules to use `court_days`:
```python
DependentDeadline(
    name="Motion for Summary Judgment",
    days_from_trigger=-75,
    calculation_method="court_days",  # Changed from calendar_days
    ...
)
```

---

### **Phase 4: Document-to-Deadline Linking** (Week 2-3)

#### Problem Statement
"Which deadlines are related to this Motion for Summary Judgment?"
Need many-to-many relationship: Document ↔ Deadline

#### Implementation

**A. Database Changes**

Create junction table:
```python
# /backend/app/models/document_deadline_link.py

class DocumentDeadlineLink(Base):
    __tablename__ = "document_deadline_links"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"))
    deadline_id = Column(String(36), ForeignKey("deadlines.id", ondelete="CASCADE"))
    link_type = Column(String(50))  # "generated_by", "relates_to", "satisfies"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(36), ForeignKey("users.id"))

    # Relationships
    document = relationship("Document", back_populates="deadline_links")
    deadline = relationship("Deadline", back_populates="document_links")
```

Update `Deadline` model:
```python
# Add to Deadline model
document_links = relationship("DocumentDeadlineLink", back_populates="deadline")
```

Update `Document` model:
```python
# Add to Document model
deadline_links = relationship("DocumentDeadlineLink", back_populates="document")
```

**B. Chatbot Tool**

Add tool to link documents:
```python
{
    "name": "link_document_to_deadline",
    "description": "Link a document to a deadline (e.g., 'Motion.pdf' relates to 'MSJ Deadline')",
    "input_schema": {
        "type": "object",
        "properties": {
            "document_id": {"type": "string"},
            "deadline_id": {"type": "string"},
            "link_type": {
                "type": "string",
                "enum": ["generated_by", "relates_to", "satisfies"]
            }
        }
    }
}
```

**C. Auto-Linking on Document Upload**

When user uploads "Notice of Deposition.pdf", AI should:
1. Analyze document type
2. Search for related deadlines (by title keywords)
3. Suggest linking: "This notice relates to 'Deposition Deadline'. Link them?"

---

### **Phase 5: Tickler System (Automated Reminders)** (Week 3)

#### Problem Statement
CompuLaw sends automated reminders: 30, 15, 7, 1 day before deadlines
Need background job scheduler

#### Implementation

**A. Database Changes**

Add reminder tracking:
```python
# Add to Deadline model
reminder_schedule = Column(JSON, default=lambda: [30, 15, 7, 1])  # Days before
reminders_sent = Column(JSON, default=list)  # [{date: "2025-06-01", days_out: 7}]
```

**B. Background Job (Celery)**

`/backend/app/tasks/reminder_tasks.py`:
```python
from celery import Celery
from datetime import date, timedelta

@celery_app.task
def send_deadline_reminders():
    """
    Run daily - check all pending deadlines and send reminders
    """
    today = date.today()

    # Get all pending deadlines
    deadlines = db.query(Deadline).filter(
        Deadline.status == 'pending',
        Deadline.deadline_date.isnot(None)
    ).all()

    for deadline in deadlines:
        days_until = (deadline.deadline_date - today).days

        # Check if this is a reminder day
        if days_until in deadline.reminder_schedule:
            # Check if we already sent this reminder
            already_sent = any(
                r['days_out'] == days_until
                for r in (deadline.reminders_sent or [])
            )

            if not already_sent:
                # Send email/notification
                send_email_reminder(deadline, days_until)

                # Mark as sent
                if not deadline.reminders_sent:
                    deadline.reminders_sent = []
                deadline.reminders_sent.append({
                    'date': today.isoformat(),
                    'days_out': days_until
                })
                db.commit()


def send_email_reminder(deadline: Deadline, days_out: int):
    """Send email to user"""
    from app.services.email_service import send_email

    subject = f"⚠️ Deadline in {days_out} days: {deadline.title}"
    body = f"""
    Upcoming Deadline Alert

    Case: {deadline.case.case_number}
    Deadline: {deadline.title}
    Due Date: {deadline.deadline_date}
    Days Remaining: {days_out}
    Priority: {deadline.priority}

    Action Required: {deadline.action_required}
    """

    send_email(deadline.user.email, subject, body)
```

**C. Celery Beat Scheduler**

`/backend/celerybeat-schedule.py`:
```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'send-deadline-reminders-daily': {
        'task': 'app.tasks.reminder_tasks.send_deadline_reminders',
        'schedule': crontab(hour=8, minute=0),  # 8 AM daily
    },
}
```

**D. User Preferences**

Allow users to customize reminder schedule:
```python
# In User model
notification_preferences = Column(JSON, default={
    'email_enabled': True,
    'reminder_days': [30, 15, 7, 1],
    'reminder_time': '08:00',
    'digest_frequency': 'daily'  # daily, weekly, never
})
```

---

### **Phase 6: Audit Trail UI & History** (Week 3-4)

#### Problem Statement
Lawyers need to know: "Who changed this date and why?"
Full audit trail with UI visibility

#### Implementation

**A. Deadline History API**

`/backend/app/api/v1/deadlines.py`:
```python
@router.get("/{deadline_id}/history")
async def get_deadline_history(deadline_id: str, db: Session = Depends(get_db)):
    """Get full change history for a deadline"""
    history = db.query(DeadlineHistory).filter(
        DeadlineHistory.deadline_id == deadline_id
    ).order_by(DeadlineHistory.created_at.desc()).all()

    return [
        {
            'id': str(h.id),
            'change_type': h.change_type,
            'old_value': h.old_value,
            'new_value': h.new_value,
            'changed_by': h.user.name,
            'changed_at': h.created_at.isoformat(),
            'reason': h.reason
        }
        for h in history
    ]
```

**B. Frontend Component**

`/frontend/components/DeadlineHistoryPanel.tsx`:
```tsx
function DeadlineHistoryPanel({ deadlineId }: Props) {
  const { data: history } = useQuery(['deadline-history', deadlineId],
    () => api.getDeadlineHistory(deadlineId)
  );

  return (
    <div className="space-y-2">
      <h3>Change History</h3>
      {history?.map(change => (
        <div key={change.id} className="border-l-2 pl-4">
          <div className="text-sm text-gray-600">
            {new Date(change.changed_at).toLocaleString()}
          </div>
          <div className="font-medium">
            {change.changed_by}
          </div>
          <div>
            {change.old_value} → {change.new_value}
          </div>
          {change.reason && (
            <div className="text-sm italic">{change.reason}</div>
          )}
        </div>
      ))}
    </div>
  );
}
```

**C. Chatbot Integration**

Add tool:
```python
{
    "name": "get_deadline_history",
    "description": "Get the full change history for a deadline (who changed it, when, why)",
    "input_schema": {
        "type": "object",
        "properties": {
            "deadline_id": {"type": "string"}
        }
    }
}
```

---

### **Phase 7: Advanced Features** (Week 4)

#### A. Deadline Conflict Detection

Detect when deadlines are too close together:
```python
def detect_deadline_conflicts(case_id: str, db: Session) -> List[Dict]:
    """Find deadlines that might conflict (within 48 hours)"""
    deadlines = db.query(Deadline).filter(
        Deadline.case_id == case_id,
        Deadline.status == 'pending'
    ).order_by(Deadline.deadline_date).all()

    conflicts = []
    for i in range(len(deadlines) - 1):
        d1 = deadlines[i]
        d2 = deadlines[i + 1]

        if d1.deadline_date and d2.deadline_date:
            days_apart = (d2.deadline_date - d1.deadline_date).days

            if days_apart <= 2:
                conflicts.append({
                    'deadline1': d1.title,
                    'deadline2': d2.title,
                    'days_apart': days_apart,
                    'severity': 'high' if days_apart == 0 else 'medium'
                })

    return conflicts
```

#### B. Local Rule Overrides

Allow circuit-specific customizations:
```python
# /backend/app/data/local_rules.json
{
  "11th_circuit": {
    "pretrial_order_due": {
      "days_before_trial": 30,  # Override from 45
      "notes": "11th Circuit requires 30 days, not 45"
    }
  },
  "15th_circuit": {
    "mediation_statement_due": {
      "days_before_mediation": 5  # Override from 7
    }
  }
}
```

#### C. Batch Operations

Chatbot tool for bulk operations:
```python
{
    "name": "batch_deadline_operations",
    "description": "Perform bulk operations on multiple deadlines (shift all by X days, change priority, etc.)",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["shift_dates", "change_priority", "change_status", "delete_all"]
            },
            "filter": {
                "type": "object",
                "properties": {
                    "priority": {"type": "string"},
                    "status": {"type": "string"},
                    "date_range": {"type": "object"}
                }
            },
            "changes": {"type": "object"}
        }
    }
}
```

---

## Implementation Timeline

| Phase | Duration | Features |
|-------|----------|----------|
| **Phase 1** | Week 1 | IsOverridden flag, manual change tracking |
| **Phase 2** | Week 1-2 | Dependency listener, cascade updates |
| **Phase 3** | Week 2 | Court days calculator |
| **Phase 4** | Week 2-3 | Document-deadline linking |
| **Phase 5** | Week 3 | Tickler system, email reminders |
| **Phase 6** | Week 3-4 | Audit trail UI, history panel |
| **Phase 7** | Week 4 | Conflict detection, local rules, batch ops |

**Total: 4 weeks to CompuLaw-level deadline engine**

---

## Success Metrics

After completion, the system should:
- ✅ Automatically cascade updates when triggers change
- ✅ Respect manual overrides (never overwrite them)
- ✅ Calculate court days accurately (skip weekends + holidays)
- ✅ Link documents to deadlines
- ✅ Send automated reminders (30, 15, 7, 1 day)
- ✅ Provide full audit trail ("who changed what when")
- ✅ Detect deadline conflicts
- ✅ Support local court rule variations

---

## Testing Plan

### Test Scenario 1: Cascade Update
1. Create trial date trigger (generates 5 deadlines)
2. Manually change one deadline
3. Move trial date
4. Verify: 4 deadlines update, 1 stays (manually overridden)

### Test Scenario 2: Court Days
1. Create deadline 30 court days from today
2. Verify it skips weekends + July 4th
3. Compare to calendar_days calculation

### Test Scenario 3: Tickler System
1. Create deadline 15 days out
2. Wait for daily job to run
3. Verify email sent
4. Verify reminder marked as sent

### Test Scenario 4: Document Linking
1. Upload "Motion for Summary Judgment.pdf"
2. AI suggests linking to MSJ deadline
3. User confirms
4. Verify link created in database
5. Test: Click deadline → see document

---

## Database Migrations

```sql
-- Migration 1: Override tracking
ALTER TABLE deadlines ADD COLUMN is_manually_overridden BOOLEAN DEFAULT FALSE;
ALTER TABLE deadlines ADD COLUMN override_timestamp TIMESTAMP;
ALTER TABLE deadlines ADD COLUMN override_user_id VARCHAR(36);
ALTER TABLE deadlines ADD COLUMN override_reason TEXT;

-- Migration 2: Reminder tracking
ALTER TABLE deadlines ADD COLUMN reminder_schedule JSON DEFAULT '[30,15,7,1]';
ALTER TABLE deadlines ADD COLUMN reminders_sent JSON DEFAULT '[]';

-- Migration 3: Document-Deadline links
CREATE TABLE document_deadline_links (
  id VARCHAR(36) PRIMARY KEY,
  document_id VARCHAR(36) REFERENCES documents(id) ON DELETE CASCADE,
  deadline_id VARCHAR(36) REFERENCES deadlines(id) ON DELETE CASCADE,
  link_type VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW(),
  created_by VARCHAR(36) REFERENCES users(id)
);

CREATE INDEX idx_doc_deadline_links_doc ON document_deadline_links(document_id);
CREATE INDEX idx_doc_deadline_links_deadline ON document_deadline_links(deadline_id);
```

---

## Questions for You

Before starting, confirm:

1. **Priority Order**: Which phase is most critical?
   - I recommend: Phase 1 → Phase 2 → Phase 3 (core functionality first)

2. **Email Service**: Do you have SendGrid or similar for tickler emails?
   - Need for Phase 5

3. **Celery/Redis**: Do you want background jobs (for reminders)?
   - Need for Phase 5

4. **Local Rules**: Which Florida circuits do you primarily work with?
   - For circuit-specific customizations

5. **Reminder Preferences**: Default reminder schedule (30, 15, 7, 1 days)?
   - Or different?

---

## Ready to Start!

This plan will transform your deadline system into a **CompuLaw-level Rules-Based Calendaring engine**.

**Next steps:**
1. Review this plan
2. Prioritize phases
3. I'll start implementing Phase 1 immediately

🚀 Let's build the most sophisticated legal deadline engine! ⚖️
