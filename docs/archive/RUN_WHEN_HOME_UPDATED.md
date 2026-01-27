# 🏠 Getting Started with LitDocket Rules Engine

**Last Updated:** 2026-01-27
**Status:** ✅ Backend is working, ready to seed rules

---

## ⚠️ Important Notice

The original `RUN_WHEN_HOME.md` referenced an **experimental rules system** that was never integrated. This document reflects the **current working architecture**.

**Key Differences:**
- ❌ No `RuleVersion` model
- ❌ No user-created rules feature yet
- ❌ No 52 jurisdictions (only FL + Federal seeded)
- ✅ Working jurisdiction system with hierarchical rules
- ✅ Trigger-based deadline calculation
- ✅ Production-ready Florida + Federal rules

---

## What You Have Right Now

### ✅ Working Features

1. **Backend API** - Fully operational at `https://litdocket-production.up.railway.app`
2. **Frontend** - Running at `https://frontend-five-azure-58.vercel.app`
3. **Authentication** - Firebase auth working
4. **Database** - PostgreSQL on Supabase
5. **Rules Engine** - Trigger-based deadline calculation (`services/rules_engine.py`)
6. **Seed Data** - Ready to seed Florida + Federal courts

### 🚧 Not Yet Implemented

1. **Rules Marketplace** - No UI for browsing/installing rules
2. **User-Created Rules** - Can't create custom rules via UI
3. **50-State Coverage** - Only FL + Federal rules exist
4. **Rules History/Versioning** - No version tracking

---

## Quick Start: Seed Your Database

### Step 1: Seed Production Database

```bash
cd backend

# Option A: Via Railway CLI (recommended)
railway run python scripts/seed_production.py

# Option B: Via Python directly on Railway
railway run python -m app.seed.rule_sets

# Option C: If you have local DB configured
python scripts/seed_production.py
```

**What this creates:**
- 📍 2 Jurisdictions (Federal + Florida)
- 📚 10+ Rule Sets (FL:RCP, FRCP, FL:RAP, etc.)
- 📋 2 Rule Templates:
  - **Florida Complaint Served** (3 deadlines: Answer, Motion to Dismiss, Affirmative Defenses)
  - **Florida Trial Date** (30+ deadlines: Discovery, Experts, MSJ, Pretrial, etc.)
- 🏛️ Court Locations for major Florida courts

---

## Step 2: Test the Rules Engine

### Via Frontend (Easiest)

1. Go to your frontend: `https://frontend-five-azure-58.vercel.app`
2. Log in with Firebase
3. Navigate to **Cases** → Select a case → **Add Deadline**
4. Choose **Add Trigger** button
5. Select:
   - Jurisdiction: **Florida**
   - Trigger Type: **Complaint Served**
   - Trigger Date: Pick a date
6. Click **Generate Deadlines**

**Expected Result:**
- 3 deadlines created automatically
- Answer Due (20 days + 5 if mailed)
- Motion to Dismiss (20 days)
- Affirmative Defenses Due (20 days)

### Via API (For Testing)

```bash
# 1. Get auth token first
AUTH_TOKEN="your_jwt_token_here"

# 2. List available rule templates
curl https://litdocket-production.up.railway.app/api/v1/jurisdictions \
  -H "Authorization: Bearer $AUTH_TOKEN"

# 3. Create deadlines from trigger
curl -X POST https://litdocket-production.up.railway.app/api/v1/triggers/execute \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "your-case-id",
    "trigger_type": "COMPLAINT_SERVED",
    "trigger_date": "2026-02-01",
    "trigger_data": {
      "service_method": "mail",
      "party_served": "defendant"
    }
  }'
```

---

## Understanding the Architecture

### Current Rule System Flow

```
User Action
   ↓
Frontend: Select Trigger + Date
   ↓
API: POST /api/v1/triggers/execute
   ↓
Rules Engine: Find RuleTemplate for jurisdiction + trigger
   ↓
Rules Engine: Load RuleTemplateDeadlines
   ↓
Rules Engine: Calculate dates (trigger_date + days_from_trigger)
   ↓
Rules Engine: Apply service method adjustments
   ↓
Database: Create Deadline records
   ↓
Response: Return deadline list to frontend
```

### Database Structure

```
jurisdictions
  ├── code (FL, FED, CA, etc.)
  ├── name
  └── jurisdiction_type (federal, state, local)

rule_sets
  ├── code (FL:RCP, FRCP, etc.)
  ├── jurisdiction_id
  └── court_type

rule_templates
  ├── rule_code (FL_CIV_COMPLAINT_SERVED)
  ├── rule_set_id
  ├── trigger_type (COMPLAINT_SERVED, TRIAL_DATE)
  └── deadlines[]

rule_template_deadlines
  ├── rule_template_id
  ├── name (Answer Due)
  ├── days_from_trigger (20)
  ├── priority (FATAL, CRITICAL, etc.)
  ├── add_service_days (true/false)
  └── calculation_method (CALENDAR_DAYS, COURT_DAYS)
```

---

## Expanding to More States

Currently only **Florida + Federal** rules are seeded. To add more states:

