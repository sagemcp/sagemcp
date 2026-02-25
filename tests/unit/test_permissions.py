"""Tests for RBAC permission model and require_permission dependency (Phase 4)."""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from sage_mcp.models.api_key import APIKeyScope
from sage_mcp.models.user import TenantRole
from sage_mcp.security.permissions import (
    ROLE_PERMISSIONS,
    SCOPE_TO_ROLE,
    Permission,
    get_permissions,
    has_permission,
)
from sage_mcp.security.auth import AuthContext, require_permission


# ---------------------------------------------------------------------------
# Permission enum
# ---------------------------------------------------------------------------


class TestPermissionEnum:
    """Permission enum has all 18 expected members."""

    EXPECTED = {
        "tenant_create", "tenant_read", "tenant_update", "tenant_delete",
        "connector_create", "connector_read", "connector_update", "connector_delete",
        "tool_call", "tool_configure",
        "process_manage",
        "stats_view_own", "stats_view_global",
        "audit_view_own", "audit_view_global",
        "key_manage", "user_manage", "policy_manage",
    }

    def test_member_count(self):
        assert len(Permission) == 18

    def test_all_expected_members_exist(self):
        actual = {p.value for p in Permission}
        assert actual == self.EXPECTED

    def test_string_enum(self):
        assert Permission.TOOL_CALL == "tool_call"
        assert isinstance(Permission.TOOL_CALL, str)


# ---------------------------------------------------------------------------
# Role → Permission mapping
# ---------------------------------------------------------------------------


class TestRolePermissions:
    """ROLE_PERMISSIONS dict maps every TenantRole to a frozenset."""

    def test_all_roles_covered(self):
        for role in TenantRole:
            assert role in ROLE_PERMISSIONS, f"Missing mapping for {role}"

    def test_platform_admin_has_all(self):
        perms = ROLE_PERMISSIONS[TenantRole.PLATFORM_ADMIN]
        assert perms == frozenset(Permission)

    def test_tenant_admin_permissions(self):
        perms = ROLE_PERMISSIONS[TenantRole.TENANT_ADMIN]
        # Has tenant CRUD
        assert Permission.TENANT_CREATE in perms
        assert Permission.TENANT_READ in perms
        assert Permission.TENANT_UPDATE in perms
        assert Permission.TENANT_DELETE in perms
        # Has connector CRUD
        assert Permission.CONNECTOR_CREATE in perms
        assert Permission.CONNECTOR_READ in perms
        assert Permission.CONNECTOR_UPDATE in perms
        assert Permission.CONNECTOR_DELETE in perms
        # Has tool ops
        assert Permission.TOOL_CALL in perms
        assert Permission.TOOL_CONFIGURE in perms
        # Has process manage
        assert Permission.PROCESS_MANAGE in perms
        # Has own-scope stats/audit
        assert Permission.STATS_VIEW_OWN in perms
        assert Permission.AUDIT_VIEW_OWN in perms
        # Has key/user/policy manage
        assert Permission.KEY_MANAGE in perms
        assert Permission.USER_MANAGE in perms
        assert Permission.POLICY_MANAGE in perms
        # Does NOT have global views
        assert Permission.STATS_VIEW_GLOBAL not in perms
        assert Permission.AUDIT_VIEW_GLOBAL not in perms

    def test_tenant_member_permissions(self):
        perms = ROLE_PERMISSIONS[TenantRole.TENANT_MEMBER]
        assert Permission.CONNECTOR_READ in perms
        assert Permission.TOOL_CALL in perms
        assert Permission.STATS_VIEW_OWN in perms
        # Should have exactly these 3
        assert len(perms) == 3

    def test_tenant_viewer_permissions(self):
        perms = ROLE_PERMISSIONS[TenantRole.TENANT_VIEWER]
        assert Permission.CONNECTOR_READ in perms
        assert Permission.STATS_VIEW_OWN in perms
        assert len(perms) == 2

    def test_immutability(self):
        """Permission sets are frozensets — cannot be mutated."""
        for role in TenantRole:
            perms = ROLE_PERMISSIONS[role]
            assert isinstance(perms, frozenset)

    def test_hierarchy_subset_property(self):
        """Each lower role's permissions are a subset of the higher role."""
        assert ROLE_PERMISSIONS[TenantRole.TENANT_VIEWER] <= ROLE_PERMISSIONS[TenantRole.TENANT_MEMBER]
        assert ROLE_PERMISSIONS[TenantRole.TENANT_MEMBER] <= ROLE_PERMISSIONS[TenantRole.TENANT_ADMIN]
        assert ROLE_PERMISSIONS[TenantRole.TENANT_ADMIN] <= ROLE_PERMISSIONS[TenantRole.PLATFORM_ADMIN]


# ---------------------------------------------------------------------------
# Scope → Role bridge
# ---------------------------------------------------------------------------


class TestScopeToRole:
    """SCOPE_TO_ROLE maps every APIKeyScope to a TenantRole."""

    def test_all_scopes_mapped(self):
        for scope in APIKeyScope:
            assert scope in SCOPE_TO_ROLE, f"Missing mapping for {scope}"

    def test_platform_admin(self):
        assert SCOPE_TO_ROLE[APIKeyScope.PLATFORM_ADMIN] == TenantRole.PLATFORM_ADMIN

    def test_tenant_admin(self):
        assert SCOPE_TO_ROLE[APIKeyScope.TENANT_ADMIN] == TenantRole.TENANT_ADMIN

    def test_tenant_user(self):
        assert SCOPE_TO_ROLE[APIKeyScope.TENANT_USER] == TenantRole.TENANT_MEMBER


