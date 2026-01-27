# LitDocket Battle Test Fix Plan

**Generated:** 2026-01-27
**Based on:** Comprehensive Battle Test Report v3.0.0-alpha

## Executive Summary

Six critical bugs are blocking core functionality. The investigations reveal:

| # | Issue | Root Cause | Severity | Effort |
|---|-------|------------|----------|--------|
| 1 | Case navigation broken | Backend only supports UUID, not case_number in URLs | CRITICAL | Low |
| 2 | AI Terminal unusable | case_id required for ALL queries, even global ones | CRITICAL | Medium |
| 3 | Rules page "Not Found" | `/rules` API router never implemented | HIGH | High |
| 4 | Date off-by-one | JavaScript timezone bug in date parsing | CRITICAL | Low |
| 5 | Case list not rendering | CSS layout conflict with fixed AITerminal | HIGH | Low |
| 6 | Rules save button disabled | State sync bug between parent/child components | HIGH | Low |

---

## Issue #1: Case Navigation Broken

### Problem
Cases exist in database and display in list, but navigating to any individual case returns "Case not found".

### Root Cause
**File:** `backend/app/api/v1/cases.py` (lines 108-139)

Backend `GET /api/v1/cases/{case_id}` only supports UUID lookup:
```python
case = db.query(Case).filter(
    Case.id == case_id,  # Only matches UUID
    Case.user_id == str(current_user.id)
).first()
```

When URL is `/cases/1:25-cv-01001-SAB` (case_number), the lookup fails because:
- `Case.id` is a UUID like `f47ac10b-58cc-4372-a567-0e02b2c3d479`
- `Case.case_number` is `1:25-cv-01001-SAB`

### Fix
Add fallback lookup by case_number in all case endpoints:

```python
# backend/app/api/v1/cases.py - GET /{case_id} endpoint (line 108+)

@router.get("/{case_id}")
def get_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get case details by ID or case_number"""
    # Try UUID first (fast path)
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    # Fall back to case_number lookup (human-readable URLs)
    if not case:
        case = db.query(Case).filter(
            Case.case_number == case_id,
            Case.user_id == str(current_user.id)
        ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # ... rest of endpoint
```

### Affected Endpoints (Apply same pattern)
- `GET /cases/{case_id}` (line 108)
- `GET /cases/{case_id}/documents` (line 142)
- `GET /cases/{case_id}/summary` (line 203)
- `PATCH /cases/{case_id}/status` (line 238)
- `PATCH /cases/{case_id}` (line 273)
- `POST /cases/{case_id}/notes` (line 371)
- `GET /cases/{case_id}/timeline` (line 412)
- `POST /cases/{case_id}/archive` (line 497)
- `POST /cases/{case_id}/unarchive` (line 522)
- `DELETE /cases/{case_id}` (line 547)

---

## Issue #2: AI Terminal Context Dependency

### Problem
AI Terminal requires case context for ALL operations, even "What cases do I have?"

### Root Cause (Frontend)
**File:** `frontend/components/layout/AITerminal.tsx` (lines 457-467)

```typescript
if (!caseId) {
  const errorMsg: Message = {
    id: `error-${Date.now()}`,
    type: 'error',
    content: 'NO CASE CONTEXT. Navigate to a case first or specify case ID.',
    timestamp: new Date(),
  };
  setMessages(prev => [...prev, errorMsg]);
  return;  // Blocks ALL queries without case context
}
```

### Root Cause (Backend)
**File:** `backend/app/api/v1/chat_stream.py` (lines 61-118)

```python
@router.get("/stream")
async def stream_chat(
    case_id: str = Query(..., description="Case UUID"),  # Required!
    ...
):
```

### Fix (Backend - Priority 1)

```python
# backend/app/api/v1/chat_stream.py

from typing import Optional

@router.get("/stream")
async def stream_chat(
    request: Request,
    case_id: Optional[str] = Query(None, description="Case UUID (optional for general queries)"),
    session_id: str = Query(...),
    message: str = Query(...),
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    # Verify token and get user
    current_user = await verify_token_from_query(token, db)

    # Case context is optional
    case = None
    if case_id:
        case = db.query(Case).filter(
            Case.id == case_id,
            Case.user_id == str(current_user.id)
        ).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

    # Proceed with or without case context
    # ... rest of endpoint
```

Also update `backend/app/api/v1/chat.py`:
```python
class ChatMessageRequest(BaseModel):
    message: str
    case_id: Optional[str] = None  # Make optional
```

### Fix (Frontend - Priority 2)

