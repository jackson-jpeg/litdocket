"""
Authentication API endpoints
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from app.config import settings


router = APIRouter()


class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    firm_name: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    full_name: str | None = None  # Optional - may be None for auto-created users
    firm_name: str | None = None
    role: str | None = None
    jurisdictions: list[str] | None = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class FirebaseTokenRequest(BaseModel):
    id_token: str


@router.post("/login/firebase", response_model=Token)
async def login_with_firebase(
    token_data: FirebaseTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Exchange Firebase ID token for backend JWT token

    This endpoint maintains backward compatibility with Firebase authentication
    while allowing migration to pure JWT authentication.

    Args:
        token_data: Firebase ID token
        db: Database session

    Returns:
        JWT access token for backend API

    Raises:
        HTTPException: If Firebase token is invalid or user doesn't exist
    """
    try:
        # Import Firebase Admin SDK and service
        from firebase_admin import auth as firebase_auth
        from app.services.firebase_service import firebase_service
        from jose import jwt as jose_jwt

        # DEVELOPMENT MODE: If DEBUG is enabled, extract email from token without verification
        if settings.DEBUG:
            print("⚠️  DEBUG MODE: Bypassing Firebase token verification")
            try:
                # Decode token without verification to get email (UNSAFE - DEV ONLY!)
                unverified_payload = jose_jwt.decode(token_data.id_token, options={"verify_signature": False})
                email = unverified_payload.get('email') or unverified_payload.get('user_id') or 'dev@docketassist.com'
                print(f"✅ DEBUG MODE: Auto-login with email: {email}")
            except Exception as decode_error:
                print(f"⚠️  Could not decode token, using demo user")
                email = 'dev@docketassist.com'
        else:
            # PRODUCTION: Verify Firebase token properly
            firebase_service._initialize_firebase()
            decoded_token = firebase_auth.verify_id_token(token_data.id_token)
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email')

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found in Firebase token"
            )

        # Find or create user in our database
        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Auto-create user from Firebase data
            if settings.DEBUG:
                # In debug mode, extract name from token if available
                display_name = email.split('@')[0].title()
            else:
                display_name = decoded_token.get('name', email.split('@')[0])

            user = User(
                email=email,
                password_hash="firebase_auth",  # Placeholder - not used for Firebase users
                full_name=display_name,
                firm_name=None
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Create backend JWT access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Firebase auth error: {str(e)}")
        print(f"Full traceback: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user
    
    Args:
        user_data: User registration data
        db: Database session
    
    Returns:
        Created user data (without password)
    
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        firm_name=user_data.firm_name
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email and password to get JWT token
    
    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session
    
    Returns:
        JWT access token
    
    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by email
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Verify password
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        User data (without password)
    """
    return current_user


class CompleteSignupRequest(BaseModel):
    id_token: str
    full_name: str | None = None
    firm_name: str | None = None
    jurisdictions: list[str] | None = None


class CompleteSignupResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


@router.post("/signup/complete", response_model=CompleteSignupResponse)
async def complete_signup(
    request: CompleteSignupRequest,
    db: Session = Depends(get_db)
):
    """
    Complete user signup with additional profile information

    This endpoint is called after Firebase authentication to update the user profile
    with additional information like firm name and jurisdictions.

    Args:
        request: Profile completion data with Firebase ID token
        db: Database session

    Returns:
        JWT token and updated user data
    """
    try:
        from firebase_admin import auth as firebase_auth
        from app.services.firebase_service import firebase_service
        from jose import jwt as jose_jwt

        # Decode token to get email
        if settings.DEBUG:
            try:
                unverified_payload = jose_jwt.decode(request.id_token, options={"verify_signature": False})
                email = unverified_payload.get('email') or 'dev@docketassist.com'
            except Exception:
                email = 'dev@docketassist.com'
        else:
            firebase_service._initialize_firebase()
            decoded_token = firebase_auth.verify_id_token(request.id_token)
            email = decoded_token.get('email')

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found in token"
            )

        # Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update user profile
        if request.full_name:
            user.full_name = request.full_name
        if request.firm_name:
            user.firm_name = request.firm_name
        if request.jurisdictions:
            user.jurisdictions = request.jurisdictions

        db.commit()
        db.refresh(user)

        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Complete signup error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete signup: {str(e)}"
        )
