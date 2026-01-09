from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from app.config import settings

# =============================================================================
# ZERO DATA LOSS POLICY: SQLite is FORBIDDEN in production
# =============================================================================
# Railway containers are ephemeral. SQLite = data loss on every deploy.
# This check runs BEFORE engine creation to fail fast.

_db_url = settings.DATABASE_URL  # This will raise RuntimeError if not configured

if "sqlite" in _db_url.lower():
    # Allow SQLite ONLY if explicitly running in local dev mode
    if os.getenv("ALLOW_SQLITE_DEV") == "true":
        print("⚠️  WARNING: Using SQLite for LOCAL DEVELOPMENT ONLY")
        print("⚠️  Set DATABASE_URL to PostgreSQL for production!")
        engine = create_engine(
            _db_url,
            connect_args={"check_same_thread": False}
        )
    else:
        raise RuntimeError(
            "\n" + "=" * 60 + "\n"
            "FATAL: SQLite detected in DATABASE_URL!\n"
            "=" * 60 + "\n"
            "SQLite causes DATA LOSS on ephemeral containers (Railway, Heroku, etc.)\n\n"
            "Fix: Set DATABASE_URL to a PostgreSQL connection string.\n"
            "Example: postgresql://user:pass@host:5432/dbname\n\n"
            "For local dev only, set: ALLOW_SQLITE_DEV=true\n"
            "=" * 60
        )
else:
    # PostgreSQL or other persistent databases - GOOD
    print(f"✅ Database: PostgreSQL connected")
    engine = create_engine(
        _db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
