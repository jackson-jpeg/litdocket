# 🚀 Deploy LitDocket to Production

**Goal**: Deploy your app to **litdocket.com** using beginner-friendly services.

**Stack Overview:**
- ☁️ **Frontend** → Vercel (Free tier, perfect for Next.js)
- ☁️ **Backend** → Railway (Easiest for Python, $5/month)
- 🗄️ **Database** → PostgreSQL on Railway (Included with backend)
- 📁 **File Storage** → Firebase Storage (Free tier for PDFs)
- 🌐 **Domain** → litdocket.com → Points to Vercel

---

## 📋 Prerequisites

Before starting, you'll need:

- [ ] GitHub account (to store your code)
- [ ] Vercel account (sign up at vercel.com with GitHub)
- [ ] Railway account (sign up at railway.app with GitHub)
- [ ] Domain purchased (litdocket.com at Namecheap/GoDaddy/etc)
- [ ] Firebase project (already have from development)
- [ ] Anthropic API key (already have)

**Time to complete**: ~2 hours (mostly waiting for deployments)

---

## 🎯 Deployment Strategy

```
┌──────────────────────────────────────────────────────────┐
│  litdocket.com (Your Domain)                             │
│  ↓                                                        │
│  Vercel (Frontend)                                       │
│  ├─ Serves Next.js app                                   │
│  └─ Makes API calls to → backend.litdocket.com          │
│                           ↓                               │
│                    Railway (Backend)                      │
│                    ├─ FastAPI Python server              │
│                    ├─ PostgreSQL database                │
│                    └─ Calls Claude AI + Firebase         │
└──────────────────────────────────────────────────────────┘
```

---

## Part 1: Prepare Your Code for Deployment

### Step 1.1: Push Code to GitHub

```bash
cd /Users/jackson/docketassist-v3

# Initialize git if not already done
git init

# Create .gitignore files if they don't exist
cat > .gitignore << 'EOF'
# Environment variables (NEVER commit these!)
.env
.env.local
*.env

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
env/

# Database
*.db
*.sqlite
*.sqlite3

# Firebase credentials
firebase-credentials.json
*-firebase-adminsdk-*.json

# Logs
*.log

# OS files
.DS_Store
EOF

cat > backend/.gitignore << 'EOF'
.env
__pycache__/
*.pyc
venv/
*.db
*.sqlite
firebase-credentials.json
EOF

cat > frontend/.gitignore << 'EOF'
.env
.env.local
.next/
node_modules/
.DS_Store
EOF

# Add all files
git add .

# Commit
git commit -m "Initial commit - Ready for deployment"

# Create GitHub repo (you'll need to do this on GitHub.com)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/litdocket.git
git branch -M main
git push -u origin main
```

**IMPORTANT**: Make sure `.env` files are NOT committed! They contain secrets.

---

## Part 2: Deploy Backend to Railway

### Step 2.1: Sign Up for Railway

1. Go to **https://railway.app**
2. Click **"Login with GitHub"**
3. Authorize Railway to access your GitHub

### Step 2.2: Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your **litdocket** repository
4. Railway will ask which folder - Select **"backend"**

### Step 2.3: Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"**
3. Choose **"PostgreSQL"**
4. Railway will automatically create a database and set `DATABASE_URL`

### Step 2.4: Configure Environment Variables

In Railway project settings, add these environment variables:

```bash
# Required - Security Keys
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(64))">
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(64))">

# Required - AI API
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE

# Required - CORS (will add frontend URL later)
ALLOWED_ORIGINS=https://litdocket.com,https://www.litdocket.com

# Optional - Enable debug mode for initial testing
DEBUG=false

# Firebase - Option 1: JSON string (recommended)
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}

# Firebase - Option 2: File path (need to upload file)
# FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json

# Database URL (auto-set by Railway, but verify it's there)
# DATABASE_URL=postgresql://... (automatically set by Railway)
```

**How to get FIREBASE_CREDENTIALS_JSON:**
```bash
# On your local machine
cat backend/firebase-credentials.json | jq -c '.'
# Copy the entire output (one long line) and paste into Railway env var
```

### Step 2.5: Deploy!

1. Railway will auto-deploy after you add env vars
2. Wait 2-3 minutes for build to complete
3. Check logs for any errors
4. Click **"Settings"** → **"Networking"** → **"Generate Domain"**
5. You'll get a URL like: `litdocket-backend-production.up.railway.app`

**Test it:**
```bash
curl https://litdocket-backend-production.up.railway.app/
# Should return: {"message": "LitDocket API"}
```

### Step 2.6: Set Up Custom Domain for Backend (Optional but Recommended)