### Option 1: Use Existing Seed Template

```python
# Copy app/seed/rule_sets.py structure
# Add new jurisdiction:

ca = Jurisdiction(
    id=str(uuid.uuid4()),
    code="CA",
    name="California State Courts",
    jurisdiction_type=JurisdictionType.STATE,
    state="CA"
)
db.add(ca)

# Add rule set:
ca_ccp = RuleSet(
    id=str(uuid.uuid4()),
    code="CA:CCP",
    name="California Code of Civil Procedure",
    jurisdiction_id=ca.id,
    court_type=CourtType.CIRCUIT
)
db.add(ca_ccp)

# Add rule template:
ca_answer = RuleTemplate(
    id=str(uuid.uuid4()),
    rule_set_id=ca_ccp.id,
    rule_code="CA_CIV_ANSWER",
    name="Answer to Complaint - California",
    trigger_type=TriggerType.COMPLAINT_SERVED,
    citation="Cal. Civ. Proc. Code § 412.20"
)
db.add(ca_answer)

# Add deadlines:
ca_answer_deadline = RuleTemplateDeadline(
    id=str(uuid.uuid4()),
    rule_template_id=ca_answer.id,
    name="Answer Due",
    days_from_trigger=30,  # CA is 30 days
    priority=DeadlinePriority.FATAL,
    add_service_days=True,  # +5/+10 for CA
    # ... more fields
)
db.add(ca_answer_deadline)
```

### Option 2: Use AI to Generate Rules

You can use Claude or GPT-4 to generate seed data from court rules:

```bash
# Prompt:
"Create a Python seed script for California Code of Civil Procedure
Rule 412.20 (Answer to Complaint). Include:
- Answer deadline (30 days)
- Service method extensions (+5 mail, +10 out of state)
- Motion to Strike deadline
- Demurrer deadline"
```

---

## Testing Checklist

After seeding, verify these features work:

### ✅ Basic Functionality
- [ ] Login with Firebase works
- [ ] Can create a case
- [ ] Can add deadlines manually
- [ ] Can view calendar

### ✅ Rules Engine
- [ ] Can select trigger type
- [ ] Deadlines generate from trigger
- [ ] Dates calculate correctly
- [ ] Service method adjustments apply
- [ ] Priority levels display correctly

### ✅ API Endpoints
- [ ] `GET /api/v1/jurisdictions` - Lists jurisdictions
- [ ] `GET /api/v1/jurisdictions/{code}/rule-sets` - Lists rule sets
- [ ] `POST /api/v1/triggers/execute` - Creates deadlines

---

## Common Issues & Solutions

### Issue: "Database already seeded"

**Solution:** This is normal if you've run the seed script before. The script is idempotent and will skip if data exists.

### Issue: "No jurisdictions found"

**Solution:** The database hasn't been seeded yet. Run `python scripts/seed_production.py`

### Issue: "Can't find rule template for trigger"

**Solution:**
1. Check if jurisdiction has rule sets: `GET /api/v1/jurisdictions/{code}/rule-sets`
2. Verify trigger type exists for that jurisdiction
3. Only `COMPLAINT_SERVED` and `TRIAL_DATE` are currently seeded

### Issue: "Dates calculating incorrectly"

**Solution:**
1. Check `add_service_days` flag on deadline
2. Verify `calculation_method` (CALENDAR_DAYS vs COURT_DAYS)
3. Check if service method is being passed correctly

---

## Next Steps (Priority Order)

1. ✅ **Seed database** (run scripts/seed_production.py)
2. ✅ **Test trigger creation** via frontend
3. 📝 **Add more Florida rules** (discovery, appeals, family law)
4. 🗺️ **Expand to California** (next highest volume state)
5. 🔧 **Build rules management UI** (admin panel for editing rules)
6. 📊 **Add analytics** (which rules are used most)

---

## File Locations

**Active Files:**
- `backend/app/models/jurisdiction.py` - Data models
- `backend/app/seed/rule_sets.py` - Seed data
- `backend/app/services/rules_engine.py` - Calculation logic
- `backend/app/api/v1/triggers.py` - API endpoints
- `backend/app/api/v1/jurisdictions.py` - Jurisdiction API
- `backend/scripts/seed_production.py` - Production seeding script

**Obsolete Files (can be deleted):**
- `backend/scripts/seed_comprehensive_rules.py` ❌
- `backend/scripts/seed_rules.py` ❌
- `backend/supabase/migrations/009_dynamic_rules_engine.sql` ❌

---

## Resources

- **API Documentation:** https://litdocket-production.up.railway.app/api/docs
- **Architecture Doc:** `/UPDATED_RULES_ARCHITECTURE.md`
- **Florida Rules Reference:** https://www.flrules.org/
- **Federal Rules Reference:** https://www.uscourts.gov/rules-policies/current-rules-practice-procedure

---

**Questions?** Check:
- Architecture doc: `UPDATED_RULES_ARCHITECTURE.md`
- API docs: `/api/docs`
- Source code: `backend/app/seed/rule_sets.py`

**Happy Docketing! ⚖️**
