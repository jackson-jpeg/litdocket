# LitDocket Implementation Plan
**Generated:** 2026-01-09
**Status:** Ready for Execution

> **Goal:** Fix integration mismatches, complete partially-implemented features, and prepare for production deployment.

---

## 📊 Current State Assessment

**Overall Code Quality:** 8.5/10
**Integration Health:** 75% (good foundation, specific gaps)
**Production Readiness:** 65% (core features work, critical fixes needed)

**Critical Issues:** 4
**High Priority Issues:** 5
**Medium Priority Issues:** 11

---

## 🎯 Implementation Phases

### **PHASE 0: Foundation Fixes** (Week 1 - CRITICAL)
*Must be completed before other work. Blocks production deployment.*

| # | Task | File(s) | Severity | Est. |
|---|------|---------|----------|------|
| 0.1 | Fix deadline date update endpoint mismatch | `frontend/app/(protected)/cases/[caseId]/page.tsx:98` | 🔴 CRITICAL | 1h |
| 0.2 | Implement full case update endpoint | `backend/app/api/v1/cases.py` | 🔴 CRITICAL | 3h |
| 0.3 | Implement full deadline update endpoint | `backend/app/api/v1/deadlines.py` | 🔴 CRITICAL | 2h |
| 0.4 | Verify dashboard response structure | `backend/app/services/dashboard_service.py` + frontend | 🔴 CRITICAL | 2h |
| 0.5 | Remove Firebase credentials from repo | `.gitignore`, repo history | 🔴 CRITICAL | 1h |
| 0.6 | Add document download endpoint | `backend/app/api/v1/documents.py` | 🟡 HIGH | 2h |

**Phase 0 Total:** 11 hours (~2 days)

---

### **PHASE 1: API Integration Hardening** (Week 1-2 - HIGH)
*Fix all API mismatches and error handling gaps.*

#### 1.1 Backend API Completeness

| # | Task | Description | Est. |
|---|------|-------------|------|
| 1.1.1 | **Case CRUD Completion** | Add `PATCH /api/v1/cases/{id}` with full update<br>Fields: court, judge, jurisdiction, parties, case_type, metadata | 3h |
| 1.1.2 | **Deadline CRUD Completion** | Add `PATCH /api/v1/deadlines/{id}` for full edit<br>Fields: title, description, priority, party_role, action_required | 2h |
| 1.1.3 | **Document Download Endpoint** | Add `GET /api/v1/documents/{id}/download`<br>Serve file from storage_path or Firebase Storage | 2h |
| 1.1.4 | **Case List with Stats** | Add `?include_stats=true` to `GET /api/v1/cases`<br>Include: doc_count, deadline_counts, last_activity | 3h |

#### 1.2 Frontend API Call Fixes

| # | Task | File | Est. |
|---|------|------|------|
| 1.2.1 | Fix deadline reschedule calls | `frontend/app/(protected)/cases/[caseId]/page.tsx:98` | 30m |
| 1.2.2 | Fix trigger update required fields | `frontend/components/cases/triggers/TriggerEventsPanel.tsx:36` | 30m |
| 1.2.3 | Add comprehensive error handling | All components with API calls | 4h |
| 1.2.4 | Fix bulk delete error handling | `frontend/components/cases/deadlines/DeadlineListPanel.tsx:208` | 1h |
| 1.2.5 | Improve upload error messages | `frontend/app/(protected)/dashboard/page.tsx:145-155` | 1h |

#### 1.3 Error Handling Infrastructure

| # | Task | Description | Est. |
|---|------|-------------|------|
| 1.3.1 | Add global ErrorBoundary | Create `frontend/components/ErrorBoundary.tsx`<br>Wrap app in error boundary with fallback UI | 2h |
| 1.3.2 | Standardize error response format | Backend: Consistent `{ detail, error_code, error_type }`<br>Frontend: Type-safe error handling | 3h |
| 1.3.3 | Add API response logging | Development-only API call/response logger | 2h |

**Phase 1 Total:** 24 hours (~3 days)

---

### **PHASE 2: Feature Completion** (Week 2-3 - MEDIUM/HIGH)
*Complete partially-implemented features.*

#### 2.1 Case Management

