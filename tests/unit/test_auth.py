"""Tests for API key authentication (Phase 2)."""

import os
import time

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from sage_mcp.models.api_key import APIKeyScope
from sage_mcp.security.auth import (
    SCOPE_HIERARCHY,
    SCOPE_PREFIX_MAP,
    AuthContext,
    _cache,
    _cache_get,
    _cache_put,
    _cache_key,
    _CACHE_TTL,
    clear_auth_cache,
    generate_api_key,
    hash_api_key,
    invalidate_cache_for_key,
    verify_api_key,
)


class TestKeyGeneration:
    """API key format: smcp_<scope>_<32_random_chars>."""

    def test_platform_admin_prefix(self):
        key = generate_api_key(APIKeyScope.PLATFORM_ADMIN)
        assert key.startswith("smcp_pa_")
        assert len(key) > 20

    def test_tenant_admin_prefix(self):
        key = generate_api_key(APIKeyScope.TENANT_ADMIN)
        assert key.startswith("smcp_ta_")

    def test_tenant_user_prefix(self):
        key = generate_api_key(APIKeyScope.TENANT_USER)
        assert key.startswith("smcp_tu_")

    def test_uniqueness(self):
        keys = {generate_api_key(APIKeyScope.PLATFORM_ADMIN) for _ in range(20)}
        assert len(keys) == 20

    def test_prefix_map_coverage(self):
        for scope in APIKeyScope:
            assert scope in SCOPE_PREFIX_MAP


class TestKeyHashing:
    """bcrypt hash + verify."""

    def test_hash_and_verify(self):
        key = generate_api_key(APIKeyScope.PLATFORM_ADMIN)
        hashed = hash_api_key(key)
        assert hashed != key
        assert verify_api_key(key, hashed)

    def test_wrong_key_fails(self):
        key = generate_api_key(APIKeyScope.PLATFORM_ADMIN)
        hashed = hash_api_key(key)
        assert not verify_api_key("smcp_pa_wrong_key_here", hashed)

    def test_different_hashes_for_same_key(self):
        """bcrypt uses random salt, so same key produces different hashes."""
        key = generate_api_key(APIKeyScope.TENANT_ADMIN)
        h1 = hash_api_key(key)
        h2 = hash_api_key(key)
        assert h1 != h2
        assert verify_api_key(key, h1)
        assert verify_api_key(key, h2)


class TestScopeHierarchy:
    """platform_admin > tenant_admin > tenant_user."""

    def test_platform_admin_covers_all(self):
        scopes = SCOPE_HIERARCHY[APIKeyScope.PLATFORM_ADMIN]
        assert APIKeyScope.PLATFORM_ADMIN in scopes
        assert APIKeyScope.TENANT_ADMIN in scopes
        assert APIKeyScope.TENANT_USER in scopes

    def test_tenant_admin_covers_user(self):
        scopes = SCOPE_HIERARCHY[APIKeyScope.TENANT_ADMIN]
        assert APIKeyScope.TENANT_ADMIN in scopes
        assert APIKeyScope.TENANT_USER in scopes
        assert APIKeyScope.PLATFORM_ADMIN not in scopes

    def test_tenant_user_self_only(self):
        scopes = SCOPE_HIERARCHY[APIKeyScope.TENANT_USER]
        assert APIKeyScope.TENANT_USER in scopes
        assert len(scopes) == 1


class TestAuthCache:
    """SHA-256 keyed LRU cache."""

    def setup_method(self):
        clear_auth_cache()

    def teardown_method(self):
        clear_auth_cache()

    def test_cache_miss(self):
        assert _cache_get("nonexistent-key") is None

    def test_cache_hit(self):
        ctx = AuthContext(
            key_id="test-id",
            name="test",
            scope=APIKeyScope.PLATFORM_ADMIN,
            tenant_id=None,
        )
        _cache_put("my-key", ctx)
        assert _cache_get("my-key") is ctx

    def test_cache_invalidate_specific(self):
        ctx = AuthContext(
            key_id="test-id",
            name="test",
            scope=APIKeyScope.PLATFORM_ADMIN,
            tenant_id=None,
        )
        _cache_put("key-to-remove", ctx)
        assert _cache_get("key-to-remove") is ctx

        invalidate_cache_for_key("key-to-remove")
        assert _cache_get("key-to-remove") is None

    def test_cache_clear(self):
        ctx = AuthContext(
            key_id="test-id",
            name="test",
            scope=APIKeyScope.PLATFORM_ADMIN,
            tenant_id=None,
        )
        _cache_put("key-a", ctx)
        _cache_put("key-b", ctx)
        assert len(_cache) == 2

        clear_auth_cache()
        assert len(_cache) == 0

    def test_cache_expiry(self):
        ctx = AuthContext(
            key_id="test-id",
            name="test",
            scope=APIKeyScope.PLATFORM_ADMIN,
            tenant_id=None,
        )
        ck = _cache_key("expired-key")
        # Insert with a timestamp that's already past TTL
        _cache[ck] = (ctx, time.monotonic() - _CACHE_TTL - 1)
        assert _cache_get("expired-key") is None

    def test_cache_max_size(self):
        """Cache evicts oldest when over max size."""
        from sage_mcp.security.auth import _CACHE_MAX

        for i in range(_CACHE_MAX + 10):
            ctx = AuthContext(
                key_id=str(i),
                name=f"key-{i}",
                scope=APIKeyScope.TENANT_USER,
                tenant_id=None,
            )
            _cache_put(f"key-{i}", ctx)

        assert len(_cache) == _CACHE_MAX


class TestAuthContext:
    """AuthContext data class."""

    def test_frozen(self):
        ctx = AuthContext(
            key_id="id",
            name="name",
            scope=APIKeyScope.PLATFORM_ADMIN,
            tenant_id=None,
        )
        with pytest.raises(AttributeError):
            ctx.scope = APIKeyScope.TENANT_USER  # type: ignore

    def test_tenant_scoped(self):
        ctx = AuthContext(
            key_id="id",
            name="name",
            scope=APIKeyScope.TENANT_ADMIN,
            tenant_id="some-uuid",
        )
        assert ctx.tenant_id == "some-uuid"
