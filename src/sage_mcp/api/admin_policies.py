"""Admin endpoints for global tool/connector governance policies."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from ..models.api_key import APIKeyScope
from ..models.tool_policy import GlobalToolPolicy, PolicyAction
from ..security.auth import require_scope, require_permission
from ..security.permissions import Permission
from ..security.tool_policy import invalidate_policy_cache, load_policies

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ToolPolicyCreate(BaseModel):
    tool_name_pattern: str
    action: PolicyAction
    reason: Optional[str] = None
    connector_type: Optional[str] = None
    is_active: bool = True


class ToolPolicyUpdate(BaseModel):
    tool_name_pattern: Optional[str] = None
    action: Optional[PolicyAction] = None
    reason: Optional[str] = None
    connector_type: Optional[str] = None
    is_active: Optional[bool] = None


class ToolPolicyResponse(BaseModel):
    id: UUID
    tool_name_pattern: str
    action: PolicyAction
    reason: Optional[str]
    created_by: Optional[str]
    connector_type: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# CRUD endpoints — platform_admin only
# ---------------------------------------------------------------------------


@router.get(
    "/policies/tools",
    response_model=List[ToolPolicyResponse],
    dependencies=[
        Depends(require_scope(APIKeyScope.PLATFORM_ADMIN)),
        Depends(require_permission(Permission.POLICY_MANAGE)),
    ],
)
async def list_tool_policies(
    session: AsyncSession = Depends(get_db_session),
):
    """List all global tool policies."""
    result = await session.execute(
        select(GlobalToolPolicy).order_by(GlobalToolPolicy.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/policies/tools",
    response_model=ToolPolicyResponse,
    status_code=201,
    dependencies=[
        Depends(require_scope(APIKeyScope.PLATFORM_ADMIN)),
        Depends(require_permission(Permission.POLICY_MANAGE)),
    ],
)
async def create_tool_policy(
    policy_data: ToolPolicyCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new global tool policy."""
    policy = GlobalToolPolicy(
        tool_name_pattern=policy_data.tool_name_pattern,
        action=policy_data.action,
        reason=policy_data.reason,
        connector_type=policy_data.connector_type,
        is_active=policy_data.is_active,
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)

    # Eagerly reload cache so enforcement is immediate
    invalidate_policy_cache()
    await load_policies(session)

    return policy


@router.put(
    "/policies/tools/{policy_id}",
    response_model=ToolPolicyResponse,
    dependencies=[
        Depends(require_scope(APIKeyScope.PLATFORM_ADMIN)),
        Depends(require_permission(Permission.POLICY_MANAGE)),
    ],
)
async def update_tool_policy(
    policy_id: UUID,
    policy_data: ToolPolicyUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """Update an existing global tool policy."""
    result = await session.execute(
        select(GlobalToolPolicy).where(GlobalToolPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if policy_data.tool_name_pattern is not None:
        policy.tool_name_pattern = policy_data.tool_name_pattern
    if policy_data.action is not None:
        policy.action = policy_data.action
    if policy_data.reason is not None:
        policy.reason = policy_data.reason
    if policy_data.connector_type is not None:
        policy.connector_type = policy_data.connector_type
    if policy_data.is_active is not None:
        policy.is_active = policy_data.is_active

    await session.commit()
    await session.refresh(policy)

    invalidate_policy_cache()
    await load_policies(session)

    return policy


@router.delete(
    "/policies/tools/{policy_id}",
    dependencies=[
        Depends(require_scope(APIKeyScope.PLATFORM_ADMIN)),
        Depends(require_permission(Permission.POLICY_MANAGE)),
    ],
)
async def delete_tool_policy(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a global tool policy."""
    result = await session.execute(
        select(GlobalToolPolicy).where(GlobalToolPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    await session.delete(policy)
    await session.commit()

    invalidate_policy_cache()
    await load_policies(session)

    return {"message": f"Policy '{policy.tool_name_pattern}' deleted"}
