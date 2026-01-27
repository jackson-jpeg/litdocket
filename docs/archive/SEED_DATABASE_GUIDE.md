# 🌱 How to Seed Your Production Database

You need to run the seed script **on Railway** where it has access to the production database.

---

## Option 1: Railway Web Terminal (Easiest) ✅

1. **Go to Railway Dashboard**
   - Open: https://railway.app/
   - Select your **backend service** (litdocket-production)

2. **Open the Web Terminal**
   - Click on the service
   - Look for "Shell" or "Terminal" tab (might be under "..." menu)
   - Or go to the deployment and look for "View Logs/Shell"

3. **Run the Seed Script**
   ```bash
   python scripts/seed_production.py
   ```

4. **Wait for Completion** (~30 seconds)
   - You'll see progress messages
   - Final summary shows what was created

---

## Option 2: Railway CLI (If You Have It)

```bash
# Login first (opens browser)
railway login

# Link to your project
railway link

# Run the seed script
railway run python scripts/seed_production.py
```

---

## Option 3: Manual SQL (Advanced)

If neither above works, you can run the migrations directly in Supabase:

1. **Get your Supabase connection string** from Railway variables:
   ```
   DATABASE_URL=postgresql://postgres.zcjbsypjatzdpaolirar:...
   ```

2. **Connect via psql**:
   ```bash
   psql "postgresql://postgres.zcjbsypjatzdpaolirar:rImke1-furcas-boxvok@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
   ```

3. **Check if migrations ran**:
   ```sql
   SELECT * FROM jurisdictions;
   ```

4. **If empty, run migration 002**:
   ```bash
   psql $DATABASE_URL < backend/supabase/migrations/002_seed_jurisdictions.sql
   ```

---

## Option 4: Create a One-Time Deploy (Recommended if Railway CLI doesn't work)

1. **Add seed command to Railway**:
   - Go to Railway → Your service → Settings
   - Find "Deploy" settings
   - Look for "Start Command" or "Run Command"

2. **Temporarily change start command** to:
   ```bash
   python scripts/seed_production.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

3. **Trigger new deployment**:
   - Push any small change OR
   - Use "Redeploy" button in Railway dashboard

4. **Watch the logs** to see seeding happen

5. **Revert the command** back to normal:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

---

## How to Verify It Worked

### Check via API:

```bash
# No auth needed for listing jurisdictions
curl https://litdocket-production.up.railway.app/api/v1/jurisdictions
```

**Expected output:**
```json
[
  {
    "code": "FED",
    "name": "Federal Courts",
    "jurisdiction_type": "federal"
  },
  {
    "code": "FL",
    "name": "Florida State Courts",
    "jurisdiction_type": "state"
  }
]
```

### Check via Frontend:

1. Login to: https://frontend-five-azure-58.vercel.app
2. Go to any case
3. Click "Add Trigger"
4. **You should see**:
   - Jurisdiction dropdown with "Federal" and "Florida"
   - Trigger type dropdown with options
   - Date picker

---

## What Gets Created

After successful seeding:

**📍 2 Jurisdictions:**
- Federal Courts (FED)
- Florida State Courts (FL)

**📚 10+ Rule Sets:**
- FRCP (Federal Rules of Civil Procedure)
- FL:RCP (Florida Rules of Civil Procedure)
- FL:RAP (Florida Rules of Appellate Procedure)
- FL:FLRP (Florida Family Law Rules)
- And more...

**📋 2 Rule Templates:**
1. **Florida Complaint Served** → 3 deadlines
   - Answer Due (20 days + 5 mail)
   - Motion to Dismiss (20 days)
   - Affirmative Defenses (20 days)

2. **Florida Trial Date** → 30+ deadlines
   - Discovery cutoffs
   - Expert disclosures
   - MSJ deadlines
   - Pretrial filings
   - Witness lists
   - And more...

**🏛️ Court Locations:**
- Major Florida courts (Miami, Tampa, Orlando, etc.)

---

## Troubleshooting

### "Database already seeded"
✅ This is good! It means it already ran. You're ready to test.

### "ModuleNotFoundError"
❌ You're running locally without dependencies. Must run on Railway.

### "Connection refused"
❌ Wrong database URL. Make sure running on Railway, not locally.

### Can't access Railway terminal
💡 Use Option 4 (modify start command temporarily)

---

## After Seeding - Test It Works

### Quick Test via Frontend:

1. **Login**: https://frontend-five-azure-58.vercel.app
2. **Go to Cases** → Click any case (or create one)
3. **Add Deadline** → Click "Add Trigger" button
4. **Select**:
   - Jurisdiction: "Florida"
   - Trigger: "Complaint Served"
   - Date: Tomorrow
5. **Generate Deadlines**

**Expected Result:**
```
✅ 3 deadlines created:
   • Answer Due - FATAL - [Date + 20 days]
   • Motion to Dismiss - CRITICAL - [Date + 20 days]
   • Affirmative Defenses Due - FATAL - [Date + 20 days]
```

If you see those 3 deadlines appear automatically, **it works!** 🎉

---

## Need Help?

If none of these options work:
1. Check Railway logs for errors
2. Verify DATABASE_URL is set correctly in Railway
3. Make sure migration 001 ran (creates the tables)
4. Try running just the import test first:
   ```bash
   railway run python -c "from app.seed.rule_sets import run_seed; print('OK')"
   ```

---

**Ready?** Pick your preferred option above and seed that database! 🌱
