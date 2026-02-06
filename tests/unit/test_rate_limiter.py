"""Tests for token bucket rate limiter."""

import time

import pytest

from sage_mcp.middleware.rate_limit import TokenBucket, RateLimiter, RateLimitMiddleware


class TestTokenBucket:
    """Test TokenBucket class."""

    def test_initial_capacity(self):
        """Test bucket starts full."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.tokens == 10.0

    def test_consume_token(self):
        """Test consuming a token."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)

        assert bucket.try_consume() is True
        assert bucket.tokens == 9.0

    def test_consume_all_tokens(self):
        """Test consuming all tokens then being rate limited."""
        bucket = TokenBucket(capacity=3.0, refill_rate=1.0)

        assert bucket.try_consume() is True
        assert bucket.try_consume() is True
        assert bucket.try_consume() is True
        assert bucket.try_consume() is False

    def test_refill_over_time(self):
        """Test that tokens refill based on elapsed time."""
        bucket = TokenBucket(capacity=10.0, refill_rate=10.0)  # 10 tokens/sec

        # Consume all tokens
        for _ in range(10):
            bucket.try_consume()

        assert bucket.try_consume() is False

        # Simulate 0.5s passing -> 5 tokens refilled
        now = time.monotonic() + 0.5
        assert bucket.try_consume(now=now) is True

    def test_refill_does_not_exceed_capacity(self):
        """Test that tokens don't exceed capacity after refill."""
        bucket = TokenBucket(capacity=5.0, refill_rate=100.0)

        # Simulate 10 seconds passing
        now = time.monotonic() + 10
        bucket.try_consume(now=now)

        # Even after massive refill, tokens should be at most capacity - 1
        assert bucket.tokens <= 5.0

    def test_time_until_token_when_available(self):
        """Test time_until_token returns 0 when tokens available."""
        bucket = TokenBucket(capacity=10.0, refill_rate=1.0)
        assert bucket.time_until_token() == 0.0

    def test_time_until_token_when_empty(self):
        """Test time_until_token returns positive value when empty."""
        bucket = TokenBucket(capacity=1.0, refill_rate=1.0)  # 1 token/sec
        bucket.try_consume()

        wait_time = bucket.time_until_token()
        assert wait_time > 0
        assert wait_time <= 1.0  # Should be at most 1 second for 1 token/sec


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_default_limit(self):
        """Test default rate limit is applied."""
        limiter = RateLimiter(default_rpm=60)

        allowed, retry_after = limiter.try_acquire("tenant-a")
        assert allowed is True
        assert retry_after == 0.0

    def test_per_tenant_isolation(self):
        """Test that tenants have separate rate limits."""
        limiter = RateLimiter(default_rpm=1)

        # First request for tenant-a passes
        allowed_a, _ = limiter.try_acquire("tenant-a")
        assert allowed_a is True

        # First request for tenant-b also passes (different bucket)
        allowed_b, _ = limiter.try_acquire("tenant-b")
        assert allowed_b is True

    def test_rate_limit_exceeded(self):
        """Test that rate limit is enforced."""
        limiter = RateLimiter(default_rpm=2)

        limiter.try_acquire("tenant-a")
        limiter.try_acquire("tenant-a")
        allowed, retry_after = limiter.try_acquire("tenant-a")

        assert allowed is False
        assert retry_after > 0

    def test_per_tenant_override(self):
        """Test per-tenant rate limit override."""
        limiter = RateLimiter(default_rpm=100)
        limiter.set_tenant_limit("vip-tenant", 200)

        # Both should work (within their respective limits)
        allowed_regular, _ = limiter.try_acquire("regular-tenant")
        allowed_vip, _ = limiter.try_acquire("vip-tenant")

        assert allowed_regular is True
        assert allowed_vip is True

    def test_override_resets_bucket(self):
        """Test that setting an override resets the tenant's bucket."""
        limiter = RateLimiter(default_rpm=1)

        # Exhaust the bucket
        limiter.try_acquire("tenant-a")
        allowed, _ = limiter.try_acquire("tenant-a")
        assert allowed is False

        # Set override (resets bucket)
        limiter.set_tenant_limit("tenant-a", 100)
        allowed, _ = limiter.try_acquire("tenant-a")
        assert allowed is True

    def test_burst_handling(self):
        """Test that burst capacity equals RPM."""
        limiter = RateLimiter(default_rpm=10)

        # Should allow exactly 10 requests in a burst
        for i in range(10):
            allowed, _ = limiter.try_acquire("tenant-a")
            assert allowed is True, f"Request {i+1} should be allowed"

        # 11th should be rejected
        allowed, _ = limiter.try_acquire("tenant-a")
        assert allowed is False


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware path extraction."""

    def test_extract_tenant_slug(self):
        """Test extracting tenant slug from MCP path."""
        slug = RateLimitMiddleware._extract_tenant_slug(
            "/api/v1/my-tenant/connectors/abc-123/mcp"
        )
        assert slug == "my-tenant"

    def test_extract_tenant_slug_with_extra_segments(self):
        """Test extracting tenant slug from longer paths."""
        slug = RateLimitMiddleware._extract_tenant_slug(
            "/api/v1/my-tenant/connectors/abc-123/mcp/sse"
        )
        assert slug == "my-tenant"

    def test_extract_tenant_slug_no_v1(self):
        """Test that paths without v1 return None."""
        slug = RateLimitMiddleware._extract_tenant_slug(
            "/api/my-tenant/connectors/abc-123/mcp"
        )
        assert slug is None

    def test_extract_tenant_slug_short_path(self):
        """Test that short paths return None."""
        slug = RateLimitMiddleware._extract_tenant_slug("/api/v1")
        assert slug is None
