"""
Redis Cache Implementation
Provides caching for sessions, query results, and expensive operations
"""

import hashlib
import json
import logging
import os
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Optional

import redis

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service"""

    def __init__(self):
        """Initialize Redis connection"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # Test connection
            self.redis_client.ping()
            self.available = True
            logger.info("Redis cache connected successfully")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.available = False
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.available:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL (time to live)

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: 5 minutes)
        """
        if not self.available:
            return False

        try:
            serialized = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.available:
            return False

        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.available:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.available:
            return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter"""
        if not self.available:
            return None

        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key"""
        if not self.available:
            return False

        try:
            return bool(self.redis_client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False


# Global cache instance
cache = CacheService()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results

    Usage:
        @cached(ttl=600, key_prefix="user_org")
        def get_user_organizations(user_id: str):
            # expensive database query
            return results
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            # Try to get from cache
            cached_result = cache.get(cache_key_str)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key_str}")
                return cached_result

            # Execute function
            logger.debug(f"Cache miss: {cache_key_str}")
            result = func(*args, **kwargs)

            # Cache result
            if result is not None:
                cache.set(cache_key_str, result, ttl=ttl)

            return result

        return wrapper

    return decorator


class SessionCache:
    """Session management with Redis"""

    @staticmethod
    def set_session(session_id: str, user_data: dict, ttl: int = 3600):
        """Store session data"""
        key = f"session:{session_id}"
        return cache.set(key, user_data, ttl=ttl)

    @staticmethod
    def get_session(session_id: str) -> Optional[dict]:
        """Get session data"""
        key = f"session:{session_id}"
        return cache.get(key)

    @staticmethod
    def delete_session(session_id: str):
        """Delete session"""
        key = f"session:{session_id}"
        return cache.delete(key)

    @staticmethod
    def extend_session(session_id: str, ttl: int = 3600):
        """Extend session expiration"""
        key = f"session:{session_id}"
        return cache.expire(key, ttl)


class QueryCache:
    """Query result caching"""

    @staticmethod
    def cache_expense_report(
        user_id: str, organization_id: str, report_data: dict, ttl: int = 300
    ):
        """Cache expense report"""
        key = f"expense_report:{organization_id}:{user_id}"
        return cache.set(key, report_data, ttl=ttl)

    @staticmethod
    def get_expense_report(user_id: str, organization_id: str) -> Optional[dict]:
        """Get cached expense report"""
        key = f"expense_report:{organization_id}:{user_id}"
        return cache.get(key)

    @staticmethod
    def invalidate_expense_report(organization_id: str):
        """Invalidate all expense reports for an organization"""
        pattern = f"expense_report:{organization_id}:*"
        return cache.delete_pattern(pattern)

    @staticmethod
    def cache_organization_members(
        organization_id: str, members_data: list, ttl: int = 600
    ):
        """Cache organization members"""
        key = f"org_members:{organization_id}"
        return cache.set(key, members_data, ttl=ttl)

    @staticmethod
    def get_organization_members(organization_id: str) -> Optional[list]:
        """Get cached organization members"""
        key = f"org_members:{organization_id}"
        return cache.get(key)

    @staticmethod
    def invalidate_organization_members(organization_id: str):
        """Invalidate organization members cache"""
        key = f"org_members:{organization_id}"
        return cache.delete(key)


class RateLimitCache:
    """Rate limiting with Redis"""

    @staticmethod
    def check_rate_limit(
        key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if rate limit exceeded

        Returns:
            (allowed: bool, remaining: int)
        """
        if not cache.available:
            return True, max_requests

        try:
            current = cache.increment(key)

            if current == 1:
                # First request in window
                cache.expire(key, window_seconds)
                return True, max_requests - 1

            if current <= max_requests:
                return True, max_requests - current

            return False, 0
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, max_requests


# Helper functions for common caching patterns


def cache_user_organizations(user_id: str, organizations: list, ttl: int = 600):
    """Cache user's organizations"""
    key = f"user_orgs:{user_id}"
    return cache.set(key, organizations, ttl=ttl)


def get_cached_user_organizations(user_id: str) -> Optional[list]:
    """Get cached user organizations"""
    key = f"user_orgs:{user_id}"
    return cache.get(key)


def invalidate_user_cache(user_id: str):
    """Invalidate all caches for a user"""
    cache.delete_pattern(f"user_orgs:{user_id}")
    cache.delete_pattern(f"expense_report:*:{user_id}")


def invalidate_organization_cache(organization_id: str):
    """Invalidate all caches for an organization"""
    cache.delete_pattern(f"org_members:{organization_id}")
    cache.delete_pattern(f"expense_report:{organization_id}:*")
