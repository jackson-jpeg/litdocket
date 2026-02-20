# LitDocket - Comprehensive Project Review

**Date:** 2026-02-20
**Scope:** Full-stack architecture, security, code quality, business logic, testing, database

---

## Executive Summary

LitDocket is an ambitious legal docketing platform that combines CompuLaw-style rules-based deadline calculation with AI-powered document analysis. The codebase (~150K+ lines) demonstrates strong architectural foundations — clean separation of concerns, consistent auth patterns, and a well-designed deadline calculation engine with legal defensibility baked in.

However, this review identified **44 security issues** (2 critical), **significant test coverage gaps** (estimated <10% overall), **database performance risks** at scale, and several business logic edge cases that need attention before this can be considered production-hardened for a legal malpractice-sensitive application.

### Scorecard

| Category | Score | Summary |
|----------|-------|---------|
| **Architecture** | 8/10 | Clean separation, good patterns, well-organized |
| **Security** | 5/10 | Strong foundations but critical IDOR + auth bypass gaps |
| **Business Logic** | 7/10 | Excellent deadline calculator, gaps in negative day chains |
| **Database Design** | 7/10 | Comprehensive schema, missing indexes for scale |
| **Test Coverage** | 3/10 | Deadline math solid, everything else dangerously untested |
| **Frontend Quality** | 8/10 | Good TypeScript, accessibility needs work |
| **AI Integration** | 7/10 | Functional with good prompts, needs better error handling |
| **Overall** | **6.5/10** | Solid foundation, not yet production-hardened |

---

## 1. CRITICAL SECURITY FINDINGS (Fix Immediately)

### 1.1 IDOR: Inbox API Has Zero User Filtering

**Severity: CRITICAL** | `backend/app/api/v1/inbox.py` + `backend/app/services/inbox_service.py`

Every endpoint in the Inbox API (list, get, delete, bulk_review) is accessible to **any authenticated user** regardless of ownership. The `current_user` dependency is injected but never used to filter queries.

```python
# inbox.py:106-111 — user_id never passed to service
items = service.list_inbox_items(
    item_type=item_type_filter,
    status=status_filter,
    limit=limit,
    offset=offset
)

# inbox.py:271 — Any user can delete any inbox item
deleted = service.delete_item(item_id)
```

**Impact:** Any authenticated user can read, modify, and delete other users' inbox items — including deadline proposals and AI recommendations. In a legal context, this could cause missed deadlines.

**Fix:** Add `user_id=str(current_user.id)` parameter to all `InboxService` methods and filter all queries by it.

### 1.2 DEV_AUTH_BYPASS Still Active in Signup

**Severity: CRITICAL** | `backend/app/api/v1/auth.py:292-300` + `backend/app/auth/firebase_auth.py:21-24`

While the login endpoint has DEV_AUTH_BYPASS removed (commented out), the `complete_signup` endpoint and `firebase_auth.py` still check for it. When `DEV_AUTH_BYPASS=true` and `DEBUG=true`:

- JWT tokens are decoded **without signature verification**
- `firebase_auth.py` returns a mock user (`dev-user-123`) for any token

If these environment variables are accidentally set in production, all authentication is bypassed.

**Fix:** Remove DEV_AUTH_BYPASS from `complete_signup` and `firebase_auth.py` entirely. Add a startup check that blocks boot if these vars are set in a non-local environment.

---

## 2. HIGH SECURITY FINDINGS (Fix This Week)

### 2.1 Mass Assignment via `**action_data` and `setattr()`

**Files:** `proposals.py:270-279`, `proposals.py:310-313`, `authority_core.py:739-748`

Proposal approval spreads untrusted data directly into model constructors and uses `setattr()` with only a `hasattr()` guard. An attacker could inject values for `user_id`, `verified_by`, `verification_status`, or any other model field.

```python
# proposals.py:270 — Spread from AI-generated proposal
deadline = Deadline(
    id=str(uuid.uuid4()),
    case_id=proposal.case_id,
    user_id=str(current_user.id),
    **action_data  # Any field accepted
)

# proposals.py:310 — setattr with no allowlist
for key, value in updates.items():
    if hasattr(deadline, key):
        setattr(deadline, key, value)
```

