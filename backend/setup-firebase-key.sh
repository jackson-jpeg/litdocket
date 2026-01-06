#!/bin/bash

# Simple script to move your Firebase key to the right place

echo "🔍 Looking for Firebase key in Downloads..."

# Find the most recent Firebase key file
KEY_FILE=$(ls -t ~/Downloads/litdocket-firebase-adminsdk-*.json 2>/dev/null | head -1)

if [ -z "$KEY_FILE" ]; then
    echo "❌ No Firebase key found in Downloads folder"
    echo ""
    echo "Please download it first:"
    echo "1. Go to: https://console.firebase.google.com/project/litdocket/settings/serviceaccounts/adminsdk"
    echo "2. Click 'Generate new private key'"
    echo "3. Then run this script again"
    exit 1
fi

echo "✅ Found: $(basename "$KEY_FILE")"
echo ""
echo "📦 Moving to backend folder..."

# Move and rename
cp "$KEY_FILE" ./firebase-credentials.json

if [ -f ./firebase-credentials.json ]; then
    echo "✅ Firebase credentials set up successfully!"
    echo ""
    echo "🚀 You're ready to go! Start the servers:"
    echo ""
    echo "   Backend:"
    echo "   source venv/bin/activate && python -m uvicorn app.main:app --reload"
    echo ""
    echo "   Frontend (in another terminal):"
    echo "   cd ../frontend && npm run dev"
    echo ""
    echo "Then visit: http://localhost:3000/signup"
else
    echo "❌ Something went wrong. Please manually copy the file to:"
    echo "   $(pwd)/firebase-credentials.json"
fi
