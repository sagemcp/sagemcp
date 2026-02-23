"""API key management endpoints."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from ..models.api_key import APIKey, APIKeyScope
from ..security.auth import (
    AuthContext,
    generate_api_key,
    get_auth_context,
    hash_api_key,
    require_scope,
    clear_auth_cache,
)

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
    dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))],
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
    dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))],
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
    dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))],
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