```typescript
// frontend/components/layout/AITerminal.tsx

// Remove or relax the case context check (lines 457-467)
// Replace with:
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!input.trim()) return;

  // Allow queries without case context - don't block here
  // Backend will handle general queries appropriately

  // Continue with streaming...
};
```

### Fix (Frontend - Priority 3: Add Case Selector)

```typescript
// frontend/components/layout/AITerminal.tsx

// Add state for manual case selection
const [manualCaseId, setManualCaseId] = useState<string | null>(null);
const [userCases, setUserCases] = useState<{id: string, case_number: string}[]>([]);

// Effective case ID: URL context OR manual selection
const effectiveCaseId = caseId || manualCaseId;

// In the terminal header, add case selector:
<select
  value={manualCaseId || ''}
  onChange={(e) => setManualCaseId(e.target.value || null)}
  className="text-xs px-2 py-1 bg-slate-700 text-white rounded"
>
  <option value="">Global (No Case)</option>
  {userCases.map(c => (
    <option key={c.id} value={c.id}>{c.case_number}</option>
  ))}
</select>
```

---

## Issue #3: Rules Page "Not Found" Error

### Problem
Every page in Rules Builder shows a red "Not Found" error banner.

### Root Cause
**The backend `/rules` API router does not exist.** It was never implemented.

**Frontend calls these endpoints (in `frontend/hooks/useRules.ts`):**
- `GET /rules/templates` (line 104)
- `POST /rules/templates` (line 166)
- `GET /rules/templates/{ruleId}` (line 137)
- `POST /rules/templates/{ruleId}/activate` (line 220)
- `POST /rules/execute` (line 195)
- `GET /rules/executions` (line 244)
- `GET /rules/marketplace` (line 273)

**All return 404 because no router handles `/rules/*`.**

### Fix
Create the missing rules router:

```python
# backend/app/api/v1/rules.py (NEW FILE)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.models.rule_template import RuleTemplate
from app.models.rule_template_deadline import RuleTemplateDeadline
from app.schemas.rules import (
    RuleTemplateCreate,
    RuleTemplateResponse,
    RuleExecutionRequest,
    RuleExecutionResponse
)
import uuid
from datetime import datetime

router = APIRouter()

@router.get("/templates", response_model=List[RuleTemplateResponse])
async def list_rules(
    include_public: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's rule templates"""
    query = db.query(RuleTemplate).filter(
        RuleTemplate.created_by == str(current_user.id)
    )

    if include_public:
        # Include public/marketplace rules
        query = db.query(RuleTemplate).filter(
            (RuleTemplate.created_by == str(current_user.id)) |
            (RuleTemplate.is_public == True)
        )

    return query.all()


@router.post("/templates", response_model=RuleTemplateResponse)
async def create_rule(
    rule_data: RuleTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new rule template"""
    rule = RuleTemplate(
        id=str(uuid.uuid4()),
        name=rule_data.rule_name,
        trigger_type=rule_data.trigger_type,
        jurisdiction_id=rule_data.jurisdiction,
        description=rule_data.description,
        created_by=str(current_user.id),
        status='draft',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(rule)

    # Add deadlines
    for dl in rule_data.deadlines:
        deadline = RuleTemplateDeadline(
            id=str(uuid.uuid4()),
            rule_template_id=rule.id,
            name=dl.name,
            days_offset=dl.days_from_trigger,
            priority=dl.priority,
            # ... other fields
        )
        db.add(deadline)

    db.commit()
    db.refresh(rule)
    return rule


@router.get("/templates/{rule_id}", response_model=RuleTemplateResponse)
async def get_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific rule template"""
    rule = db.query(RuleTemplate).filter(
        RuleTemplate.id == rule_id,
        (RuleTemplate.created_by == str(current_user.id)) |
        (RuleTemplate.is_public == True)
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return rule


@router.post("/templates/{rule_id}/activate")
async def activate_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activate a draft rule"""
    rule = db.query(RuleTemplate).filter(
        RuleTemplate.id == rule_id,
        RuleTemplate.created_by == str(current_user.id)
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.status = 'active'
    rule.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Rule activated"}


@router.post("/execute", response_model=RuleExecutionResponse)
async def execute_rule(
    request: RuleExecutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a rule to generate deadlines for a case"""
    # Implementation using rules_engine.py
    pass


@router.get("/executions")
async def list_executions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List rule execution history"""
    # Return empty list for now, add RuleExecution model later
    return []


@router.get("/marketplace")
async def list_marketplace_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List public marketplace rules"""
    rules = db.query(RuleTemplate).filter(
        RuleTemplate.is_public == True
    ).all()
    return rules
```

**Register the router in `backend/app/api/v1/router.py`:**
```python
from app.api.v1 import rules

api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
```

---

