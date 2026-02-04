# Technical Debt Audit Report
**Date:** 2026-02-03
**Auditor:** Principal Architect (Claude Opus 4.5)
**Codebase:** LitDocket - AI Docketing Assistant

---

## Executive Summary

Conducted a comprehensive audit of the LitDocket codebase covering 43,608+ lines of TypeScript/TSX (frontend) and 15,000+ lines of Python (backend). **Found 65+ issues** across security, performance, type safety, and code quality.

**Key Metrics:**
- Files with `any` types: 24+ files (65+ instances)
- Large components (>300 lines): 9 files
- N+1 query patterns: 2 confirmed critical locations
- Silent exception handlers: 3+ locations
- Configuration duplication: 3 sources of CORS origins

---

## CRITICAL SEVERITY (Fix Immediately)

### C1. IDOR Vulnerability in Audit Endpoint
**File:** `backend/app/api/v1/audit.py:78-120`
**Issue:** `verify_audit_chain` endpoint receives `current_user` but doesn't verify that `record_id` belongs to the user. Attackers could audit chains for records they don't own.
```python
@router.get("/verify/{record_id}")
async def verify_audit_chain(record_id: str, current_user: User = Depends(get_current_user)):
    # MISSING: Ownership verification
    result = db.execute(text("SELECT * FROM verify_audit_chain(:record_id)"), {"record_id": record_id})
```
**Fix:** Add ownership check before database function call.

### C2. Blocking HTTP in Async Function
**File:** `backend/app/api/v1/documents.py:328`
**Issue:** Uses synchronous `requests.get()` inside `async def download_document()`. Blocks the entire event loop.
```python
response = requests.get(signed_url, stream=True)  # BLOCKING!
```
**Fix:** Replace with `httpx.AsyncClient` (already used elsewhere in codebase).

### C3. N+1 Query in Case Intelligence
**File:** `backend/app/api/v1/case_intelligence.py:109-124`
**Issue:** Loops through case IDs making separate DB query for each health score. 100 cases = 101 queries.
```python
for case_id in case_ids:
    score = db.query(CaseHealthScore).filter(CaseHealthScore.case_id == case_id)...
```
**Fix:** Use single query with `func.row_number()` window function or batch query.

### C4. N+1 Query in Rules Engine
**File:** `backend/app/services/rules_engine.py:3007-3013`
**Issue:** Queries each jurisdiction's rule sets in a loop.
```python
for local_juris in local_jurisdictions.all():
    local_rule_sets = self.db.query(RuleSet).filter(RuleSet.jurisdiction_id == local_juris.id)...
```
**Fix:** Collect jurisdiction IDs, then single query with `RuleSet.jurisdiction_id.in_(ids)`.

### C5. React State Mutation in Render
**File:** `frontend/components/calendar/CalendarGrid.tsx:65-72`
**Issue:** Calls `setState` directly during render cycle, causing infinite re-render loops.
```typescript
if (navigateToDate && navigateToDate.getTime() !== currentDate.getTime()) {
    setCurrentDate(navigateToDate);  // State update IN RENDER
}
```
**Fix:** Move to `useEffect` with proper dependency array.

---

## HIGH SEVERITY (Fix Soon)

### H1. Widespread `any` Type Usage (65+ instances)
**Files:** 24+ files across frontend
**Key Offenders:**
| File | Instances | Risk |
|------|-----------|------|
| `lib/eventBus.ts` | 11 | Entire event system untyped |
| `hooks/useRules.ts` | 7 | Error handling untyped |
| `app/(protected)/rules/RulesBuilderDashboard.tsx` | 7 | Rule state untyped |
| `components/layout/AITerminal.tsx` | 6 | User-facing AI untyped |
| `lib/auth/auth-context.tsx` | 4 | Auth errors untyped |

**CLAUDE.md Violation:** States "No `any` types - use proper interfaces"

### H2. Large Components Needing Split
| Component | Lines | Suggested Split |
|-----------|-------|-----------------|
| `SovereignTreeGrid.tsx` | 1,098 | TreePanel, RuleSelector, ConflictResolver |
| `UnifiedAddEventModal.tsx` | 983 | QuickAddTab, ApplyRuleTab, RuleChainTab |
| `cases/[caseId]/page.tsx` | 944 | CaseHeader, TabNav, ModalManager |
| `cases/page.tsx` | 924 | CasesTable, CaseFilters |
| `dashboard/page.tsx` | 873 | MorningReport, StatsCards, ActivityFeed |
| `authority-core/page.tsx` | 775 | (service extraction needed) |
| `rules/proposals/page.tsx` | 764 | ProposalsTable, ProposalForm |
| `RulesBuilderDashboard.tsx` | 745 | MyRulesTab, RuleCreator |
| `AITerminal.tsx` | 671 | ChatMessages, FileUploadZone, ChatInputBar |