**Fix:** Replace with an explicit allowlist of permitted fields.

### 2.2 Missing Rate Limiting on AI/Chat Endpoints

**File:** `backend/app/middleware/security.py`

Rate limits are defined for auth (5/min), uploads (10/min), and AI (20/min), but the `@limiter.limit()` decorators are only applied to auth and document endpoints. These expensive endpoints have **no rate limiting**:

- `/chat/stream` (SSE streaming with Claude API)
- `/chat/` (non-streaming chat)
- `/rag-search/semantic`, `/rag-search/ask`
- `/workload/analysis`, `/workload/suggestions`
- All `/authority-core/harvest`, `/scrape-url`, `/extract-enhanced` endpoints
- All `/case-intelligence/` endpoints

**Impact:** An attacker could run up significant Anthropic API costs or cause resource exhaustion.

### 2.3 Error Detail Leakage (42 Endpoints)

Across 10 router files, **42 endpoints** expose raw exception messages to clients via `detail=f"... {str(e)}"`. This violates the project's own CLAUDE.md standard and can leak database schema, file paths, and service configuration.

**Top offenders:**
- `authority_core.py` — 18 instances
- `audit.py` — 6 instances
- `documents.py` — 5 instances

**Fix:** Replace all `detail=f"...{str(e)}"` with generic messages. Log the actual exception server-side.

### 2.4 Authority Core Read Endpoints Missing User Filtering

`authority_core.py` endpoints for listing, searching, and viewing rules return all rules regardless of ownership. While system rules may be public, user-created rules (which have a `user_id` field) are exposed to all authenticated users. The update and deactivate endpoints correctly filter by `user_id`.

### 2.5 No Content-Security-Policy Header

The `SecurityHeadersMiddleware` sets X-Frame-Options, HSTS, X-XSS-Protection, and Permissions-Policy but omits Content-Security-Policy — the most important header for XSS prevention.

---

## 3. BACKEND ARCHITECTURE

### Strengths

- **~223 endpoints across 26 routers** — well-organized by domain
- **Consistent auth pattern** — `get_current_user` dependency injection used across all protected routes
- **117 ownership checks** via `user_id == str(current_user.id)` filter pattern
- **Security headers middleware** — HSTS, X-Frame-Options, X-Content-Type-Options, Permissions-Policy
- **Database connection pooling** — pool_size=10, max_overflow=20, pool_pre_ping=True
- **Structured rate limiting tiers** — auth (5/min), default (100/min), upload (10/min), AI (20/min)
- **Global exception handler** — CORS-aware, prevents stack trace leakage (when used)
- **Good dependency injection** — FastAPI's `Depends()` used consistently

### Weaknesses

- **CORS too permissive** — `allow_headers=["*"]` and `expose_headers=["*"]` should be restricted
- **Token in query params for SSE** — inherent limitation of EventSource API, but tokens end up in server logs and browser history
- **Mixed auth utility locations** — `app/auth/jwt_handler.py` and `app/utils/auth.py` serve overlapping purposes
- **No request ID/correlation tracing** — makes production debugging and security forensics harder
- **No CSRF protection** — mitigated by SameSite cookies + CORS, but explicit tokens recommended for legal software
- **No token revocation** — compromised JWTs valid for full 7-day lifetime
- **Slowapi dependency unmaintained** since 2021 — consider alternatives

### Dependency Concerns

| Package | Current | Issue |
|---------|---------|-------|
| `slowapi==0.1.9` | Unmaintained since 2021 | Consider starlette-rate-limiter |
| `PyPDF2==3.0.1` | v4+ available | Performance and security improvements |
| `firebase-admin==6.4.0` | 6.5+ available | Should update |

---

## 4. FRONTEND ARCHITECTURE

### Strengths (Score: 8/10)

- **Clean App Router structure** — (auth), (protected), (public) route groups
- **Strong TypeScript** — comprehensive `types/index.ts` with all interfaces
- **Excellent auth flow** — Firebase ID tokens exchanged for backend JWT, proper interceptor pattern
- **Event Bus pattern** — type-safe pub/sub for cross-component communication without prop drilling
- **ErrorBoundary** — global error catcher with dev-mode stack traces
- **Paper & Steel design system** — consistent enterprise legal aesthetic
- **20+ custom hooks** — good separation of concerns

