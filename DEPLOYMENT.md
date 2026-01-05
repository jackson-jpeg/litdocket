# LitDocket.com Deployment Guide

## Overview
We'll deploy:
- **Frontend (Next.js)** → Vercel (free, instant SSL, optimized for Next.js)
- **Backend (FastAPI)** → Railway (free tier, easy PostgreSQL integration)
- **Database** → Railway PostgreSQL (managed, automatic backups)
- **Files** → Firebase Storage (already configured)
- **Domain** → litdocket.com via Squarespace DNS

---

## Step 1: Backend Deployment (Railway)

### 1.1 Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"

### 1.2 Prepare Backend for Railway

Railway will automatically detect the Python app. We need to:
- Add production requirements
- Create Procfile
- Set environment variables

### 1.3 Environment Variables to Set in Railway

```
ANTHROPIC_API_KEY=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
DATABASE_URL=postgresql://... (Railway will auto-generate this)
FIREBASE_SERVICE_ACCOUNT_KEY=/app/firebase-service-account.json
ALLOWED_ORIGINS=https://litdocket.com,https://www.litdocket.com
```

### 1.4 Add PostgreSQL Database
1. In Railway project, click "+ New"
2. Select "PostgreSQL"
3. Railway will automatically link it and set DATABASE_URL

---

## Step 2: Frontend Deployment (Vercel)

### 2.1 Create Vercel Account
1. Go to https://vercel.com
2. Sign up with GitHub
3. Click "Add New..." → "Project"
4. Import from Git: `/Users/jackson/docketassist-v3/frontend`

### 2.2 Configure Build Settings
- Framework Preset: **Next.js**
- Root Directory: `frontend`
- Build Command: `npm run build` (default)
- Output Directory: `.next` (default)

### 2.3 Environment Variables in Vercel

```
NEXT_PUBLIC_API_URL=https://your-backend-railway-url.railway.app
```

### 2.4 After First Deploy
Vercel will give you a URL like: `litdocket-frontend-abc123.vercel.app`
We'll use this temporarily, then add custom domain.

---

## Step 3: Domain Configuration (Squarespace DNS)

### 3.1 Point litdocket.com to Vercel (Frontend)

In Squarespace DNS settings, add these records:

**For root domain (litdocket.com):**
- Type: **A Record**
- Host: **@**
- Points to: **76.76.21.21** (Vercel's IP)

**For www subdomain:**
- Type: **CNAME**
- Host: **www**
- Points to: **cname.vercel-dns.com**

### 3.2 Point api.litdocket.com to Railway (Backend)

**For API subdomain:**
- Type: **CNAME**
- Host: **api**
- Points to: **your-app-name.railway.app** (get this from Railway)

### 3.3 Add Custom Domains in Vercel
1. Go to Vercel project settings → Domains
2. Add domain: `litdocket.com`
3. Add domain: `www.litdocket.com`
4. Vercel will auto-configure SSL (Let's Encrypt)

### 3.4 Add Custom Domain in Railway
1. Go to Railway project settings → Domains
2. Add domain: `api.litdocket.com`
3. Railway will provide instructions for DNS verification

---

## Step 4: Update Production URLs

### 4.1 Update Frontend API URL
After Railway backend is deployed, update Vercel environment variable:
```
NEXT_PUBLIC_API_URL=https://api.litdocket.com
```

### 4.2 Update Backend CORS
In Railway environment variables, update:
```
ALLOWED_ORIGINS=https://litdocket.com,https://www.litdocket.com
```

---

## Step 5: Firebase Production Setup

### 5.1 Ensure Firebase Service Account is Uploaded
1. In Railway, go to your project
2. Upload `firebase-service-account.json` file
3. Ensure environment variable points to it

### 5.2 Update Firebase Security Rules for Production
- Already configured in firestore.rules
- Already configured in storage.rules
- These are deployed via: `firebase deploy --only firestore,storage`

---

## Step 6: Database Migration

### 6.1 Railway PostgreSQL Setup
Railway automatically creates and links PostgreSQL database.

The app will auto-create tables on first startup because we have:
```python
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
```

### 6.2 Verify Database Connection
After deployment, check Railway logs:
```
INFO:app.main:Starting Florida Docketing Assistant API...
INFO:app.main:Creating database tables...
INFO:app.main:Application startup complete
```

---

## Step 7: Testing & Verification

### 7.1 Test Checklist
- [ ] Visit https://litdocket.com (should load Next.js app)
- [ ] Upload a PDF document
- [ ] Verify backend API connection (check Network tab)
- [ ] Verify Firebase storage upload
- [ ] Check database records created
- [ ] Test AI deadline extraction
- [ ] Test chatbot functionality

### 7.2 Monitor Logs
- **Frontend:** Vercel Dashboard → Logs
- **Backend:** Railway Dashboard → Logs
- **Database:** Railway Dashboard → PostgreSQL → Metrics

---

## Step 8: Production Optimizations (Post-Launch)

### 8.1 Performance
- [ ] Enable Vercel Image Optimization
- [ ] Configure caching headers
- [ ] Monitor API response times

### 8.2 Security
- [ ] Enable Railway IP whitelisting (optional)
- [ ] Review Firebase security rules
- [ ] Set up rate limiting
- [ ] Configure CORS strictly

### 8.3 Monitoring
- [ ] Set up Sentry for error tracking
- [ ] Configure uptime monitoring (e.g., UptimeRobot)
- [ ] Set up analytics (Vercel Analytics)

---

## Estimated Costs

**FREE Tier (Adequate for Launch):**
- Vercel: Free (100GB bandwidth, unlimited deployments)
- Railway: $5/month (includes PostgreSQL, 500 hours compute)
- Firebase: Free tier (1GB storage, 50K reads/day, 20K writes/day)
- Domain: ~$20/year (via Squarespace)

**Total: ~$5/month + $20/year domain**

---

## Quick Start Commands

```bash
# Deploy Firebase rules
cd /Users/jackson/docketassist-v3
firebase deploy --only firestore,storage --project florida-docket-assist

# The rest happens via Git push:
# - Push backend to GitHub → Railway auto-deploys
# - Push frontend to GitHub → Vercel auto-deploys
```

---

## Support

**Railway Docs:** https://docs.railway.app
**Vercel Docs:** https://vercel.com/docs
**Squarespace DNS:** https://support.squarespace.com/hc/en-us/articles/360002101888

---

## Rollback Plan

If something goes wrong:
1. Vercel: Click "Rollback" on previous deployment
2. Railway: Click "Redeploy" on previous deployment
3. Both keep deployment history for instant rollback
