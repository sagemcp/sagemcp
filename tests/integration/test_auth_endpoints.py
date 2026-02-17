"""Integration tests for auth endpoints (Phase 2).

Tests cover:
- Auth disabled (default): all endpoints accessible without auth
- Auth enabled: 401 without key, 200 with valid key
- Key CRUD lifecycle via /auth/keys
- Verify endpoint
"""

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from sage_mcp.security.auth import clear_auth_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Ensure a clean auth cache for every test."""
    clear_auth_cache()
    yield
    clear_auth_cache()


# ---------------------------------------------------------------------------
# Tests: Auth disabled (default)
# ---------------------------------------------------------------------------


class TestAuthDisabledEndpoints:
    """When SAGEMCP_ENABLE_AUTH=false (default), all endpoints work without auth."""

    def test_admin_tenants_no_auth(self, client):
        resp = client.get("/api/v1/admin/tenants")
        assert resp.status_code == 200

    def test_admin_settings_no_auth(self, client):
        resp = client.get("/api/v1/admin/settings")
        assert resp.status_code == 200

    def test_auth_verify_no_auth(self, client):
        resp = client.post("/api/v1/auth/verify")
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["key_id"] is None  # No identity when auth disabled

    def test_create_key_without_auth(self, client):
        """Key creation endpoint works when auth is disabled."""
        resp = client.post(
            "/api/v1/auth/keys",
            json={"name": "test-key", "scope": "platform_admin"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-key"
        assert data["scope"] == "platform_admin"
        assert data["key"].startswith("smcp_pa_")
        assert data["key_prefix"] == data["key"][:8]

    def test_list_keys_without_auth(self, client):
        resp = client.get("/api/v1/auth/keys")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_health_always_public(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_live_always_public(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: Auth enabled (mock settings to avoid env var race)
# ---------------------------------------------------------------------------


class TestAuthEnabledEndpoints:
    """When auth is enabled, endpoints require valid API keys.

    We mock Settings.enable_auth directly instead of using env vars,
    to avoid lru_cache timing issues with TestClient.
    """

    @pytest.fixture(autouse=True)
    def _enable_auth(self):
        """Patch enable_auth on the Settings instance."""
        from sage_mcp.config import get_settings
        settings = get_settings()
        original = settings.enable_auth
        settings.enable_auth = True
        yield
        settings.enable_auth = original

    def test_admin_tenants_401_without_key(self, client):
        resp = client.get("/api/v1/admin/tenants")
        assert resp.status_code == 401

    def test_admin_settings_401_without_key(self, client):
        resp = client.get("/api/v1/admin/settings")
        assert resp.status_code == 401

    def test_admin_tenants_401_with_invalid_key(self, client):
        resp = client.get(
            "/api/v1/admin/tenants",
            headers={"Authorization": "Bearer smcp_pa_invalid_key_here_xyzabc"},
        )
        assert resp.status_code == 401

    def test_auth_verify_401_without_key(self, client):
        resp = client.post("/api/v1/auth/verify")
        assert resp.status_code == 401

    def test_missing_bearer_returns_401(self, client):
        resp = client.get(
            "/api/v1/admin/tenants",
            headers={"Authorization": "Basic abc123"},
        )
        assert resp.status_code == 401

    def test_health_still_public_with_auth_enabled(self, client):
        """Health endpoints are always public, even with auth enabled."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_live_still_public(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tests: Key lifecycle (auth disabled)
# ---------------------------------------------------------------------------


class TestKeyLifecycle:
    """Full create / list / revoke / verify cycle with auth disabled."""

    def test_create_and_verify_key(self, client):
        """Create a key and use it to verify identity."""
        create_resp = client.post(
            "/api/v1/auth/keys",
            json={"name": "lifecycle-test", "scope": "platform_admin"},
        )
        assert create_resp.status_code == 201
        raw_key = create_resp.json()["key"]
        assert raw_key.startswith("smcp_pa_")

        # Verify endpoint works (auth disabled, so returns valid=True with no identity)
        verify_resp = client.post(
            "/api/v1/auth/verify",
            headers={"Authorization": f"Bearer {raw_key}"},
        )
        assert verify_resp.status_code == 200

    def test_create_different_scopes(self, client):
        """Create keys for each scope tier."""
        for scope, prefix in [
            ("platform_admin", "smcp_pa_"),
            ("tenant_admin", "smcp_ta_"),
            ("tenant_user", "smcp_tu_"),
        ]:
            resp = client.post(
                "/api/v1/auth/keys",
                json={"name": f"test-{scope}", "scope": scope},
            )
            assert resp.status_code == 201
            assert resp.json()["key"].startswith(prefix)
            assert resp.json()["scope"] == scope

    def test_create_tenant_scoped_key(self, client):
        """Create a key scoped to a specific tenant."""
        # First create a tenant
        tenant_resp = client.post(
            "/api/v1/admin/tenants",
            json={"slug": "key-test-tenant", "name": "Key Test Tenant"},
        )
        assert tenant_resp.status_code == 201
        tenant_id = tenant_resp.json()["id"]

        # Create a tenant-scoped key
        key_resp = client.post(
            "/api/v1/auth/keys",
            json={
                "name": "tenant-key",
                "scope": "tenant_admin",
                "tenant_id": tenant_id,
            },
        )
        assert key_resp.status_code == 201
        data = key_resp.json()
        assert data["tenant_id"] == tenant_id
        assert data["scope"] == "tenant_admin"
