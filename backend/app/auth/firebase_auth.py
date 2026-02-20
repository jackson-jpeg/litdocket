"""
Firebase Authentication integration.

Handles Firebase Admin SDK initialization and token verification.
"""

import os
import json
import logging
from typing import Dict, Optional
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
_firebase_initialized = False

def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials."""
    global _firebase_initialized

    if _firebase_initialized:
        return

    # Check for Firebase credentials in environment
    firebase_creds_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
    firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS_JSON')

    try:
        if firebase_creds_path and os.path.exists(firebase_creds_path):
            # Load from file path
            cred = credentials.Certificate(firebase_creds_path)
        elif firebase_creds_json:
            # Load from JSON string (useful for deployment)
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # Development mode - use default application credentials
            logger.warning("No Firebase credentials found. Using development mode.")
            logger.warning("Set FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON for production.")
            cred = None

        if cred:
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        logger.warning("App will run in development mode with mock authentication")


async def verify_firebase_token(id_token: str) -> Dict:
    """
    Verify a Firebase ID token and return the decoded claims.

    Args:
        id_token: Firebase ID token from client

    Returns:
        Dict containing user claims (uid, email, etc.)

    Raises:
        HTTPException: If token is invalid
    """
    if not _firebase_initialized:
        # Firebase not initialized - reject authentication
        # For local development, use Firebase Local Emulator Suite:
        #   https://firebase.google.com/docs/emulator-suite
        logger.error("Firebase not initialized - cannot verify tokens")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )

    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token

    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired"
        )
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_user_from_firebase(uid: str) -> Optional[Dict]:
    """
    Get user information from Firebase by UID.

    Args:
        uid: Firebase user ID

    Returns:
        Dict containing user information or None if not found
    """
    if not _firebase_initialized:
        logger.error("Firebase not initialized - cannot fetch user info")
        return None

    try:
        user = auth.get_user(uid)
        return {
            'uid': user.uid,
            'email': user.email,
            'display_name': user.display_name,
            'photo_url': user.photo_url,
            'email_verified': user.email_verified,
            'provider_data': [
                {
                    'provider_id': provider.provider_id,
                    'uid': provider.uid
                }
                for provider in user.provider_data
            ]
        }
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        logger.error(f"Error fetching user from Firebase: {str(e)}")
        return None


# Initialize on module import
initialize_firebase()
