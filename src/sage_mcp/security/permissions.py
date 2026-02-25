"""RBAC permission model for SageMCP.

Maps ``TenantRole`` to fine-grained ``Permission`` sets. All functions are pure
and operate on immutable data — safe for concurrent use on the hot path with
zero allocations per call (frozensets are pre-built at import time).

API key scopes are bridged to roles via ``SCOPE_TO_ROLE`` so that the same
permission checks work for both JWT and API key authentication.
"""

import enum
from typing import FrozenSet

from ..models.api_key import APIKeyScope
from ..models.user import TenantRole


class Permission(str, enum.Enum):
    """Fine-grained permissions for RBAC enforcement."""

    TENANT_CREATE = "tenant_create"
    TENANT_READ = "tenant_read"
    TENANT_UPDATE = "tenant_update"
    TENANT_DELETE = "tenant_delete"

    CONNECTOR_CREATE = "connector_create"
    CONNECTOR_READ = "connector_read"
    CONNECTOR_UPDATE = "connector_update"
    CONNECTOR_DELETE = "connector_delete"

    TOOL_CALL = "tool_call"
    TOOL_CONFIGURE = "tool_configure"

    PROCESS_MANAGE = "process_manage"

    STATS_VIEW_OWN = "stats_view_own"
    STATS_VIEW_GLOBAL = "stats_view_global"

    AUDIT_VIEW_OWN = "audit_view_own"
    AUDIT_VIEW_GLOBAL = "audit_view_global"

    KEY_MANAGE = "key_manage"
    USER_MANAGE = "user_manage"
    POLICY_MANAGE = "policy_manage"


# ---------------------------------------------------------------------------
# Role → Permission mapping (immutable, pre-built at import time)
# ---------------------------------------------------------------------------

_ALL_PERMISSIONS: FrozenSet[Permission] = frozenset(Permission)

ROLE_PERMISSIONS: dict[TenantRole, FrozenSet[Permission]] = {
    TenantRole.PLATFORM_ADMIN: _ALL_PERMISSIONS,

    TenantRole.TENANT_ADMIN: frozenset({
        Permission.TENANT_CREATE,
        Permission.TENANT_READ,
        Permission.TENANT_UPDATE,
        Permission.TENANT_DELETE,
        Permission.CONNECTOR_CREATE,
        Permission.CONNECTOR_READ,
        Permission.CONNECTOR_UPDATE,
        Permission.CONNECTOR_DELETE,
        Permission.TOOL_CALL,
        Permission.TOOL_CONFIGURE,
        Permission.PROCESS_MANAGE,
        Permission.STATS_VIEW_OWN,
        Permission.AUDIT_VIEW_OWN,
        Permission.KEY_MANAGE,
        Permission.USER_MANAGE,
        Permission.POLICY_MANAGE,
    }),

    TenantRole.TENANT_MEMBER: frozenset({
        Permission.CONNECTOR_READ,
        Permission.TOOL_CALL,
        Permission.STATS_VIEW_OWN,
    }),

    TenantRole.TENANT_VIEWER: frozenset({
        Permission.CONNECTOR_READ,
        Permission.STATS_VIEW_OWN,
    }),
}

# ---------------------------------------------------------------------------
# API key scope → role bridge
# ---------------------------------------------------------------------------

SCOPE_TO_ROLE: dict[APIKeyScope, TenantRole] = {
    APIKeyScope.PLATFORM_ADMIN: TenantRole.PLATFORM_ADMIN,
    APIKeyScope.TENANT_ADMIN: TenantRole.TENANT_ADMIN,
    APIKeyScope.TENANT_USER: TenantRole.TENANT_MEMBER,
}


# ---------------------------------------------------------------------------
# Pure query functions (zero-alloc hot path)
# ---------------------------------------------------------------------------

def has_permission(role: TenantRole, permission: Permission) -> bool:
    """Check whether *role* grants *permission*.

    O(1) frozenset membership test. No allocations.
    """
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def get_permissions(role: TenantRole) -> FrozenSet[Permission]:
    """Return the full permission set for *role*.

    Returns a pre-built frozenset — no copy, no allocation.
    """
    return ROLE_PERMISSIONS.get(role, frozenset())
