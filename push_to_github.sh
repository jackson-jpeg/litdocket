#!/bin/bash

echo "🚀 Pushing to GitHub (litdocket repo)"
echo ""
echo "This will use your existing GitHub credentials."
echo "If you haven't set up git credentials, you'll need your Personal Access Token."
echo ""

# Use the git credential helper or prompt
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Code pushed to GitHub: https://github.com/jackson-jpeg/litdocket"
    echo ""
    echo "📍 Next steps:"
    echo "   1. Deploy backend to Railway"
    echo "   2. Deploy frontend to Vercel"
    echo "   3. Configure custom domain (litdocket.com)"
    echo ""
else
    echo ""
    echo "❌ Push failed."
    echo ""
    echo "If you got an authentication error, you may need to configure git credentials:"
    echo "   git config credential.helper store"
    echo "   Then run this script again"
    echo ""
fi