### Issues

**TypeScript Quality:**
- 32 instances of `catch (err: any)` — should be `catch (err: unknown)`
- Several `as any` casts in calendar DnD, global search, and polyfills
- `Record<string, any>` in streaming chat hook

**Accessibility (Critical Gap):**
- Only 14 `aria-` attributes in entire codebase
- 0 `role=` attributes on custom interactive elements
- No focus management in modals — missing `role="dialog"`, `aria-modal`, focus trap
- Icon-only buttons missing `aria-label`
- Forms missing `aria-required`, `aria-invalid`
- Loading spinners missing `aria-busy`

**For legal software used by attorneys (who may have accessibility needs or work with screen readers), this needs immediate attention.**

**Performance:**
- Most pages are Client Components (40+ use `'use client'`) — Server Components underutilized
- No query caching — dashboard data refetched on every navigation
- No request debouncing — rapid API calls possible
- No route prefetching

---

## 5. DATABASE DESIGN

### Overview

- **51 model classes** across 31 files
- **157 foreign keys**
- **22 migrations**
- **UUID primary keys** (VARCHAR(36)) consistently

### Strengths

- Comprehensive schema covering cases, deadlines, documents, chat, jurisdictions, rules, collaboration
- Cryptographic audit trail system (migration 003)
- Proper cascade deletes for owned relationships
- Centralized enums in `enums.py`
- Proper timestamps on all models

### Critical Issues

**N+1 Query Risk — Deadline Model:**
The `Deadline` model has **10 relationships** (case, document, user, override_user, verified_by_user, authority_rule, chains, dependencies, history, ai_feedback). Without explicit `joinedload`/`selectinload`, fetching 100 deadlines generates 500+ queries. This will impact dashboard, calendar, and case view performance.

**Missing Composite Indexes:**
The most common query patterns lack indexes:

| Missing Index | Query Pattern |
|---------------|---------------|
| `deadlines(case_id, priority, deadline_date)` | Case view with priority filter |
| `deadlines(user_id, status, deadline_date)` | Morning report — upcoming FATAL deadlines |
| `documents(case_id, analysis_status)` | Find unprocessed documents |
| `chat_messages(case_id, created_at DESC)` | Conversation history loading |
| `authority_rules(jurisdiction_id, authority_tier, is_active)` | Rule lookup per case |
| `deadline_dependencies(depends_on_deadline_id)` | Cascade recalculation |

**Relationship Definitions Incomplete:**
Multiple models have relationships without `back_populates` — `ActiveSession`, `authority_core.py`, `case_intelligence.py`, `notification.py`. This breaks bidirectional ORM consistency.

**Soft Delete Incomplete:**
Only `Deadline` has `is_archived`. `ChatMessage`, `CalendarEvent`, `Document` use hard DELETE. For legal software requiring audit trails, this is a compliance gap.

**CaseAccess Missing Unique Constraint:**
No `UNIQUE(case_id, invited_email)` constraint — allows duplicate invitations to the same user.

---

## 6. BUSINESS LOGIC — RULES ENGINE & DEADLINE CALCULATION

### Strengths (Deadline Calculator: 9/10)

The `AuthoritativeDeadlineCalculator` (`app/utils/deadline_calculator.py`, 511 lines) is excellent:

- **Full calculation transparency** — every deadline includes step-by-step basis with trigger date, base days, service extension, roll logic, and rule citations
- **Proper service extensions** — Florida state (mail +5, electronic +0 post-2019), Federal (mail +3, electronic +3)
- **Holiday handling** — Computus algorithm for Easter, all federal + Florida holidays, proper weekend observation
- **Two calculation methods** — calendar days (count all, roll to business day) and court days (skip weekends/holidays)

### Critical Issues

**Negative Day Chains Not Using Authoritative Calculator:**
The rules engine defines 60+ deadlines with negative `days_from_trigger` (e.g., MSJ due 60 days *before* trial). The `AuthoritativeDeadlineCalculator` does NOT support negative day calculations. These deadlines bypass the calculator entirely, missing proper roll logic and audit trails.