## Issue #4: Date Calculation Off-by-One

### Problem
Entered trigger date "01/27/2026" but result shows "1/26/2026".

### Root Cause
**File:** `frontend/app/(protected)/tools/deadline-calculator/page.tsx` (line 55)

```typescript
const handleCalculate = () => {
  const trigger = new Date(triggerDate);  // BUG: Interprets as UTC midnight!
  // ...
};
```

When `triggerDate` is `"2026-01-27"` (ISO string from date input):
- `new Date("2026-01-27")` creates **UTC midnight** (00:00:00Z)
- In Eastern Time (UTC-5), this displays as `2026-01-26 19:00:00`
- `toLocaleDateString()` shows **"1/26/2026"** - one day off!

### Fix

```typescript
// frontend/app/(protected)/tools/deadline-calculator/page.tsx

const handleCalculate = () => {
  // Parse ISO date string correctly as local midnight
  const [year, month, day] = triggerDate.split('-').map(Number);
  const trigger = new Date(year, month - 1, day);  // Creates LOCAL midnight

  const result = calculateFederalDeadline(
    trigger,
    days,
    countingMethod,
    serviceMethod
  );
  setCalculationResult(result);
};
```

### Alternative Fix (Utility Function)
Create a reusable date parsing utility:

```typescript
// frontend/lib/date-utils.ts

/**
 * Parse ISO date string (YYYY-MM-DD) as local midnight.
 * Avoids UTC timezone interpretation issues.
 */
export function parseLocalDate(isoDateStr: string): Date {
  const [year, month, day] = isoDateStr.split('-').map(Number);
  return new Date(year, month - 1, day);
}
```

Then use throughout:
```typescript
import { parseLocalDate } from '@/lib/date-utils';

const trigger = parseLocalDate(triggerDate);
```

---

## Issue #5: Case List Not Rendering

### Problem
Cases page shows "Showing 4 of 4 cases" but case rows don't render visually.

### Root Cause (Multiple Issues)

1. **Fixed AITerminal overlaps content**
   - **File:** `frontend/app/globals.css` (lines 375-393)
   - `.cockpit-terminal` uses `fixed bottom-0` positioning
   - No padding-bottom in scrollable area to compensate

2. **Page wrapper pushes content below viewport**
   - **File:** `frontend/app/(protected)/cases/page.tsx` (line 405)
   - `min-h-screen` wrapper + sticky header pushes rows off-screen

### Fix 1: Add Bottom Padding to Layout

```typescript
// frontend/components/layout/CockpitLayout.tsx (line 33)

// Before:
<div className="flex-1 overflow-auto p-6 scrollbar-dark">

// After:
<div className="flex-1 overflow-auto p-6 pb-48 scrollbar-dark">
```

The `pb-48` (12rem) reserves space for the AITerminal when expanded.

### Fix 2: Remove min-h-screen from Cases Page

```typescript
// frontend/app/(protected)/cases/page.tsx (line 405)

// Before:
<div className="min-h-screen bg-slate-50">

// After:
<div className="bg-slate-50">
```

### Fix 3 (Alternative): Make AITerminal Part of Layout Flow

```css
/* frontend/app/globals.css */

/* Instead of fixed positioning, use sticky at bottom of flex container */
.cockpit-terminal {
  @apply sticky bottom-0 left-0 right-0 z-50;
  /* Remove 'fixed' - let it flow with content */
}
```

This requires restructuring CockpitLayout to not use fixed positioning.

---

## Issue #6: Rules Save Button Disabled

### Problem
Added a deadline to a rule, but "Save as Draft" remained disabled.

### Root Cause
**State synchronization bug between parent and child components.**

**Parent:** `frontend/app/(protected)/rules/RulesBuilderDashboard.tsx` (line 235)
```typescript
const [deadlines, setDeadlines] = useState<any[]>([]);  // Parent state
```

**Child:** `frontend/components/rules/TimelineRuleBuilder.tsx` (line 32)
```typescript
const [deadlines, setDeadlines] = useState<Deadline[]>([]);  // Separate local state!
```

**Validation check uses parent's state (line 330):**
```typescript
const isFormValid = formData.rule_name && formData.jurisdiction &&
                    formData.trigger_type && deadlines.length > 0;
```

**Child adds deadline to ITS state, not parent's:**
```typescript
const addDeadline = (deadline: Deadline) => {
  const updated = [...deadlines, deadline];  // Child's local state
  setDeadlines(updated);                      // Updates child
  onChange?.(updated);                        // Should update parent...
};
```

The `onChange` callback is called but something prevents parent update.

### Fix

**Option A: Remove duplicate state in child**