| # | Task | Description | Est. |
|---|------|-------------|------|
| 2.1.1 | **Case Edit Modal** | Create `frontend/components/cases/EditCaseModal.tsx`<br>Full CRUD for case metadata (court, judge, parties, etc.) | 4h |
| 2.1.2 | **Case Timeline View** | Create `frontend/components/cases/CaseTimeline.tsx`<br>Use existing `GET /api/v1/cases/{id}/timeline` endpoint | 3h |
| 2.1.3 | **Case Delete with Confirmation** | Add delete to case context menu<br>Confirmation modal with cascading delete warning | 2h |

#### 2.2 Deadline Management

| # | Task | Description | Est. |
|---|------|-------------|------|
| 2.2.1 | **Full Deadline Edit Modal** | Enhance `DeadlineDetailModal.tsx`<br>Edit all fields: title, description, priority, rule, party_role | 3h |
| 2.2.2 | **Deadline Bulk Operations** | Bulk status change, bulk reschedule, bulk delete<br>Use existing bulk endpoints or implement | 4h |
| 2.2.3 | **Deadline Comments/Notes** | Add notes field to deadline model and UI<br>Track modification history | 3h |

#### 2.3 Document Management

| # | Task | Description | Est. |
|---|------|-------------|------|
| 2.3.1 | **Document Tagging UI** | Add tag selector to document cards<br>Backend endpoints already exist | 3h |
| 2.3.2 | **Bulk Document Upload** | Multi-file dropzone<br>Use existing `POST /api/v1/documents/bulk-upload` | 2h |
| 2.3.3 | **Document Preview/Viewer** | PDF viewer modal with Firebase Storage integration | 4h |
| 2.3.4 | **Document Metadata Edit** | Edit document type, filing date, received date | 2h |

#### 2.4 Trigger Management

| # | Task | Description | Est. |
|---|------|-------------|------|
| 2.4.1 | **Cascade Preview UI** | Show "What will change" table in EditTriggerModal<br>Use existing `GET /api/v1/triggers/{id}/preview-cascade` | 3h |
| 2.4.2 | **Trigger Delete Protection** | Prevent accidental deletion if has dependent deadlines<br>Confirmation modal with impact summary | 2h |
| 2.4.3 | **Trigger History/Audit** | Show trigger modification history<br>Who changed dates, when, and why | 3h |

**Phase 2 Total:** 38 hours (~5 days)

---

### **PHASE 3: Security & Performance** (Week 3-4 - CRITICAL/HIGH)
*Production readiness requirements.*

#### 3.1 Security Hardening

| # | Task | Description | Est. |
|---|------|-------------|------|
| 3.1.1 | **Migrate JWT to httpOnly Cookies** | Backend: Set JWT in secure httpOnly cookie<br>Frontend: Remove localStorage, use cookie automatically | 6h |
| 3.1.2 | **S3 Storage Implementation** | Replace `/tmp/` file storage with S3/Firebase Storage<br>Update document upload/download flow | 8h |
| 3.1.3 | **Remove DEV_AUTH_BYPASS** | Audit all auth bypass code<br>Ensure never enabled in production | 2h |
| 3.1.4 | **Add Rate Limiting Headers** | Return rate limit info in response headers<br>Show rate limit warnings to users | 2h |
| 3.1.5 | **Comprehensive Health Checks** | Add `/health/live` and `/health/ready` endpoints<br>Check: DB, Anthropic API, Firebase, Storage | 3h |

#### 3.2 Performance Optimization

| # | Task | Description | Est. |
|---|------|-------------|------|
| 3.2.1 | **Case List Optimization** | Implement `include_stats=true` parameter<br>Single query instead of N+1 | 3h |
| 3.2.2 | **Dashboard Caching** | Add Redis caching for dashboard data<br>Cache TTL: 5 minutes, invalidate on updates | 4h |
| 3.2.3 | **Calendar Pagination** | Add date range filtering to calendar<br>Lazy load months as user navigates | 3h |
| 3.2.4 | **Database Indexes** | Add indexes on:<br>- `deadlines.deadline_date`<br>- `deadlines.priority`<br>- `deadlines.status`<br>- `documents.analysis_status` | 2h |
| 3.2.5 | **Frontend Code Splitting** | Lazy load heavy components (PDF viewer, calendar)<br>Reduce initial bundle size | 4h |

#### 3.3 Monitoring & Observability