This is critical because trial preparation deadlines (the most important deadline chains) rely heavily on negative offsets.

**Service Extension Application for Court Days:**
When the base period uses court days, the service extension (mail +5 days) is also applied as court days. The correct legal interpretation (per Florida R. Jud. Admin. 2.514) is ambiguous — service extensions may need to be calendar days even when the base period is court days. This needs legal review and documentation.

**Service Method Normalization:**
The system recognizes "email", "mail", "personal", "electronic" but real certificates of service may say "EFILED", "ELECTRONIC FILING", "facsimile", "by hand", "overnight delivery". Unknown methods silently default to 0-day extension.

**Authority Core Migration Risk:**
The hardcoded rules engine is deprecated (`LOAD_HARDCODED_RULES=false`). All deadline calculation depends on Authority Core database seeding. If Authority Core rules are incomplete, the system fails silently — no startup validation checks for rule completeness.

---

## 7. AI INTEGRATION

### Strengths

- Claude API integration with `max_retries=3`
- Comprehensive document analysis prompt (15K token context)
- Structured JSON extraction of dates, parties, deadlines
- Confidence scoring on extracted deadlines
- Streaming chat with SSE and tool approval workflow

### Issues

- **No circuit breaker** — if Claude API is down, requests queue up with retries only
- **JSON parse failures unhandled** — `_parse_json_response()` called without try/catch; invalid JSON from Claude crashes the request
- **AI rule knowledge may be stale** — Claude's knowledge cutoff may miss recent rule changes; no mechanism to inject current rules from database into prompts
- **Confidence scoring opaque** — scores generated but methodology undocumented; attorneys can't assess trustworthiness

---

## 8. TEST COVERAGE (Score: 3/10)

### What's Tested (Well)

| Test File | Lines | Quality |
|-----------|-------|---------|
| `test_deadline_calculator.py` | 506 | Excellent — 18+ cases, service methods, roll logic, holidays |
| `test_florida_rule_2514.py` | 316 | Solid — Florida-specific compliance |
| `test_auth.py` | 229 | Good — JWT, password hashing, user model |
| `test_document_upload.py` | 309 | Partial — model structure, file validation |
| `test_phase7_golden_path.py` | 542 | Good — end-to-end trigger→deadline flow |
| `sovereign-calculator.test.ts` (frontend) | 390 | Excellent — holiday handling, retrograde calculations |

### What's NOT Tested (Critical Gaps)

**Zero API endpoint tests.** None of the 26 routers have TestClient-based integration tests. This means:
- IDOR vulnerabilities like the Inbox issue go undetected
- Auth edge cases (expired tokens, missing tokens, wrong user) untested
- Error handling (proper 404 vs 500 responses) unverified
- Rate limiting enforcement unverified

**Zero security/ownership tests.** No test verifies "User A cannot access User B's cases."

**Zero frontend test infrastructure.** No Jest/Vitest configuration, no test scripts in package.json, only 1 calculator test file exists.

**Missing test areas:**
- Negative day deadline calculations
- AI JSON parsing failures
- Authority Core integration
- Database operations (soft delete, cascades, concurrent access)
- Document→deadline extraction pipeline
- Confidence scoring accuracy

### Estimated Coverage
- Backend business logic: ~35%
- API endpoints: <5%
- Security: 0%
- Frontend: ~2%
- Integration: 0%

---

## 9. ADDITIONAL CONCERNS

### Operational Readiness

- **No request ID middleware** — can't trace requests across services
- **No structured security audit log** — failed auth, IDOR denials, and rate limit violations logged at WARNING but not in a searchable format
- **PII in logs** — email addresses logged in notification service; potential GDPR/privacy concern
- **Print statements in production** — `jurisdiction_detector.py` and `rule_ingestion_service.py` use `print()` instead of `logger`
- **No health check for dependencies** — `/health` endpoint checks scheduler but not database, Redis, or Claude API availability

### Code Organization

