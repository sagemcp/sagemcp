"""Tests for tenant isolation security fixes.

Covers three security gaps fixed in the auth enforcement:
1. WebSocket MCP tenant scope check
2. list_connectors scope guard
3. Process management endpoint tenant isolation
"""

import os
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.websockets import WebSocketDisconnect

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from sage_mcp.models.api_key import APIKeyScope
from sage_mcp.security.auth import AuthContext, clear_auth_cache, get_auth_context


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_auth_cache()
    yield
    clear_auth_cache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    """Short unique suffix to avoid slug collisions across tests."""
    return uuid.uuid4().hex[:8]


def _make_auth_context(scope: APIKeyScope, tenant_id: str = None) -> AuthContext:
    return AuthContext(
        key_id=str(uuid.uuid4()),
        name="test-key",
        scope=scope,
        tenant_id=tenant_id,
    )


def _create_tenant(client, slug: str, name: str) -> dict:
    resp = client.post(
        "/api/v1/admin/tenants",
        json={"slug": slug, "name": name},
    )
    assert resp.status_code == 201, f"Failed to create tenant {slug}: {resp.text}"
    return resp.json()


def _create_connector(client, tenant_slug: str, name: str, connector_type: str = "github") -> dict:
    resp = client.post(
        f"/api/v1/admin/tenants/{tenant_slug}/connectors",
        json={"connector_type": connector_type, "name": name},
    )
    assert resp.status_code == 201, f"Failed to create connector: {resp.text}"
    return resp.json()


def _mock_db_context_for_tenant(tenant_id_str: str):
    """Create a mock get_db_context that returns a session resolving to the given tenant_id."""
    @asynccontextmanager
    async def mock_ctx():
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid.UUID(tenant_id_str)
        mock_session.execute.return_value = mock_result
        yield mock_session
    return mock_ctx


def _mock_db_context_no_tenant():
    """Create a mock get_db_context that returns None for the tenant lookup."""
    @asynccontextmanager
    async def mock_ctx():
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        yield mock_session
    return mock_ctx


# ---------------------------------------------------------------------------
# Fix 1: WebSocket MCP tenant scope check
# ---------------------------------------------------------------------------

class TestWebSocketTenantIsolation:
    """WebSocket connections must verify the key's tenant matches the URL tenant."""

    @pytest.fixture(autouse=True)
    def _enable_auth(self):
        from sage_mcp.config import get_settings
        settings = get_settings()
        original = settings.enable_auth
        settings.enable_auth = True
        yield
        settings.enable_auth = original

    def test_ws_cross_tenant_rejected(self, client):
        """A key scoped to tenant A cannot connect to tenant B's WebSocket."""
        tenant_a_id = str(uuid.uuid4())
        tenant_b_id = str(uuid.uuid4())

        auth_ctx = _make_auth_context(APIKeyScope.TENANT_USER, tenant_id=tenant_a_id)

        with patch("sage_mcp.api.mcp.validate_websocket_auth", new_callable=AsyncMock, return_value=auth_ctx):
            # Mock DB to return tenant B's ID for the slug lookup
            with patch("sage_mcp.api.mcp.get_db_context", _mock_db_context_for_tenant(tenant_b_id)):
                with pytest.raises(WebSocketDisconnect) as exc_info:
                    with client.websocket_connect(
                        "/api/v1/some-tenant/connectors/some-id/mcp"
                    ):
                        pass
                assert exc_info.value.code == 4403

    def test_ws_cross_tenant_unknown_tenant_rejected(self, client):
        """A tenant-scoped key is rejected when the URL tenant doesn't exist."""
        tenant_a_id = str(uuid.uuid4())

        auth_ctx = _make_auth_context(APIKeyScope.TENANT_USER, tenant_id=tenant_a_id)

        with patch("sage_mcp.api.mcp.validate_websocket_auth", new_callable=AsyncMock, return_value=auth_ctx):
            # Mock DB to return None (tenant not found)
            with patch("sage_mcp.api.mcp.get_db_context", _mock_db_context_no_tenant()):
                with pytest.raises(WebSocketDisconnect) as exc_info:
                    with client.websocket_connect(
                        "/api/v1/unknown-tenant/connectors/some-id/mcp"
                    ):
                        pass
                assert exc_info.value.code == 4403

    def test_ws_same_tenant_passes_auth(self, client):
        """A key scoped to tenant A passes the tenant check for tenant A's WebSocket."""
        tenant_a_id = str(uuid.uuid4())

        auth_ctx = _make_auth_context(APIKeyScope.TENANT_USER, tenant_id=tenant_a_id)

        async def _close_ws(websocket, **kwargs):
            """Accept then immediately close so the test doesn't hang."""
            await websocket.accept()
            await websocket.close()

        with patch("sage_mcp.api.mcp.validate_websocket_auth", new_callable=AsyncMock, return_value=auth_ctx):
            # Mock DB to return the SAME tenant ID (key's tenant matches URL tenant)
            with patch("sage_mcp.api.mcp.get_db_context", _mock_db_context_for_tenant(tenant_a_id)):
                with patch("sage_mcp.api.mcp.MCPTransport") as mock_transport_cls:
                    mock_transport = MagicMock()
                    mock_transport.handle_websocket = _close_ws
                    mock_transport_cls.return_value = mock_transport

                    try:
                        with client.websocket_connect(
                            "/api/v1/my-tenant/connectors/some-id/mcp"
                        ):
                            pass
                    except WebSocketDisconnect:
                        pass  # Expected — server closed the connection

                    # Transport was created — auth check passed
                    mock_transport_cls.assert_called_once()

    def test_ws_platform_admin_bypasses_check(self, client):
        """Platform admin keys skip the tenant scope check entirely."""
        auth_ctx = _make_auth_context(APIKeyScope.PLATFORM_ADMIN, tenant_id=None)

        async def _close_ws(websocket, **kwargs):
            await websocket.accept()
            await websocket.close()

        with patch("sage_mcp.api.mcp.validate_websocket_auth", new_callable=AsyncMock, return_value=auth_ctx):
            with patch("sage_mcp.api.mcp.MCPTransport") as mock_transport_cls:
                mock_transport = MagicMock()
                mock_transport.handle_websocket = _close_ws
                mock_transport_cls.return_value = mock_transport

                try:
                    with client.websocket_connect(
                        "/api/v1/any-tenant/connectors/some-id/mcp"
                    ):
                        pass
                except WebSocketDisconnect:
                    pass  # Expected

                # Transport was created — auth check passed (no DB lookup needed)
                mock_transport_cls.assert_called_once()

    def test_ws_auth_disabled_skips_check(self, client):
        """When auth is disabled, the tenant check is skipped."""
        from sage_mcp.config import get_settings
        settings = get_settings()
        settings.enable_auth = False

        async def _close_ws(websocket, **kwargs):
            await websocket.accept()
            await websocket.close()

        # validate_websocket_auth returns None when auth disabled
        with patch("sage_mcp.api.mcp.validate_websocket_auth", new_callable=AsyncMock, return_value=None):
            with patch("sage_mcp.api.mcp.MCPTransport") as mock_transport_cls:
                mock_transport = MagicMock()
                mock_transport.handle_websocket = _close_ws
                mock_transport_cls.return_value = mock_transport

                try:
                    with client.websocket_connect(
                        "/api/v1/any-tenant/connectors/some-id/mcp"
                    ):
                        pass
                except WebSocketDisconnect:
                    pass  # Expected

                mock_transport_cls.assert_called_once()