### H3. Untyped EventBus System
**File:** `frontend/lib/eventBus.ts`
**Issue:** Core event system uses `any` for all payloads. Subscribers receive untyped data.
```typescript
type EventCallback = (data?: any) => void;  // No type safety!
```
**Fix:** Create typed event map:
```typescript
type EventMap = {
  'deadline:created': DeadlineCreatedEvent;
  'deadline:updated': DeadlineUpdatedEvent;
};
```

### H4. Silent Exception Swallowing
**File:** `backend/app/services/document_service.py:1297-1300`
```python
for s in suggestions_created:
    try:
        self.db.refresh(s)
    except Exception:
        pass  # SILENT FAILURE - no logging!
```
**Fix:** Add `logger.warning(f"Failed to refresh: {e}", exc_info=True)`

### H5. API Response Format Inconsistency
**CLAUDE.md Claim:** `{"success": True, "data": {...}, "message": "..."}`
**Reality:** Multiple formats in use:
- `{"id": "...", "case_id": "..."}` (deadlines.py)
- `{"success": True, "deadline_id": "..."}` (triggers.py)
- `{"access_token": "...", "token_type": "..."}` (auth.py)

### H6. Blocking time.sleep() in Async Context
**File:** `backend/app/services/enhanced_chat_service.py:90,96,103,113`
```python
time.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))  # Blocks event loop!
```
**Fix:** Use `await asyncio.sleep()` or run in thread pool.

---

## MEDIUM SEVERITY (Refactor Gradually)

### M1. Configuration Duplication (CORS Origins)
**Problem:** Three sources of truth for allowed origins:
1. `backend/app/config.py:58-65` - 6 origins
2. `backend/app/middleware/security.py:124-128` - 3 origins (missing some!)
3. `frontend/lib/config.ts` - hardcoded production URL

**Impact:** Vercel preview deployments may fail; config drift risk.

### M2. Prop Drilling Without Context
**File:** `frontend/app/(protected)/cases/[caseId]/page.tsx`
**Issue:** Passes `modals`, `caseData`, `deadlines`, `triggers`, `documents` through 3+ layers.
**Fix:** Create CaseContext for shared state.

### M3. Dead Code: Backup Files
**File:** `frontend/app/(protected)/cases/[caseId]/page.tsx.backup`
**Issue:** 140+ line backup file committed to source.
**Fix:** Delete immediately.

### M4. Commented-Out WebSocket Routes
**Files:** `backend/app/main.py:163-172`, `deadlines.py:15-16`
**Issue:** Disabled code cluttering codebase.
**Fix:** Remove or move to feature branch.

### M5. CLAUDE.md Documentation Drift
| Claim | Reality |
|-------|---------|
| "18 routers" | 23 route files |
| "20+ services" | 31 service files |
| WebSocket "commented out" | Still has misleading examples |

### M6. Hardcoded Rate Limits
**Files:** `backend/app/api/v1/auth.py`, `documents.py`
**Issue:** `@limiter.limit("5/minute")` scattered as strings instead of constants.
**Fix:** Reference `RATE_LIMITS` dict from `middleware/security.py`.

### M7. Bare Exception Catches
**File:** `backend/app/api/v1/auth.py:299-300`
```python
except Exception:
    email = 'dev@docketassist.com'  # Silent fallback!
```
**Fix:** Catch specific exceptions: `except (JWTError, JWTClaimsError):`

### M8. traceback.print_exc() in Production
**File:** `backend/app/api/v1/documents.py:249`
```python
traceback.print_exc()  # Bypasses logging system!
```
**Fix:** Remove; use `logger.error(..., exc_info=True)` instead.

### M9. Massive Service File
**File:** `backend/app/services/rules_engine.py` (3,460 lines)
**Issue:** Single file handling multiple concerns: dataclasses, RulesEngine class (50+ methods), hardcoded rules.
**Fix:** Extract to separate modules.

### M10. Missing Eager Loading
**Issue:** No `joinedload()`/`selectinload()` usage for relationships causes hidden N+1 on serialization.
**Affected:** Case → Documents → Deadlines chains.