| # | Task | Description | Est. |
|---|------|-------------|------|
| 3.3.1 | **Request ID Middleware** | Add correlation IDs to all requests<br>Log request/response for debugging | 2h |
| 3.3.2 | **Error Tracking (Sentry)** | Add Sentry to frontend and backend<br>Track errors, performance, user sessions | 3h |
| 3.3.3 | **API Analytics** | Track endpoint usage, response times, error rates<br>Dashboard for monitoring | 4h |

**Phase 3 Total:** 46 hours (~6 days)

---

### **PHASE 4: User Experience Polish** (Week 4-5 - MEDIUM)
*Nice-to-have features that improve UX.*

#### 4.1 Navigation & Search

| # | Task | Description | Est. |
|---|------|-------------|------|
| 4.1.1 | **Global Search Improvements** | Add search filters: by case, by date range, by type<br>Show search result counts | 3h |
| 4.1.2 | **Recent Items Dropdown** | Quick access to recently viewed cases<br>Store in localStorage | 2h |
| 4.1.3 | **Keyboard Shortcuts Help** | Add Cmd/Ctrl+? modal showing all shortcuts<br>Discoverable keyboard navigation | 2h |

#### 4.2 Notifications & Alerts

| # | Task | Description | Est. |
|---|------|-------------|------|
| 4.2.1 | **Email Notification Service** | Implement actual email sending<br>Use SendGrid/AWS SES | 4h |
| 4.2.2 | **Push Notifications** | Browser push notifications for urgent deadlines<br>Service worker setup | 6h |
| 4.2.3 | **Notification Center** | Inbox-style notification center in header<br>Mark as read, dismiss, snooze | 4h |

#### 4.3 AI Features

| # | Task | Description | Est. |
|---|------|-------------|------|
| 4.3.1 | **Morning Report Enhancement** | Verify AI service implementation<br>Add personalization based on user preferences | 4h |
| 4.3.2 | **Smart Document Suggestions** | AI suggests which case to attach document to<br>Show confidence scores | 3h |
| 4.3.3 | **Deadline Risk Scoring** | AI analyzes deadline complexity and risk<br>Flag high-risk deadlines | 4h |

#### 4.4 Mobile Responsiveness

| # | Task | Description | Est. |
|---|------|-------------|------|
| 4.4.1 | **Mobile Case Room** | Optimize 3-pane cockpit layout for mobile<br>Collapsible panels, swipe gestures | 6h |
| 4.4.2 | **Mobile Calendar** | Touch-friendly calendar navigation<br>Swipe between months | 3h |
| 4.4.3 | **Mobile Document Upload** | Camera integration for mobile uploads<br>Optimize for 4G/5G bandwidth | 3h |

**Phase 4 Total:** 44 hours (~6 days)

---

### **PHASE 5: Production Deployment** (Week 5-6 - CRITICAL)
*Final production prep.*

#### 5.1 Testing

| # | Task | Description | Est. |
|---|------|-------------|------|
| 5.1.1 | **Integration Test Suite** | E2E tests for critical flows:<br>- Document upload → deadline extraction<br>- Trigger creation → cascade generation<br>- Case creation → full workflow | 12h |
| 5.1.2 | **API Contract Tests** | Validate all API responses match frontend types<br>Catch breaking changes early | 6h |
| 5.1.3 | **Load Testing** | Simulate 100 concurrent users<br>Identify bottlenecks and optimize | 8h |
| 5.1.4 | **Security Audit** | OWASP Top 10 checklist<br>SQL injection, XSS, CSRF, IDOR tests | 8h |

#### 5.2 Documentation

| # | Task | Description | Est. |
|---|------|-------------|------|
| 5.2.1 | **API Documentation** | Complete Swagger/OpenAPI docs<br>Add examples for all endpoints | 4h |
| 5.2.2 | **Deployment Guide** | Step-by-step production deployment<br>Environment variables, secrets management | 3h |
| 5.2.3 | **User Guide** | Basic user documentation<br>Screenshots and tutorials | 6h |
| 5.2.4 | **Runbook** | Operations playbook<br>Common issues and resolutions | 4h |

#### 5.3 Infrastructure

| # | Task | Description | Est. |
|---|------|-------------|------|
| 5.3.1 | **CI/CD Pipeline** | GitHub Actions for:<br>- Automated tests<br>- Linting and type checking<br>- Deployment to Railway/Vercel | 6h |
| 5.3.2 | **Database Backups** | Automated daily backups to S3<br>Point-in-time recovery setup | 4h |
| 5.3.3 | **Environment Separation** | Staging environment for testing<br>Production environment locked down | 4h |
| 5.3.4 | **Domain & SSL** | Configure custom domain<br>SSL certificates for production | 2h |

