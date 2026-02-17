"""API key authentication and authorization.

Feature-flagged via ``SAGEMCP_ENABLE_AUTH``. When disabled, all checks pass through.

Hot-path optimisation: SHA256-keyed LRU cache avoids repeated bcrypt verifies (~100ms each).
"""

import hashlib
import logging
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, HTTPException, Request, WebSocket
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database.connection import get_db_context, get_db_session
from ..models.api_key import APIKey, APIKeyScope

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
    """Resolved identity from a valid API key."""
    key_id: str
    name: str
    scope: APIKeyScope
    tenant_id: Optional[str]  # UUID as string, or None for platform-wide


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
    """Extract and validate API key from Authorization header.

    Returns ``None`` when auth is disabled.
    Raises 401 when auth is enabled but no valid key is provided.
    """
    settings = get_settings()
    if not settings.enable_auth:
        return None

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    raw_key = auth_header[7:]
    ctx = await _authenticate_raw_key(raw_key, session)
    if ctx is not None:
        return ctx

    raise HTTPException(status_code=401, detail="Invalid API key")


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
    """Authenticate a WebSocket connection via API key.

    Extracts the API key from the ``api_key`` query parameter or the
    ``Authorization: Bearer <key>`` header.

    Returns ``None`` when auth is disabled, ``AuthContext`` when valid.
    Raises ``WebSocketDisconnect(4401)`` on authentication failure.
    """
    settings = get_settings()
    if not settings.enable_auth:
        return None

    # Try query param first, then Authorization header
    raw_key = websocket.query_params.get("api_key")
    if not raw_key:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            raw_key = auth_header[7:]

    if not raw_key:
        raise WebSocketDisconnect(code=4401, reason="Missing API key")

    async with get_db_context() as session:
        ctx = await _authenticate_raw_key(raw_key, session)
        if ctx is not None:
            return ctx

    raise WebSocketDisconnect(code=4401, reason="Invalid API key")
