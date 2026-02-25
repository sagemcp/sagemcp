"""API key and JWT authentication and authorization.

Feature-flagged via ``SAGEMCP_ENABLE_AUTH``. When disabled, all checks pass through.

Hot-path optimisation: JWT decode is tried first (~0.1ms, no DB) before falling
back to API key lookup with SHA256-keyed LRU cache to avoid repeated bcrypt
verifies (~100ms each).
"""

import hashlib
import logging
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import Depends, HTTPException, Request, WebSocket
from jose import JWTError
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database.connection import get_db_context, get_db_session
from ..models.api_key import APIKey, APIKeyScope
from .tokens import decode_token

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth context
# ---------------------------------------------------------------------------

SCOPE_PREFIX_MAP = {
    APIKeyScope.PLATFORM_ADMIN: "smcp_pa_",
    APIKeyScope.TENANT_ADMIN: "smcp_ta_",
    APIKeyScope.TENANT_USER: "smcp_tu_",
}

SCOPE_HIERARCHY: dict[APIKeyScope, set[APIKeyScope]] = {
    APIKeyScope.PLATFORM_ADMIN: {
        APIKeyScope.PLATFORM_ADMIN,
        APIKeyScope.TENANT_ADMIN,
        APIKeyScope.TENANT_USER,
    },
    APIKeyScope.TENANT_ADMIN: {
        APIKeyScope.TENANT_ADMIN,
        APIKeyScope.TENANT_USER,
    },
    APIKeyScope.TENANT_USER: {
        APIKeyScope.TENANT_USER,
    },
}


@dataclass(frozen=True)
class AuthContext:
    """Resolved identity from a valid API key or JWT token.

    When authenticated via API key: ``user_id`` and ``email`` are ``None``.
    When authenticated via JWT: ``user_id`` and ``email`` are populated from
    token claims; ``key_id`` is set to ``"jwt:<user_id>"``.
    """
    key_id: str
    name: str
    scope: APIKeyScope
    tenant_id: Optional[str]  # UUID as string, or None for platform-wide
    user_id: Optional[str] = None
    email: Optional[str] = None


# ---------------------------------------------------------------------------
# SHA-256 keyed LRU cache
# ---------------------------------------------------------------------------

_CACHE_MAX = 1000
_CACHE_TTL = 300  # 5 minutes

_cache: OrderedDict[str, tuple[AuthContext, float]] = OrderedDict()
_cache_lock = threading.Lock()


def _cache_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _cache_get(raw_key: str) -> Optional[AuthContext]:
    with _cache_lock:
        ck = _cache_key(raw_key)
        entry = _cache.get(ck)
        if entry is None:
            return None
        ctx, ts = entry
        if time.monotonic() - ts > _CACHE_TTL:
            _cache.pop(ck, None)
            return None
        _cache.move_to_end(ck)
        return ctx


def _cache_put(raw_key: str, ctx: AuthContext) -> None:
    with _cache_lock:
        ck = _cache_key(raw_key)
        _cache[ck] = (ctx, time.monotonic())
        _cache.move_to_end(ck)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


def invalidate_cache_for_key(raw_key: str) -> None:
    """Remove a specific key from the auth cache."""
    with _cache_lock:
        _cache.pop(_cache_key(raw_key), None)


def clear_auth_cache() -> None:
    """Clear the entire auth cache (used on key revocation)."""
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------
# JWT authentication (fast path — no DB query)
# ---------------------------------------------------------------------------

# Maps TenantRole values → APIKeyScope. TenantRole has finer granularity
# (tenant_member, tenant_viewer) which collapse to TENANT_USER for AuthContext.
_ROLE_TO_SCOPE: Dict[str, APIKeyScope] = {
    "platform_admin": APIKeyScope.PLATFORM_ADMIN,
    "tenant_admin": APIKeyScope.TENANT_ADMIN,
    "tenant_member": APIKeyScope.TENANT_USER,
    "tenant_viewer": APIKeyScope.TENANT_USER,
    "tenant_user": APIKeyScope.TENANT_USER,
}

# Lower index = higher privilege, used for scope resolution across multiple roles.
_SCOPE_PRIORITY: List[APIKeyScope] = [
    APIKeyScope.PLATFORM_ADMIN,
    APIKeyScope.TENANT_ADMIN,
    APIKeyScope.TENANT_USER,
]