---

## LOW SEVERITY (Best Practices)

### L1. print() Statements in Production
**Files:** `backend/app/seed/rule_sets.py` (7), `utils/florida_holidays.py` (3)
**Fix:** Replace with `logger.info()`.

### L2. console.error in Frontend
**Files:** `AITerminal.tsx`, `authority-core/page.tsx`, `eventBus.ts`
**Fix:** Use proper logging service.

### L3. Unaddressed TODO Comments
- `services/chat_tools.py:1382`: `# TODO: Delete from Firebase Storage`
- `api/v1/documents.py:1150`: `# TODO: Get from case` (hardcoded jurisdiction)
- `services/rules_engine.py:2867`: `# TODO: Match against detection_patterns`

### L4. Redundant React Imports
**File:** `RulesBuilderDashboard.tsx:4`
```typescript
import * as React from 'react';  // Redundant with useState import
```

### L5. Inconsistent Global State
**File:** `frontend/lib/config.ts:62-79`
**Issue:** Uses `globalThis.__LITDOCKET_API_URL__` as undocumented runtime override.

---

---

## CLEANUP: Unused Files to Delete

### Backup Files
- `frontend/app/(protected)/cases/[caseId]/page.tsx.backup` (51 KB) - Stale backup of active page

### Archived/Obsolete Scripts
**Directory:** `backend/scripts/archive_obsolete_scripts/` (entire directory)
- `seed_rules.py` - Broken, imports deleted models
- `seed_comprehensive_rules.py` - Broken, imports deleted models
- `seed_federal_districts_phase3.py` - Broken, imports deleted models
- `generate_rule_template.py` - Generates code for wrong schema
- `seed_via_api.py` - Incomplete stub

### Unused Services
- `backend/app/services/secure_storage.py` (435 lines) - WORM storage manager never integrated

### Archived Documentation (Optional)
**Directory:** `docs/archive/` (18 files) - Historical docs no longer relevant
- ACCURACY_AUDIT_CHECKLIST.md, APP_REVIEW.md, DEBUG_DIAGNOSIS.md, etc.

### Build Artifacts (Auto-cleaned)
- `frontend/.next/cache/webpack/**/index.pack.gz.old`
- `frontend/.next/cache/webpack/**/index.pack.old`

**Total Cleanup:** ~380 KB of dead code + archived documentation

---

## Summary Table

| Severity | Count | Category Breakdown |
|----------|-------|-------------------|
| CRITICAL | 5 | Security (1), Async (1), Performance (2), React (1) |
| HIGH | 6 | Type Safety (2), Architecture (2), Error Handling (1), API (1) |
| MEDIUM | 10 | Config (1), State (1), Dead Code (2), Docs (1), Code Quality (5) |
| LOW | 5 | Logging (2), TODOs (1), Imports (1), Config (1) |
| CLEANUP | 4 | Backup (1), Scripts (1), Services (1), Docs (1) |
| **TOTAL** | **30** | |

---

## Recommended Fix Order

### Phase 1: Critical Security & Correctness (Week 1)
1. C1: Add ownership check to audit endpoint
2. C2: Replace `requests` with `httpx.AsyncClient`
3. C5: Move CalendarGrid state mutation to useEffect
4. H4: Add logging to silent exception handlers

### Phase 2: Performance (Week 2)
1. C3: Fix N+1 in case_intelligence.py
2. C4: Fix N+1 in rules_engine.py
3. M10: Add eager loading for common relationship chains

### Phase 3: Type Safety (Week 3-4)
1. H1: Eliminate all `any` types (prioritize eventBus.ts, auth-context.tsx)
2. H3: Create typed event map for EventBus

### Phase 4: Architecture (Week 5-6)
1. H2: Split oversized components (start with SovereignTreeGrid, UnifiedAddEventModal)
2. M9: Refactor rules_engine.py into modules
3. M1: Centralize CORS configuration

### Phase 5: Cleanup (Ongoing)
1. M3: Delete backup files
2. M4: Remove commented-out code
3. M5: Update CLAUDE.md
4. L1-L5: Address low-severity items

---

## Verification Checklist

After fixes, verify:
- [ ] `pytest` passes all tests
- [ ] `npm run build` succeeds without TypeScript errors
- [ ] `npm run lint` passes
- [ ] Load test confirms N+1 fixes (< 10 queries for 100 cases)
- [ ] Ownership check blocks cross-user audit access
- [ ] Calendar renders without infinite loops
