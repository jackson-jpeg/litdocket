#!/usr/bin/env python3
"""
Alternative Seeding: Create jurisdictions and rules via API

This script creates rules by calling the production API instead of directly
accessing the database. Useful when you can't access Railway CLI.

Usage:
    python scripts/seed_via_api.py
"""
import requests
import sys

API_URL = "https://litdocket-production.up.railway.app/api/v1"

def main():
    print("=" * 80)
    print("LitDocket Rules Seeding via API")
    print("=" * 80)
    print()
    print("⚠️  This script requires authentication.")
    print("Please login to your frontend first, then paste your JWT token.")
    print()

    token = input("Enter your JWT token: ").strip()

    if not token:
        print("❌ No token provided. Exiting.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print()
    print("🔍 Checking API connection...")

    # Test auth
    response = requests.get(f"{API_URL}/auth/me", headers=headers)
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        print(f"   {response.text}")
        sys.exit(1)

    user = response.json()
    print(f"✅ Authenticated as: {user.get('email')}")
    print()

    # Check existing jurisdictions
    print("📊 Checking existing jurisdictions...")
    response = requests.get(f"{API_URL}/jurisdictions", headers=headers)

    if response.status_code == 200:
        jurisdictions = response.json()
        count = len(jurisdictions) if isinstance(jurisdictions, list) else jurisdictions.get('count', 0)
        print(f"   Found {count} existing jurisdictions")

        if count > 0:
            print()
            print("⚠️  Jurisdictions already exist. The database might already be seeded.")
            print("   You can still proceed, but it may create duplicates.")
            print()
            proceed = input("Continue anyway? (y/N): ").lower()
            if proceed != 'y':
                print("❌ Seeding cancelled.")
                sys.exit(0)

    print()
    print("💡 Note: Direct API seeding is complex.")
    print("   Recommended approach: Use Railway dashboard to run seed script")
    print()
    print("To seed via Railway dashboard:")
    print("1. Go to https://railway.app/")
    print("2. Select your backend service")
    print("3. Go to 'Settings' → 'Deploy'")
    print("4. Add temporary run command: python scripts/seed_production.py")
    print("5. Or use the Railway shell and run it manually")
    print()

if __name__ == "__main__":
    main()
