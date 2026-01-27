#!/usr/bin/env python3
"""
Production Database Seeding Script

Seeds the production database with Florida + Federal court rules.
Uses the working architecture from migration 001 (jurisdiction_system).

Usage:
    # Locally (requires local database):
    python scripts/seed_production.py

    # On Railway:
    railway run python scripts/seed_production.py

    # Or directly:
    python -m scripts.seed_production
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.seed.rule_sets import run_seed


def main():
    """Main seeding function"""
    print("=" * 80)
    print("LitDocket Production Database Seeding")
    print("=" * 80)
    print()

    db = SessionLocal()
    try:
        print("📊 Checking database connection...")
        # Test connection
        from app.models.jurisdiction import Jurisdiction
        existing_count = db.query(Jurisdiction).count()
        print(f"✅ Database connected. Current jurisdictions: {existing_count}")
        print()

        if existing_count > 0:
            print("⚠️  Database already has data.")
            response = input("Continue seeding anyway? (y/N): ").lower()
            if response != 'y':
                print("❌ Seeding cancelled.")
                return
            print()

        print("🌱 Starting seed process...")
        print()
        run_seed(db)

        print()
        print("=" * 80)
        print("✅ Seeding Complete!")
        print("=" * 80)

        # Show summary
        from app.models.jurisdiction import Jurisdiction, RuleSet, RuleTemplate, RuleTemplateDeadline

        juris_count = db.query(Jurisdiction).count()
        ruleset_count = db.query(RuleSet).count()
        template_count = db.query(RuleTemplate).count()
        deadline_count = db.query(RuleTemplateDeadline).count()

        print()
        print("📊 Database Summary:")
        print(f"   Jurisdictions: {juris_count}")
        print(f"   Rule Sets: {ruleset_count}")
        print(f"   Rule Templates: {template_count}")
        print(f"   Deadline Definitions: {deadline_count}")
        print()

        # Show jurisdictions
        print("🗺️  Jurisdictions Created:")
        jurisdictions = db.query(Jurisdiction).all()
        for j in jurisdictions:
            print(f"   • {j.code}: {j.name}")
        print()

        # Show rule templates
        print("📋 Rule Templates Created:")
        templates = db.query(RuleTemplate).all()
        for t in templates:
            deadlines = db.query(RuleTemplateDeadline).filter(
                RuleTemplateDeadline.rule_template_id == t.id
            ).count()
            print(f"   • {t.rule_code}: {t.name} ({deadlines} deadlines)")
        print()

        print("🎉 Your rules engine is ready to use!")
        print()

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
