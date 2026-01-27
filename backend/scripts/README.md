# Backend Scripts Directory

## Active Scripts

### ✅ seed_production.py

**Purpose:** Seeds the production database with jurisdictions, rule sets, and rule templates.

**Status:** WORKING

**What it does:**
- Creates 2 jurisdictions (Florida + Federal)
- Creates 10+ rule sets (FRCP, FL:RCP, FL:RAP, etc.)
- Creates 2 rule templates:
  - FL_CIV_COMPLAINT_SERVED (3 deadlines)
  - FL_CIV_TRIAL (30+ deadlines)
- Creates court locations for Florida

**How to run:**

```bash
# Option 1: Railway Shell (Recommended)
railway shell
python scripts/seed_production.py

# Option 2: Railway Web Terminal
1. Go to https://railway.app/
2. Select backend service (litdocket-production)
3. Open Shell tab
4. Run: python scripts/seed_production.py
```

**Expected output:**
```
================================================================================
LitDocket Production Database Seeding
================================================================================

📊 Checking database connection...
✅ Database connected. Current jurisdictions: 0

🌱 Starting seed process...

Seeding jurisdictions...
Seeding rule sets...
Seeding rule dependencies...
Seeding court locations...
Seeding rule templates...
Seed complete!

================================================================================
✅ Seeding Complete!
================================================================================

📊 Database Summary:
   Jurisdictions: 2
   Rule Sets: 10
   Rule Templates: 2
   Deadline Definitions: 33

🗺️  Jurisdictions Created:
   • FED: Federal Courts
   • FL: Florida State Courts

📋 Rule Templates Created:
   • FL_CIV_COMPLAINT_SERVED: Complaint Served - Full Response Chain (3 deadlines)
   • FL_CIV_TRIAL: Trial Date Dependencies (30 deadlines)

🎉 Your rules engine is ready to use!
```

**Data source:** `app/seed/rule_sets.py`

**Safe to run multiple times:** Yes - checks for existing data and skips if already seeded.

## Archived Scripts

The `archive_obsolete_scripts/` directory contains scripts that were written for an experimental database schema that was never integrated. These scripts are broken and should not be used.

See `archive_obsolete_scripts/README.md` for details.

## Need More Rules?

To add more jurisdictions or rule templates:

1. Edit `app/seed/rule_sets.py`
2. Add new jurisdiction data
3. Add new rule template definitions
4. Run `seed_production.py` again (it will skip existing data)

Or refer to the data in the archived scripts for inspiration (but you'll need to rewrite to match the current schema).

## Troubleshooting

### "No such file or directory"
You're running locally instead of on Railway. Use `railway shell` first.

### "Database already seeded"
This is GOOD! It means seeding already ran. You're ready to test.

### "Connection refused"
Wrong database URL. Make sure you're running on Railway with correct DATABASE_URL env var.

## Related Documentation

- `QUICK_START.md` - 5-minute guide to seed and test
- `SEED_DATABASE_GUIDE.md` - Detailed seeding instructions
- `UPDATED_RULES_ARCHITECTURE.md` - Current rules system architecture
- `RUN_WHEN_HOME_UPDATED.md` - Full setup and testing guide