# ---------------------------------------------------------------------------
# has_permission() / get_permissions()
# ---------------------------------------------------------------------------


class TestHasPermission:
    """Pure function: has_permission(role, permission) -> bool."""

    def test_platform_admin_has_everything(self):
        for perm in Permission:
            assert has_permission(TenantRole.PLATFORM_ADMIN, perm)

    def test_tenant_viewer_cannot_call_tools(self):
        assert not has_permission(TenantRole.TENANT_VIEWER, Permission.TOOL_CALL)

    def test_tenant_member_can_call_tools(self):
        assert has_permission(TenantRole.TENANT_MEMBER, Permission.TOOL_CALL)

    def test_tenant_member_cannot_delete_connectors(self):
        assert not has_permission(TenantRole.TENANT_MEMBER, Permission.CONNECTOR_DELETE)

    def test_tenant_admin_cannot_view_global_stats(self):
        assert not has_permission(TenantRole.TENANT_ADMIN, Permission.STATS_VIEW_GLOBAL)

    def test_tenant_admin_can_manage_users(self):
        assert has_permission(TenantRole.TENANT_ADMIN, Permission.USER_MANAGE)


class TestGetPermissions:
    """Pure function: get_permissions(role) -> frozenset[Permission]."""

    def test_returns_frozenset(self):
        result = get_permissions(TenantRole.TENANT_MEMBER)
        assert isinstance(result, frozenset)

    def test_same_object_as_dict(self):
        """Returns the pre-built frozenset, not a copy."""
        result = get_permissions(TenantRole.TENANT_ADMIN)
        assert result is ROLE_PERMISSIONS[TenantRole.TENANT_ADMIN]


# ---------------------------------------------------------------------------
# require_permission() dependency
# ---------------------------------------------------------------------------


class TestRequirePermission:
    """Dependency factory mirrors require_scope pattern."""

    @pytest.mark.asyncio
    async def test_auth_disabled_passes(self):
        """When auth is disabled (None context), all permission checks pass."""
        check = require_permission(Permission.TENANT_DELETE)
        await check(auth=None)  # Should not raise

    @pytest.mark.asyncio
    async def test_platform_admin_passes_any_permission(self):
        ctx = AuthContext(
            key_id="k1", name="admin", scope=APIKeyScope.PLATFORM_ADMIN, tenant_id=None
        )
        check = require_permission(Permission.TENANT_DELETE, Permission.STATS_VIEW_GLOBAL)
        await check(auth=ctx)  # Should not raise

    @pytest.mark.asyncio
    async def test_tenant_user_passes_tool_call(self):
        ctx = AuthContext(
            key_id="k2", name="user", scope=APIKeyScope.TENANT_USER, tenant_id="t1"
        )
        check = require_permission(Permission.TOOL_CALL)
        await check(auth=ctx)  # Should not raise

    @pytest.mark.asyncio
    async def test_tenant_user_denied_connector_delete(self):
        from fastapi import HTTPException

        ctx = AuthContext(
            key_id="k3", name="user", scope=APIKeyScope.TENANT_USER, tenant_id="t1"
        )
        check = require_permission(Permission.CONNECTOR_DELETE)
        with pytest.raises(HTTPException) as exc_info:
            await check(auth=ctx)
        assert exc_info.value.status_code == 403
        assert "connector_delete" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_tenant_admin_denied_global_stats(self):
        from fastapi import HTTPException

        ctx = AuthContext(
            key_id="k4", name="ta", scope=APIKeyScope.TENANT_ADMIN, tenant_id="t1"
        )
        check = require_permission(Permission.STATS_VIEW_GLOBAL)
        with pytest.raises(HTTPException) as exc_info:
            await check(auth=ctx)
        assert exc_info.value.status_code == 403
        assert "stats_view_global" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_multiple_permissions_all_required(self):
        """All listed permissions must be held — not just one."""
        from fastapi import HTTPException

        ctx = AuthContext(
            key_id="k5", name="user", scope=APIKeyScope.TENANT_USER, tenant_id="t1"
        )
        # TENANT_USER (→ TENANT_MEMBER) has TOOL_CALL but not CONNECTOR_DELETE
        check = require_permission(Permission.TOOL_CALL, Permission.CONNECTOR_DELETE)
        with pytest.raises(HTTPException) as exc_info:
            await check(auth=ctx)
        assert exc_info.value.status_code == 403
        assert "connector_delete" in exc_info.value.detail
        # TOOL_CALL should NOT be in the missing list
        assert "tool_call" not in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_tenant_admin_passes_connector_crud(self):
        ctx = AuthContext(
            key_id="k6", name="ta", scope=APIKeyScope.TENANT_ADMIN, tenant_id="t1"
        )
        check = require_permission(
            Permission.CONNECTOR_CREATE,
            Permission.CONNECTOR_READ,
            Permission.CONNECTOR_UPDATE,
            Permission.CONNECTOR_DELETE,
        )
        await check(auth=ctx)  # Should not raise

    @pytest.mark.asyncio
    async def test_tenant_viewer_denied_tool_call(self):
        """TENANT_USER with viewer-equivalent scope would be denied, but
        currently APIKeyScope has no VIEWER. This tests that TENANT_USER
        (mapped to TENANT_MEMBER) cannot do admin ops."""
        from fastapi import HTTPException

        ctx = AuthContext(
            key_id="k7", name="viewer", scope=APIKeyScope.TENANT_USER, tenant_id="t1"
        )
        check = require_permission(Permission.USER_MANAGE)
        with pytest.raises(HTTPException) as exc_info:
            await check(auth=ctx)
        assert exc_info.value.status_code == 403
