# 🚀 Quick Start - Seed & Test (5 Minutes)

**You're here:** Backend is working, documentation is ready. Now let's get the rules into your database!

---

## Step 1: Seed Production Database (2 minutes)

Since Railway CLI needs interactive login, use the **Railway Web Terminal** (easiest):

### Option A: Railway Dashboard (Recommended) ⭐

1. **Open Railway:** https://railway.app/
2. **Select your backend service** (litdocket-production)
3. **Find the Shell/Terminal:**
   - Look for "Shell" tab
   - Or click "..." menu → "Shell"
   - Or go to recent deployment → "View Logs" → "Shell" tab
4. **Run this command:**
   ```bash
   python scripts/seed_production.py
   ```
5. **Wait ~30 seconds** - You'll see:
   ```
   ✅ Seeding Complete!
   📊 Database Summary:
      Jurisdictions: 2
      Rule Sets: 10+
      Rule Templates: 2
      Deadline Definitions: 33+
   ```

### Option B: Quick CLI Check (If you're logged into Railway)

```bash
cd backend
railway login  # Opens browser - login
railway link   # Select your project
railway run python scripts/seed_production.py
```

---

## Step 2: Verify It Worked (30 seconds)

### Quick API Check:

```bash
# Test the health endpoint
curl https://litdocket-production.up.railway.app/health

# Expected: {"status":"healthy"...}
```

The jurisdictions endpoint requires auth, so we'll verify via the frontend instead.

---

## Step 3: Test Trigger Creation (2 minutes) 🎯

**NOW THE FUN PART!**

1. **Open your frontend:** https://frontend-five-azure-58.vercel.app

2. **Login** with your Firebase account

3. **Create or select a case:**
   - Click "Cases" in navigation
   - Either open existing case or create new one

4. **Add a deadline trigger:**
   - Look for "Add Deadline" or "Add Trigger" button
   - Click it

5. **Fill out the form:**
   - **Jurisdiction:** Select "Florida" (should appear in dropdown)
   - **Trigger Type:** Select "Complaint Served"
   - **Trigger Date:** Pick any date (e.g., today)
   - **Service Method:** Mail (optional)

6. **Click "Generate Deadlines"** 🎉

### Expected Result:

You should see **3 deadlines automatically created:**

```
✅ Answer Due
   Priority: FATAL
   Date: [Trigger Date + 25 days] (20 days + 5 for mail service)
   Party: Defendant
   Action: File and serve Answer to Complaint

✅ Motion to Dismiss Deadline
   Priority: CRITICAL
   Date: [Trigger Date + 25 days]
   Party: Defendant
   Action: File motion to dismiss under Rule 1.140(b)

✅ Affirmative Defenses Due
   Priority: FATAL
   Date: [Trigger Date + 25 days]
   Party: Defendant
   Action: Include all affirmative defenses in Answer
```

**If you see those 3 deadlines appear, IT WORKS!** 🎊

---

## Step 4: Try the Trial Date Trigger (Bonus)

If that worked, try the more complex trigger:

1. **Add another trigger** to the same case
2. **Select:**
   - Jurisdiction: "Florida"
   - Trigger Type: "Trial Date"
   - Trigger Date: Pick a date 6 months out
3. **Click "Generate Deadlines"**

### Expected Result:

You should see **30+ deadlines automatically created:**
- Discovery cutoffs (45 days before trial)
- Expert disclosures (90 days before for plaintiff)
- Motion for summary judgment (60 days before)
- Pretrial conference dates
- Witness lists
- Jury instructions
- And many more!

This shows the real power of the trigger system - one date generates an entire case timeline.

---

## Troubleshooting

### "No jurisdictions available"
❌ Database not seeded yet. Go back to Step 1.

### "Trigger type not found"
❌ Rule templates not created. Check Railway logs for seed errors.

### "Can't find Railway terminal"
💡 Try Option B (Railway CLI) or see `SEED_DATABASE_GUIDE.md` for 4 different approaches.

### Frontend shows error
1. Check browser console for actual error
2. Verify backend is healthy: `curl https://litdocket-production.up.railway.app/health`
3. Try logging out and back in

---

## What's Next?

After you successfully create deadlines from triggers:

### Today:
- ✅ Test with different dates
- ✅ Try personal service vs mail service (different deadline dates)
- ✅ Test the trial date trigger
- ✅ Add deadlines to your calendar view

### This Week:
- Add more case-specific rules as needed
- Test with real case data
- Adjust priorities if needed
- Add custom deadlines alongside trigger-generated ones

### Later:
- Expand to more states (see `UPDATED_RULES_ARCHITECTURE.md`)
- Add more trigger types (discovery, appeals, etc.)
- Build rules management UI

---

## Success Metrics

You'll know it's working when:
- ✅ Jurisdictions load in dropdown
- ✅ Trigger types appear for selected jurisdiction
- ✅ Deadlines generate automatically from trigger
- ✅ Date calculations are correct (trigger + days + service adjustment)
- ✅ Priorities display correctly (FATAL in red, etc.)

---

## Need Help?

**Can't seed database?**
→ Read `SEED_DATABASE_GUIDE.md` for 4 different methods

**Need to understand architecture?**
→ Read `UPDATED_RULES_ARCHITECTURE.md`

**Want full documentation?**
→ Read `RUN_WHEN_HOME_UPDATED.md`

**API not responding?**
→ Check Railway logs, verify deployment is healthy

---

**Ready?** Go to Step 1 and seed that database! 🌱

**Expected total time:** 5 minutes
**Difficulty:** Easy (mostly waiting)
**Reward:** Fully automated deadline calculation! ⚖️
