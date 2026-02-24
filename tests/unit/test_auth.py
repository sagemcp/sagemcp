"""Tests for API key and JWT authentication."""

import os
import time
from datetime import timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from sage_mcp.models.api_key import APIKeyScope
from sage_mcp.security.auth import (
    SCOPE_HIERARCHY,
    SCOPE_PREFIX_MAP,
    AuthContext,
    _authenticate_jwt,
    _cache,
    _cache_get,
    _cache_put,
    _cache_key,
    _CACHE_TTL,
    _resolve_scope_from_roles,
    _ROLE_TO_SCOPE,
    clear_auth_cache,
    generate_api_key,
    hash_api_key,
    invalidate_cache_for_key,
    require_scope,
    verify_api_key,
)
from sage_mcp.security.tokens import create_access_token, create_refresh_token


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


class TestRequireScope:
    """Test require_scope dependency factory enforces scope hierarchy correctly."""

    @pytest.mark.asyncio
    async def test_platform_admin_passes_tenant_user_check(self):
        """Platform admin should pass a tenant_user scope check."""
        check_fn = require_scope(APIKeyScope.TENANT_USER)
        ctx = AuthContext(
            key_id="id", name="admin", scope=APIKeyScope.PLATFORM_ADMIN, tenant_id=None
        )
        # Should not raise
        await check_fn(auth=ctx)

    @pytest.mark.asyncio
    async def test_tenant_user_fails_tenant_admin_check(self):
        """Tenant user should be rejected by a tenant_admin scope check (403)."""
        from fastapi import HTTPException

        check_fn = require_scope(APIKeyScope.TENANT_ADMIN)
        ctx = AuthContext(
            key_id="id", name="user", scope=APIKeyScope.TENANT_USER, tenant_id="t1"
        )
        with pytest.raises(HTTPException) as exc_info:
            await check_fn(auth=ctx)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_auth_none_passes_all_checks(self):
        """When auth is disabled (None), all scope checks pass through."""
        check_fn = require_scope(APIKeyScope.PLATFORM_ADMIN)
        # Should not raise
        await check_fn(auth=None)

    @pytest.mark.asyncio
    async def test_tenant_admin_passes_tenant_user_check(self):
        """Tenant admin should pass a tenant_user scope check."""
        check_fn = require_scope(APIKeyScope.TENANT_USER)
        ctx = AuthContext(
            key_id="id", name="ta", scope=APIKeyScope.TENANT_ADMIN, tenant_id="t1"
        )
        # Should not raise
        await check_fn(auth=ctx)


class TestResolveScopeFromRoles:
    """JWT roles dict → (APIKeyScope, tenant_id) resolution."""

    def test_empty_roles(self):
        scope, tid = _resolve_scope_from_roles({})
        assert scope == APIKeyScope.TENANT_USER
        assert tid is None

    def test_single_tenant_admin(self):
        scope, tid = _resolve_scope_from_roles({"tenant-uuid-1": "tenant_admin"})
        assert scope == APIKeyScope.TENANT_ADMIN
        assert tid == "tenant-uuid-1"

    def test_single_tenant_member(self):
        scope, tid = _resolve_scope_from_roles({"tenant-uuid-1": "tenant_member"})
        assert scope == APIKeyScope.TENANT_USER
        assert tid == "tenant-uuid-1"

    def test_single_tenant_viewer(self):
        scope, tid = _resolve_scope_from_roles({"tenant-uuid-1": "tenant_viewer"})
        assert scope == APIKeyScope.TENANT_USER
        assert tid == "tenant-uuid-1"

    def test_platform_admin_wildcard(self):
        scope, tid = _resolve_scope_from_roles({"*": "platform_admin"})
        assert scope == APIKeyScope.PLATFORM_ADMIN
        assert tid is None

    def test_platform_admin_overrides_tenant_id(self):
        """Platform admin scope always yields tenant_id=None."""
        scope, tid = _resolve_scope_from_roles({"tenant-uuid-1": "platform_admin"})
        assert scope == APIKeyScope.PLATFORM_ADMIN
        assert tid is None

    def test_multi_tenant_yields_no_tenant_id(self):
        """Multiple tenant memberships → tenant_id=None (ambiguous)."""
        scope, tid = _resolve_scope_from_roles({
            "tenant-1": "tenant_admin",
            "tenant-2": "tenant_member",
        })
        assert scope == APIKeyScope.TENANT_ADMIN
        assert tid is None

    def test_highest_privilege_wins(self):
        scope, tid = _resolve_scope_from_roles({
            "tenant-1": "tenant_member",
            "tenant-2": "tenant_admin",
        })
        assert scope == APIKeyScope.TENANT_ADMIN
        assert tid is None  # multi-tenant

    def test_unknown_role_defaults_to_tenant_user(self):
        scope, tid = _resolve_scope_from_roles({"tenant-1": "unknown_role"})
        assert scope == APIKeyScope.TENANT_USER
        assert tid == "tenant-1"