- `rules_engine.py` is 3,504 lines — should be broken into smaller modules
- `document_service.py` is 1,307 lines
- `authority_core.py` (router) has 58 endpoints — consider splitting by sub-domain
- Deadline model has 80+ fields — consider splitting into Deadline + DeadlineApproval + DeadlineMetrics

---

## 10. PRIORITIZED RECOMMENDATIONS

### P0 — Fix Today (Security Critical)

1. **Add user_id filtering to all Inbox API endpoints and service methods**
2. **Remove DEV_AUTH_BYPASS from `complete_signup` and `firebase_auth.py`**
3. **Replace `**action_data` spread and `setattr()` loops with explicit field allowlists**

### P1 — Fix This Week (Security High)

4. Add `@limiter.limit("20/minute")` to all chat, AI, RAG, and harvest endpoints
5. Replace all 42 instances of `detail=str(e)` with generic error messages
6. Add Content-Security-Policy header to SecurityHeadersMiddleware
7. Restrict CORS `allow_headers` and `expose_headers` to specific values
8. Add file size validation to document upload endpoint

### P2 — Fix This Sprint (Quality + Performance)

9. Add composite indexes for top query patterns (deadline, document, chat, authority rules)
10. Add `joinedload`/`selectinload` to high-frequency Deadline queries
11. Fix all `catch (err: any)` → `catch (err: unknown)` in frontend (32 instances)
12. Add ARIA attributes to modals, forms, buttons, and loading states
13. Implement negative day support in AuthoritativeDeadlineCalculator
14. Add request ID/correlation middleware
15. Add `back_populates` to all unidirectional relationships

### P3 — Fix This Quarter (Testing + Hardening)

16. Write API endpoint tests with TestClient for all 26 routers
17. Write security tests (IDOR, auth edge cases, rate limiting)
18. Set up frontend test infrastructure (Jest/Vitest + testing-library)
19. Add startup validation for Authority Core rule completeness
20. Reduce token expiration to 24 hours with refresh token support
21. Add token revocation mechanism
22. Implement consistent soft-delete across all models
23. Add structured security audit logging
24. Add unique constraint on CaseAccess(case_id, invited_email)

### P4 — Future Improvements

25. Break `rules_engine.py` (3,504 lines) into smaller modules
26. Consider Deadline model decomposition
27. Add circuit breaker for Claude API calls
28. Implement query caching layer (React Query) on frontend
29. Replace slowapi with maintained rate-limiting library
30. Performance benchmark with realistic data volumes (1M+ deadlines)

---

## 11. WHAT'S WORKING WELL

It's important to acknowledge what this project does right:

1. **Deadline calculation engine** — The authoritative calculator with full transparency and legal citations is production-quality. Every deadline gets a step-by-step calculation basis that could be presented in court.

2. **Auth architecture** — Firebase + JWT token exchange is a solid pattern. The ownership check consistency (117 instances across the codebase) shows security-first thinking.

3. **Frontend organization** — Clean App Router structure, comprehensive TypeScript interfaces, and the event bus pattern show good React architecture.

4. **Schema comprehensiveness** — 51 models covering cases, deadlines, documents, jurisdictions, rules, collaboration, audit trails, and AI agents is ambitious and well-structured.

5. **AI document analysis** — The prompt engineering for date extraction, confidence scoring, and verification gates shows thoughtful human-in-the-loop design for a legal context.

6. **Security middleware** — Rate limiting tiers, security headers, CORS configuration (despite needing tightening) show the right priorities for legal software.

7. **Audit trail system** — The cryptographic audit trail (migration 003) is exactly what legal software needs.

---

## Conclusion

LitDocket has a **strong architectural foundation** that demonstrates security-first thinking and deep domain expertise in legal deadline management. The core deadline calculator is genuinely excellent — transparent, auditable, and legally defensible.

The primary risks are:
- **Two critical IDOR/auth vulnerabilities** that need immediate fixes
- **Near-zero test coverage** on API endpoints and security, meaning bugs like the Inbox IDOR go undetected
- **Database performance** will degrade at scale without composite indexes and eager loading
- **Negative deadline chains** (trial prep deadlines) bypass the authoritative calculator

With the P0 and P1 fixes applied and a serious investment in test coverage, this could be a production-ready legal technology platform. The bones are good — it needs hardening.
