"""
Authentication module for DocketAssist v3.

Handles Firebase authentication, JWT token generation, and user session management.
"""

from .firebase_auth import verify_firebase_token, get_user_from_firebase
from .jwt_handler import create_access_token, decode_access_token
from .middleware import get_current_user

__all__ = [
    'verify_firebase_token',
    'get_user_from_firebase',
    'create_access_token',
    'decode_access_token',
    'get_current_user'
]
