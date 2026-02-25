"""Integration tests verifying require_permission enforcement on endpoints.

Tests that different API key scopes (mapped to roles) get correct access:
- platform_admin → all permissions
- tenant_admin → tenant/connector CRUD, tool/process/key/user/policy manage, own stats/audit
- tenant_user → connector_read, tool_call, stats_view_own only
"""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sage_mcp.models.api_key import APIKeyScope
from sage_mcp.security.auth import AuthContext, require_permission
from sage_mcp.security.permissions import Permission


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(scope: APIKeyScope, tenant_id: str = "t1") -> AuthContext:
    return AuthContext(key_id="k", name="test", scope=scope, tenant_id=tenant_id)


PA = _ctx(APIKeyScope.PLATFORM_ADMIN, tenant_id=None)
TA = _ctx(APIKeyScope.TENANT_ADMIN)
TU = _ctx(APIKeyScope.TENANT_USER)


async def _check(permission: Permission, ctx: AuthContext):
    """Run the require_permission dependency and return True if allowed."""
    dep = require_permission(permission)
    try:
        await dep(auth=ctx)
        return True
    except HTTPException:
        return False


# ---------------------------------------------------------------------------
# Tenant CRUD permissions
# ---------------------------------------------------------------------------


class TestTenantCRUDPermissions:

    @pytest.mark.asyncio
    async def test_platform_admin_can_create_tenant(self):
        assert await _check(Permission.TENANT_CREATE, PA)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_create_tenant(self):
        assert await _check(Permission.TENANT_CREATE, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_create_tenant(self):
        assert not await _check(Permission.TENANT_CREATE, TU)

    @pytest.mark.asyncio
    async def test_platform_admin_can_read_tenant(self):
        assert await _check(Permission.TENANT_READ, PA)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_read_tenant(self):
        assert await _check(Permission.TENANT_READ, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_read_tenant(self):
        assert not await _check(Permission.TENANT_READ, TU)

    @pytest.mark.asyncio
    async def test_platform_admin_can_update_tenant(self):
        assert await _check(Permission.TENANT_UPDATE, PA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_update_tenant(self):
        assert not await _check(Permission.TENANT_UPDATE, TU)

    @pytest.mark.asyncio
    async def test_platform_admin_can_delete_tenant(self):
        assert await _check(Permission.TENANT_DELETE, PA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_delete_tenant(self):
        assert not await _check(Permission.TENANT_DELETE, TU)


# ---------------------------------------------------------------------------
# Connector CRUD permissions
# ---------------------------------------------------------------------------


class TestConnectorCRUDPermissions:

    @pytest.mark.asyncio
    async def test_platform_admin_can_create_connector(self):
        assert await _check(Permission.CONNECTOR_CREATE, PA)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_create_connector(self):
        assert await _check(Permission.CONNECTOR_CREATE, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_create_connector(self):
        assert not await _check(Permission.CONNECTOR_CREATE, TU)

    @pytest.mark.asyncio
    async def test_all_roles_can_read_connectors(self):
        """connector_read is granted to platform_admin, tenant_admin, and tenant_user."""
        assert await _check(Permission.CONNECTOR_READ, PA)
        assert await _check(Permission.CONNECTOR_READ, TA)
        assert await _check(Permission.CONNECTOR_READ, TU)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_update_connector(self):
        assert await _check(Permission.CONNECTOR_UPDATE, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_update_connector(self):
        assert not await _check(Permission.CONNECTOR_UPDATE, TU)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_delete_connector(self):
        assert await _check(Permission.CONNECTOR_DELETE, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_delete_connector(self):
        assert not await _check(Permission.CONNECTOR_DELETE, TU)


# ---------------------------------------------------------------------------
# Tool permissions
# ---------------------------------------------------------------------------


class TestToolPermissions:

    @pytest.mark.asyncio
    async def test_platform_admin_can_call_tools(self):
        assert await _check(Permission.TOOL_CALL, PA)

    @pytest.mark.asyncio
    async def test_tenant_user_can_call_tools(self):
        """tenant_user maps to TENANT_MEMBER which has tool_call."""
        assert await _check(Permission.TOOL_CALL, TU)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_configure_tools(self):
        assert await _check(Permission.TOOL_CONFIGURE, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_configure_tools(self):
        assert not await _check(Permission.TOOL_CONFIGURE, TU)


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------


class TestProcessManagePermissions:

    @pytest.mark.asyncio
    async def test_platform_admin_can_manage_processes(self):
        assert await _check(Permission.PROCESS_MANAGE, PA)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_manage_processes(self):
        assert await _check(Permission.PROCESS_MANAGE, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_manage_processes(self):
        assert not await _check(Permission.PROCESS_MANAGE, TU)


# ---------------------------------------------------------------------------
# Stats / audit permissions
# ---------------------------------------------------------------------------


class TestStatsAuditPermissions:

    @pytest.mark.asyncio
    async def test_platform_admin_can_view_global_stats(self):
        assert await _check(Permission.STATS_VIEW_GLOBAL, PA)

    @pytest.mark.asyncio
    async def test_tenant_admin_cannot_view_global_stats(self):
        """Global stats/pool/sessions/settings require platform_admin."""
        assert not await _check(Permission.STATS_VIEW_GLOBAL, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_view_global_stats(self):
        assert not await _check(Permission.STATS_VIEW_GLOBAL, TU)

    @pytest.mark.asyncio
    async def test_all_roles_can_view_own_stats(self):
        assert await _check(Permission.STATS_VIEW_OWN, PA)
        assert await _check(Permission.STATS_VIEW_OWN, TA)
        assert await _check(Permission.STATS_VIEW_OWN, TU)

    @pytest.mark.asyncio
    async def test_platform_admin_can_view_global_audit(self):
        assert await _check(Permission.AUDIT_VIEW_GLOBAL, PA)

    @pytest.mark.asyncio
    async def test_tenant_admin_cannot_view_global_audit(self):
        assert not await _check(Permission.AUDIT_VIEW_GLOBAL, TA)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_view_own_audit(self):
        assert await _check(Permission.AUDIT_VIEW_OWN, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_view_own_audit(self):
        assert not await _check(Permission.AUDIT_VIEW_OWN, TU)


# ---------------------------------------------------------------------------
# Key / user / policy management
# ---------------------------------------------------------------------------


class TestManagementPermissions:

    @pytest.mark.asyncio
    async def test_platform_admin_can_manage_keys(self):
        assert await _check(Permission.KEY_MANAGE, PA)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_manage_keys(self):
        assert await _check(Permission.KEY_MANAGE, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_manage_keys(self):
        assert not await _check(Permission.KEY_MANAGE, TU)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_manage_users(self):
        assert await _check(Permission.USER_MANAGE, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_manage_users(self):
        assert not await _check(Permission.USER_MANAGE, TU)

    @pytest.mark.asyncio
    async def test_platform_admin_can_manage_policies(self):
        assert await _check(Permission.POLICY_MANAGE, PA)

    @pytest.mark.asyncio
    async def test_tenant_admin_can_manage_policies(self):
        assert await _check(Permission.POLICY_MANAGE, TA)

    @pytest.mark.asyncio
    async def test_tenant_user_cannot_manage_policies(self):
        assert not await _check(Permission.POLICY_MANAGE, TU)


# ---------------------------------------------------------------------------
# Auth-disabled passthrough
# ---------------------------------------------------------------------------


class TestAuthDisabledPassthrough:

    @pytest.mark.asyncio
    async def test_all_permissions_pass_when_auth_disabled(self):
        """When auth is disabled (None context), every permission check passes."""
        for perm in Permission:
            dep = require_permission(perm)
            await dep(auth=None)  # Should not raise


# ---------------------------------------------------------------------------
# Multiple permissions required simultaneously
# ---------------------------------------------------------------------------


class TestMultiplePermissions:

    @pytest.mark.asyncio
    async def test_platform_admin_passes_multiple(self):
        dep = require_permission(
            Permission.TENANT_CREATE,
            Permission.CONNECTOR_DELETE,
            Permission.STATS_VIEW_GLOBAL,
        )
        await dep(auth=PA)  # Should not raise

    @pytest.mark.asyncio
    async def test_tenant_admin_fails_if_any_missing(self):
        """tenant_admin has TENANT_CREATE but not STATS_VIEW_GLOBAL."""
        dep = require_permission(
            Permission.TENANT_CREATE,
            Permission.STATS_VIEW_GLOBAL,
        )
        with pytest.raises(HTTPException) as exc_info:
            await dep(auth=TA)
        assert exc_info.value.status_code == 403
        assert "stats_view_global" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_error_message_lists_only_missing_permissions(self):
        dep = require_permission(
            Permission.TOOL_CALL,       # TU has this
            Permission.TOOL_CONFIGURE,  # TU does NOT have this
            Permission.PROCESS_MANAGE,  # TU does NOT have this
        )
        with pytest.raises(HTTPException) as exc_info:
            await dep(auth=TU)
        detail = exc_info.value.detail
        assert "tool_configure" in detail
        assert "process_manage" in detail
        assert "tool_call" not in detail  # should not list held permissions