# ---------------------------------------------------------------------------
# Fix 2: list_connectors scope guard
# ---------------------------------------------------------------------------

class TestListConnectorsScopeGuard:
    """list_connectors endpoint must enforce scope check."""

    @pytest.fixture(autouse=True)
    def _enable_auth(self):
        from sage_mcp.config import get_settings
        settings = get_settings()
        original = settings.enable_auth
        settings.enable_auth = True
        yield
        settings.enable_auth = original

    def test_list_connectors_401_without_key(self, client):
        """list_connectors returns 401 when auth is enabled and no key is provided."""
        resp = client.get("/api/v1/admin/tenants/some-tenant/connectors")
        assert resp.status_code == 401

    def test_list_connectors_allowed_for_tenant_user(self, client):
        """tenant_user scope is allowed to list connectors."""
        from sage_mcp.main import app
        from sage_mcp.config import get_settings

        settings = get_settings()
        settings.enable_auth = False

        uid = _uid()
        tenant = _create_tenant(client, f"lc-tu-{uid}", "LC TU")

        settings.enable_auth = True

        auth_ctx = _make_auth_context(APIKeyScope.TENANT_USER, tenant_id=tenant["id"])

        async def override_auth():
            return auth_ctx

        app.dependency_overrides[get_auth_context] = override_auth
        try:
            resp = client.get(f"/api/v1/admin/tenants/{tenant['slug']}/connectors")
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_auth_context, None)

    def test_list_connectors_tenant_user_cross_tenant_denied(self, client):
        """tenant_user for tenant A cannot list tenant B's connectors."""
        from sage_mcp.main import app
        from sage_mcp.config import get_settings

        settings = get_settings()
        settings.enable_auth = False

        uid = _uid()
        tenant_a = _create_tenant(client, f"lc-a-{uid}", "LC A")
        tenant_b = _create_tenant(client, f"lc-b-{uid}", "LC B")

        settings.enable_auth = True

        auth_ctx = _make_auth_context(APIKeyScope.TENANT_USER, tenant_id=tenant_a["id"])

        async def override_auth():
            return auth_ctx

        app.dependency_overrides[get_auth_context] = override_auth
        try:
            resp = client.get(f"/api/v1/admin/tenants/{tenant_b['slug']}/connectors")
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(get_auth_context, None)


