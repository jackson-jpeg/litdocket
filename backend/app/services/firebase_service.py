"""
Firebase Service - Handles Firestore database and Cloud Storage operations
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
from typing import Dict, List, Optional, Any
from datetime import datetime
import os


class FirebaseService:
    """Service for interacting with Firebase Firestore and Storage"""

    _initialized = False
    _db = None
    _bucket = None

    def __init__(self):
        """Initialize Firebase if not already initialized"""
        # Don't initialize on import - wait until first use
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
                import json
                cred_dict = json.loads(firebase_cred_json)
                cred = credentials.Certificate(cred_dict)
                print("✅ Firebase initialized from environment variable")
            else:
                # Local development: Load from file
                cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY', 'firebase-service-account.json')

                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    print("✅ Firebase initialized from service account file")
                else:
                    print(f"⚠️  Firebase service account key not found at: {cred_path}")
                    print(f"⚠️  Set FIREBASE_SERVICE_ACCOUNT_KEY_JSON env var or download key from Firebase Console")
                    raise FileNotFoundError(f"Firebase credentials not found")

            # Initialize Firebase app
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'florida-docket-assist.firebasestorage.app'
            })

            FirebaseService._db = firestore.client()
            FirebaseService._bucket = storage.bucket()
            FirebaseService._initialized = True

        except Exception as e:
            print(f"❌ Firebase initialization error: {e}")
            raise

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

    # ====================
    # USER OPERATIONS
    # ====================

    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user in Firestore"""
        user_ref = self.db.collection('users').document()
        user_data['created_at'] = firestore.SERVER_TIMESTAMP
        user_data['updated_at'] = firestore.SERVER_TIMESTAMP
        user_ref.set(user_data)
        return user_ref.id

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        doc = self.db.collection('users').document(user_id).get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        users = self.db.collection('users').where('email', '==', email).limit(1).get()
        if users:
            doc = users[0]
            return {'id': doc.id, **doc.to_dict()}
        return None

    # ====================
    # CASE OPERATIONS
    # ====================

    def create_case(self, case_data: Dict[str, Any]) -> str:
        """Create a new case"""
        case_ref = self.db.collection('cases').document()
        case_data['created_at'] = firestore.SERVER_TIMESTAMP
        case_data['updated_at'] = firestore.SERVER_TIMESTAMP
        case_ref.set(case_data)
        return case_ref.id

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case by ID"""
        doc = self.db.collection('cases').document(case_id).get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None

    def find_case_by_number(self, user_id: str, case_number: str) -> Optional[Dict[str, Any]]:
        """Find a case by case number for a specific user"""
        cases = (self.db.collection('cases')
                .where('userId', '==', user_id)
                .where('case_number', '==', case_number)
                .limit(1)
                .get())

        if cases:
            doc = cases[0]
            return {'id': doc.id, **doc.to_dict()}
        return None

    def get_user_cases(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all cases for a user"""
        cases = (self.db.collection('cases')
                .where('userId', '==', user_id)
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .get())

        return [{'id': doc.id, **doc.to_dict()} for doc in cases]

    def update_case(self, case_id: str, updates: Dict[str, Any]):
        """Update a case"""
        updates['updated_at'] = firestore.SERVER_TIMESTAMP
        self.db.collection('cases').document(case_id).update(updates)

    # ====================
    # DOCUMENT OPERATIONS
    # ====================

    def create_document(self, document_data: Dict[str, Any]) -> str:
        """Create a new document record"""
        doc_ref = self.db.collection('documents').document()
        document_data['created_at'] = firestore.SERVER_TIMESTAMP
        document_data['updated_at'] = firestore.SERVER_TIMESTAMP
        doc_ref.set(document_data)
        return doc_ref.id

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        doc = self.db.collection('documents').document(document_id).get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None

    def get_case_documents(self, case_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a case"""
        docs = (self.db.collection('documents')
               .where('caseId', '==', case_id)
               .order_by('created_at', direction=firestore.Query.DESCENDING)
               .get())

        return [{'id': doc.id, **doc.to_dict()} for doc in docs]

    def update_document(self, document_id: str, updates: Dict[str, Any]):
        """Update a document"""
        updates['updated_at'] = firestore.SERVER_TIMESTAMP
        self.db.collection('documents').document(document_id).update(updates)

    # ====================
    # STORAGE OPERATIONS
    # ====================

    def upload_pdf(self, user_id: str, file_name: str, pdf_bytes: bytes) -> tuple[str, str]:
        """
        Upload PDF to Firebase Storage
        Returns: (storage_path, public_url)
        """
        # Create a unique path: documents/{userId}/{timestamp}_{filename}
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        storage_path = f"documents/{user_id}/{timestamp}_{file_name}"

        # Upload to Cloud Storage
        blob = self.bucket.blob(storage_path)
        blob.upload_from_string(pdf_bytes, content_type='application/pdf')

        # Make the blob publicly accessible (optional - for signed URLs)
        # blob.make_public()

        # Generate a signed URL (valid for 7 days)
        from datetime import timedelta
        url = blob.generate_signed_url(expiration=timedelta(days=7))

        return storage_path, url

    def get_download_url(self, storage_path: str, expiration_days: int = 7) -> str:
        """Get a signed download URL for a file"""
        from datetime import timedelta
        blob = self.bucket.blob(storage_path)
        return blob.generate_signed_url(expiration=timedelta(days=expiration_days))

    def delete_file(self, storage_path: str):
        """Delete a file from Storage"""
        blob = self.bucket.blob(storage_path)
        blob.delete()

    # ====================
    # DEADLINE OPERATIONS
    # ====================

    def create_deadline(self, deadline_data: Dict[str, Any]) -> str:
        """Create a new deadline"""
        deadline_ref = self.db.collection('deadlines').document()
        deadline_data['created_at'] = firestore.SERVER_TIMESTAMP
        deadline_data['updated_at'] = firestore.SERVER_TIMESTAMP
        deadline_ref.set(deadline_data)
        return deadline_ref.id

    def get_case_deadlines(self, case_id: str) -> List[Dict[str, Any]]:
        """Get all deadlines for a case"""
        deadlines = (self.db.collection('deadlines')
                    .where('caseId', '==', case_id)
                    .order_by('deadline_date', direction=firestore.Query.ASCENDING)
                    .get())

        return [{'id': doc.id, **doc.to_dict()} for doc in deadlines]

    def get_user_upcoming_deadlines(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get upcoming deadlines for a user"""
        from datetime import datetime
        today = datetime.now().date()

        deadlines = (self.db.collection('deadlines')
                    .where('userId', '==', user_id)
                    .where('deadline_date', '>=', today)
                    .order_by('deadline_date', direction=firestore.Query.ASCENDING)
                    .limit(limit)
                    .get())

        return [{'id': doc.id, **doc.to_dict()} for doc in deadlines]

    # ====================
    # CHAT MESSAGE OPERATIONS
    # ====================

    def create_chat_message(self, message_data: Dict[str, Any]) -> str:
        """Create a new chat message"""
        msg_ref = self.db.collection('chat_messages').document()
        message_data['created_at'] = firestore.SERVER_TIMESTAMP
        msg_ref.set(message_data)
        return msg_ref.id

    def get_case_messages(self, case_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get chat messages for a case"""
        messages = (self.db.collection('chat_messages')
                   .where('caseId', '==', case_id)
                   .order_by('created_at', direction=firestore.Query.ASCENDING)
                   .limit(limit)
                   .get())

        return [{'id': doc.id, **doc.to_dict()} for doc in messages]


# Singleton instance
firebase_service = FirebaseService()
