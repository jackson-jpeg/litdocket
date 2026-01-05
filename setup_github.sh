#!/bin/bash

echo "🔐 GitHub Setup for Florida Docket Assistant"
echo "============================================"
echo ""
echo "📋 Step 1: Create a Personal Access Token (PAT)"
echo "   1. Visit: https://github.com/settings/tokens/new"
echo "   2. Note: 'Florida Docket Assistant Deploy'"
echo "   3. Expiration: 90 days (or your preference)"
echo "   4. Select scopes:"
echo "      ✓ repo (all)"
echo "      ✓ workflow"
echo "   5. Click 'Generate token'"
echo "   6. COPY THE TOKEN - you won't see it again!"
echo ""
echo "📋 Step 2: Create GitHub Repository"
echo "   1. Visit: https://github.com/new"
echo "   2. Repository name: litdocket"
echo "   3. Description: Florida Legal Docketing Assistant"
echo "   4. Visibility: Private (recommended)"
echo "   5. DO NOT initialize with README, .gitignore, or license"
echo "   6. Click 'Create repository'"
echo ""
read -p "✅ Have you completed both steps above? (yes/no): " READY

if [[ "$READY" != "yes" ]]; then
    echo "❌ Please complete the steps above first, then run this script again."
    exit 1
fi

echo ""
read -p "📝 Enter your GitHub username: " GITHUB_USERNAME
read -s -p "🔑 Paste your Personal Access Token: " GITHUB_TOKEN
echo ""
echo ""

# Configure git
cd /Users/jackson/docketassist-v3/backend

# Add remote using token
REPO_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/litdocket.git"
git remote add origin $REPO_URL

echo "✅ Git remote configured!"
echo ""
echo "📤 Pushing code to GitHub..."

# Push to GitHub
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 SUCCESS! Code pushed to GitHub!"
    echo ""
    echo "📍 Next steps:"
    echo "   1. Backend is now on GitHub at: https://github.com/${GITHUB_USERNAME}/litdocket"
    echo "   2. Ready to deploy to Railway"
    echo ""
else
    echo ""
    echo "❌ Push failed. Please check:"
    echo "   - Your Personal Access Token is correct"
    echo "   - Your GitHub username is correct"
    echo "   - The repository exists and is empty"
fi
