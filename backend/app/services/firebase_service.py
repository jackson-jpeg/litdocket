"""
Firebase Service - Handles Firestore database and Cloud Storage operations
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os
import re
import logging
import json

logger = logging.getLogger(__name__)


class FirebaseService:
    """Service for interacting with Firebase Firestore and Storage"""

    _initialized = False
    _db = None
    _bucket = None

    def __init__(self):
        """Initialize Firebase if not already initialized"""
        pass

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK (lazy initialization)"""
        if FirebaseService._initialized:
            return

        try:
            # Try to get credentials from environment variable (for production)
            firebase_cred_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY_JSON')

            if firebase_cred_json:
                # Production: Load from environment variable JSON string
                cred_dict = json.loads(firebase_cred_json)

                # NUCLEAR FIX: Force correct Private Key formatting
                if 'private_key' in cred_dict:
                    raw_key = cred_dict['private_key']

                    # CRITICAL FIX: Handle double-escapes (\\n) BEFORE single escapes (\n)
                    # This prevents the first replace from corrupting the second.
                    key = raw_key.replace('\\\\n', '\n').replace('\\n', '\n')

                    # Step 2: Fix PEM headers if they were merged into one line
                    if '-----BEGIN PRIVATE KEY----- ' in key:
                         key = key.replace('-----BEGIN PRIVATE KEY----- ', '-----BEGIN PRIVATE KEY-----\n')
                    if ' -----END PRIVATE KEY-----' in key:
                         key = key.replace(' -----END PRIVATE KEY-----', '\n-----END PRIVATE KEY-----')

                    cred_dict['private_key'] = key
                    logger.info(f"Firebase: Key sanitized. Final Length: {len(key)}")

                cred = credentials.Certificate(cred_dict)
                logger.info("Firebase initialized from environment variable")
            else:
                # Local development: Load from file
                cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', 'firebase-service-account.json')

                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    logger.info(f"Firebase initialized from file: {cred_path}")
                else:
                    logger.warning(f"Firebase credentials not found at {cred_path}")
                    return

            # Initialize the app
            if not firebase_admin._apps:
                # Use the actual Firebase Storage bucket created in console
                firebase_admin.initialize_app(cred, {
                    'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET', 'litdocket.firebasestorage.app')
                })

            FirebaseService._db = firestore.client()
            FirebaseService._bucket = storage.bucket()
            FirebaseService._initialized = True
            logger.info("Firebase initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            # Do not raise here, allow app to start even if Firebase fails

    @property
    def db(self):
        """Get Firestore database client"""
        if not FirebaseService._initialized:
            self._initialize_firebase()
        return FirebaseService._db

    @property
    def bucket(self):
        """Get Cloud Storage bucket"""
        if not FirebaseService._initialized:
            self._initialize_firebase()
        return FirebaseService._bucket

    @staticmethod
    def sanitize_storage_path(path: str) -> str:
        """
        Sanitize storage path to prevent double slashes and path issues.

        The "Double Slash Killer" - prevents signature mismatches.

        Args:
            path: Raw storage path

        Returns:
            Cleaned path safe for Firebase Storage
        """
        if not path:
            return ""

        # Remove leading/trailing slashes
        cleaned = path.strip("/")

        # Collapse multiple consecutive slashes to single slash
        cleaned = re.sub(r'/+', '/', cleaned)

        return cleaned

    def upload_pdf(self, user_id: str, file_name: str, pdf_bytes: bytes) -> tuple[str, str]:
        """
        Upload PDF to Firebase Storage with path sanitization.

        Returns: (storage_path, signed_url)
        """
        # Create a unique path: documents/{userId}/{timestamp}_{filename}
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        # Sanitize filename to remove any dangerous characters
        safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file_name)

        # Build path
        storage_path = f"documents/{user_id}/{timestamp}_{safe_filename}"

        # CRITICAL: Sanitize path to prevent double-slash signature errors
        storage_path = self.sanitize_storage_path(storage_path)

        # Upload to Cloud Storage
        blob = self.bucket.blob(storage_path)
        blob.upload_from_string(pdf_bytes, content_type='application/pdf')

        # Generate a signed URL (valid for 7 days)
        url = blob.generate_signed_url(expiration=timedelta(days=7))

        return storage_path, url

    def get_download_url(self, storage_path: str, expiration_days: int = 7) -> str:
        """Get a signed download URL for a file with path sanitization"""
        # CRITICAL: Sanitize path to prevent SignatureDoesNotMatch errors
        storage_path = self.sanitize_storage_path(storage_path)

        blob = self.bucket.blob(storage_path)
        return blob.generate_signed_url(expiration=timedelta(days=expiration_days))

    def delete_file(self, storage_path: str):
        """Delete a file from Storage with path sanitization and ghost-safe error handling"""
        try:
            # Sanitize path for consistency
            storage_path = self.sanitize_storage_path(storage_path)

            blob = self.bucket.blob(storage_path)
            blob.delete()
            logger.info(f"Successfully deleted file: {storage_path}")
        except Exception as e:
            # Ghost-safe: Log warning but don't crash if file doesn't exist
            logger.warning(f"Failed to delete file {storage_path} (might be ghost document): {e}")


# Singleton instance
firebase_service = FirebaseService()
