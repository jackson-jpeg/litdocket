#!/usr/bin/env python3
"""
Run Pending Database Migrations

Applies SQL migration files to the production database.
Specifically designed to apply migration 010_user_rules_additions.sql
which creates the user_rule_templates tables.

Usage:
    # On Railway:
    railway shell
    python scripts/run_migration.py

    # Locally (if DATABASE_URL is set):
    python scripts/run_migration.py

    # Specific migration:
    python scripts/run_migration.py 010_user_rules_additions.sql
"""
import sys
import os
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def get_database_url():
    """Get database URL from environment"""
    # Try SUPABASE_DB_URL first (takes priority), then DATABASE_URL
    db_url = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')

    if not db_url:
        print("❌ ERROR: No database URL found!")
        print("   Set SUPABASE_DB_URL or DATABASE_URL environment variable")
        sys.exit(1)

    return db_url


def run_migration_file(migration_file: Path):
    """Execute a SQL migration file"""
    print(f"\n📄 Reading migration: {migration_file.name}")

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    # Read SQL content
    with open(migration_file, 'r') as f:
        sql_content = f.read()

    print(f"   File size: {len(sql_content)} bytes")

    # Connect to database
    db_url = get_database_url()
    print(f"\n🔌 Connecting to database...")

    try:
        conn = psycopg2.connect(db_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("✅ Connected!")
        print(f"\n⚙️  Executing migration...")

        # Execute the migration
        cursor.execute(sql_content)

        print("✅ Migration executed successfully!")

        # Verify tables were created
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('user_rule_templates', 'user_rule_template_versions', 'user_rule_executions')
            ORDER BY table_name
        """)

        tables = cursor.fetchall()

        if tables:
            print(f"\n✅ Tables created:")
            for table in tables:
                table_name = table[0]
                print(f"   • {table_name}")

                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"     ({count} rows)")
        else:
            print("\n⚠️  Warning: Expected tables not found. Check migration output above.")

        cursor.close()
        conn.close()

        return True

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        print(f"   Error code: {e.pgcode}")
        print(f"   Details: {e.pgerror}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main migration runner"""
    print("=" * 80)
    print("LitDocket Database Migration Runner")
    print("=" * 80)

    # Determine which migration to run
    migrations_dir = backend_dir / "supabase" / "migrations"

    if len(sys.argv) > 1:
        # Specific migration file provided
        migration_name = sys.argv[1]
        migration_file = migrations_dir / migration_name
    else:
        # Default to 010_user_rules_additions.sql
        migration_file = migrations_dir / "010_user_rules_additions.sql"

    print(f"\n📁 Migration directory: {migrations_dir}")
    print(f"📄 Target migration: {migration_file.name}")

    # Confirm with user
    print("\n⚠️  This will execute SQL directly on the production database.")
    response = input("Continue? (y/N): ").lower()

    if response != 'y':
        print("❌ Migration cancelled.")
        sys.exit(0)

    # Run the migration
    success = run_migration_file(migration_file)

    print("\n" + "=" * 80)
    if success:
        print("✅ Migration Complete!")
        print("=" * 80)
        print("\n🎉 The user_rule_templates tables are now available!")
        print("   You can now use the /api/v1/rules/templates endpoint.")
    else:
        print("❌ Migration Failed!")
        print("=" * 80)
        print("\n   Please check the errors above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
