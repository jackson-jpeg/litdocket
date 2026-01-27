# Archived Obsolete Scripts

**Date Archived:** 2026-01-27
**Reason:** These scripts were written for an experimental database schema (Migration 009: dynamic_rules_engine) that was never fully integrated into the codebase.

## What Happened

The codebase had two conflicting rule template schemas:

1. **Migration 001 (jurisdiction_system.sql)** - CURRENT, ACTIVE SCHEMA
   - Models in `app/models/jurisdiction.py`
   - RuleTemplate has fields: id, rule_set_id, rule_code, name, trigger_type
   - No `created_by`, `slug`, `current_version_id` fields
   - No RuleVersion model

2. **Migration 009 (dynamic_rules_engine.sql)** - EXPERIMENTAL, NEVER INTEGRATED
   - Models were in `app/models/rule_template.py` (now deleted)
   - RuleTemplate had fields: created_by, slug, current_version_id
   - Had RuleVersion model for versioning
   - **This schema was never applied to production**

## Scripts Archived

### ❌ seed_comprehensive_rules.py (252K)
- **Problem:** Imports `from app.models.rule_template import RuleTemplate, RuleVersion`
- **Status:** Broken - imports deleted module
- **Purpose:** Would seed 52 jurisdictions with 54 rules
- **Fix Required:** Complete rewrite to use Migration 001 schema

### ❌ seed_federal_districts_phase3.py (28K)
- **Problem:** Imports `from app.models.rule_template import RuleTemplate, RuleVersion`
- **Status:** Broken - imports deleted module
- **Purpose:** Seed federal district court rules
- **Fix Required:** Rewrite to use Migration 001 schema

### ❌ seed_rules.py (13K)
- **Problem:** Imports `from app.models.rule_template import RuleTemplate, RuleVersion`
- **Status:** Broken - imports deleted module
- **Purpose:** Seed basic rules
- **Fix Required:** Rewrite to use Migration 001 schema

### ❌ generate_rule_template.py (14K)
- **Problem:** Generates code using Migration 009 schema (RuleVersion, created_by, slug fields)
- **Status:** Broken - generates code for wrong schema
- **Purpose:** Interactive CLI to create rule templates
- **Fix Required:** Rewrite to generate code using Migration 001 schema

### ⚠️ seed_via_api.py (2.5K)
- **Problem:** Doesn't actually seed anything - just checks and tells user to use Railway
- **Status:** Incomplete implementation
- **Purpose:** Seed via API calls instead of direct DB access
- **Note:** Could be useful if completed, but current seeding works fine

## Working Script (Still Active)

### ✅ seed_production.py
- **Location:** `/Users/jackson/docketassist-v3/backend/scripts/seed_production.py`
- **Status:** WORKING
- **Models Used:** Migration 001 schema from `app/models/jurisdiction.py`
- **Purpose:** Seeds production database with Florida + Federal rules
- **Data Source:** `app/seed/rule_sets.py`

**To seed production database:**
```bash
railway shell
python scripts/seed_production.py
```

## What to Do With These Scripts

### Option 1: Delete Permanently
If you don't plan to use the data they contain, just delete this entire archive folder.

### Option 2: Salvage the Data
If you want to use the comprehensive rules data (52 jurisdictions, etc.), you'll need to:

1. Extract the actual rule definitions (the JSON schemas)
2. Rewrite the seeding code to use Migration 001 schema
3. Add the data to `app/seed/rule_sets.py`
4. Test with `seed_production.py`

## Migration History

- **Migration 001** (jurisdiction_system.sql) - Jan 2025 - ACTIVE
- **Migration 009** (dynamic_rules_engine.sql) - Later - EXPERIMENTAL, ABANDONED
- **Cleanup** - Jan 27, 2026 - Deleted Migration 009 models, archived incompatible scripts

## Related Files Deleted

These files were deleted from the codebase as part of the cleanup:
- `app/models/rule_template.py` - Conflicting model definitions
- `app/api/v1/rules.py` - Used deleted models
- `app/services/dynamic_rules_engine.py` - Used deleted models

## Current Architecture

See `UPDATED_RULES_ARCHITECTURE.md` in project root for full documentation of the current rules system.
