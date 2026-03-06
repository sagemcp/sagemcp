"""Integration tests for user auth endpoints (Phase 3.3).

Tests cover:
- Register first user (bootstrap)
- Register blocked for second user (no admin auth yet)
- Login success / failure
- Token refresh with rotation
- Logout (revoke refresh token)
- Feature-flag guard (404 when auth disabled)
"""

import asyncio
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from sage_mcp.security.auth import clear_auth_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_auth_cache()
    yield
    clear_auth_cache()


@pytest.fixture(autouse=True)
def _clean_async_db(event_loop):
    """Clean user-related tables in the async DB between tests.

    The global cleanup_db fixture only touches the sync engine. The TestClient
    writes to the async engine (separate in-memory SQLite), so we must clean
    both to get proper test isolation.
    """
    yield
    from tests.conftest import test_async_engine
    from sqlalchemy import text

    async def _clean():
        async with test_async_engine.begin() as conn:
            await conn.execute(text("DELETE FROM refresh_tokens"))
            await conn.execute(text("DELETE FROM user_tenant_memberships"))
            await conn.execute(text("DELETE FROM users"))

    event_loop.run_until_complete(_clean())


# ---------------------------------------------------------------------------
# Tests: Auth disabled (default) — login endpoints return 404
# ---------------------------------------------------------------------------


class TestAuthLoginDisabled:
    """Login endpoints return 404 when SAGEMCP_ENABLE_AUTH is False."""

    def test_register_404_when_auth_disabled(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "a@b.com", "password": "longpassword123"},
        )
        assert resp.status_code == 404

    def test_login_404_when_auth_disabled(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "a@b.com", "password": "longpassword123"},
        )
        assert resp.status_code == 404

    def test_refresh_404_when_auth_disabled(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "fake"},
        )
        assert resp.status_code == 404

    def test_logout_404_when_auth_disabled(self, client):
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "fake"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Auth enabled — full lifecycle
# ---------------------------------------------------------------------------


class TestAuthLoginEnabled:
    """Login/register endpoints with SAGEMCP_ENABLE_AUTH=True."""

    @pytest.fixture(autouse=True)
    def _enable_auth(self):
        from sage_mcp.config import get_settings

        settings = get_settings()
        original = settings.enable_auth
        settings.enable_auth = True
        yield
        settings.enable_auth = original

    # -- Registration -------------------------------------------------------

    def test_register_first_user(self, client):
        """First user registration succeeds without auth (bootstrap)."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@example.com",
                "password": "strong-password-123",
                "display_name": "Admin",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "admin@example.com"
        assert data["display_name"] == "Admin"
        assert data["is_active"] is True
        assert "id" in data

    def test_register_duplicate_email(self, client):
        """Cannot register twice with the same email."""
        payload = {
            "email": "dupe@example.com",
            "password": "strong-password-123",
        }
        resp1 = client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 201

        resp2 = client.post("/api/v1/auth/register", json=payload)
        # Second user blocked (no admin auth to authorize)
        assert resp2.status_code == 403

    def test_register_short_password(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "short@example.com", "password": "abc"},
        )
        # First user but short password
        assert resp.status_code == 422

    def test_register_blocked_when_users_exist(self, client):
        """After first user, registration requires admin auth."""
        # Create first user
        client.post(
            "/api/v1/auth/register",
            json={"email": "first@example.com", "password": "longpassword123"},
        )

        # Second registration without admin auth is blocked
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "second@example.com", "password": "longpassword123"},
        )
        assert resp.status_code == 403

    # -- Login --------------------------------------------------------------

    def test_login_success(self, client):
        """Login with correct credentials returns token pair."""
        # Register
        client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "validpass123"},
        )

        # Login
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "validpass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_wrong_password(self, client):
        client.post(
            "/api/v1/auth/register",
            json={"email": "wrong@example.com", "password": "correctpass1"},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpass!!"},
        )
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "whatever123"},
        )
        assert resp.status_code == 401

    # -- Token refresh ------------------------------------------------------

    def test_refresh_rotates_tokens(self, client):
        """Refresh endpoint revokes old token and issues new pair."""
        # Register + login
        client.post(
            "/api/v1/auth/register",
            json={"email": "refresh@example.com", "password": "mypassword1"},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "refresh@example.com", "password": "mypassword1"},
        )
        old_refresh = login_resp.json()["refresh_token"]

        # Refresh
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert refresh_resp.status_code == 200
        new_data = refresh_resp.json()
        assert "access_token" in new_data
        assert "refresh_token" in new_data
        assert new_data["refresh_token"] != old_refresh

    def test_refresh_old_token_revoked(self, client):
        """After rotation, using the old refresh token fails."""
        client.post(
            "/api/v1/auth/register",
            json={"email": "rotate@example.com", "password": "mypassword1"},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "rotate@example.com", "password": "mypassword1"},
        )
        old_refresh = login_resp.json()["refresh_token"]

        # Rotate
        client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

        # Old token should be revoked
        resp = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
        )
        assert resp.status_code == 401

    def test_refresh_invalid_token(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not-a-valid-jwt"},
        )
        assert resp.status_code == 401

    # -- Logout -------------------------------------------------------------

    def test_logout_revokes_refresh(self, client):
        """Logout revokes the refresh token so it can't be reused."""
        client.post(
            "/api/v1/auth/register",
            json={"email": "logout@example.com", "password": "mypassword1"},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "logout@example.com", "password": "mypassword1"},
        )
        refresh_tok = login_resp.json()["refresh_token"]

        # Logout
        resp = client.post(
            "/api/v1/auth/logout", json={"refresh_token": refresh_tok}
        )
        assert resp.status_code == 200

        # Refresh should fail now
        resp = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_tok}
        )
        assert resp.status_code == 401

    def test_logout_idempotent(self, client):
        """Logging out twice is fine (no error)."""
        client.post(
            "/api/v1/auth/register",
            json={"email": "idem@example.com", "password": "mypassword1"},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "idem@example.com", "password": "mypassword1"},
        )
        refresh_tok = login_resp.json()["refresh_token"]

        client.post("/api/v1/auth/logout", json={"refresh_token": refresh_tok})
        resp = client.post(
            "/api/v1/auth/logout", json={"refresh_token": refresh_tok}
        )
        assert resp.status_code == 200
