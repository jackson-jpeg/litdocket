# Authority Core Implementation Guide
## Fully Automated AI-Powered Docketing System

**Status:** Phase 3 Complete (3/6 phases) | **Timeline:** 3 months remaining

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Completed Phases (1-3)](#completed-phases-1-3)
3. [Remaining Phases (4-6)](#remaining-phases-4-6)
4. [How to Follow This Guide](#how-to-follow-this-guide)
5. [Success Metrics](#success-metrics)
6. [Resource Requirements](#resource-requirements)

---

## Executive Summary

### Vision
Transform LitDocket from hardcoded rules to a fully automated, database-driven docketing system that:
- Discovers and extracts court rules automatically
- Requires no code changes for new jurisdictions
- Self-heals when scrapers break
- Scales to 200+ jurisdictions

### Current Status: ✅ 50% Complete

| Phase | Status | Duration | Completion Date |
|-------|--------|----------|-----------------|
| **Phase 1:** Background Job Infrastructure | ✅ Complete | 1-2 weeks | Feb 9, 2026 |
| **Phase 2:** Hardcoded to Database Migration | ✅ Complete | 2-3 weeks | Feb 9, 2026 |
| **Phase 3:** Auto-Harvest Foundation | ✅ Complete | 2-3 weeks | Feb 9, 2026 |
| **Phase 4:** Chat Integration | ⏳ Pending | 3-4 weeks | Est. Mar 2, 2026 |
| **Phase 5:** Multi-Jurisdiction Scaling | ⏳ Pending | 3-4 weeks | Est. Mar 30, 2026 |
| **Phase 6:** Advanced Intelligence | ⏳ Pending | 2-3 weeks | Est. Apr 20, 2026 |

### Key Achievements So Far

✅ **100%** of deadlines now use Authority Core (was 0%)
✅ **29** hardcoded rules migrated to database
✅ **0** hardcoded rules remain
✅ **8-step** automated harvest pipeline operational
✅ **4** scheduled background jobs running
✅ **Email notifications** for harvest events
✅ **Confidence scoring** algorithm implemented

---

## Completed Phases (1-3)

### ✅ Phase 1: Background Job Infrastructure

**Goal:** Enable automated execution of harvesting tasks

**Delivered:**
- APScheduler integration with job persistence
- 4 scheduled jobs:
  - Daily Watchtower (6am UTC)
  - Weekly Watchtower (Sunday 3am UTC)
  - Scraper health check (5am UTC)
  - Inbox cleanup (2am UTC)
- Manual trigger API endpoints for on-demand execution
- SendGrid email notification system

**Files Modified:**
- `/backend/app/scheduler/__init__.py` (NEW)
- `/backend/app/scheduler/jobs.py` (NEW)
- `/backend/app/services/authority_notification_service.py` (NEW)
- `/backend/app/api/v1/authority_core.py` (5 new endpoints)
- `/backend/app/main.py` (scheduler integration)

**Verification:**
```bash
curl http://localhost:8000/health
# Should show: "scheduler": {"running": true, "jobs": [...]}
```

---

### ✅ Phase 2: Hardcoded to Database Migration

**Goal:** Eliminate all hardcoded rules

**Delivered:**
- **Critical Bug Fixed:** Authority Core parameter mismatch (was calling `start_date=...`, should be `trigger_date=...`)
- Feature flag `USE_AUTHORITY_CORE=true` (default)
- Hardcoded rules disabled via `LOAD_HARDCODED_RULES=false` (default)
- Migration script executed (29 rules migrated)
- 100% Authority Core usage verified

**Key Stats:**
- **Before:** 100% hardcoded rules
- **After:** 100% Authority Core rules
- **Test:** 49/49 deadlines with source_rule_id populated

**Files Modified:**
- `/backend/app/services/authority_core_service.py` (bug fix lines 1025-1041)
- `/backend/app/services/rules_engine.py` (deprecation + feature flag)

**Verification:**
```sql
SELECT COUNT(*) as total,
       SUM(CASE WHEN source_rule_id IS NOT NULL THEN 1 ELSE 0 END) as from_authority_core
FROM deadlines
WHERE created_at > NOW() - INTERVAL '7 days';
-- Result: 100% from Authority Core
```

---

### ✅ Phase 3: Auto-Harvest Foundation

**Goal:** Enable automated rule harvesting with attorney approval workflow

**Delivered:**
- **End-to-end 8-step pipeline:**
  1. Admin adds jurisdiction
  2. Cartographer discovers CSS selectors
  3. Extract rules via AI
  4. Create AuthorityRule proposals
  5. ✨ **NEW:** Create inbox items automatically
  6. Attorney reviews via inbox API
  7. ✨ **NEW:** Approval creates AuthorityRule (integrated)
  8. Watchtower monitors for changes

- **Confidence scoring algorithm:**
  - Has rule code: +30 points
  - Specific trigger: +20 points
  - Has deadlines: +20 points
  - Has citations: +15 points
  - Clean text: +15 points

- **Auto-approval thresholds:**
  - ≥95%: Auto-approve + notify
  - ≥80%: Recommend approval
  - <80%: Require manual review

**Key Integrations:**
- `AuthorityCoreService.create_proposal()` → `InboxService.create_inbox_item()`
- `InboxService.review_item()` → `AuthorityCoreService.approve_proposal()`

**Files Modified:**
- `/backend/app/services/authority_core_service.py` (inbox integration)
- `/backend/app/services/inbox_service.py` (proposal approval integration)
- `/backend/app/services/rule_extraction_service.py` (confidence calculation)

**Testing Guide:**
- See `/backend/PHASE3_TESTING_GUIDE.md` for pilot jurisdiction testing procedures

**Frontend TODO:**
- See `/FRONTEND_INBOX_TODO.md` for inbox UI implementation guide (deferred to future sprint)

**Verification:**
```bash
# Test harvest pipeline
curl -X POST http://localhost:8000/api/v1/authority-core/harvest \
  -d '{"jurisdiction_id": "...", "url": "https://example.com/rules"}'

# Check inbox items created
curl http://localhost:8000/api/v1/inbox?type=RULE_VERIFICATION
```

---

## Remaining Phases (4-6)

### ⏳ Phase 4: Chat Integration - AI-Powered Docketing

**Duration:** 3-4 weeks (20-30 hours)

**Goal:** Enable Claude to use Authority Core rules for all docketing operations

#### Deliverables:

**1. Expand Authority Core Chat Tools** (8-10 hours)
Add 9 new chat tools to existing `chat_tools.py`:

- **Primary tool:** `find_applicable_rules(jurisdiction_id, trigger_type, court_type)`
  - This is the MAIN docketing tool
  - Claude will call this instead of using hardcoded rules
  - Returns applicable AuthorityRule entries with confidence scores

- **Supporting tools:**
  - `compare_rules_across_jurisdictions(rule_code, jurisdictions[])`
  - `get_rule_history(rule_id)` - Show version timeline with diffs
  - `validate_deadline_against_rules(case_id, deadline_id)`
  - `generate_all_deadlines_for_case(case_id, trigger_type, trigger_date)`
  - `analyze_rule_coverage(jurisdiction_id)` - Identify gaps
  - `explain_deadline_from_rule(rule_id, trigger_date)` - Step-by-step calculation
  - `suggest_related_rules(rule_id)` - Proactive recommendations
  - `request_jurisdiction_harvest(jurisdiction_name, court_website)` - Admin tool

**2. Update Chat System Prompt** (2-3 hours)
Modify `/backend/app/services/streaming_chat_service.py`:

```python
SYSTEM_PROMPT = """
You are a legal docketing assistant with access to Authority Core,
a database of 29+ verified court rules from 14+ jurisdictions.

When calculating deadlines:
1. ALWAYS call find_applicable_rules() first
2. Use returned AuthorityRule entries (not hardcoded rules)
3. Show confidence scores for each deadline
4. Cite the specific rule (e.g., "Fla. R. Civ. P. 1.140(a) - confidence: 92%")

Confidence handling:
- High (≥90%): Auto-act and inform user
- Medium (80-89%): Recommend with caveat
- Low (<80%): Require explicit user confirmation

Transparency requirements:
- ALWAYS cite the rule and confidence score
- Explain calculation method (calendar vs business days)
- Note any service method extensions applied
- Link to full rule details

You have access to {total_rules} verified rules across {jurisdiction_count} jurisdictions.
"""
```

**3. Enhance Tool Execution** (4-6 hours)
Update `ChatToolExecutor` class:

```python
class ChatToolExecutor:
    def __init__(self, db: Session):
        self.db = db
        self.authority_service = AuthorityCoreService(db)
        self.deadline_service = AuthorityIntegratedDeadlineService(db)

    async def execute_find_applicable_rules(self, **kwargs):
        """
        PRIMARY DOCKETING TOOL

        Finds rules from Authority Core, not hardcoded templates.
        Sorts by confidence score + authority tier.
        """
        rules = await self.authority_service.get_effective_rules(
            jurisdiction_id=kwargs['jurisdiction_id'],
            trigger_type=kwargs['trigger_type'],
            court_type=kwargs.get('court_type'),
            case_context=kwargs.get('case_context')
        )

        # Sort by confidence (desc) and authority tier (federal > state > local)
        sorted_rules = sorted(
            rules,
            key=lambda r: (r.confidence_score, r.authority_tier.value),
            reverse=True
        )

        return [{
            "rule_id": r.id,
            "rule_code": r.rule_code,
            "rule_name": r.rule_name,
            "citation": r.citation,
            "trigger_type": r.trigger_type,
            "deadlines_count": len(r.deadlines),
            "confidence": r.confidence_score,
            "authority_tier": r.authority_tier.value
        } for r in sorted_rules]
```

**4. Frontend Chat UX** (6-8 hours)
Create components for displaying Authority Core rule results:

```typescript
// /frontend/components/chat/RuleCard.tsx
<RuleCard>
  <RuleHeader>
    <RuleCode>{rule.rule_code}</RuleCode>
    <ConfidenceBadge score={rule.confidence} />
  </RuleHeader>
  <RuleName>{rule.rule_name}</RuleName>
  <Citation>{rule.citation}</Citation>
  <DeadlineCount>{rule.deadlines_count} deadlines</DeadlineCount>
  <ViewRuleButton />
</RuleCard>

// /frontend/components/chat/RuleComparisonTable.tsx
// Side-by-side comparison of rules across jurisdictions
```

#### Success Criteria:
- [ ] Claude generates deadlines using Authority Core for 95%+ of requests
- [ ] Zero usage of hardcoded rules in chat
- [ ] Average confidence score ≥ 85%
- [ ] Every deadline explained with full citation trail
- [ ] User satisfaction: 8/10+ on "accuracy of AI-generated deadlines"

#### Files to Modify:
- `/backend/app/services/chat_tools.py` (9 new tools)
- `/backend/app/services/streaming_chat_service.py` (system prompt)
- `/backend/app/services/authority_core_service.py` (enhanced search)
- `/frontend/components/chat/RuleCard.tsx` (NEW)
- `/frontend/components/chat/ConfidenceBadge.tsx` (NEW)
- `/frontend/components/chat/RuleComparisonTable.tsx` (NEW)

#### Verification:
```typescript
// In chat: "Set up my Florida civil case with trial on June 15, 2026"

// Expected response should include:
// - "Found 12 applicable rules in Authority Core"
// - Confidence scores for each deadline
// - Full citations (e.g., "Fla. R. Civ. P. 1.440(a) - confidence: 92%")

// Verify in database:
SELECT COUNT(*) as total_deadlines,
       SUM(CASE WHEN source = 'authority_core' THEN 1 ELSE 0 END) as from_authority
FROM deadline_audit_logs
WHERE created_at > NOW() - INTERVAL '7 days';
// from_authority should be >95% of total
```

---

### ⏳ Phase 5: Multi-Jurisdiction Scaling

**Duration:** 3-4 weeks (24-32 hours)

**Goal:** Scale automated harvesting to 50+ jurisdictions with operational maturity

#### Deliverables:

**1. Jurisdiction Onboarding Automation** (6-8 hours)

Create `/backend/app/services/jurisdiction_onboarding_service.py`:

```python
class JurisdictionOnboardingService:
    async def onboard_jurisdiction(
        self,
        name: str,
        court_website: str,
        court_type: str = "civil"
    ) -> OnboardingResult:
        """
        End-to-end automated onboarding workflow.

        Steps:
        1. Validate URL is accessible
        2. Run Cartographer to discover scraper config
        3. Auto-harvest if confidence ≥85
        4. Create Watchtower baseline
        5. Set sync schedule based on jurisdiction type
        6. Generate onboarding report

        Returns OnboardingResult with success/failure and metrics.
        """
```

API Endpoint:
```bash
POST /api/v1/authority-core/jurisdictions/onboard
{
  "name": "California Superior Court",
  "court_website": "https://www.courts.ca.gov/",
  "court_type": "civil",
  "auto_harvest": true  # If confidence ≥85
}
```

**2. Scraper Template Library** (4-6 hours)

Create `/backend/app/services/scraper_templates.py`:

```python
# Reusable templates for common CMS platforms
TEMPLATES = {
    "judicare": {
        "selectors": {
            "rule_links": "div.rule-list a.rule-link",
            "rule_text": "div.rule-content",
            "citation": "span.citation"
        },
        "confidence": 0.95  # High confidence for known platform
    },
    "wordpress_courts": {
        "selectors": {
            "rule_links": "article.rule a",
            "rule_text": "div.entry-content",
            "citation": "h2.rule-number"
        },
        "confidence": 0.90
    },
    "legacy_html": {
        # Fallback for older sites
        "selectors": {
            "rule_links": "a[href*='rule']",
            "rule_text": "body main",
            "citation": "h1, h2"
        },
        "confidence": 0.70  # Lower confidence
    }
}

def match_template(url: str, html: str) -> Optional[str]:
    """
    Auto-detect which template matches the site structure.
    Reduces Cartographer API calls by 50%.
    """
```

**3. Batch Operations** (6-8 hours)

```python
@router.post("/jurisdictions/batch-onboard")
async def batch_onboard_jurisdictions(
    batch: BatchOnboardRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Onboard 50+ jurisdictions in parallel.

    Features:
    - Queue-based processing (max 10 concurrent)
    - Progress tracking via batch_id
    - Email notification on completion
    - Retry failed jurisdictions
    """
```

**4. Scraper Diversity Handling** (4-6 hours)

Handle different website types:

```python
class ScraperDiversityHandler:
    async def handle_javascript_site(self, url: str):
        """
        Use Playwright for JS-rendered sites.
        Set requires_js: true flag.
        """
        from playwright.async_api import async_playwright
        # Render with headless browser

    async def handle_pdf_rules(self, url: str):
        """
        Extract text from PDF-based rules.
        Apply -20 confidence penalty.
        """
        import pdfplumber
        # Extract and parse PDF

    async def handle_authenticated_site(self, url: str):
        """
        Manual scraping workflow.
        Set requires_auth: true flag.
        Create inbox item for admin to provide credentials.
        """

    async def handle_rate_limited_site(self, url: str):
        """
        Respect robots.txt.
        Exponential backoff on 429 errors.
        """
```

**5. Operational Dashboards** (6-8 hours)

Frontend pages:

```typescript
// /frontend/app/(protected)/admin/harvest/page.tsx
<HarvestDashboard>
  <JobQueue />
  <RetryFailedJobs />
  <CoverageHeatmap />  {/* Map showing jurisdiction coverage */}
</HarvestDashboard>

// /frontend/app/(protected)/admin/scraper-health/page.tsx
<ScraperHealthDashboard>
  <HealthSummary />
  <ScraperList />
  <ConfigEditor />
</ScraperHealthDashboard>

// /frontend/app/(protected)/admin/inbox-analytics/page.tsx
<InboxAnalytics>
  <ThroughputMetrics />
  <AttorneyLeaderboard />  {/* Review speed by attorney */}
  <ConfidenceDistribution />
</InboxAnalytics>
```

#### Success Criteria:
- [ ] 50+ jurisdictions onboarded
- [ ] >75% rule coverage per jurisdiction
- [ ] <5% scraper failure rate
- [ ] Batch onboarding completes 50 jurisdictions in <6 hours
- [ ] Scraper template library covers 50% of new jurisdictions

#### Files to Create:
- `/backend/app/services/jurisdiction_onboarding_service.py` (NEW)
- `/backend/app/services/scraper_templates.py` (NEW)
- `/backend/app/services/scraper_diversity_handler.py` (NEW)
- `/frontend/app/(protected)/admin/harvest/page.tsx` (NEW)
- `/frontend/app/(protected)/admin/scraper-health/page.tsx` (NEW)
- `/frontend/app/(protected)/admin/inbox-analytics/page.tsx` (NEW)

---

### ⏳ Phase 6: Advanced Intelligence & Self-Healing

**Duration:** 2-3 weeks (16-24 hours)

**Goal:** Make system fully autonomous with self-healing and advanced AI reasoning

#### Deliverables:

**1. Self-Healing Scrapers** (6-8 hours)

Create `/backend/app/services/self_healing_scraper_service.py`:

```python
class SelfHealingScraperService:
    async def auto_fix_broken_scraper(self, jurisdiction_id: str):
        """
        Auto-fix workflow:

        1. Detect: 3 consecutive failures
        2. Disable: Set auto_sync_enabled=False
        3. Rediscover: Run Cartographer again
        4. Validate: Test new config
        5. If confidence ≥70:
           - Update scraper_config
           - Re-enable auto_sync
           - Notify admin
        6. If rediscovery fails:
           - Create inbox item for manual intervention
        """
```

Target: **80%** auto-fix success rate

**2. AI Rule Conflict Resolution** (4-6 hours)

Create `/backend/app/services/ai_conflict_resolver.py`:

```python
class AIConflictResolver:
    async def resolve_conflict(
        self,
        rule_a: AuthorityRule,
        rule_b: AuthorityRule
    ) -> ConflictResolution:
        """
        Use Claude to analyze conflicting rules.

        Factors:
        - Date of rule (newer takes precedence)
        - Authority tier (federal > state > local)
        - Citation specificity
        - Jurisdiction hierarchy

        If confidence ≥90: Auto-resolve
        If confidence 70-90: Create inbox item with recommendation
        If confidence <70: Flag for attorney review
        """
```

**3. Proactive Rule Recommendations** (3-4 hours)

Create `/backend/app/services/proactive_rule_assistant.py`:

```python
class ProactiveRuleAssistant:
    async def monitor_chat_context(self, message: str, case_id: str):
        """
        Monitor chat for triggers and suggest rules.

        Examples:
        - User uploads "MSJ" document → Suggest response deadline rule
        - User mentions "discovery" → Suggest discovery deadline rules
        - User sets trial date → Suggest pretrial deadline rules

        Non-intrusive suggestions via chat.
        """
```

**4. Rule Update Notifications** (3-4 hours)

Create `/backend/app/services/rule_update_notification_service.py`:

```python
class RuleUpdateNotificationService:
    async def subscribe_to_rule(self, user_id: str, rule_id: str):
        """Subscribe to updates for a rule"""

    async def notify_subscribers(self, rule_id: str, change: RuleChange):
        """
        When Watchtower detects change:
        1. Notify all subscribers
        2. Send email with diff
        3. Create inbox item
        4. Mark as "action required"
        """
```

Target: <5% missed changes

#### Success Criteria:
- [ ] Self-healing fixes 80%+ of scraper failures automatically
- [ ] AI conflict resolution handles 70%+ of conflicts without manual review
- [ ] Proactive suggestions rated 8/10+ for relevance
- [ ] Rule update notifications reduce missed changes to <5%

#### Files to Create:
- `/backend/app/services/self_healing_scraper_service.py` (NEW)
- `/backend/app/services/ai_conflict_resolver.py` (NEW)
- `/backend/app/services/proactive_rule_assistant.py` (NEW)
- `/backend/app/services/rule_update_notification_service.py` (NEW)

---

## How to Follow This Guide

### 1. **Read the Strategic Roadmap First**

Location: Original plan document (this file summarizes it)

Understand the full vision before diving into any phase.

### 2. **Work Sequentially Through Phases**

✅ **DO:** Complete phases in order (4 → 5 → 6)

❌ **DON'T:** Jump ahead to Phase 6 before Phase 4 is done

**Why:** Each phase builds on the previous. Phase 4 (Chat) depends on Phase 3 (Harvest). Phase 5 (Scaling) depends on Phase 4 (Chat).

### 3. **Within Each Phase, Follow This Order:**

#### A. **Read Phase Overview** (10 mins)
- Understand the goal
- Review deliverables
- Check success criteria

#### B. **Review Critical Files** (30-60 mins)
- Read files marked "to modify"
- Understand existing code structure
- Identify integration points

#### C. **Implement Incrementally** (varies by phase)

**Example for Phase 4:**

Day 1-2: Add 3 core chat tools (`find_applicable_rules`, `generate_all_deadlines_for_case`, `explain_deadline_from_rule`)

Day 3-4: Add 6 supporting tools

Day 5-6: Update system prompt and test with Claude

Day 7-8: Build frontend RuleCard component

Day 9-10: Integration testing and polish

#### D. **Test Thoroughly** (20% of implementation time)
- Unit tests for new functions
- Integration tests for workflows
- End-to-end tests for user scenarios

#### E. **Verify Success Criteria** (1-2 hours)
- Run all verification queries
- Check metrics match targets
- Document any deviations

#### F. **Update This Guide** (30 mins)
- Mark phase as complete
- Document any changes to plan
- Note lessons learned

### 4. **Use Task Tracking**

Create tasks for each deliverable:

```bash
# Example for Phase 4
Task 1: Add find_applicable_rules tool
Task 2: Add compare_rules_across_jurisdictions tool
Task 3: Add get_rule_history tool
# ... etc
Task 10: Update system prompt
Task 11: Build RuleCard component
Task 12: Integration testing
```

Track progress in project management tool (Jira, Linear, GitHub Issues, etc.)

### 5. **Parallel Work Opportunities**

Some tasks can be done in parallel:

**Phase 4 Example:**
- **Backend dev:** Implement chat tools
- **Frontend dev:** Build RuleCard components
- Both work simultaneously, integrate at end

**Phase 5 Example:**
- **Backend dev:** Scraper diversity handling
- **DevOps:** Batch operation infrastructure
- **Frontend dev:** Admin dashboards

### 6. **Code Review Checkpoints**

Required reviews before moving to next phase:

- [ ] All tests passing
- [ ] Code review by senior engineer
- [ ] Security audit (especially for scrapers)
- [ ] Performance benchmarks met
- [ ] Documentation updated

### 7. **Rollout Strategy**

For each phase:

**Week 1:** Development in feature branch

**Week 2:** Testing in staging environment

**Week 3:** 50% production rollout (A/B test)

**Week 4:** 100% production + monitoring

**Don't rush rollouts!** Legal software requires high reliability.

### 8. **When Things Go Wrong**

**Issue:** Feature is more complex than estimated

**Solution:**
- Break it down into smaller tasks
- Extend timeline (don't cut corners)
- Document the complexity for future reference

**Issue:** Integration doesn't work as expected

**Solution:**
- Check assumptions in the plan
- Review API contracts
- Add integration tests
- Update the plan if architecture needs to change

**Issue:** Performance is worse than expected

**Solution:**
- Profile the bottleneck
- Optimize or add caching
- Consider architectural change if needed
- Update performance targets in plan

### 9. **Documentation as You Go**

Update these documents continuously:

- **This file:** Mark phases complete, note deviations
- **CLAUDE.md:** Update with new features and patterns
- **API docs:** Add new endpoints
- **README:** Update setup instructions
- **CHANGELOG:** Track all changes

### 10. **Celebrate Milestones! 🎉**

After each phase:
- Demo to team/stakeholders
- Collect user feedback
- Share metrics improvements
- Document wins and lessons learned

---

## Success Metrics

### Overall System Metrics

| Metric | Current | Target (End of Phase 6) |
|--------|---------|-------------------------|
| Jurisdictions | 14 | 200+ |
| Rules in database | 29 | 2000+ |
| Hardcoded rules | 0 ✅ | 0 |
| Authority Core usage | 100% ✅ | 100% |
| Scraper uptime | 95% | 95% |
| Self-healing success | N/A | 80% |
| Chat Authority Core usage | 0% | 95% |
| Rule confidence avg | N/A | 85% |
| Attorney satisfaction | N/A | 8/10+ |

### Phase-Specific KPIs

**Phase 4 (Chat Integration):**
- Chat uses Authority Core for 95%+ of docketing requests ✓
- Every deadline has source_rule_id ✓
- Average response includes rule citation ✓

**Phase 5 (Scaling):**
- 50+ jurisdictions onboarded ✓
- <5% scraper failure rate ✓
- Batch processing completes 50 jurisdictions in <6 hours ✓

**Phase 6 (Intelligence):**
- 80%+ self-healing success rate ✓
- 70%+ AI conflict auto-resolution ✓
- <5% missed rule changes ✓

---

## Resource Requirements

### Engineering Team

**Minimum:**
- 1 backend engineer (Python/FastAPI) - 20-30 hrs/week
- 1 frontend engineer (Next.js/React) - 10-15 hrs/week
- 0.5 DevOps engineer - 5-10 hrs/week

**Optimal:**
- 2 backend engineers (parallel work on Phase 4-5)
- 1 frontend engineer
- 1 QA engineer (test automation)
- 0.5 DevOps engineer

### Infrastructure Costs

**Current (Phase 1-3):**
- Railway/Vercel: ~$50/month
- Anthropic API: ~$500/month
- SendGrid: ~$15/month
- PostgreSQL: Included in Railway
- **Total: ~$565/month**

**Projected (Phase 4-6):**
- Railway/Vercel: ~$100/month (more traffic)
- Anthropic API: ~$2000/month (increased chat usage)
- SendGrid: ~$50/month (more emails)
- PostgreSQL: ~$50/month (more data)
- Redis: ~$30/month (caching)
- **Total: ~$2,230/month**

### API Usage

**Anthropic API:**
- Phase 3: ~10K tokens/rule extraction = ~$1/rule
- Phase 4: ~5K tokens/chat interaction = ~$0.50/interaction
- Phase 5: Scaling to 50 jurisdictions = ~$50 one-time
- Phase 6: Conflict resolution = ~$0.10/conflict

**Budget Planning:**
- Initial harvest (200 jurisdictions × 30 rules × $1) = $6,000 one-time
- Ongoing chat usage (1000 interactions/day × $0.50) = $15,000/month at scale
- Watchtower monitoring: Minimal (only checks hashes)

### Time Investment

**Total Remaining:** ~60-90 hours over 3 months

| Phase | Backend | Frontend | DevOps | Testing | Total |
|-------|---------|----------|--------|---------|-------|
| Phase 4 | 20 hrs | 8 hrs | 2 hrs | 5 hrs | **35 hrs** |
| Phase 5 | 24 hrs | 8 hrs | 4 hrs | 6 hrs | **42 hrs** |
| Phase 6 | 16 hrs | 4 hrs | 2 hrs | 4 hrs | **26 hrs** |
| **Total** | **60 hrs** | **20 hrs** | **8 hrs** | **15 hrs** | **103 hrs** |

**Pace:** ~8-10 hours/week = 3 months to completion

---

## Critical Success Factors

### ✅ What's Working Well

1. **Architecture:** Clean separation between hardcoded fallback and Authority Core
2. **Integration:** Proposal → Inbox → AuthorityRule workflow is seamless
3. **Confidence scoring:** Algorithm is conservative (good for legal)
4. **Scheduler:** APScheduler running reliably
5. **Phase 2 bug fix:** Unblocked Authority Core adoption

### ⚠️ Risks to Monitor

1. **Anthropic API costs** scaling faster than expected
   - Mitigation: Cache rule extractions, use Haiku for simple tasks

2. **Scraper maintenance burden** with 200+ jurisdictions
   - Mitigation: Self-healing (Phase 6) will reduce manual fixes

3. **Attorney approval bottleneck** with high rule volume
   - Mitigation: Auto-approval for ≥95% confidence rules

4. **Frontend development** lagging behind backend
   - Mitigation: Prioritize API-first development, frontend can catch up

5. **Complex jurisdiction rules** that AI struggles to extract
   - Mitigation: Manual rule entry workflow + human-in-the-loop

### 🎯 Keys to Success

1. **Test thoroughly at each phase** before moving forward
2. **Keep confidence scoring conservative** (legal accuracy > speed)
3. **Monitor costs** closely (set Anthropic API budget alerts)
4. **Iterate on prompts** based on extraction quality
5. **Involve attorneys early** for feedback on inbox workflow
6. **Document everything** for future maintenance

---

## Conclusion

### Current State (Phase 3 Complete)

You now have:
- ✅ Fully operational harvest pipeline
- ✅ 100% Authority Core deadline calculation
- ✅ Automated background jobs
- ✅ Confidence scoring system
- ✅ Email notifications

### Next Milestone (Phase 4)

Priority: **Get Claude using Authority Core rules in chat**

Impact: Users will experience AI-powered docketing with real-time rule lookups

Timeline: 3-4 weeks

Start with: Implementing `find_applicable_rules` chat tool

### Vision (End of Phase 6)

Fully automated system where:
- New jurisdictions onboard in minutes
- Rules stay current automatically
- System self-heals when scrapers break
- AI resolves rule conflicts
- 200+ jurisdictions supported
- Zero hardcoded rules
- Zero manual maintenance

**You're 50% there. Keep going!** 🚀

---

## Questions or Issues?

- Check `/backend/PHASE3_TESTING_GUIDE.md` for testing procedures
- Check `/FRONTEND_INBOX_TODO.md` for inbox UI implementation
- Review original roadmap for detailed implementation specs
- Consult `/backend/CLAUDE.md` for codebase standards

**Last Updated:** February 9, 2026
**Phase Status:** 3/6 Complete (50%)
**Estimated Completion:** April 20, 2026