class TestAuthenticateJWT:
    """JWT token → AuthContext conversion."""

    def test_valid_access_token(self):
        """Valid access token produces correct AuthContext."""
        token = create_access_token(
            user_id="user-123",
            email="test@example.com",
            roles={"tenant-1": "tenant_admin"},
        )
        ctx = _authenticate_jwt(token)
        assert ctx is not None
        assert ctx.key_id == "jwt:user-123"
        assert ctx.user_id == "user-123"
        assert ctx.email == "test@example.com"
        assert ctx.name == "test@example.com"
        assert ctx.scope == APIKeyScope.TENANT_ADMIN
        assert ctx.tenant_id == "tenant-1"

    def test_platform_admin_jwt(self):
        token = create_access_token(
            user_id="admin-1",
            email="admin@example.com",
            roles={"*": "platform_admin"},
        )
        ctx = _authenticate_jwt(token)
        assert ctx is not None
        assert ctx.scope == APIKeyScope.PLATFORM_ADMIN
        assert ctx.tenant_id is None
        assert ctx.user_id == "admin-1"

    def test_refresh_token_rejected(self):
        """Refresh tokens must not authenticate (type != 'access')."""
        token = create_refresh_token(user_id="user-123")
        ctx = _authenticate_jwt(token)
        assert ctx is None

    def test_expired_token_rejected(self):
        """Expired JWT returns None (falls through to API key path)."""
        token = create_access_token(
            user_id="user-123",
            email="test@example.com",
            roles={},
            expires_delta=timedelta(seconds=-1),
        )
        ctx = _authenticate_jwt(token)
        assert ctx is None

    def test_garbage_token_rejected(self):
        """Non-JWT string returns None (not an exception)."""
        ctx = _authenticate_jwt("smcp_pa_not-a-jwt-token")
        assert ctx is None

    def test_empty_string_rejected(self):
        ctx = _authenticate_jwt("")
        assert ctx is None

    def test_no_email_uses_user_id_as_name(self):
        """When email is empty, name falls back to user_id."""
        token = create_access_token(
            user_id="user-456",
            email="",
            roles={"t1": "tenant_member"},
        )
        ctx = _authenticate_jwt(token)
        assert ctx is not None
        assert ctx.name == "user-456"
        assert ctx.email is None  # empty string → None

    def test_no_roles_defaults_to_tenant_user(self):
        token = create_access_token(
            user_id="user-789",
            email="user@example.com",
            roles={},
        )
        ctx = _authenticate_jwt(token)
        assert ctx is not None
        assert ctx.scope == APIKeyScope.TENANT_USER
        assert ctx.tenant_id is None

    def test_wrong_secret_rejected(self):
        """Token signed with different secret is rejected."""
        from jose import jwt as _jwt
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "roles": {},
            "type": "access",
            "exp": time.time() + 3600,
        }
        token = _jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        ctx = _authenticate_jwt(token)
        assert ctx is None


class TestAuthContextExtended:
    """AuthContext with new user_id/email fields."""

    def test_api_key_context_defaults(self):
        """API key auth leaves user_id and email as None."""
        ctx = AuthContext(
            key_id="key-1",
            name="my-key",
            scope=APIKeyScope.TENANT_ADMIN,
            tenant_id="t1",
        )
        assert ctx.user_id is None
        assert ctx.email is None

    def test_jwt_context_fields(self):
        """JWT auth populates user_id and email."""
        ctx = AuthContext(
            key_id="jwt:user-1",
            name="user@example.com",
            scope=APIKeyScope.TENANT_ADMIN,
            tenant_id="t1",
            user_id="user-1",
            email="user@example.com",
        )
        assert ctx.user_id == "user-1"
        assert ctx.email == "user@example.com"

    def test_frozen_new_fields(self):
        """New fields are also frozen."""
        ctx = AuthContext(
            key_id="jwt:u",
            name="n",
            scope=APIKeyScope.TENANT_USER,
            tenant_id=None,
            user_id="u",
            email="e@e.com",
        )
        with pytest.raises(AttributeError):
            ctx.user_id = "other"  # type: ignore
        with pytest.raises(AttributeError):
            ctx.email = "other"  # type: ignore


class TestRoleToScopeMapping:
    """Verify _ROLE_TO_SCOPE covers all expected role strings."""

    def test_covers_api_key_scopes(self):
        """All APIKeyScope .value strings are mapped."""
        for scope in APIKeyScope:
            assert scope.value in _ROLE_TO_SCOPE

    def test_covers_tenant_roles(self):
        """TenantRole values (from user model) are mapped."""
        for role_val in ("platform_admin", "tenant_admin", "tenant_member", "tenant_viewer"):
            assert role_val in _ROLE_TO_SCOPE