```typescript
// frontend/components/rules/TimelineRuleBuilder.tsx

interface TimelineRuleBuilderProps {
  triggerType: string;
  deadlines: Deadline[];  // Receive from parent
  onChange: (deadlines: Deadline[]) => void;
}

export default function TimelineRuleBuilder({
  triggerType,
  deadlines,  // Use parent's state
  onChange
}: TimelineRuleBuilderProps) {
  // Remove local useState for deadlines

  const addDeadline = (deadline: Deadline) => {
    onChange([...deadlines, deadline]);  // Directly update parent
    setShowAddForm(false);
  };

  // ... rest uses `deadlines` prop
}
```

**Parent passes state down:**
```typescript
// frontend/app/(protected)/rules/RulesBuilderDashboard.tsx

<TimelineRuleBuilder
  triggerType={formData.trigger_type}
  deadlines={deadlines}        // Pass state down
  onChange={setDeadlines}      // Pass setter
/>
```

**Option B: Debug why onChange isn't propagating**

Add logging to trace the issue:
```typescript
// TimelineRuleBuilder.tsx
const addDeadline = (deadline: Deadline) => {
  const updated = [...deadlines, deadline];
  console.log('Child: Adding deadline, calling onChange with:', updated);
  setDeadlines(updated);
  onChange?.(updated);
};

// RulesBuilderDashboard.tsx
const handleDeadlinesChange = (newDeadlines: any[]) => {
  console.log('Parent: Received deadlines update:', newDeadlines);
  setDeadlines(newDeadlines);
};

// Pass named function instead
<TimelineRuleBuilder
  triggerType={formData.trigger_type}
  onChange={handleDeadlinesChange}
/>
```

---

## Priority Order for Fixes

### P0 - BLOCKING (Fix Immediately)

| # | Issue | File(s) | Est. Lines |
|---|-------|---------|------------|
| 4 | Date off-by-one | `deadline-calculator/page.tsx` | ~5 |
| 1 | Case navigation | `backend/app/api/v1/cases.py` | ~30 |
| 5 | Case list rendering | `CockpitLayout.tsx`, `cases/page.tsx` | ~5 |

### P1 - CRITICAL (Fix This Week)

| # | Issue | File(s) | Est. Lines |
|---|-------|---------|------------|
| 2 | AI Terminal context | `chat_stream.py`, `AITerminal.tsx` | ~50 |
| 6 | Rules save button | `TimelineRuleBuilder.tsx` | ~20 |

### P2 - HIGH (Fix Next Sprint)

| # | Issue | File(s) | Est. Lines |
|---|-------|---------|------------|
| 3 | Rules router missing | NEW: `backend/app/api/v1/rules.py` | ~200 |

---

## Implementation Checklist

**ALL FIXES COMPLETED** - 2026-01-27

```
[x] P0: Fix date parsing in deadline calculator (commit 9897221)
    [x] Manually parse ISO date to local midnight
    [x] Avoid new Date() UTC interpretation bug

[x] P0: Add case_number fallback lookup (commit 9897221)
    [x] Created get_case_by_id_or_number() helper
    [x] Updated all 11 case endpoints
    [x] Works with both UUID and case_number URLs

[x] P0: Fix case list rendering (commit 9897221)
    [x] Added pb-48 to CockpitLayout scrollable area
    [x] Removed min-h-screen from cases page wrapper

[x] P1: Make AI case_id optional (commit aa630c3)
    [x] Updated chat_stream.py to accept Optional[str]
    [x] Updated chat.py ChatMessageRequest
    [x] Removed frontend case context requirement
    [x] Updated useStreamingChat.ts URL building

[x] P1: Fix rules save button (commit aa630c3)
    [x] Made TimelineRuleBuilder accept controlled deadlines prop
    [x] Parent now passes deadlines state down
    [x] State synchronization works correctly

[x] P2: Implement rules router (commit eaa0078)
    [x] Created backend/app/api/v1/rules.py (711 lines)
    [x] Created app/schemas/user_rules.py (Pydantic schemas)
    [x] Created app/models/user_rule.py (SQLAlchemy models)
    [x] Registered router in router.py
    [x] Created migration 010_user_rules_additions.sql
```

---

## Testing After Fixes

1. **Case Navigation:** Navigate to `/cases/[case_number]` - should load case
2. **AI Terminal:** Ask "What cases do I have?" from `/dashboard` - should work
3. **Date Calculation:** Enter 01/27/2026, verify result shows 01/27/2026 base
4. **Case List:** Visit `/cases` - rows should be visible immediately
5. **Rules Save:** Add deadline, verify Save button enables
6. **Rules Page:** No error banner on any Rules Builder tab
