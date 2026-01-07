"""
Authentication Tests - Critical Path Testing

Tests for JWT authentication, user registration, and login flows.

NOTE: This file uses fixtures from conftest.py for database isolation.
Tests use in-memory SQLite and are completely isolated from production data.
"""
import pytest
from datetime import datetime, timedelta
import uuid

# Database fixtures (db_session, test_user, test_case) are provided by conftest.py
# No need to define database setup here - it's all handled safely in conftest.py


class TestJWTAuthentication:
    """Test JWT token creation and validation"""

    def test_create_access_token(self):
        """Test JWT token creation"""
        from app.utils.auth import create_access_token

        token = create_access_token(
            data={"sub": "test-user-id"},
            expires_delta=timedelta(minutes=30)
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test JWT token with custom expiry"""
        from app.utils.auth import create_access_token

        token = create_access_token(
            data={"sub": "test-user-id"},
            expires_delta=timedelta(hours=1)
        )

        assert token is not None

    def test_decode_valid_token(self):
        """Test decoding a valid JWT token"""
        from app.utils.auth import create_access_token
        from jose import jwt
        from app.config import settings

        user_id = str(uuid.uuid4())
        token = create_access_token(
            data={"sub": user_id},
            expires_delta=timedelta(minutes=30)
        )

        # Decode token
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])

        assert payload.get("sub") == user_id
        assert "exp" in payload

    def test_token_expiry(self):
        """Test that expired tokens are rejected"""
        from app.utils.auth import create_access_token
        from jose import jwt, ExpiredSignatureError
        from app.config import settings

        # Create token that's already expired
        token = create_access_token(
            data={"sub": "test-user-id"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        # Attempt to decode should raise ExpiredSignatureError
        with pytest.raises(ExpiredSignatureError):
            jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_password_hash(self):
        """Test password hashing"""
        from app.utils.auth import get_password_hash

        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_password_verification_correct(self):
        """Test correct password verification"""
        from app.utils.auth import get_password_hash, verify_password

        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_password_verification_incorrect(self):
        """Test incorrect password verification"""
        from app.utils.auth import get_password_hash, verify_password

        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes"""
        from app.utils.auth import get_password_hash

        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")

        assert hash1 != hash2


class TestUserModel:
    """Test User model operations"""

    def test_create_user(self, db_session):
        """Test creating a user"""
        from app.models.user import User

        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            firm_name="Test Firm"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.role == "attorney"  # Default value

    def test_user_unique_email(self, db_session):
        """Test that duplicate emails are rejected"""
        from app.models.user import User
        from sqlalchemy.exc import IntegrityError

        user1 = User(
            email="unique@example.com",
            password_hash="hash1",
            full_name="User 1"
        )
        db_session.add(user1)
        db_session.commit()

        user2 = User(
            email="unique@example.com",  # Same email
            password_hash="hash2",
            full_name="User 2"
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestAuthEndpoints:
    """Test authentication API endpoints"""

    def test_register_success(self, db_session):
        """Test successful user registration"""
        # Note: This would use TestClient with actual API
        # For unit testing, we test the logic directly
        from app.utils.auth import get_password_hash
        from app.models.user import User

        email = f"newuser_{uuid.uuid4().hex[:8]}@example.com"
        password = "secure_password_123"
        hashed = get_password_hash(password)

        user = User(
            email=email,
            password_hash=hashed,
            full_name="New User",
            firm_name="New Firm"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == email

    def test_login_creates_token(self, db_session):
        """Test that login creates a valid token"""
        from app.utils.auth import get_password_hash, verify_password, create_access_token
        from app.models.user import User
        from datetime import timedelta

        # Create user
        email = f"loginuser_{uuid.uuid4().hex[:8]}@example.com"
        password = "login_password_123"
        hashed = get_password_hash(password)

        user = User(
            email=email,
            password_hash=hashed,
            full_name="Login User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Verify password and create token
        assert verify_password(password, user.password_hash) is True

        token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=30)
        )

        assert token is not None
        assert len(token) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
