# 10-Minute LitDocket Deployment

## Step 1: Fix GitHub (1 min)

Your push failed because GitHub killed password auth. Quick fix:

**Option A (EASIEST):** Download [GitHub Desktop](https://desktop.github.com), it handles auth automatically.

**Option B (Token):**
1. Go to https://github.com/settings/tokens/new
2. Name: "litdocket", Expiration: 90 days, Check: "repo"
3. Click "Generate token", copy it (starts with ghp_...)
4. Run:
```bash
git remote set-url origin https://YOUR_TOKEN_HERE@github.com/jackson-jpeg/litdocket.git
git push -u origin main
```

## Step 2: Deploy Frontend to Vercel (3 min)

```bash
cd /Users/jackson/docketassist-v3/frontend
vercel
```

Follow prompts (just hit enter for defaults). When asked "Which scope?", choose your account.

After deployment, go to Vercel dashboard → Settings → Environment Variables and add:

```
NEXT_PUBLIC_API_URL=https://YOUR-RAILWAY-URL.railway.app
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyCiqXuFKr3qYquN_5d4Xb-UCcEHa4VEOXw
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=litdocket.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=litdocket
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=litdocket.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=944286580962
NEXT_PUBLIC_FIREBASE_APP_ID=1:944286580962:web:f09a32a577010c7e921ebb
```

## Step 3: Deploy Backend to Railway (5 min)

1. Go to https://railway.app → Login with GitHub

2. New Project → Deploy from GitHub repo → Select: litdocket
   - **Important:** Set root directory to `/backend`

3. Add Database:
   - Click "+ New" → Database → PostgreSQL
   - Railway auto-connects it ✓

4. Add Environment Variables (Settings → Variables):

```bash
SECRET_KEY=n3hjn8HNKGqHRg4egfB4P2Db12r8FEqSu5yi9nqVQx83KZZTy0n4tK_vYXjjF-F0ig8WHljJ-LDbE1Q3fbUNsg

JWT_SECRET_KEY=EQuUgqOZoAzbctY-GRYVFeKKwOjPIPc1bqH1i5gHUcnqJCY9nnT-g5akznK7Mou7r7F-mIT73Mcpoafob5G_-g

ANTHROPIC_API_KEY=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

DEBUG=false

ALLOWED_ORIGINS=https://your-vercel-url.vercel.app

FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"litdocket","private_key_id":"5a40255216a2f612e47721e862bd3a4183763b19","private_key":"-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC+jrI0SttTD7rN\nLUHxAQFKYrHc9WQDD5NC5vxVhqKn1evzpypBYtPBSkM9py/ON+7xFpY4hVGJHx72\ngLjWE45h3flxFsrMTP8EQAFYx6vANigu12+ti+dw7wxrF9xGxKvQ+gp2GTU78meV\nvqoc9+sAFMv+dXotWc5LMsezF4WXZYPqnrX5maRhjvrnFP965CUC9DEK6kv/Zv0b\n6Q+SB4AHu1/j49z/yLkCjv2KLP+7DYFSF2dKyIkWMny/722KVHPDZZbO5RfKBOht\nGIocBNWZ88vO5woYy/bvnIfDXxDmes96yuZdplJHF3/W0QuQwLn2s4/Ff1qwV6l8\n0h0C5fTrAgMBAAECggEAK2IgZzBds5DitgCmQSC58v36QXRqsxmyLKqa6zvOP0jA\nQcYepClETX7DRT+RbjEkyKWcSLztfbrkmTlgG3jzUwuu1RTb0dx7uLN7uwMmconB\n5zwsFEZESF1cJeuWPlRbS6YJiK6fhIjhFWIFp7e3vFp/wOxtBvMpuMwUVA04YGmb\nGl0RF9Jm4C/v9nZLGcaLPgg+UhOyN8dS3ri95i8cuj7FHeAIKjeJhDblydpg+gX/\nMgqDHxL9uERHHub/TVyzVnov9S86jKm5/bt/K3e6XGQA1Hq4ht+1X8hU3qmuc/dI\nFOuFf3ylQdNjI+Ko/r0gNKn6uGmYNcpA0+RRdRX9PQKBgQDkEaKMv/E3RbFgsM41\nv1U6ND80gGWCCFhA+LIsQI/PStGnvGIchgCIlIRj26KcuGsxwRP7iOJ4kda1sQbC\niqY1Zp9vkjr6tBxrgfO6Iu2bUHLS8/Ln9z9fgf2wm1LLUgcGdYjVrzE8Jw3lkqsQ\nqDMYVcqQoaJlT+AST6rY+0XSzwKBgQDV5QJzNfGBcGeDOyutjNO6O6QN8SWIj4uH\nNtLZNrOUnEmvJxV8mJFd295il8/9T26RfD2S5qgsCIyeXas26a8+b8Isf3tJWHDL\nPDAcwzEfFx0/khWdxGEeVHsmaFHGdxvX11wWCNUjmloA8yRlJDVJrqrYX9UFYNYv\n3AEGJwzzJQKBgQDORgzolCmMviHhu8el4PkqfVq1F3O3meiISuaLE5F+AMOCm+V4\nutH8tabP0jRO3pVFGMYD+BgsyGqTRhtBFLmjDsAg3vctDH2v1ocj0Ldqg+Z2WWFW\n386XiTBz7OeDMRtdgixSZ/N13jS5cF/73sTnu6BME4SXcRjONvPk786FDQKBgHGD\nI5W43v3uhUCjuj5UKlj/JcUwYNbkNwv/EE6uNQd9Ga2WdFS3Mw44jQCNyJeJ/AfB\ng3veZQlZUCcLVr3BrnrYHJg431jBUrrIqk/ZVsxFHASMpmQfv9q0wtZTLnLA60nU\nxM38ygAm/fTbFEmIua7sv0YtNYOxLHohq3l0Z+7xAoGBANlPV0xuwTg002+Fvuvf\nV2lssUtOo0hMgEMCr29gW876f+Oj7y267/OEov0ATEM8M7qNsLwfu1nQePZ/kEKT\nlDNpYAw5d8nKEqFD/ZCAFuRjge6S+DVisw/41qzHqIvu9QckGIXwc4p4rIsXq4wP\nVzOHJcEGthqBxTfdd2oi8sdd\n-----END PRIVATE KEY-----\n","client_email":"firebase-adminsdk-fbsvc@litdocket.iam.gserviceaccount.com","client_id":"112141988351292469320","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40litdocket.iam.gserviceaccount.com","universe_domain":"googleapis.com"}
```

5. Generate Public Domain:
   - Settings → Networking → Generate Domain
   - Copy URL (like: `litdocket-production-abc.railway.app`)

6. Go back to Vercel:
   - Settings → Environment Variables
   - Update `NEXT_PUBLIC_API_URL` to your Railway URL
   - Deployments → Redeploy

## Step 4: Update Firebase (1 min)

Go to Firebase Console → Authentication → Settings → Authorized Domains

Add:
- Your Vercel URL (e.g., `litdocket.vercel.app`)
- (Optional) Your custom domain if you add one later

## Done!

Visit your Vercel URL. Your app is live.

**Connect custom domain (optional):**
- Vercel: Settings → Domains → Add `litdocket.com`
- Update DNS at your registrar with the records Vercel shows you

**Cost:**
- Vercel: FREE
- Railway: $5/month
- Total: $5/month + Anthropic API usage

---

**Troubleshooting:**

- Frontend can't reach backend? Check CORS in Railway env vars
- 401 errors? Check Firebase domains are authorized
- Backend not starting? Check Railway logs
