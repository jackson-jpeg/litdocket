"""
Test Configuration - Proper Database Isolation

CRITICAL: Tests MUST use isolated databases to prevent data loss.
This file ensures tests never touch production/development data.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Use in-memory SQLite for ALL tests - completely isolated from production
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """
    Create a test database engine using in-memory SQLite.

    This is completely isolated from any production database.
    The database only exists for the duration of the test session.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool  # Required for in-memory SQLite with multiple threads
    )

    # Import models to ensure they're registered
    from app.database import Base

    # Create all tables in the test database
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup - dispose of engine connections
    # Note: In-memory database is automatically destroyed when connection closes
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """
    Create a new database session for each test function.

    Each test gets a fresh transaction that is rolled back after the test,
    ensuring complete isolation between tests.
    """
    from app.database import Base

    # Create a new connection for this test
    connection = test_engine.connect()

    # Begin a transaction that we'll roll back
    transaction = connection.begin()

    # Create session bound to this connection
    TestingSessionLocal = sessionmaker(bind=connection)
    session = TestingSessionLocal()

    # Begin a nested transaction (savepoint)
    nested = connection.begin_nested()

    # If the session commits, restart the nested transaction
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.begin_nested()

    yield session

    # Cleanup: rollback everything
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_user(db_session):
    """
    Create a test user for authentication tests.

    This user only exists within the test and is rolled back after.
    """
    from app.models.user import User
    from app.utils.auth import get_password_hash
    import uuid

    user = User(
        id=str(uuid.uuid4()),
        email=f"test_{uuid.uuid4().hex[:8]}@litdocket.com",
        password_hash=get_password_hash("test_password_123"),
        full_name="Test User",
        firm_name="Test Law Firm"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture(scope="function")
def test_case(db_session, test_user):
    """
    Create a test case for case-related tests.

    This case only exists within the test and is rolled back after.
    """
    from app.models.case import Case
    import uuid

    case = Case(
        id=str(uuid.uuid4()),
        user_id=str(test_user.id),
        case_number=f"TEST-{uuid.uuid4().hex[:8].upper()}",
        title="Test Case for Unit Tests",
        court="Test Circuit Court",
        case_type="civil",
        jurisdiction="state",
        status="active"
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    return case


# Override the get_db dependency for tests
@pytest.fixture
def override_get_db(db_session):
    """
    Override FastAPI's get_db dependency to use the test session.

    Usage in tests:
        def test_something(override_get_db):
            app.dependency_overrides[get_db] = override_get_db
    """
    def _override():
        yield db_session
    return _override


# Prevent any accidental use of production database in tests
@pytest.fixture(autouse=True)
def prevent_production_db_access(monkeypatch):
    """
    Safety measure: Ensure tests cannot accidentally connect to production database.

    This patches environment variables that might point to production databases.
    """
    # Force DATABASE_URL to be the test database
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)

    # Disable Firebase in tests
    monkeypatch.setenv("FIREBASE_CREDENTIALS_PATH", "")
    monkeypatch.setenv("FIREBASE_CREDENTIALS_JSON", "")