def _resolve_scope_from_roles(
    roles: Dict[str, str],
) -> Tuple[APIKeyScope, Optional[str]]:
    """Derive APIKeyScope and tenant_id from JWT roles dict.

    ``roles`` maps tenant_id → role_string (e.g. ``{"<uuid>": "tenant_admin"}``).
    A wildcard key ``"*"`` indicates platform-wide access.

    Returns ``(highest_scope, tenant_id_or_None)``.
    """
    if not roles:
        return APIKeyScope.TENANT_USER, None

    best_scope = APIKeyScope.TENANT_USER
    best_scope_idx = _SCOPE_PRIORITY.index(best_scope)
    best_tenant: Optional[str] = None

    for tid, role_str in roles.items():
        scope = _ROLE_TO_SCOPE.get(role_str, APIKeyScope.TENANT_USER)
        idx = _SCOPE_PRIORITY.index(scope)
        if idx <= best_scope_idx:
            best_scope = scope
            best_scope_idx = idx
            best_tenant = tid if tid != "*" else None

    # Platform admin → no tenant restriction
    if best_scope == APIKeyScope.PLATFORM_ADMIN:
        best_tenant = None
    # Multiple tenants → no single tenant restriction
    elif len(roles) > 1:
        best_tenant = None

    return best_scope, best_tenant


def _authenticate_jwt(token: str) -> Optional[AuthContext]:
    """Try to authenticate a Bearer token as a JWT.

    Returns ``AuthContext`` on success, ``None`` if the token is not a valid JWT.
    Fast path: ~0.1ms signature verification, zero DB queries.
    """
    try:
        payload = decode_token(token)
    except (JWTError, Exception):
        return None

    # Only accept access tokens (not refresh tokens)
    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    email = payload.get("email", "")
    roles: Dict[str, str] = payload.get("roles", {})

    scope, tenant_id = _resolve_scope_from_roles(roles)

    return AuthContext(
        key_id=f"jwt:{user_id}",
        name=email or user_id,
        scope=scope,
        tenant_id=tenant_id,
        user_id=user_id,
        email=email or None,
    )


# ---------------------------------------------------------------------------
# Key generation / verification
# ---------------------------------------------------------------------------

def generate_api_key(scope: APIKeyScope) -> str:
    """Generate a new API key with scope-specific prefix."""
    prefix = SCOPE_PREFIX_MAP[scope]
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}{random_part}"


