"""Token bucket rate limiter for per-tenant request limiting.

Uses in-memory token buckets keyed by tenant slug.
Default: 100 req/min (configurable globally, overridable per tenant).
Returns 429 Too Many Requests with Retry-After header.
Uses time.monotonic() for timing (no syscall overhead).
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """A token bucket for rate limiting."""
    capacity: float
    refill_rate: float  # tokens per second
    tokens: float = 0.0
    last_refill: float = field(default_factory=time.monotonic)

    def __post_init__(self):
        self.tokens = self.capacity

    def try_consume(self, now: Optional[float] = None) -> bool:
        """Try to consume one token.

        Returns True if the request is allowed, False if rate-limited.
        """
        if now is None:
            now = time.monotonic()

        # Refill tokens based on elapsed time
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    def time_until_token(self) -> float:
        """Time in seconds until the next token is available."""
        if self.tokens >= 1.0:
            return 0.0
        deficit = 1.0 - self.tokens
        return deficit / self.refill_rate


class RateLimiter:
    """In-memory per-tenant rate limiter using token buckets."""

    def __init__(self, default_rpm: int = 100):
        self._buckets: Dict[str, TokenBucket] = {}
        self._default_rpm = default_rpm
        self._tenant_overrides: Dict[str, int] = {}

    def set_tenant_limit(self, tenant_slug: str, rpm: int):
        """Set a per-tenant rate limit override."""
        self._tenant_overrides[tenant_slug] = rpm
        # Reset bucket to apply new limit
        self._buckets.pop(tenant_slug, None)

    def _get_bucket(self, tenant_slug: str) -> TokenBucket:
        """Get or create a token bucket for a tenant."""
        bucket = self._buckets.get(tenant_slug)
        if bucket is None:
            rpm = self._tenant_overrides.get(tenant_slug, self._default_rpm)
            bucket = TokenBucket(
                capacity=float(rpm),
                refill_rate=rpm / 60.0,
            )
            self._buckets[tenant_slug] = bucket
        return bucket

    def try_acquire(self, tenant_slug: str) -> tuple[bool, float]:
        """Try to acquire a rate limit token.

        Returns:
            Tuple of (allowed: bool, retry_after_seconds: float)
        """
        bucket = self._get_bucket(tenant_slug)
        if bucket.try_consume():
            return True, 0.0
        return False, bucket.time_until_token()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for per-tenant rate limiting.

    Extracts tenant_slug from URL path pattern:
    /api/v1/{tenant_slug}/connectors/{connector_id}/mcp
    """

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit MCP endpoints
        path = request.url.path
        if "/connectors/" not in path or "/mcp" not in path:
            return await call_next(request)

        # Extract tenant_slug from path
        tenant_slug = self._extract_tenant_slug(path)
        if not tenant_slug:
            return await call_next(request)

        allowed, retry_after = self.rate_limiter.try_acquire(tenant_slug)
        if not allowed:
            logger.warning("Rate limited tenant %s (retry_after=%.1fs)", tenant_slug, retry_after)
            return JSONResponse(
                status_code=429,
                content={"error": "Too Many Requests"},
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

        return await call_next(request)

    @staticmethod
    def _extract_tenant_slug(path: str) -> Optional[str]:
        """Extract tenant_slug from /api/v1/{tenant_slug}/connectors/... path."""
        parts = path.split("/")
        try:
            # Path: /api/v1/{tenant_slug}/connectors/...
            api_idx = parts.index("v1")
            if api_idx + 1 < len(parts):
                return parts[api_idx + 1]
        except (ValueError, IndexError):
            pass
        return None
