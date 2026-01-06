# 🚀 Quick Deployment Checklist

**Goal**: Deploy LitDocket to production in ~2 hours

---

## ✅ Pre-Deployment (15 minutes)

- [ ] Push code to GitHub
  ```bash
  cd /Users/jackson/docketassist-v3
  git init
  git add .
  git commit -m "Ready for deployment"
  # Create repo on GitHub, then:
  git remote add origin https://github.com/YOUR_USERNAME/litdocket.git
  git push -u origin main
  ```

- [ ] Generate security keys
  ```bash
  # SECRET_KEY
  python3 -c "import secrets; print(secrets.token_urlsafe(64))"

  # JWT_SECRET_KEY
  python3 -c "import secrets; print(secrets.token_urlsafe(64))"
  ```

- [ ] Get Firebase credentials JSON (one-liner)
  ```bash
  cat backend/firebase-credentials.json | python3 -m json.tool --compact
  ```

---

## 🚂 Deploy Backend - Railway (30 minutes)

1. [ ] Go to https://railway.app → Login with GitHub

2. [ ] Create New Project → Deploy from GitHub → Select `litdocket` repo

3. [ ] Railway detects Python → Will auto-deploy backend folder

4. [ ] Add PostgreSQL Database:
   - Click "+ New" → Database → PostgreSQL
   - Railway auto-sets `DATABASE_URL` ✓

5. [ ] Add Environment Variables (click Settings → Variables):
   ```bash
   SECRET_KEY=<paste generated key>
   JWT_SECRET_KEY=<paste generated key>
   ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY
   ALLOWED_ORIGINS=https://litdocket.com,https://www.litdocket.com
   FIREBASE_CREDENTIALS_JSON=<paste one-line JSON>
   DEBUG=false
   ```

6. [ ] Generate Public Domain:
   - Settings → Networking → Generate Domain
   - Save URL: `litdocket-backend-production.up.railway.app`

7. [ ] Test backend:
   ```bash
   curl https://litdocket-backend-production.up.railway.app/
   # Should return: {"message": "LitDocket API"}
   ```

---

## ▲ Deploy Frontend - Vercel (20 minutes)

1. [ ] Go to https://vercel.com → Login with GitHub

2. [ ] Add New Project → Import `litdocket` repo

3. [ ] Configure:
   - Root Directory: `frontend`
   - Framework Preset: Next.js (auto-detected)
   - Click Deploy

4. [ ] Add Environment Variables (Settings → Environment Variables):
   ```bash
   NEXT_PUBLIC_API_URL=https://litdocket-backend-production.up.railway.app
   NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSy...
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=litdocket.firebaseapp.com
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=litdocket
   NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=litdocket.appspot.com
   NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
   NEXT_PUBLIC_FIREBASE_APP_ID=1:123456:web:abc123
   ```

5. [ ] Redeploy after adding env vars:
   - Deployments → Click latest → Redeploy

---

## 🌐 Connect Domain (30 minutes + DNS wait)

### Vercel Domain Setup

1. [ ] In Vercel Project → Settings → Domains
2. [ ] Add Domain: `litdocket.com`
3. [ ] Vercel shows DNS records needed

### Update DNS at Registrar (Namecheap example)

1. [ ] Go to your domain registrar
2. [ ] Advanced DNS → Delete existing A/CNAME for `@` and `www`
3. [ ] Add these records:
   ```
   Type: A
   Host: @
   Value: 76.76.21.21
   TTL: Auto

   Type: CNAME
   Host: www
   Value: cname.vercel-dns.com
   TTL: Auto
   ```

4. [ ] Wait 15-30 minutes for DNS propagation
5. [ ] Check: https://dnschecker.org/#A/litdocket.com

### Optional: Custom Backend Domain

1. [ ] In Railway → Settings → Networking → Custom Domain
2. [ ] Add: `api.litdocket.com`
3. [ ] Add CNAME at registrar:
   ```
   Type: CNAME
   Host: api
   Value: litdocket-backend-production.up.railway.app
   TTL: Auto
   ```
4. [ ] Update Vercel env var:
   ```
   NEXT_PUBLIC_API_URL=https://api.litdocket.com
   ```

---

## 🔥 Configure Firebase (10 minutes)

1. [ ] Firebase Console → Authentication → Settings → Authorized Domains
   - Add: `litdocket.com`
   - Add: `www.litdocket.com`

2. [ ] Firebase Console → Storage → Rules:
   ```javascript
   rules_version = '2';
   service firebase.storage {
     match /b/{bucket}/o {
       match /documents/{userId}/{allPaths=**} {
         allow read, write: if request.auth != null && request.auth.uid == userId;
       }
     }
   }
   ```

---

## 🧪 Test Everything (15 minutes)

- [ ] Visit https://litdocket.com
- [ ] Sign up / Login works
- [ ] Upload a PDF
- [ ] AI analyzes document
- [ ] Deadlines show up
- [ ] Chat works
- [ ] Refresh - data persists

### Check Logs

**Railway:**
```bash
npm i -g @railway/cli
railway login
railway logs
```

**Vercel:**
- Dashboard → Deployments → View Logs

---

## 🐛 Quick Troubleshooting

**Frontend can't reach backend?**
- Check `NEXT_PUBLIC_API_URL` in Vercel
- Check `ALLOWED_ORIGINS` in Railway
- Test backend: `curl https://your-backend.railway.app/`

**Database errors?**
- Check Railway PostgreSQL is running
- Verify `DATABASE_URL` is set

**Firebase auth not working?**
- Check all `NEXT_PUBLIC_FIREBASE_*` env vars
- Verify domain authorized in Firebase Console

**AI not working?**
- Check `ANTHROPIC_API_KEY` in Railway
- Verify key has credits: https://console.anthropic.com

---

## 💰 Monthly Costs

| Service | Cost |
|---------|------|
| Railway (Backend + DB) | $5 |
| Vercel (Frontend) | FREE |
| Firebase (Storage) | FREE |
| Anthropic API | ~$10-50 |
| Domain | ~$1/month |

**Total: ~$16-56/month**

---

## 🎉 Post-Deployment

- [ ] Test all features
- [ ] Invite beta users
- [ ] Monitor Railway/Vercel dashboards
- [ ] Set up error tracking (optional)
- [ ] Plan for scaling

---

## 🆘 Need Help?

1. **Check logs first**:
   - Railway: Click deployment → View Logs
   - Vercel: Deployments → Function Logs
   - Browser: Open DevTools Console

2. **Common fixes**:
   - Redeploy (often fixes caching issues)
   - Check environment variables are set
   - Verify DNS has propagated

3. **Documentation**:
   - Railway: https://docs.railway.app
   - Vercel: https://vercel.com/docs
   - Full guide: See DEPLOYMENT_GUIDE.md

---

**You've got this! 🚀**