1. In Railway, go to **Settings** → **Networking**
2. Click **"Custom Domain"**
3. Add: `api.litdocket.com`
4. Railway will give you a CNAME record
5. Go to your domain registrar (Namecheap/GoDaddy)
6. Add CNAME record:
   ```
   Type: CNAME
   Host: api
   Value: litdocket-backend-production.up.railway.app
   TTL: 3600
   ```
7. Wait 5-15 minutes for DNS to propagate
8. Test: `https://api.litdocket.com/`

---

## Part 3: Deploy Frontend to Vercel

### Step 3.1: Sign Up for Vercel

1. Go to **https://vercel.com**
2. Click **"Sign Up"** → **"Continue with GitHub"**
3. Authorize Vercel

### Step 3.2: Import Your Project

1. Click **"Add New..."** → **"Project"**
2. Find your **litdocket** repo
3. Click **"Import"**
4. Vercel detects it's a Next.js app ✓

### Step 3.3: Configure Build Settings

**Root Directory**: `frontend`

**Build Command**: `npm run build` (auto-detected)

**Output Directory**: `.next` (auto-detected)

**Install Command**: `npm install` (auto-detected)

### Step 3.4: Add Environment Variables

Click **"Environment Variables"** and add:

```bash
# Backend API URL (use your Railway URL)
NEXT_PUBLIC_API_URL=https://api.litdocket.com

# Firebase Config (get from Firebase Console → Project Settings → Web App)
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSy...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=litdocket.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=litdocket
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=litdocket.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456:web:abc123

# Optional - WebSocket URL (if you add real-time features later)
# NEXT_PUBLIC_WS_URL=wss://api.litdocket.com/ws
```

### Step 3.5: Deploy!

1. Click **"Deploy"**
2. Wait 2-3 minutes for build
3. Vercel gives you a URL: `litdocket.vercel.app`
4. Test it - should load but might have errors (need to connect domain)

---

## Part 4: Connect Your Domain (litdocket.com)

### Step 4.1: Add Domain to Vercel

1. In Vercel project, click **"Settings"** → **"Domains"**
2. Click **"Add"**
3. Enter: `litdocket.com`
4. Vercel will show DNS records you need to add

### Step 4.2: Configure DNS at Your Registrar

Go to your domain registrar (Namecheap, GoDaddy, etc.) and add:

**For Namecheap:**
1. Go to Domain List → Manage → Advanced DNS
2. Delete any existing A/CNAME records for `@` and `www`
3. Add these records:

```
Type: A Record
Host: @
Value: 76.76.21.21
TTL: Automatic

Type: CNAME Record
Host: www
Value: cname.vercel-dns.com
TTL: Automatic
```

**For GoDaddy/Other:**
Similar process - check Vercel's instructions for your specific registrar.

### Step 4.3: Wait for DNS Propagation

- Takes 5 minutes to 48 hours (usually ~15 minutes)
- Check status: https://dnschecker.org/#A/litdocket.com
- Once propagated, visit https://litdocket.com - should work!

### Step 4.4: Force HTTPS

In Vercel:
1. Go to **Settings** → **Domains**
2. Ensure **"Redirect www to non-www"** is enabled
3. Ensure **"Force HTTPS"** is enabled

---

## Part 5: Configure Firebase Storage for Production

### Step 5.1: Update Firebase Rules

