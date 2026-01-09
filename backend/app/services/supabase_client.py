"""
Supabase Client - Single Source of Truth Database

This module provides both:
1. Direct PostgreSQL access via SQLAlchemy (for complex queries)
2. Supabase Python client (for REST API, real-time, storage)

The Supabase PostgreSQL database is the single source of truth for:
- Jurisdiction and Rule System (CompuLaw-style)
- Cases, Deadlines, Documents
- User data and preferences
"""
import logging
from typing import Optional
from functools import lru_cache

from app.config import settings

logger = logging.getLogger(__name__)

# Supabase Python client (optional - for REST API access)
_supabase_client = None

def get_supabase_client():
    """
    Get Supabase client for REST API access.

    Use this for:
    - Real-time subscriptions
    - Storage operations
    - RLS-aware queries from client context

    For complex SQL queries, use SQLAlchemy session instead.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase not configured - client unavailable")
        return None

    try:
        from supabase import create_client, Client

        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY  # Use service role for backend
        )
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except ImportError:
        logger.warning("supabase-py not installed. Install with: pip install supabase")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def get_supabase_anon_client():
    """
    Get Supabase client with anon key (respects RLS).

    Use this for operations that should respect Row Level Security.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        return None

    try:
        from supabase import create_client
        return create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
    except Exception as e:
        logger.error(f"Failed to create anon Supabase client: {e}")
        return None


class SupabaseService:
    """
    High-level service for Supabase operations.

    Provides convenient methods for common operations while
    abstracting away the client initialization.
    """

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @property
    def is_available(self) -> bool:
        return self.client is not None

    # ==========================================
    # Rule System Operations
    # ==========================================

    def get_jurisdictions(self, active_only: bool = True):
        """Get all jurisdictions"""
        if not self.is_available:
            return []

        query = self.client.table("jurisdictions").select("*")
        if active_only:
            query = query.eq("is_active", True)

        result = query.execute()
        return result.data if result.data else []

    def get_rule_sets(self, jurisdiction_id: Optional[str] = None, active_only: bool = True):
        """Get rule sets, optionally filtered by jurisdiction"""
        if not self.is_available:
            return []

        query = self.client.table("rule_sets").select("*")

        if jurisdiction_id:
            query = query.eq("jurisdiction_id", jurisdiction_id)
        if active_only:
            query = query.eq("is_active", True)

        result = query.execute()
        return result.data if result.data else []

    def get_rule_set_with_dependencies(self, rule_set_id: str):
        """Get a rule set with its dependencies resolved"""
        if not self.is_available:
            return None

        # Get the rule set
        rule_set = self.client.table("rule_sets").select("*").eq("id", rule_set_id).single().execute()

        if not rule_set.data:
            return None

        # Get dependencies
        deps = self.client.table("rule_set_dependencies").select(
            "*, required_rule_set:rule_sets!required_rule_set_id(*)"
        ).eq("rule_set_id", rule_set_id).execute()

        rule_set.data["dependencies"] = deps.data if deps.data else []

        return rule_set.data

    def get_rule_templates(self, rule_set_id: str, trigger_type: Optional[str] = None):
        """Get rule templates for a rule set"""
        if not self.is_available:
            return []

        query = self.client.table("rule_templates").select(
            "*, deadlines:rule_template_deadlines(*)"
        ).eq("rule_set_id", rule_set_id).eq("is_active", True)

        if trigger_type:
            query = query.eq("trigger_type", trigger_type)

        result = query.execute()
        return result.data if result.data else []

    def get_court_locations(self, jurisdiction_id: Optional[str] = None):
        """Get court locations"""
        if not self.is_available:
            return []

        query = self.client.table("court_locations").select("*").eq("is_active", True)

        if jurisdiction_id:
            query = query.eq("jurisdiction_id", jurisdiction_id)

        result = query.execute()
        return result.data if result.data else []

    # ==========================================
    # Case Rule Set Assignment
    # ==========================================

    def get_case_rule_sets(self, case_id: str):
        """Get rule sets assigned to a case"""
        if not self.is_available:
            return []

        result = self.client.table("case_rule_sets").select(
            "*, rule_set:rule_sets(*)"
        ).eq("case_id", case_id).eq("is_active", True).execute()

        return result.data if result.data else []

    def assign_rule_set_to_case(
        self,
        case_id: str,
        rule_set_id: str,
        assignment_method: str = "auto_detected",
        priority: int = 0
    ):
        """Assign a rule set to a case"""
        if not self.is_available:
            return None

        import uuid

        result = self.client.table("case_rule_sets").upsert({
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "rule_set_id": rule_set_id,
            "assignment_method": assignment_method,
            "priority": priority,
            "is_active": True
        }, on_conflict="case_id,rule_set_id").execute()

        return result.data[0] if result.data else None

    # ==========================================
    # Ingestion Operations (for rule text files)
    # ==========================================

    def upsert_jurisdiction(self, jurisdiction_data: dict):
        """Insert or update a jurisdiction"""
        if not self.is_available:
            return None

        result = self.client.table("jurisdictions").upsert(
            jurisdiction_data,
            on_conflict="code"
        ).execute()

        return result.data[0] if result.data else None

    def upsert_rule_set(self, rule_set_data: dict):
        """Insert or update a rule set"""
        if not self.is_available:
            return None

        result = self.client.table("rule_sets").upsert(
            rule_set_data,
            on_conflict="code"
        ).execute()

        return result.data[0] if result.data else None

    def upsert_rule_template(self, template_data: dict):
        """Insert or update a rule template"""
        if not self.is_available:
            return None

        result = self.client.table("rule_templates").upsert(
            template_data,
            on_conflict="rule_set_id,rule_code"
        ).execute()

        return result.data[0] if result.data else None

    def bulk_upsert_rule_templates(self, templates: list):
        """Bulk insert/update rule templates"""
        if not self.is_available or not templates:
            return []

        result = self.client.table("rule_templates").upsert(
            templates,
            on_conflict="rule_set_id,rule_code"
        ).execute()

        return result.data if result.data else []


# Singleton instance
supabase_service = SupabaseService()
