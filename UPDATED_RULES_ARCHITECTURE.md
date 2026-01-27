# Rules System Architecture - Current State (2026-01-27)

## ⚠️ IMPORTANT: RUN_WHEN_HOME.md is OUTDATED

The RUN_WHEN_HOME.md file references an **experimental rules system** (migration 009) that was never fully integrated. This document reflects the **actual current architecture**.

---

## Current Architecture

### Database Schema (Migration 001 - jurisdiction_system.sql)

**Active Tables:**
```
jurisdictions
├── rule_sets
│   ├── rule_templates
│   │   └── rule_template_deadlines
│   └── rule_set_dependencies
└── court_locations
```

**Key Models:**
- `Jurisdiction` - Geographic/court jurisdictions (Federal, State, Local)
- `RuleSet` - Collection of rules (e.g., FL:RCP, FRCP, FL:RAP)
- `RuleTemplate` - Trigger-based deadline generator
- `RuleTemplateDeadline` - Individual deadline definitions
- `RuleSetDependency` - Dependencies between rule sets
- `CourtLocation` - Physical court locations

### What Works ✅

1. **Jurisdiction System:**
   - Hierarchical jurisdiction structure (Federal → State → Local)
   - Court type classification
   - Rule set management

2. **Rule Templates:**
   - Trigger-based deadline calculation
   - Service method adjustments
   - Priority levels (FATAL, CRITICAL, IMPORTANT, STANDARD)
   - Multiple deadlines per trigger

3. **Seed Data Available:**
   - Located in: `backend/app/seed/rule_sets.py`
   - Creates: Florida courts + Federal courts
   - Includes: ~50+ deadlines across multiple triggers

4. **Active API Endpoints:**
   - `/api/v1/jurisdictions` - Jurisdiction management
   - `/api/v1/triggers` - Trigger-based deadline creation
   - Integration with `services/rules_engine.py`

### What Doesn't Work ❌

1. **scripts/seed_comprehensive_rules.py** - BROKEN
   - Imports deleted `rule_template.py` module
   - References `RuleVersion` model (doesn't exist)
   - Uses wrong schema (migration 009 vs 001)

2. **scripts/seed_rules.py** - BROKEN
   - Same issues as above

3. **User-Created Rules Feature** - NOT IMPLEMENTED
   - `created_by` column doesn't exist
   - No UI for rule creation
   - No versioning system

4. **Rules Marketplace** - NOT IMPLEMENTED
   - No public/private rule distinction in current schema
   - No sharing mechanism

---

## How to Seed Production Database

### Option 1: Run Existing Seed Script (Recommended)

```bash
# Connect to production database via Railway
railway run python -m app.seed.rule_sets
```

This will create:
- **2 Jurisdictions:** Federal, Florida
- **10+ Rule Sets:** FL:RCP, FRCP, FL:RAP, etc.
- **2 Rule Templates:**
  - Florida Complaint Served (3 deadlines)
  - Florida Trial Date (30+ deadlines)
- **Court Locations:** Major Florida courts

### Option 2: Manual Database Seeding

If you need to seed directly via SQL:

```bash
# 1. Connect to Supabase
psql $DATABASE_URL

# 2. Run migration 001
\i backend/supabase/migrations/001_jurisdiction_system.sql

# 3. Run seed data migration
\i backend/supabase/migrations/002_seed_jurisdictions.sql
```

---

## Current Limitations

1. **Limited Geographic Coverage:**
   - Only Florida + Federal courts seeded
   - No other states

2. **Limited Triggers:**
   - Only COMPLAINT_SERVED and TRIAL_DATE implemented
   - Missing: Discovery, Motions, Appeals, etc.

3. **No UI for Rule Management:**
   - Rules must be added via database/seed scripts
   - No admin panel for rule editing

4. **No Versioning:**
   - Can't track rule changes over time
   - No rollback capability

5. **No User-Created Rules:**
   - System rules only
   - Can't add custom jurisdictions via UI

---

## Integration Points

### Frontend:
- `frontend/app/(protected)/triggers/` - Trigger selection UI
- Deadline creation uses `triggers` API

### Backend:
- `app/api/v1/triggers.py` - API endpoints
- `app/services/rules_engine.py` - Deadline calculation logic
- `app/models/jurisdiction.py` - Data models

### Rules Engine Flow:
```
User selects trigger →
API calls rules_engine.execute_trigger() →
Looks up RuleTemplate for jurisdiction →
Calculates dates from RuleTemplateDeadlines →
Creates Deadline records →
Returns deadline list
```

---

## Migration Path (If You Want Full 50-State Coverage)

The old `scripts/seed_comprehensive_rules.py` claimed to have 52 jurisdictions and 54 rules. To achieve this with the current architecture:

1. **Create new seed file** using `app/seed/rule_sets.py` as template
2. **Add each state:**
   ```python
   state = Jurisdiction(code="CA", name="California", ...)
   rule_set = RuleSet(code="CA:CCP", name="California Civil Procedure", ...)
   template = RuleTemplate(rule_code="CA_CIV_ANSWER", ...)
   ```

3. **Run once on production:**
   ```bash
   railway run python -m app.seed.state_expansion
   ```

**Estimated effort:**
- 1-2 hours per state (research rules + deadlines)
- 50 states = 50-100 hours total
- Or use AI to generate from rule text

---

## Next Steps (Recommended Priority)

1. ✅ **Fix authentication** (DONE)
2. ✅ **Seed core Florida + Federal rules** (READY - just run seed script)
3. **Test trigger creation via UI**
4. **Add more Florida-specific rules**
5. **Expand to other states** (as needed by users)
6. **Build rules management UI** (admin panel)

---

## Files to Keep vs Delete

### Keep ✅
- `app/models/jurisdiction.py` - Current models
- `app/seed/rule_sets.py` - Working seed script
- `app/services/rules_engine.py` - Active rules engine
- `app/api/v1/triggers.py` - Active API
- `app/api/v1/jurisdictions.py` - Active API
- `supabase/migrations/001_jurisdiction_system.sql` - Active schema

### Delete ❌ (Obsolete)
- `scripts/seed_comprehensive_rules.py` - Broken, uses wrong models
- `scripts/seed_rules.py` - Broken, uses wrong models
- `supabase/migrations/009_dynamic_rules_engine.sql` - Never integrated
- Any references to `RuleVersion` model

---

**Last Updated:** 2026-01-27
**Architecture Version:** Migration 001 (Jurisdiction System)
