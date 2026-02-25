"""API key management and user authentication endpoints."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database.connection import get_db_session
from ..models.api_key import APIKey, APIKeyScope
from ..models.user import AuthProvider, RefreshToken, TenantRole, User
from ..security.auth import (
    AuthContext,
    generate_api_key,
    get_auth_context,
    hash_api_key,
    require_scope,
    require_permission,
    clear_auth_cache,
)
from ..security.permissions import Permission
from ..security.tokens import create_access_token, create_refresh_token, decode_token

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class APIKeyCreateRequest(BaseModel):
    name: str
    scope: APIKeyScope
    tenant_id: Optional[UUID] = None


class APIKeyCreateResponse(BaseModel):
    id: str
    name: str
    key: str  # Plaintext — shown only once
    key_prefix: str
    scope: APIKeyScope
    tenant_id: Optional[str]
    created_at: datetime


class APIKeyListItem(BaseModel):
    id: str
    name: str
    key_prefix: str
    scope: APIKeyScope
    tenant_id: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime


class APIKeyVerifyResponse(BaseModel):
    valid: bool
    key_id: Optional[str] = None
    name: Optional[str] = None
    scope: Optional[APIKeyScope] = None
    tenant_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/keys",
    response_model=APIKeyCreateResponse,
    status_code=201,
    dependencies=[
        Depends(require_scope(APIKeyScope.PLATFORM_ADMIN)),
        Depends(require_permission(Permission.KEY_MANAGE)),
    ],
)
async def create_api_key(
    request: APIKeyCreateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new API key. Only platform admins can create keys."""
    raw_key = generate_api_key(request.scope)
    key_hash = hash_api_key(raw_key)

    api_key = APIKey(
        name=request.name,
        key_prefix=raw_key[:8],
        key_hash=key_hash,
        scope=request.scope,
        tenant_id=request.tenant_id,
        is_active=True,
    )
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    logger.info("Created API key '%s' (scope=%s)", request.name, request.scope.value)

    return APIKeyCreateResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        scope=api_key.scope,
        tenant_id=str(api_key.tenant_id) if api_key.tenant_id else None,
        created_at=api_key.created_at,
    )


