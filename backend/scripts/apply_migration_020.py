#!/usr/bin/env python3
"""
Apply Migration 020 - Rules Harvester Integration

This script applies the 020_rules_harvester_integration.sql migration
to add the new columns and tables needed for the Rules Harvester features.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text

def apply_migration():
    """Apply the SQL migration file"""
    migration_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "supabase/migrations/020_rules_harvester_integration.sql"
    )

    print(f"Reading migration file: {migration_file}")

    with open(migration_file, 'r') as f:
        sql = f.read()

    print("Applying migration to database...")

    with engine.connect() as conn:
        # Execute the SQL (split by statement if needed for proper error handling)
        try:
            conn.execute(text(sql))
            conn.commit()
            print("✅ Migration 020 applied successfully!")
        except Exception as e:
            print(f"❌ Error applying migration: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    apply_migration()