def hash_api_key(raw_key: str) -> str:
    """Hash an API key with bcrypt for storage."""
    import bcrypt as _bcrypt
    return _bcrypt.hashpw(raw_key.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_api_key(raw_key: str, hashed: str) -> bool:
    """Verify an API key against its bcrypt hash."""
    import bcrypt as _bcrypt
    return _bcrypt.checkpw(raw_key.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def _authenticate_raw_key(
    raw_key: str,
    session: AsyncSession,
) -> Optional[AuthContext]:
    """Authenticate a raw API key string against the database.

    Returns an ``AuthContext`` on success. Returns ``None`` if the key is invalid.
    Uses the SHA-256 LRU cache to avoid repeated bcrypt verifies.
    """
    # Check cache first
    cached = _cache_get(raw_key)
    if cached is not None:
        return cached

    # DB lookup by prefix
    prefix = raw_key[:8]  # "smcp_XX_"
    result = await session.execute(
        select(APIKey).where(
            APIKey.key_prefix == prefix,
            APIKey.is_active.is_(True),
        )
    )
    candidates = result.scalars().all()

    for api_key in candidates:
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            continue
        if verify_api_key(raw_key, api_key.key_hash):
            ctx = AuthContext(
                key_id=str(api_key.id),
                name=api_key.name,
                scope=api_key.scope,
                tenant_id=str(api_key.tenant_id) if api_key.tenant_id else None,
            )
            _cache_put(raw_key, ctx)
            return ctx

    return None


async def get_auth_context(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Optional[AuthContext]:
    """Extract and validate credentials from Authorization header.

    Supports both JWT tokens and API keys via ``Authorization: Bearer <token>``.
    JWT decode is tried first (~0.1ms, no DB query) before falling back to
    API key lookup (bcrypt verify, ~100ms worst case).

    Returns ``None`` when auth is disabled.
    Raises 401 when auth is enabled but no valid credentials are provided.
    """
    settings = get_settings()
    if not settings.enable_auth:
        return None

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    raw_token = auth_header[7:]

    # Fast path: try JWT decode first (no DB query)
    ctx = _authenticate_jwt(raw_token)
    if ctx is not None:
        return ctx

    # Slow path: fall back to API key lookup (bcrypt verify)
    ctx = await _authenticate_raw_key(raw_token, session)
    if ctx is not None:
        return ctx

    raise HTTPException(status_code=401, detail="Invalid credentials")


def require_scope(*allowed_scopes: APIKeyScope):
    """Dependency factory: require the auth context to have one of *allowed_scopes*."""

    async def _check(
        auth: Optional[AuthContext] = Depends(get_auth_context),
    ):
        if auth is None:
            return  # Auth disabled
        for scope in allowed_scopes:
            if scope in SCOPE_HIERARCHY.get(auth.scope, set()):
                return
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return _check


def require_permission(*permissions: "Permission"):
    """Dependency factory: require the auth context to have **all** listed permissions.

    Resolves the caller's role from their API key scope (via ``SCOPE_TO_ROLE``)
    and checks each requested permission against the role's permission set.

    When auth is disabled (``AuthContext`` is ``None``), all checks pass through —
    same behaviour as ``require_scope()``.

    Returns 403 with a descriptive message listing missing permissions.
    """
    from .permissions import Permission as _Perm, SCOPE_TO_ROLE, has_permission

    async def _check(
        auth: Optional[AuthContext] = Depends(get_auth_context),
    ):
        if auth is None:
            return  # Auth disabled

        role = SCOPE_TO_ROLE.get(auth.scope)
        if role is None:
            raise HTTPException(
                status_code=403,
                detail=f"Unknown scope '{auth.scope.value}' — cannot resolve permissions",
            )

        missing = [p.value for p in permissions if not has_permission(role, p)]
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"Missing permissions: {', '.join(missing)}",
            )

    return _check


def require_tenant_access(slug_param: str = "tenant_slug"):
    """Dependency factory: require tenant-scoped access.

    - ``platform_admin`` keys have access to all tenants.
    - ``tenant_admin`` and ``tenant_user`` keys must match the tenant.
    """

    async def _check(
        request: Request,
        auth: Optional[AuthContext] = Depends(get_auth_context),
        session: AsyncSession = Depends(get_db_session),
    ):
        if auth is None:
            return  # Auth disabled

        # Platform admins can access any tenant
        if auth.scope == APIKeyScope.PLATFORM_ADMIN:
            return

        # Extract tenant slug from path
        tenant_slug = request.path_params.get(slug_param)
        if not tenant_slug:
            return  # No tenant in path, scope check suffices

        # Resolve tenant ID from slug
        from ..models.tenant import Tenant

        result = await session.execute(
            select(Tenant.id).where(Tenant.slug == tenant_slug)
        )
        tenant_id = result.scalar_one_or_none()
        if tenant_id is None:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Check tenant-scoped key matches
        if auth.tenant_id and auth.tenant_id != str(tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to this tenant")

    return _check


async def validate_websocket_auth(websocket: WebSocket) -> Optional[AuthContext]:
    """Authenticate a WebSocket connection via JWT token or API key.

    Extracts credentials from the ``api_key`` query parameter or the
    ``Authorization: Bearer <token>`` header. JWT decode is tried first
    (fast path), then falls back to API key lookup.

    Returns ``None`` when auth is disabled, ``AuthContext`` when valid.
    Raises ``WebSocketDisconnect(4401)`` on authentication failure.
    """
    settings = get_settings()
    if not settings.enable_auth:
        return None

    # Try query param first, then Authorization header
    raw_token = websocket.query_params.get("api_key")
    if not raw_token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]

    if not raw_token:
        raise WebSocketDisconnect(code=4401, reason="Missing credentials")

    # Fast path: try JWT decode first (no DB query)
    ctx = _authenticate_jwt(raw_token)
    if ctx is not None:
        return ctx

    # Slow path: fall back to API key lookup
    async with get_db_context() as session:
        ctx = await _authenticate_raw_key(raw_token, session)
        if ctx is not None:
            return ctx

    raise WebSocketDisconnect(code=4401, reason="Invalid credentials")
