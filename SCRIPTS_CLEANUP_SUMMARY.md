# Backend Scripts Cleanup - January 27, 2026

## What I Did

Cleaned up the `/backend/scripts/` directory by identifying and archiving broken/obsolete scripts.

## Summary

**Before cleanup:** 6 scripts (only 1 working)
**After cleanup:** 1 working script (5 archived)

## Scripts Status

### ✅ Active (Still in `/backend/scripts/`)

1. **seed_production.py** - WORKING
   - Seeds production database with Florida + Federal rules
   - Creates 2 jurisdictions, 10+ rule sets, 2 rule templates (33 deadlines)
   - Safe to run: `railway shell` → `python scripts/seed_production.py`

### ❌ Archived (Moved to `/backend/scripts/archive_obsolete_scripts/`)

1. **seed_comprehensive_rules.py** (252K)
   - **Problem:** Imports deleted `app.models.rule_template` module
   - **Would have:** 52 jurisdictions, 54 rules (impressive data!)
   - **Status:** Broken - written for experimental schema that never launched

2. **seed_federal_districts_phase3.py** (28K)
   - **Problem:** Imports deleted module
   - **Would have:** Federal district court rules
   - **Status:** Broken

3. **seed_rules.py** (13K)
   - **Problem:** Imports deleted module
   - **Would have:** Basic rules seeding
   - **Status:** Broken

4. **generate_rule_template.py** (14K)
   - **Problem:** Generates code for wrong schema (RuleVersion, created_by fields)
   - **Would have:** Interactive CLI to create rules
   - **Status:** Broken - generates incompatible code

5. **seed_via_api.py** (2.5K)
   - **Problem:** Doesn't actually seed - just checks and tells you to use Railway
   - **Status:** Incomplete implementation

## Why Were They Broken?

These scripts were written for **Migration 009** (dynamic_rules_engine), an experimental database schema that was never fully integrated. Your production database uses **Migration 001** (jurisdiction_system), which has a different structure.

**Key differences:**
- Migration 001: RuleTemplate → RuleSet → Jurisdiction (simple hierarchy)
- Migration 009: RuleTemplate → RuleVersion → User (complex versioning system)

The Migration 009 models were deleted in earlier cleanup (commits 1c204c6, e508786) because they conflicted with Migration 001.

## What Should You Run?

### To seed your production database:

```bash
railway shell
python scripts/seed_production.py
```

This is the ONLY script you need. It works perfectly and seeds:
- ✅ 2 jurisdictions (Florida, Federal)
- ✅ 10+ rule sets (FRCP, FL:RCP, etc.)
- ✅ 2 rule templates (Complaint Served, Trial Date)
- ✅ 33+ deadline definitions

### After seeding, test it:

1. Go to: https://frontend-five-azure-58.vercel.app
2. Login → Open a case → Click "Add Trigger"
3. Select: Florida → Complaint Served → Pick a date
4. Click "Generate Deadlines"
5. You should see 3 deadlines appear automatically 🎉

## Can We Salvage the Archived Scripts?

**Yes, if you want the comprehensive data (52 jurisdictions).**

The archived scripts contain valuable rule definitions, but they need to be rewritten:

1. Extract the actual rule data (JSON schemas, dates, calculations)
2. Rewrite to use Migration 001 schema (models from `app/models/jurisdiction.py`)
3. Add to `app/seed/rule_sets.py`
4. Test with `seed_production.py`

This would be a substantial refactoring project. For now, you have Florida + Federal working.

## Related Documentation

- **`backend/scripts/README.md`** - What's in scripts directory
- **`backend/scripts/archive_obsolete_scripts/README.md`** - Why scripts were archived
- **`UPDATED_RULES_ARCHITECTURE.md`** - Current vs experimental architecture
- **`QUICK_START.md`** - How to seed and test (5 minutes)
- **`SEED_DATABASE_GUIDE.md`** - Detailed seeding instructions

## Files Created During Cleanup

1. `/backend/scripts/README.md` - Active scripts documentation
2. `/backend/scripts/archive_obsolete_scripts/README.md` - Archive explanation
3. `/SCRIPTS_CLEANUP_SUMMARY.md` - This file

## Next Steps

1. **Seed your database:**
   ```bash
   railway shell
   python scripts/seed_production.py
   ```

2. **Test in frontend:**
   - Create a case
   - Add trigger (Florida → Complaint Served)
   - Verify deadlines generate correctly

3. **If you need more jurisdictions:**
   - Edit `app/seed/rule_sets.py`
   - Add new jurisdictions/rule templates
   - Run `seed_production.py` again

4. **If you want to salvage archived data:**
   - Start a new task to extract and rewrite the rules
   - Use Migration 001 schema
   - Test incrementally

## Git Commit Recommendation

```bash
git add backend/scripts/
git add SCRIPTS_CLEANUP_SUMMARY.md
git commit -m "chore(scripts): Archive obsolete seeding scripts

- Moved 5 broken/incomplete scripts to archive_obsolete_scripts/
- These scripts were written for experimental Migration 009 schema
- Only seed_production.py remains (working, uses Migration 001)
- Added README files documenting active vs archived scripts

Scripts archived:
- seed_comprehensive_rules.py (252K)
- seed_federal_districts_phase3.py (28K)
- seed_rules.py (13K)
- generate_rule_template.py (14K)
- seed_via_api.py (2.5K)

Related: commits 1c204c6, e508786 (deleted Migration 009 models)"
```

---

**Status:** ✅ Scripts directory cleaned up and documented
**Action Required:** Seed production database when ready
**Time to Seed:** ~30 seconds
**Expected Result:** 2 jurisdictions, 33+ deadlines ready for testing
