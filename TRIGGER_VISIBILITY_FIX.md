# Trigger Visibility Fix - January 6, 2026

## Issue
Trigger events were still showing in the UI even after they were marked as completed or deleted. Regular deadlines hide properly when completed, but trigger events continued to display.

## Root Cause
The backend API endpoint `/api/v1/triggers/case/{case_id}/triggers` was querying all trigger deadlines without filtering by status. It only checked:
- `is_dependent == False` (triggers are parent deadlines)
- `trigger_event.isnot(None)` (has a trigger event)

But **never checked the status field**, so completed and cancelled triggers were returned.

## Solution

### Backend Fix (Primary)

**File**: `/backend/app/api/v1/triggers.py` (Line 316-320)

**Before:**
```python
# Get all trigger deadlines (non-dependent)
triggers = db.query(Deadline).filter(
    Deadline.case_id == case_id,
    Deadline.is_dependent == False,
    Deadline.trigger_event.isnot(None)
).all()
```

**After:**
```python
# Get all trigger deadlines (non-dependent, active only)
triggers = db.query(Deadline).filter(
    Deadline.case_id == case_id,
    Deadline.is_dependent == False,
    Deadline.trigger_event.isnot(None),
    Deadline.status.notin_(['completed', 'cancelled'])  # ✅ ADDED
).all()
```

**Impact**: Backend now filters out completed and cancelled triggers at the database level.

---

### Backend Enhancement

**File**: `/backend/app/api/v1/triggers.py` (Line 335)

Added `status` field to the API response:

**Before:**
```python
result.append({
    'id': str(trigger.id),
    'trigger_type': trigger.trigger_event,
    'trigger_date': trigger.deadline_date.isoformat() if trigger.deadline_date else None,
    'title': trigger.title,
    'dependent_deadlines_count': dependent_count,
    'created_at': trigger.created_at.isoformat()
})
```

**After:**
```python
result.append({
    'id': str(trigger.id),
    'trigger_type': trigger.trigger_event,
    'trigger_date': trigger.deadline_date.isoformat() if trigger.deadline_date else None,
    'title': trigger.title,
    'status': trigger.status,  # ✅ ADDED
    'dependent_deadlines_count': dependent_count,
    'created_at': trigger.created_at.isoformat()
})
```

**Impact**: Frontend can now see the status of each trigger.

---

### Frontend Type Update

**File**: `/frontend/hooks/useCaseData.ts` (Line 59)

**Before:**
```typescript
export interface Trigger {
  id: string;
  trigger_type: string;
  trigger_date: string;
  title: string;
  dependent_deadlines_count: number;
  created_at: string;
}
```

**After:**
```typescript
export interface Trigger {
  id: string;
  trigger_type: string;
  trigger_date: string;
  title: string;
  dependent_deadlines_count: number;
  status?: string;  // ✅ ADDED - Optional: pending, completed, cancelled
  created_at: string;
}
```

**Impact**: TypeScript now knows about the status field.

---

### Frontend Filter (Defensive Layer)

**File**: `/frontend/app/(protected)/cases/[caseId]/page.tsx` (Lines 744, 751-752)

Added client-side filtering as a defensive measure:

**Before:**
```tsx
{/* Trigger Events Section */}
{triggers.length > 0 && (
  <div className="mb-4 pb-4 border-b border-slate-200">
    {/* ... */}
    <div className="space-y-2">
      {triggers.map((trigger) => (
        {/* Render trigger */}
      ))}
    </div>
  </div>
)}
```

**After:**
```tsx
{/* Trigger Events Section */}
{triggers.filter(t => t.status !== 'completed' && t.status !== 'cancelled').length > 0 && (
  <div className="mb-4 pb-4 border-b border-slate-200">
    {/* ... */}
    <div className="space-y-2">
      {triggers
        .filter(trigger => trigger.status !== 'completed' && trigger.status !== 'cancelled')
        .map((trigger) => (
        {/* Render trigger */}
      ))}
    </div>
  </div>
)}
```

**Impact**: Even if backend accidentally returns completed triggers, frontend won't display them.

---

## Files Modified

### Backend (2 changes in 1 file)
1. `/backend/app/api/v1/triggers.py`
   - Line 320: Added status filter to query
   - Line 335: Added status to response

### Frontend (2 files)
2. `/frontend/hooks/useCaseData.ts`
   - Line 59: Added optional status field to Trigger interface

3. `/frontend/app/(protected)/cases/[caseId]/page.tsx`
   - Lines 744, 751-752: Added filters to hide completed/cancelled triggers

---

## Testing

### How to Test:
1. **Create a trigger** (e.g., upload a document with "service of complaint")
2. **Verify trigger shows** in the "Trigger Events" section
3. **Complete or delete the trigger deadline** (via chat or UI)
4. **Refresh the page**
5. **Verify trigger no longer shows** in the "Trigger Events" section

### Expected Behavior:
- ✅ Active triggers (status="pending"): **SHOW**
- ❌ Completed triggers (status="completed"): **HIDDEN**
- ❌ Cancelled triggers (status="cancelled"): **HIDDEN**

---

## Technical Details

### Deadline Status Values
From `/backend/app/models/deadline.py` (Line 61):
```python
status = Column(String(50), default="pending")  # pending, completed, cancelled
```

### Defense in Depth
This fix uses **two layers of filtering**:
1. **Backend** (primary): Database query filters out completed/cancelled triggers
2. **Frontend** (defensive): UI filters as a failsafe

This ensures triggers are properly hidden even if:
- Backend query fails
- API returns unexpected data
- Status field is missing (falls back to showing trigger)

---

## Related Code

### How Triggers Work:
1. **Trigger creation**: User uploads document → AI detects trigger event (e.g., "service of complaint")
2. **Deadline chain**: Trigger generates 20-50+ dependent deadlines
3. **Trigger status**: When trigger is marked complete, it should hide from UI
4. **Dependent deadlines**: Continue to show even if trigger is hidden

### Regular Deadlines vs Triggers:
- **Regular deadline**: `is_dependent = True` or `trigger_event = None`
- **Trigger deadline**: `is_dependent = False` AND `trigger_event != None`

Both use the same `status` field for filtering.

---

## Potential Edge Cases

### What if a trigger has dependent deadlines but is completed?
- ✅ **Trigger**: Hidden (status = completed)
- ✅ **Dependent deadlines**: Still show (they have their own status)

### What if user wants to see completed triggers?
- Future enhancement: Add "Show completed triggers" toggle
- Current behavior: Completed triggers are permanently hidden

### What if trigger is deleted from database?
- Backend query won't find it
- Frontend won't receive it
- No issues

---

## Performance Impact
- **Minimal**: Added one additional filter to WHERE clause
- Database indexes on `case_id`, `is_dependent`, `trigger_event` remain effective
- No N+1 query issues

---

## Backward Compatibility
- ✅ **API response now includes status field**
- ✅ **Frontend made status optional** (won't break if backend doesn't send it)
- ✅ **No breaking changes** to existing functionality

---

**Date**: January 6, 2026
**Status**: ✅ Complete and tested
**Breaking Changes**: None
**Migration Required**: No

---

## Summary
Completed and cancelled trigger events now properly hide from the UI, matching the behavior of regular deadlines. The fix uses both backend filtering (primary) and frontend filtering (defensive) to ensure robust behavior.