# ---------------------------------------------------------------------------
# Fix 3: Process management tenant isolation
# ---------------------------------------------------------------------------

class TestProcessEndpointTenantIsolation:
    """Process management endpoints must enforce tenant isolation."""

    @pytest.fixture(autouse=True)
    def _enable_auth(self):
        from sage_mcp.config import get_settings
        settings = get_settings()
        original = settings.enable_auth
        settings.enable_auth = True
        yield
        settings.enable_auth = original

    @pytest.fixture()
    def two_tenants_with_connectors(self, client):
        """Create two tenants each with a connector (auth disabled for setup)."""
        from sage_mcp.config import get_settings
        settings = get_settings()
        settings.enable_auth = False

        uid = _uid()
        tenant_a = _create_tenant(client, f"proc-a-{uid}", "Proc A")
        tenant_b = _create_tenant(client, f"proc-b-{uid}", "Proc B")
        conn_a = _create_connector(client, f"proc-a-{uid}", "Conn A")
        conn_b = _create_connector(client, f"proc-b-{uid}", "Conn B")

        settings.enable_auth = True
        return tenant_a, tenant_b, conn_a, conn_b

    def test_process_status_cross_tenant_denied(self, client, two_tenants_with_connectors):
        """tenant_admin for tenant A cannot get process status for tenant B's connector."""
        from sage_mcp.main import app
        tenant_a, tenant_b, conn_a, conn_b = two_tenants_with_connectors

        auth_ctx = _make_auth_context(APIKeyScope.TENANT_ADMIN, tenant_id=tenant_a["id"])

        async def override_auth():
            return auth_ctx

        app.dependency_overrides[get_auth_context] = override_auth
        try:
            resp = client.get(f"/api/v1/admin/connectors/{conn_b['id']}/process/status")
            assert resp.status_code == 403
            assert "Access denied" in resp.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_context, None)

    def test_process_restart_cross_tenant_denied(self, client, two_tenants_with_connectors):
        """tenant_admin for tenant A cannot restart tenant B's connector process."""
        from sage_mcp.main import app
        tenant_a, tenant_b, conn_a, conn_b = two_tenants_with_connectors

        auth_ctx = _make_auth_context(APIKeyScope.TENANT_ADMIN, tenant_id=tenant_a["id"])

        async def override_auth():
            return auth_ctx

        app.dependency_overrides[get_auth_context] = override_auth
        try:
            resp = client.post(f"/api/v1/admin/connectors/{conn_b['id']}/process/restart")
            assert resp.status_code == 403
            assert "Access denied" in resp.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_context, None)

    def test_process_terminate_cross_tenant_denied(self, client, two_tenants_with_connectors):
        """tenant_admin for tenant A cannot terminate tenant B's connector process."""
        from sage_mcp.main import app
        tenant_a, tenant_b, conn_a, conn_b = two_tenants_with_connectors

        auth_ctx = _make_auth_context(APIKeyScope.TENANT_ADMIN, tenant_id=tenant_a["id"])

        async def override_auth():
            return auth_ctx

        app.dependency_overrides[get_auth_context] = override_auth
        try:
            resp = client.delete(f"/api/v1/admin/connectors/{conn_b['id']}/process")
            assert resp.status_code == 403
            assert "Access denied" in resp.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_context, None)

    def test_process_status_same_tenant_allowed(self, client, two_tenants_with_connectors):
        """tenant_admin for tenant A can access tenant A's connector process."""
        from sage_mcp.main import app
        tenant_a, tenant_b, conn_a, conn_b = two_tenants_with_connectors

        auth_ctx = _make_auth_context(APIKeyScope.TENANT_ADMIN, tenant_id=tenant_a["id"])

        async def override_auth():
            return auth_ctx

        app.dependency_overrides[get_auth_context] = override_auth
        try:
            resp = client.get(f"/api/v1/admin/connectors/{conn_a['id']}/process/status")
            # 400 = "native connector" error — means we passed the tenant isolation check
            assert resp.status_code == 400
            assert "native connector" in resp.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_context, None)

    def test_process_platform_admin_any_tenant(self, client, two_tenants_with_connectors):
        """platform_admin can access any tenant's connector process."""
        from sage_mcp.main import app
        tenant_a, tenant_b, conn_a, conn_b = two_tenants_with_connectors

        auth_ctx = _make_auth_context(APIKeyScope.PLATFORM_ADMIN, tenant_id=None)

        async def override_auth():
            return auth_ctx

        app.dependency_overrides[get_auth_context] = override_auth
        try:
            resp = client.get(f"/api/v1/admin/connectors/{conn_b['id']}/process/status")
            # 400 = "native connector" error — means we passed the tenant isolation check
            assert resp.status_code == 400
            assert "native connector" in resp.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_context, None)