@router.get(
    "/keys",
    response_model=List[APIKeyListItem],
    dependencies=[
        Depends(require_scope(APIKeyScope.PLATFORM_ADMIN)),
        Depends(require_permission(Permission.KEY_MANAGE)),
    ],
)
async def list_api_keys(
    session: AsyncSession = Depends(get_db_session),
):
    """List all API keys (without hashes). Only platform admins."""
    result = await session.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    keys = result.scalars().all()

    return [
        APIKeyListItem(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            scope=k.scope,
            tenant_id=str(k.tenant_id) if k.tenant_id else None,
            is_active=k.is_active,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete(
    "/keys/{key_id}",
    dependencies=[
        Depends(require_scope(APIKeyScope.PLATFORM_ADMIN)),
        Depends(require_permission(Permission.KEY_MANAGE)),
    ],
)
async def revoke_api_key(
    key_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Revoke (deactivate) an API key. Only platform admins."""
    result = await session.execute(select(APIKey).where(APIKey.id == key_id))
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await session.commit()

    # Invalidate the entire auth cache — we don't know the raw key
    clear_auth_cache()

    logger.info("Revoked API key '%s' (id=%s)", api_key.name, key_id)
    return {"message": f"API key '{api_key.name}' has been revoked"}


@router.post("/verify", response_model=APIKeyVerifyResponse)
async def verify_key(
    auth: Optional[AuthContext] = Depends(get_auth_context),
):
    """Verify the current API key and return its identity."""
    if auth is None:
        # Auth disabled — report as valid with no identity
        return APIKeyVerifyResponse(valid=True)
    return APIKeyVerifyResponse(
        valid=True,
        key_id=auth.key_id,
        name=auth.name,
        scope=auth.scope,
        tenant_id=auth.tenant_id,
    )


# ---------------------------------------------------------------------------
# User auth schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class RegisterResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    is_active: bool


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _hash_refresh_token(raw_token: str) -> str:
    """SHA-256 hash of the raw refresh token for DB storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def _build_roles(user_id, session: AsyncSession) -> dict:
    """Load tenant->role map for JWT claims."""
    from ..models.user import UserTenantMembership

    result = await session.execute(
        select(UserTenantMembership).where(
            UserTenantMembership.user_id == user_id
        )
    )
    memberships = result.scalars().all()
    return {str(m.tenant_id): m.role.value for m in memberships}


async def _issue_tokens(
    user: User,
    session: AsyncSession,
) -> TokenResponse:
    """Create access + refresh token pair, persist refresh hash."""
    settings = get_settings()
    roles = await _build_roles(user.id, session)

    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        roles=roles,
    )

    raw_refresh = create_refresh_token(user_id=str(user.id))
    token_hash = _hash_refresh_token(raw_refresh)

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(rt)
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


# ---------------------------------------------------------------------------
# User auth endpoints (feature-flagged under SAGEMCP_ENABLE_AUTH)
# ---------------------------------------------------------------------------

@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Register a new user.

    Open when no users exist (first-user bootstrap). After that, requires
    a valid platform_admin JWT in the Authorization header.
    """
    settings = get_settings()
    if not settings.enable_auth:
        raise HTTPException(status_code=404, detail="Auth endpoints not enabled")

    # Check if any users exist
    count_result = await session.execute(select(func.count()).select_from(User))
    user_count = count_result.scalar()

    if user_count > 0:
        # Not first user — require platform_admin JWT
        # (We inline auth check here because get_auth_context is API-key-oriented.
        #  Task #2 will unify JWT+API key auth in get_auth_context.)
        raise HTTPException(
            status_code=403,
            detail="Registration requires platform_admin privileges",
        )

    # Check email uniqueness
    existing = await session.execute(
        select(User).where(User.email == request.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(request.password) < 8:
        raise HTTPException(
            status_code=422, detail="Password must be at least 8 characters"
        )

    user = User(
        email=request.email,
        display_name=request.display_name,
        password_hash=_hash_password(request.password),
        auth_provider=AuthProvider.LOCAL,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info("Registered user '%s' (first_user=%s)", user.email, user_count == 0)

    return RegisterResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Authenticate with email + password and receive a token pair."""
    settings = get_settings()
    if not settings.enable_auth:
        raise HTTPException(status_code=404, detail="Auth endpoints not enabled")

    result = await session.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")

    if not _verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token_resp = await _issue_tokens(user, session)
    logger.info("User '%s' logged in", user.email)
    return token_resp


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Rotate refresh token: revoke old, issue new pair."""
    settings = get_settings()
    if not settings.enable_auth:
        raise HTTPException(status_code=404, detail="Auth endpoints not enabled")

    # Decode to verify signature + expiry
    try:
        payload = decode_token(request.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    token_hash = _hash_refresh_token(request.refresh_token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()

    if not rt or rt.revoked:
        raise HTTPException(status_code=401, detail="Refresh token revoked or unknown")

    # SQLite strips timezone info, so normalize both sides to UTC
    expires_at = rt.expires_at.replace(tzinfo=timezone.utc) if rt.expires_at.tzinfo is None else rt.expires_at
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # Revoke the old token
    rt.revoked = True
    await session.flush()

    # Fetch user to issue new pair
    user_result = await session.execute(
        select(User).where(User.id == rt.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    token_resp = await _issue_tokens(user, session)
    logger.info("Refreshed tokens for user '%s'", user.email)
    return token_resp


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Revoke a refresh token (logout)."""
    settings = get_settings()
    if not settings.enable_auth:
        raise HTTPException(status_code=404, detail="Auth endpoints not enabled")

    token_hash = _hash_refresh_token(request.refresh_token)
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()

    if rt and not rt.revoked:
        rt.revoked = True
        await session.commit()
        logger.info("Logged out (revoked refresh token for user %s)", rt.user_id)

    return {"message": "Logged out"}
