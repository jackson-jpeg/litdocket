# Get Your Firebase Service Account Key (2 Minutes)

You're almost done! Just need to download ONE file from Firebase.

---

## Step 1: Go to Firebase Console

Click this link (it will take you directly to the right page):

👉 **https://console.firebase.google.com/project/litdocket/settings/serviceaccounts/adminsdk**

---

## Step 2: Download the Key

1. You'll see a section called **"Admin SDK configuration snippet"**
2. Make sure **"Node.js"** is selected (should be by default)
3. Click the button: **"Generate new private key"**
4. Click **"Generate key"** in the popup

A file will download: `litdocket-firebase-adminsdk-xxxxx.json`

---

## Step 3: Move the File

Move the downloaded file to your backend folder and rename it:

```bash
mv ~/Downloads/litdocket-firebase-adminsdk-*.json /Users/jackson/docketassist-v3/backend/firebase-credentials.json
```

Or just:
1. Find the downloaded file in your Downloads folder
2. Drag it to: `/Users/jackson/docketassist-v3/backend/`
3. Rename it to: `firebase-credentials.json`

---

## That's It! ✅

Now you can test the authentication:

```bash
# Make sure backend is running
cd /Users/jackson/docketassist-v3/backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000

# In another terminal, start frontend
cd /Users/jackson/docketassist-v3/frontend
npm run dev
```

Then visit: **http://localhost:3000/signup**

---

## Already Set Up For You ✅

I've already configured:
- ✅ Frontend Firebase config (`.env.local`)
- ✅ Backend environment variables (`.env`)
- ✅ Database (using SQLite - no PostgreSQL needed)
- ✅ JWT secret keys
- ✅ CORS settings

All you needed to do was get that one Firebase file!
