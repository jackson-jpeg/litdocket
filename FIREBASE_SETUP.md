# Firebase Setup Instructions

## ✅ Project Created
**Project ID:** florida-docket-assist
**Console:** https://console.firebase.google.com/project/florida-docket-assist/overview

---

## Steps to Complete (Do these in order):

### 1. Enable Firestore API
🔗 **URL:** https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=florida-docket-assist

- Click **"Enable"** button
- Wait for it to complete (~30 seconds)

### 2. Initialize Firebase Storage
🔗 **URL:** https://console.firebase.google.com/project/florida-docket-assist/storage

- Click **"Get Started"**
- Choose **"Start in production mode"** (we have custom rules)
- Select location: **us-central1** (recommended)
- Click **"Done"**

### 3. Generate Service Account Key
🔗 **URL:** https://console.firebase.google.com/project/florida-docket-assist/settings/serviceaccounts/adminsdk

- Scroll to **"Firebase Admin SDK"** section
- Click **"Generate new private key"**
- Click **"Generate key"** in confirmation dialog
- **Save the downloaded JSON file as:**
  ```
  /Users/jackson/docketassist-v3/backend/firebase-service-account.json
  ```

### 4. Deploy Firebase Rules
Once you've completed steps 1-3, run this command:

```bash
cd /Users/jackson/docketassist-v3
firebase deploy --only firestore,storage --project florida-docket-assist
```

---

## What's Already Done

✅ Firebase project created
✅ Firestore security rules configured
✅ Storage security rules configured (PDFs only, 50MB max)
✅ Backend integrated with Firebase Storage
✅ Claude AI integration ready

---

## Next Steps After Setup

Once Firebase is configured:
1. Restart the backend server
2. Test PDF upload at http://localhost:3000
3. Check Firebase Console to see uploaded files

---

## Need Help?

**Firebase Console:** https://console.firebase.google.com/project/florida-docket-assist
**Storage Browser:** https://console.firebase.google.com/project/florida-docket-assist/storage
**Firestore Database:** https://console.firebase.google.com/project/florida-docket-assist/firestore