Go to Firebase Console → Storage → Rules:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Documents - Only authenticated users can read/write their own
    match /documents/{userId}/{allPaths=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }

    // Case files
    match /cases/{userId}/{caseId}/{allPaths=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

### Step 5.2: Add Production Domain to Firebase

1. Firebase Console → Authentication → Settings → Authorized Domains
2. Add: `litdocket.com`
3. Add: `www.litdocket.com`
4. Add: `api.litdocket.com` (for backend)

---

## Part 6: Update Backend CORS for Production

### Step 6.1: Update Railway Environment Variables

In Railway, update `ALLOWED_ORIGINS`:

```bash
ALLOWED_ORIGINS=https://litdocket.com,https://www.litdocket.com,https://litdocket.vercel.app
```

### Step 6.2: Redeploy

Railway will auto-redeploy with new CORS settings.

---

## Part 7: Test Everything

### Step 7.1: Smoke Test Checklist

- [ ] Visit https://litdocket.com - Loads homepage
- [ ] Click **"Sign Up"** - Firebase auth works
- [ ] Login with Google - OAuth works
- [ ] Upload a PDF - Backend receives it
- [ ] AI analysis runs - Deadlines extracted
- [ ] Case summary generates - AI working
- [ ] Chat works - Messages send/receive
- [ ] Refresh page - Data persists (database working)

### Step 7.2: Check Backend Logs

In Railway:
1. Go to **Deployments** → Click latest deployment
2. Click **"View Logs"**
3. Look for errors (especially CORS, database, Firebase)

### Step 7.3: Check Frontend Logs

In Vercel:
1. Go to **Deployments** → Click latest
2. Click **"View Function Logs"**
3. Check browser console for errors

---

## 🐛 Troubleshooting Common Issues

### Issue: Frontend can't reach backend

**Symptoms**: Network errors, CORS errors

**Fix**:
1. Check `NEXT_PUBLIC_API_URL` in Vercel env vars
2. Check `ALLOWED_ORIGINS` in Railway env vars
3. Verify backend is responding: `curl https://api.litdocket.com/`

### Issue: Database connection errors

**Symptoms**: `sqlalchemy.exc.OperationalError`

**Fix**:
1. Check Railway logs
2. Verify `DATABASE_URL` env var is set
3. Check PostgreSQL database is running (Railway dashboard)

### Issue: Firebase authentication not working

**Symptoms**: "Firebase: Error (auth/invalid-api-key)"

**Fix**:
1. Check all `NEXT_PUBLIC_FIREBASE_*` env vars in Vercel
2. Verify domain is authorized in Firebase Console
3. Check Firebase credentials JSON in Railway

### Issue: AI not responding

**Symptoms**: Deadlines not extracting, chat not working

**Fix**:
1. Check `ANTHROPIC_API_KEY` in Railway
2. Verify API key is valid and has credits
3. Check Railway logs for AI errors

### Issue: File uploads failing

**Symptoms**: "Failed to upload document"

**Fix**:
1. Check Firebase Storage rules allow uploads
2. Verify `FIREBASE_CREDENTIALS_JSON` in Railway
3. Check Firebase Storage bucket exists and is writable

---

## 💰 Cost Breakdown

| Service | Tier | Cost | Notes |
|---------|------|------|-------|
| **Vercel** | Hobby | **FREE** | Perfect for personal projects |
| **Railway** | Starter | **$5/month** | Includes PostgreSQL database |
| **Firebase** | Spark (Free) | **FREE** | 1GB storage, 50K reads/day |
| **Anthropic** | Pay-as-you-go | **~$10-50/month** | Depends on usage |
| **Domain** | Annual | **$10-15/year** | One-time purchase |

**Total**: ~$15-65/month (mostly AI costs)

---

## 🔄 Updating Your Deployment

### Update Frontend

```bash
# Make changes to frontend code
git add .
git commit -m "Update frontend"
git push

# Vercel auto-deploys on every push to main!
# Check: https://vercel.com/dashboard
```

### Update Backend

```bash
# Make changes to backend code
git add .
git commit -m "Update backend"
git push

# Railway auto-deploys on every push to main!
# Check: https://railway.app/dashboard
```

---

## 🔐 Security Checklist

Before going live:

- [ ] All secrets are in environment variables (NOT in code)
- [ ] `.env` files are in `.gitignore`
- [ ] Firebase credentials are NOT in git repo
- [ ] `DEBUG=false` in production
- [ ] HTTPS is forced (Vercel does this automatically)
- [ ] CORS only allows your domain
- [ ] Firebase Storage rules restrict access
- [ ] PostgreSQL password is strong (Railway generates this)
- [ ] Rotate API keys regularly

---

## 📊 Monitoring Your App

### Railway Metrics
- CPU usage
- Memory usage
- Request count
- Response times

### Vercel Analytics (Optional - $10/month)
- Page views
- Unique visitors
- Performance scores

### Firebase Console
- Authentication users
- Storage usage
- Database reads/writes

---

## 🚀 Optional Enhancements

### Add Custom Domain for Backend
- `api.litdocket.com` looks more professional
- Follow Railway custom domain instructions above

### Enable Vercel Analytics
- Get insights on traffic and performance
- $10/month or free tier for basic metrics

### Set Up Error Tracking (Sentry)
- Free tier: 5K errors/month
- Helps debug production issues
- Add to both frontend and backend

### Add Database Backups
- Railway includes daily backups
- Can export PostgreSQL dumps manually

---

## 📝 Post-Deployment Tasks

- [ ] Test all features in production
- [ ] Set up monitoring alerts
- [ ] Create admin account
- [ ] Prepare user documentation
- [ ] Set up analytics (Google Analytics, Vercel Analytics)
- [ ] Create backup strategy
- [ ] Plan for scaling (if usage grows)

---

## 🎉 You're Live!

Congratulations! Your app is now running at **https://litdocket.com**

**Share it with the world!** 🌎

---

## Need Help?

### Common Commands

**Check Railway logs:**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# View logs
railway logs
```

**Check Vercel logs:**
```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# View logs
vercel logs litdocket
```

### Documentation Links
- Railway: https://docs.railway.app
- Vercel: https://vercel.com/docs
- Firebase: https://firebase.google.com/docs
- Next.js: https://nextjs.org/docs

---

**Last Updated**: January 6, 2026
**Deployment Status**: Ready to deploy! 🚀
