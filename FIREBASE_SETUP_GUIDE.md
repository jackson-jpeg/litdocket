# Firebase Setup Guide for LitDocket Authentication

This guide walks you through setting up Firebase Authentication for the LitDocket application.

---

## 🚀 Quick Start

### 1. Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Add project"**
3. Enter project name: `LitDocket` (or your preferred name)
4. Disable Google Analytics (optional, can enable later)
5. Click **"Create project"**

---

### 2. Enable Authentication Methods

1. In Firebase Console, go to **Build > Authentication**
2. Click **"Get started"**
3. Go to **"Sign-in method"** tab

#### Enable Google Sign-In:
1. Click on **Google**
2. Toggle **"Enable"**
3. Set project support email (your email)
4. Click **"Save"**

#### Enable Email/Password:
1. Click on **Email/Password**
2. Toggle **"Enable"**
3. Click **"Save"**

---

### 3. Get Firebase Configuration (Frontend)

1. In Firebase Console, go to **Project Settings** (⚙️ icon)
2. Scroll down to **"Your apps"**
3. Click the **Web** icon (`</>`)
4. Register app with nickname: `LitDocket Web`
5. **Copy the Firebase config object**

It will look like this:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyA...",
  authDomain: "litdocket-xyz.firebaseapp.com",
  projectId: "litdocket-xyz",
  storageBucket: "litdocket-xyz.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123..."
};
```

6. Add these values to `/frontend/.env.local`:

```bash
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyA...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=litdocket-xyz.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=litdocket-xyz
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=litdocket-xyz.appspot.com
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=123456789
NEXT_PUBLIC_FIREBASE_APP_ID=1:123456789:web:abc123...
```

---

### 4. Get Firebase Admin SDK Credentials (Backend)

1. In Firebase Console, go to **Project Settings > Service accounts**
2. Click **"Generate new private key"**
3. Click **"Generate key"** (downloads a JSON file)
4. **IMPORTANT:** Keep this file secure! Never commit to Git!

#### Option A: Use File Path (Development)

1. Move the downloaded JSON file to your backend directory:
   ```bash
   mv ~/Downloads/litdocket-xyz-firebase-adminsdk-xxxxx.json /path/to/backend/firebase-credentials.json
   ```

2. Add to `/backend/.env`:
   ```bash
   FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
   ```

3. Add to `.gitignore` (should already be there):
   ```
   firebase-credentials.json
   ```

#### Option B: Use Environment Variable (Production)

1. Copy the entire contents of the JSON file
2. Minify it (remove whitespace): https://www.cleancss.com/json-minify/
3. Add to your production environment:
   ```bash
   FIREBASE_CREDENTIALS_JSON='{"type":"service_account","project_id":"...",...}'
   ```

---

### 5. Configure Firebase Storage (For Document Uploads)

1. In Firebase Console, go to **Build > Storage**
2. Click **"Get started"**
3. Select **"Start in production mode"** (we'll add security rules later)
4. Choose storage location (e.g., `us-central1`)
5. Click **"Done"**

6. Add storage bucket to `/backend/.env`:
   ```bash
   FIREBASE_STORAGE_BUCKET=litdocket-xyz.appspot.com
   ```

#### Security Rules (Recommended):

Go to **Storage > Rules** and update:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /documents/{userId}/{allPaths=**} {
      // Users can only read/write their own documents
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    match /public/{allPaths=**} {
      // Public files readable by anyone
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

---

### 6. Configure Authorized Domains

1. In Firebase Console, go to **Authentication > Settings > Authorized domains**
2. Add your domains:
   - `localhost` (for development)
   - `litdocket.com` (for production)
   - Any other domains you'll deploy to

---

### 7. Update Backend Environment

Create or update `/backend/.env`:

```bash
# Copy from .env.example and fill in your values

# Firebase
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
FIREBASE_STORAGE_BUCKET=litdocket-xyz.appspot.com

# JWT (change this secret!)
JWT_SECRET_KEY=your-random-secret-key-here

# Database
DATABASE_URL=sqlite:///./docket_assist.db

# Claude API
ANTHROPIC_API_KEY=your-anthropic-key

# CORS
ALLOWED_ORIGINS=http://localhost:3000
```

---

### 8. Test the Setup

#### Start Backend:
```bash
cd backend
source venv/bin/activate  # or: . venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

#### Start Frontend:
```bash
cd frontend
npm run dev
```

#### Test Authentication:

1. Visit `http://localhost:3000/signup`
2. Try creating an account with:
   - **Google Sign-In** (should open Google popup)
   - **Email/Password** (should create account)
3. Check Firebase Console > **Authentication > Users** to see new user

---

## 🔐 Security Best Practices

### Development:
- ✅ Use `firebase-credentials.json` file
- ✅ Add to `.gitignore`
- ✅ Never commit credentials

### Production:
- ✅ Use `FIREBASE_CREDENTIALS_JSON` environment variable
- ✅ Store in secure environment (Vercel, Railway, etc.)
- ✅ Rotate JWT secret regularly
- ✅ Enable Firebase App Check (optional, advanced)
- ✅ Set up Firebase Security Rules for Storage

---

## 🐛 Troubleshooting

### Error: "Firebase app not initialized"
**Fix:** Make sure you've added all Firebase environment variables to `.env.local`

### Error: "Invalid API key"
**Fix:** Double-check your `NEXT_PUBLIC_FIREBASE_API_KEY` in `.env.local`

### Error: "Credential implementation provided to initializeApp() via the 'credential' property failed to fetch a valid Google OAuth2 access token"
**Fix:** Make sure your `firebase-credentials.json` file is valid and in the correct location

### Error: "The email address is already in use"
**Fix:** User already exists. Try logging in instead of signing up, or use a different email.

### Google Sign-In Popup Blocked
**Fix:** Allow popups in your browser for `localhost:3000`

### CORS Error from Backend
**Fix:** Make sure `ALLOWED_ORIGINS` in backend `.env` includes `http://localhost:3000`

---

## 📚 Next Steps

After Firebase is set up:

1. ✅ **Test the authentication flow**
   - Sign up with email/password
   - Sign up with Google
   - Sign in with existing account
   - Complete profile (firm, role, jurisdictions)

2. ✅ **Customize the experience**
   - Update branding colors
   - Add custom email templates (Firebase Console > Authentication > Templates)
   - Set up email verification (optional)

3. ✅ **Deploy to production**
   - Add production domain to Firebase Authorized Domains
   - Use `FIREBASE_CREDENTIALS_JSON` env variable
   - Update `ALLOWED_ORIGINS` in backend
   - Change `JWT_SECRET_KEY` to a secure random string

---

## 🎉 You're All Set!

Authentication is now integrated with LitDocket. Users can:
- Sign up with Google or email/password
- Complete their profile with firm and jurisdiction info
- Access the dashboard with full authentication

Need help? Check the [Firebase Documentation](https://firebase.google.com/docs/auth) or open an issue.
