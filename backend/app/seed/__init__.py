"""
Seed data for LitDocket

Usage:
    from app.seed.rule_sets import run_seed
    from app.database import SessionLocal

    db = SessionLocal()
    run_seed(db)
    db.close()
"""
from app.seed.rule_sets import run_seed

__all__ = ["run_seed"]
