# 🚀 Quick Deployment Checklist for litdocket.com

Follow these steps in order to go live in ~30 minutes.

---

## ✅ Pre-Deployment Checklist

- [ ] Domain purchased: litdocket.com ✓ (via Squarespace)
- [ ] GitHub account ready
- [ ] Code committed to GitHub

---

## 📦 Step 1: Push Code to GitHub (5 minutes)

```bash
cd /Users/jackson/docketassist-v3

# Initialize git if not already done
git init
git add .
git commit -m "Initial commit - Florida Legal Docketing Assistant"

# Create GitHub repo (go to github.com/new)
# Then push:
git remote add origin https://github.com/YOUR-USERNAME/litdocket.git
git branch -M main
git push -u origin main
```

---

## 🗄️ Step 2: Deploy Backend to Railway (10 minutes)

### 2.1 Create Railway Project
1. Go to https://railway.app
2. Sign up with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose your `litdocket` repository
6. **Root directory:** Select `/backend`

### 2.2 Add PostgreSQL Database
1. In Railway project dashboard, click **"+ New"**
2. Select **"Database" → "PostgreSQL"**
3. Railway auto-links it (sets DATABASE_URL variable)

### 2.3 Upload Firebase Service Account
1. In Railway, click your backend service
2. Go to **"Settings"** → **"Variables"**
3. Click **"RAW Editor"**
4. Add this variable:
```
FIREBASE_SERVICE_ACCOUNT_KEY_JSON=<paste entire firebase-service-account.json content>
```

Then update `backend/app/services/firebase_service.py` to read from env var instead of file.

### 2.4 Set Environment Variables
In Railway Variables tab, add:
```
ANTHROPIC_API_KEY=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
ALLOWED_ORIGINS=https://litdocket.com,https://www.litdocket.com
```

### 2.5 Get Railway URL
After deployment, Railway will show: `your-app.railway.app`
**Copy this URL** - you'll need it for Step 3.

---

## 🌐 Step 3: Deploy Frontend to Vercel (10 minutes)

### 3.1 Create Vercel Project
1. Go to https://vercel.com
2. Sign up with GitHub
3. Click **"Add New..." → "Project"**
4. Import your `litdocket` repository
5. **Root Directory:** Select `frontend`
6. Click **"Deploy"**

### 3.2 Set Environment Variable
1. In Vercel project settings → **"Environment Variables"**
2. Add:
```
NEXT_PUBLIC_API_URL=https://your-app.railway.app
```
(Use the Railway URL from Step 2.5)

3. Click **"Redeploy"** to apply the variable

### 3.3 Get Vercel URL
Vercel will show: `litdocket.vercel.app`
**Test it works** before adding custom domain.

---

## 🔗 Step 4: Configure Custom Domain (15 minutes)

### 4.1 In Squarespace DNS Settings

Go to Squarespace → Settings → Domains → litdocket.com → DNS Settings

Add these records:

**For Frontend (litdocket.com):**
```
Type: A
Name: @
Value: 76.76.21.21
TTL: Auto
```

```
Type: CNAME
Name: www
Value: cname.vercel-dns.com
TTL: Auto
```

**For Backend API (api.litdocket.com):**
```
Type: CNAME
Name: api
Value: your-app.railway.app
TTL: Auto
```

### 4.2 Add Domain in Vercel
1. Vercel project → **"Settings" → "Domains"**
2. Add: `litdocket.com`
3. Add: `www.litdocket.com`
4. Vercel will verify DNS and provision SSL (~5-10 minutes)

### 4.3 Add Domain in Railway
1. Railway backend service → **"Settings" → "Domains"**
2. Click **"+ Custom Domain"**
3. Enter: `api.litdocket.com`
4. Railway will verify DNS

### 4.4 Update Frontend API URL
1. In Vercel → **"Environment Variables"**
2. Change:
```
NEXT_PUBLIC_API_URL=https://api.litdocket.com
```
3. Click **"Redeploy"**

### 4.5 Update Backend CORS
1. In Railway → **"Variables"**
2. Ensure ALLOWED_ORIGINS includes:
```
ALLOWED_ORIGINS=https://litdocket.com,https://www.litdocket.com
```
3. Railway will auto-redeploy

---

## 🧪 Step 5: Test Everything

### 5.1 Wait for DNS Propagation (5-30 minutes)
Check status: https://dnschecker.org/#A/litdocket.com

### 5.2 Test Checklist
- [ ] Visit https://litdocket.com (loads homepage)
- [ ] Upload a PDF document
- [ ] Check case details page loads
- [ ] Verify deadline extraction works
- [ ] Test chatbot
- [ ] Check Firebase storage (via Firebase Console)

### 5.3 Check Logs
- **Frontend Logs:** Vercel Dashboard → Deployments → View Function Logs
- **Backend Logs:** Railway Dashboard → Your Service → Deployments → View Logs

---

## 🎉 You're Live!

**Production URLs:**
- Frontend: https://litdocket.com
- Backend API: https://api.litdocket.com
- API Docs: https://api.litdocket.com/api/docs

**Dashboards:**
- Vercel: https://vercel.com/dashboard
- Railway: https://railway.app/dashboard
- Firebase: https://console.firebase.google.com/project/florida-docket-assist

---

## 🔧 Common Issues

**Issue: "Failed to load resource" errors**
- Solution: Check CORS settings in Railway (ALLOWED_ORIGINS must include litdocket.com)

**Issue: "Database connection failed"**
- Solution: Ensure PostgreSQL is linked in Railway, check DATABASE_URL variable

**Issue: Domain not resolving**
- Solution: DNS can take up to 48 hours, but usually 5-30 minutes. Check dnschecker.org

**Issue: SSL certificate pending**
- Solution: Vercel SSL provisioning takes 5-10 minutes after DNS is verified

---

## 📊 Monitoring (Post-Launch)

1. **Set up uptime monitoring:** https://uptimerobot.com (free)
   - Monitor: https://litdocket.com
   - Monitor: https://api.litdocket.com/health

2. **Enable error tracking:** https://sentry.io (free tier)

3. **Check costs:**
   - Railway: Free $5/month credit (usually sufficient)
   - Vercel: Free tier (100GB bandwidth)
   - Firebase: Free tier (1GB storage, 50K reads/day)

---

## 🚨 Need Help?

Check `DEPLOYMENT.md` for detailed documentation.

**Quick troubleshooting:**
```bash
# Check Railway logs
railway logs

# Check Vercel logs
vercel logs

# Test backend health
curl https://api.litdocket.com/health
```
