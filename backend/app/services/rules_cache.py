"""
Rules Cache - TTL-based caching for Authority Core rules

Provides in-memory caching with 5-minute TTL for database rule lookups.
This reduces database load for frequently accessed rule templates.

Features:
- In-memory cache with configurable TTL (default 5 minutes)
- Cache key format: rules:{jurisdiction_id}:{trigger_type}
- Automatic expiration and cleanup
- invalidate() method for manual cache busting
- Thread-safe implementation

Usage:
    cache = RulesCache()

    # Get from cache or return None
    rules = cache.get(jurisdiction_id, trigger_type)

    # Set cache value
    cache.set(jurisdiction_id, trigger_type, rules)

    # Invalidate specific key
    cache.invalidate(jurisdiction_id, trigger_type)

    # Invalidate all rules for a jurisdiction
    cache.invalidate_jurisdiction(jurisdiction_id)

    # Clear entire cache
    cache.clear()
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class CacheEntry:
    """A single cache entry with expiration tracking."""

    def __init__(self, data: Any, ttl_seconds: int):
        self.data = data
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expires_at

    @property
    def age_seconds(self) -> float:
        return (datetime.utcnow() - self.created_at).total_seconds()


class RulesCache:
    """
    TTL-based in-memory cache for Authority Core rules.

    Thread-safe implementation with automatic expiration.
    Default TTL is 5 minutes (300 seconds).
    """

    # Default TTL of 5 minutes
    DEFAULT_TTL_SECONDS = 300

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        """
        Initialize the rules cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default 300)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "expirations": 0,
        }
        logger.info(f"RulesCache initialized with TTL={ttl_seconds}s")

    def _make_key(self, jurisdiction_id: str, trigger_type: str) -> str:
        """Generate cache key from jurisdiction and trigger type."""
        return f"rules:{jurisdiction_id}:{trigger_type}"

    def _parse_key(self, key: str) -> Tuple[str, str]:
        """Parse cache key back to jurisdiction_id and trigger_type."""
        parts = key.split(":")
        if len(parts) == 3 and parts[0] == "rules":
            return parts[1], parts[2]
        return "", ""

    def get(
        self,
        jurisdiction_id: str,
        trigger_type: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get rules from cache if present and not expired.

        Args:
            jurisdiction_id: UUID of the jurisdiction
            trigger_type: Trigger type string (e.g., "complaint_served")

        Returns:
            Cached rules list or None if not found/expired
        """
        key = self._make_key(jurisdiction_id, trigger_type)

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired:
                # Remove expired entry
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                logger.debug(f"Cache entry expired: {key}")
                return None

            self._stats["hits"] += 1
            logger.debug(f"Cache hit: {key} (age={entry.age_seconds:.1f}s)")
            return entry.data

    def set(
        self,
        jurisdiction_id: str,
        trigger_type: str,
        rules: List[Dict[str, Any]],
        ttl_seconds: Optional[int] = None
    ) -> None:
        """
        Store rules in cache.

        Args:
            jurisdiction_id: UUID of the jurisdiction
            trigger_type: Trigger type string
            rules: List of rule dictionaries to cache
            ttl_seconds: Optional custom TTL (uses default if not specified)
        """
        key = self._make_key(jurisdiction_id, trigger_type)
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds

        with self._lock:
            self._cache[key] = CacheEntry(rules, ttl)
            self._stats["sets"] += 1
            logger.debug(f"Cache set: {key} ({len(rules)} rules, TTL={ttl}s)")

    def invalidate(
        self,
        jurisdiction_id: str,
        trigger_type: str
    ) -> bool:
        """
        Invalidate a specific cache entry.

        Args:
            jurisdiction_id: UUID of the jurisdiction
            trigger_type: Trigger type string

        Returns:
            True if entry was found and removed, False otherwise
        """
        key = self._make_key(jurisdiction_id, trigger_type)

        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats["invalidations"] += 1
                logger.debug(f"Cache invalidated: {key}")
                return True
            return False

    def invalidate_jurisdiction(self, jurisdiction_id: str) -> int:
        """
        Invalidate all cache entries for a specific jurisdiction.

        Useful when jurisdiction rules are updated via admin interface.

        Args:
            jurisdiction_id: UUID of the jurisdiction

        Returns:
            Number of entries invalidated
        """
        count = 0
        prefix = f"rules:{jurisdiction_id}:"

        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys()
                if key.startswith(prefix)
            ]

            for key in keys_to_remove:
                del self._cache[key]
                count += 1

            self._stats["invalidations"] += count

        if count > 0:
            logger.info(f"Invalidated {count} cache entries for jurisdiction {jurisdiction_id}")

        return count

    def invalidate_all(self) -> int:
        """
        Invalidate all cache entries (alias for clear()).

        Returns:
            Number of entries cleared
        """
        return self.clear()

    def clear(self) -> int:
        """
        Clear the entire cache.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats["invalidations"] += count

        if count > 0:
            logger.info(f"Cache cleared: {count} entries removed")

        return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        This is automatically called during get() operations,
        but can be called manually for proactive cleanup.

        Returns:
            Number of expired entries removed
        """
        count = 0

        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]

            for key in keys_to_remove:
                del self._cache[key]
                count += 1

            self._stats["expirations"] += count

        if count > 0:
            logger.debug(f"Cleaned up {count} expired cache entries")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics including hit rate
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests * 100
                if total_requests > 0
                else 0.0
            )

            return {
                "size": len(self._cache),
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": f"{hit_rate:.1f}%",
                "sets": self._stats["sets"],
                "invalidations": self._stats["invalidations"],
                "expirations": self._stats["expirations"],
                "ttl_seconds": self._ttl_seconds,
            }

    def __len__(self) -> int:
        """Return number of entries in cache."""
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache (does not check expiration)."""
        with self._lock:
            return key in self._cache


# Global singleton instance
rules_cache = RulesCache()


def get_rules_cache() -> RulesCache:
    """Get the global rules cache instance."""
    return rules_cache