**Phase 5 Total:** 67 hours (~9 days)

---

## 📅 Timeline Summary

| Phase | Duration | Priority | Dependencies |
|-------|----------|----------|--------------|
| **Phase 0:** Foundation Fixes | 2 days | 🔴 CRITICAL | None - start here |
| **Phase 1:** API Integration | 3 days | 🟡 HIGH | Phase 0 complete |
| **Phase 2:** Feature Completion | 5 days | 🟡 MEDIUM | Phase 1 complete |
| **Phase 3:** Security & Performance | 6 days | 🔴 CRITICAL | Phase 1 complete |
| **Phase 4:** UX Polish | 6 days | 🟢 LOW | Phase 2 complete |
| **Phase 5:** Production Prep | 9 days | 🔴 CRITICAL | Phases 1-3 complete |

**Total Estimated Time:** 31 days (~6 weeks for 1 developer)

**Recommended Order:**
1. **Week 1:** Phase 0 + Start Phase 1
2. **Week 2:** Complete Phase 1 + Start Phase 3 (security)
3. **Week 3:** Complete Phase 3 + Start Phase 2
4. **Week 4:** Complete Phase 2 + Start Phase 4
5. **Week 5:** Complete Phase 4 + Start Phase 5
6. **Week 6:** Complete Phase 5 + Final testing

---

## 🚀 Quick Start Guide

### To Begin Implementation:

```bash
# 1. Create a feature branch
git checkout -b feature/implementation-plan

# 2. Start with Phase 0, Task 0.1 (critical fix)
# File: frontend/app/(protected)/cases/[caseId]/page.tsx

# 3. Track progress using this document
# Mark tasks complete as you go
```

### Task Tracking Template:

```markdown
## Task 0.1: Fix deadline date update endpoint
- [ ] Read current implementation
- [ ] Update API call to use /reschedule endpoint
- [ ] Add required fields (new_date, reason)
- [ ] Test with real backend
- [ ] Commit: "fix(deadlines): use correct reschedule endpoint"
```

---

## 🎯 Success Metrics

### Phase 0 Complete When:
- [ ] All critical API mismatches resolved
- [ ] Dashboard loads without errors
- [ ] Deadline updates work end-to-end
- [ ] Case updates work end-to-end

### Phase 1 Complete When:
- [ ] All API calls have proper error handling
- [ ] No console errors on any page
- [ ] Error boundary catches and displays crashes
- [ ] API integration tests pass

### Phase 3 Complete When:
- [ ] JWT in httpOnly cookies
- [ ] S3 storage operational
- [ ] Health checks return 200
- [ ] Case list loads in <500ms for 50 cases

### Production Ready When:
- [ ] All Phase 0, 1, 3, 5 tasks complete
- [ ] Load tests pass (100 concurrent users)
- [ ] Security audit complete
- [ ] Staging deployment successful
- [ ] User acceptance testing complete

---

## 📝 Notes

### Design Decisions Made:
1. **JWT Migration:** Use httpOnly cookies for better security
2. **Storage:** S3 for documents (scalable, reliable)
3. **Caching:** Redis for dashboard (5-minute TTL)
4. **Error Tracking:** Sentry (industry standard)
5. **Testing:** Playwright for E2E tests

### Questions to Resolve:
1. **Backend Framework:** Confirm Python 3.11+ for all environments
2. **Database:** PostgreSQL version and connection pool size
3. **Storage Provider:** AWS S3 vs Firebase Storage vs other?
4. **Email Provider:** SendGrid vs AWS SES vs other?
5. **Deployment:** Confirm Railway for backend, Vercel for frontend

### Risk Mitigation:
- **Risk:** JWT cookie migration breaks auth
  - **Mitigation:** Feature flag, test thoroughly in staging
- **Risk:** S3 migration loses documents
  - **Mitigation:** Dual-write during migration, verify all uploads
- **Risk:** Performance regressions
  - **Mitigation:** Benchmark before/after, monitor production metrics

---

## 🤝 Getting Help

- **Stuck on a task?** Ask Claude to drill into specific implementation details
- **Need code review?** Use `/review-pr` skill for automated feedback
- **Deployment issues?** Check CLAUDE.md for environment setup

**Ready to start? Begin with Phase 0, Task 0.1!**
