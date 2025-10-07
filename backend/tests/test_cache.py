"""
Tests for Redis Cache Implementation
"""

import pytest
import time
from src.cache import (
    cache, cached, SessionCache, QueryCache, RateLimitCache,
    cache_user_organizations, get_cached_user_organizations,
    invalidate_user_cache, invalidate_organization_cache
)


class TestCacheService:
    """Test basic cache operations"""

    def test_set_and_get(self):
        """Test basic set and get operations"""
        if not cache.available:
            pytest.skip("Redis not available")

        key = "test_key"
        value = {"name": "Test", "value": 123}

        # Set value
        result = cache.set(key, value, ttl=60)
        assert result is True

        # Get value
        retrieved = cache.get(key)
        assert retrieved == value

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist"""
        if not cache.available:
            pytest.skip("Redis not available")

        result = cache.get("nonexistent_key_12345")
        assert result is None

    def test_delete_key(self):
        """Test deleting a key"""
        if not cache.available:
            pytest.skip("Redis not available")

        key = "delete_test"
        cache.set(key, "value", ttl=60)

        # Verify it exists
        assert cache.exists(key) is True

        # Delete it
        cache.delete(key)

        # Verify it's gone
        assert cache.exists(key) is False

    def test_ttl_expiration(self):
        """Test that keys expire after TTL"""
        if not cache.available:
            pytest.skip("Redis not available")

        key = "ttl_test"
        cache.set(key, "value", ttl=1)

        # Should exist immediately
        assert cache.get(key) == "value"

        # Wait for expiration
        time.sleep(2)

        # Should be gone
        assert cache.get(key) is None

    def test_increment(self):
        """Test incrementing a counter"""
        if not cache.available:
            pytest.skip("Redis not available")

        key = "counter_test"

        # First increment creates key with value 1
        result = cache.increment(key, amount=1)
        assert result == 1

        # Second increment
        result = cache.increment(key, amount=5)
        assert result == 6

    def test_delete_pattern(self):
        """Test deleting keys by pattern"""
        if not cache.available:
            pytest.skip("Redis not available")

        # Create multiple keys
        cache.set("user:123:data", "value1", ttl=60)
        cache.set("user:123:profile", "value2", ttl=60)
        cache.set("user:456:data", "value3", ttl=60)

        # Delete all user:123:* keys
        deleted_count = cache.delete_pattern("user:123:*")
        assert deleted_count == 2

        # Verify deletion
        assert cache.get("user:123:data") is None
        assert cache.get("user:123:profile") is None
        assert cache.get("user:456:data") == "value3"


class TestCachedDecorator:
    """Test the @cached decorator"""

    def test_cached_decorator_caches_result(self):
        """Test that decorator caches function results"""
        if not cache.available:
            pytest.skip("Redis not available")

        call_count = 0

        @cached(ttl=60, key_prefix="test_func")
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # First call executes function
        result1 = expensive_function(5, 3)
        assert result1 == 8
        assert call_count == 1

        # Second call with same args returns cached result
        result2 = expensive_function(5, 3)
        assert result2 == 8
        assert call_count == 1  # Function not called again

        # Call with different args executes function
        result3 = expensive_function(10, 2)
        assert result3 == 12
        assert call_count == 2

    def test_cached_decorator_with_kwargs(self):
        """Test decorator with keyword arguments"""
        if not cache.available:
            pytest.skip("Redis not available")

        call_count = 0

        @cached(ttl=60, key_prefix="test_kwargs")
        def func_with_kwargs(a, b=10):
            nonlocal call_count
            call_count += 1
            return a * b

        # First call
        result1 = func_with_kwargs(5, b=2)
        assert result1 == 10
        assert call_count == 1

        # Cached call
        result2 = func_with_kwargs(5, b=2)
        assert result2 == 10
        assert call_count == 1


class TestSessionCache:
    """Test session caching"""

    def test_set_and_get_session(self):
        """Test session storage and retrieval"""
        if not cache.available:
            pytest.skip("Redis not available")

        session_id = "test_session_123"
        user_data = {
            "user_id": "user_456",
            "email": "test@example.com",
            "role": "admin"
        }

        # Set session
        result = SessionCache.set_session(session_id, user_data, ttl=3600)
        assert result is True

        # Get session
        retrieved = SessionCache.get_session(session_id)
        assert retrieved == user_data

    def test_delete_session(self):
        """Test session deletion"""
        if not cache.available:
            pytest.skip("Redis not available")

        session_id = "delete_session_123"
        user_data = {"user_id": "user_789"}

        SessionCache.set_session(session_id, user_data)
        assert SessionCache.get_session(session_id) is not None

        # Delete session
        SessionCache.delete_session(session_id)
        assert SessionCache.get_session(session_id) is None

    def test_extend_session(self):
        """Test extending session TTL"""
        if not cache.available:
            pytest.skip("Redis not available")

        session_id = "extend_session_123"
        user_data = {"user_id": "user_999"}

        # Create session with short TTL
        SessionCache.set_session(session_id, user_data, ttl=2)

        # Extend it
        SessionCache.extend_session(session_id, ttl=60)

        # Should still exist after original TTL
        time.sleep(3)
        assert SessionCache.get_session(session_id) is not None


class TestQueryCache:
    """Test query result caching"""

    def test_cache_and_get_expense_report(self):
        """Test expense report caching"""
        if not cache.available:
            pytest.skip("Redis not available")

        user_id = "user_123"
        org_id = "org_456"
        report_data = {
            "total_expenses": 1500.00,
            "expense_count": 5,
            "categories": {"meals": 800.00, "transport": 700.00}
        }

        # Cache report
        result = QueryCache.cache_expense_report(user_id, org_id, report_data)
        assert result is True

        # Retrieve report
        retrieved = QueryCache.get_expense_report(user_id, org_id)
        assert retrieved == report_data

    def test_invalidate_expense_report(self):
        """Test expense report invalidation"""
        if not cache.available:
            pytest.skip("Redis not available")

        org_id = "org_789"

        # Cache multiple reports for the organization
        QueryCache.cache_expense_report("user_1", org_id, {"total": 100})
        QueryCache.cache_expense_report("user_2", org_id, {"total": 200})

        # Invalidate all reports for organization
        QueryCache.invalidate_expense_report(org_id)

        # All reports should be gone
        assert QueryCache.get_expense_report("user_1", org_id) is None
        assert QueryCache.get_expense_report("user_2", org_id) is None

    def test_cache_organization_members(self):
        """Test organization members caching"""
        if not cache.available:
            pytest.skip("Redis not available")

        org_id = "org_members_test"
        members_data = [
            {"id": "user_1", "email": "user1@example.com", "role": "admin"},
            {"id": "user_2", "email": "user2@example.com", "role": "member"}
        ]

        # Cache members
        QueryCache.cache_organization_members(org_id, members_data)

        # Retrieve members
        retrieved = QueryCache.get_organization_members(org_id)
        assert retrieved == members_data

    def test_invalidate_organization_members(self):
        """Test organization members cache invalidation"""
        if not cache.available:
            pytest.skip("Redis not available")

        org_id = "org_invalidate_test"
        members_data = [{"id": "user_1"}]

        QueryCache.cache_organization_members(org_id, members_data)
        assert QueryCache.get_organization_members(org_id) is not None

        # Invalidate
        QueryCache.invalidate_organization_members(org_id)
        assert QueryCache.get_organization_members(org_id) is None


class TestRateLimitCache:
    """Test rate limiting"""

    def test_rate_limit_allows_within_limit(self):
        """Test that requests are allowed within rate limit"""
        if not cache.available:
            pytest.skip("Redis not available")

        key = "rate_limit_test_1"
        max_requests = 5
        window = 10

        # First 5 requests should be allowed
        for i in range(max_requests):
            allowed, remaining = RateLimitCache.check_rate_limit(key, max_requests, window)
            assert allowed is True
            assert remaining == max_requests - (i + 1)

    def test_rate_limit_blocks_over_limit(self):
        """Test that requests are blocked when limit exceeded"""
        if not cache.available:
            pytest.skip("Redis not available")

        key = "rate_limit_test_2"
        max_requests = 3
        window = 10

        # Use up the limit
        for _ in range(max_requests):
            RateLimitCache.check_rate_limit(key, max_requests, window)

        # Next request should be blocked
        allowed, remaining = RateLimitCache.check_rate_limit(key, max_requests, window)
        assert allowed is False
        assert remaining == 0

    def test_rate_limit_resets_after_window(self):
        """Test that rate limit resets after time window"""
        if not cache.available:
            pytest.skip("Redis not available")

        key = "rate_limit_test_3"
        max_requests = 2
        window = 2

        # Use up the limit
        RateLimitCache.check_rate_limit(key, max_requests, window)
        RateLimitCache.check_rate_limit(key, max_requests, window)

        # Should be blocked
        allowed, _ = RateLimitCache.check_rate_limit(key, max_requests, window)
        assert allowed is False

        # Wait for window to expire
        time.sleep(3)

        # Should be allowed again
        allowed, remaining = RateLimitCache.check_rate_limit(key, max_requests, window)
        assert allowed is True
        assert remaining == max_requests - 1


class TestHelperFunctions:
    """Test cache helper functions"""

    def test_cache_user_organizations(self):
        """Test caching user organizations"""
        if not cache.available:
            pytest.skip("Redis not available")

        user_id = "user_cache_test"
        orgs = [
            {"id": "org_1", "name": "Org 1"},
            {"id": "org_2", "name": "Org 2"}
        ]

        # Cache organizations
        cache_user_organizations(user_id, orgs)

        # Retrieve
        retrieved = get_cached_user_organizations(user_id)
        assert retrieved == orgs

    def test_invalidate_user_cache(self):
        """Test invalidating all user caches"""
        if not cache.available:
            pytest.skip("Redis not available")

        user_id = "user_invalidate_test"

        # Cache some data for user
        cache_user_organizations(user_id, [{"id": "org_1"}])
        QueryCache.cache_expense_report(user_id, "org_1", {"total": 100})

        # Invalidate all user caches
        invalidate_user_cache(user_id)

        # All should be gone
        assert get_cached_user_organizations(user_id) is None
        assert QueryCache.get_expense_report(user_id, "org_1") is None

    def test_invalidate_organization_cache(self):
        """Test invalidating all organization caches"""
        if not cache.available:
            pytest.skip("Redis not available")

        org_id = "org_cache_invalidate_test"

        # Cache organization data
        QueryCache.cache_organization_members(org_id, [{"id": "user_1"}])
        QueryCache.cache_expense_report("user_1", org_id, {"total": 100})

        # Invalidate organization caches
        invalidate_organization_cache(org_id)

        # All should be gone
        assert QueryCache.get_organization_members(org_id) is None
        assert QueryCache.get_expense_report("user_1", org_id) is None
