from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create database engine with appropriate settings for database type
# SQLite doesn't support connection pooling options
if "sqlite" in settings.DATABASE_URL.lower():
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL or other databases support full pooling
    engine = create_engine(
        settings.DATABASE_URL,
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
    """
    Database session dependency with proper cleanup.

    CRITICAL: This handles "zombie" transactions by rolling back
    any uncommitted changes if an exception occurred during the request.
    Without this, a failed request can leave the connection in a broken
    state (InFailedSqlTransaction) that affects subsequent requests.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # CRITICAL: Roll back any failed transaction before returning to pool
        db.rollback()
        raise
    finally:
        db.close()
