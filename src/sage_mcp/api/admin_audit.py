"""Admin API endpoints for querying the audit log."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from ..models.api_key import APIKeyScope
from ..models.audit_log import AuditLog
from ..models.tenant import Tenant
from ..security.auth import require_scope, require_tenant_access, require_permission
from ..security.permissions import Permission

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AuditLogItem(BaseModel):
    id: str
    timestamp: datetime
    actor_id: str
    actor_type: str
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    tenant_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogListResponse(BaseModel):
    items: List[AuditLogItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _audit_row_to_item(row: AuditLog) -> AuditLogItem:
    return AuditLogItem(
        id=str(row.id),
        timestamp=row.timestamp,
        actor_id=row.actor_id,
        actor_type=row.actor_type,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        tenant_id=str(row.tenant_id) if row.tenant_id else None,
        details=row.details,
        ip_address=row.ip_address,
        user_agent=row.user_agent,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/audit",
    response_model=AuditLogListResponse,
    dependencies=[
        Depends(require_scope(APIKeyScope.PLATFORM_ADMIN)),
        Depends(require_permission(Permission.AUDIT_VIEW_GLOBAL)),
    ],
)
async def list_audit_logs(
    session: AsyncSession = Depends(get_db_session),
    action: Optional[str] = Query(default=None),
    actor_id: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Query audit logs (platform admin only).

    Supports filtering by action, actor_id, tenant_id, and time range.
    Returns paginated results ordered by timestamp descending.
    """
    query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
        count_query = count_query.where(AuditLog.actor_id == actor_id)
    if tenant_id:
        query = query.where(AuditLog.tenant_id == tenant_id)
        count_query = count_query.where(AuditLog.tenant_id == tenant_id)
    if start:
        query = query.where(AuditLog.timestamp >= start)
        count_query = count_query.where(AuditLog.timestamp >= start)
    if end:
        query = query.where(AuditLog.timestamp <= end)
        count_query = count_query.where(AuditLog.timestamp <= end)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    rows = result.scalars().all()

    return AuditLogListResponse(
        items=[_audit_row_to_item(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/tenants/{tenant_slug}/audit",
    response_model=AuditLogListResponse,
    dependencies=[
        Depends(require_scope(APIKeyScope.PLATFORM_ADMIN, APIKeyScope.TENANT_ADMIN)),
        Depends(require_tenant_access()),
        Depends(require_permission(Permission.AUDIT_VIEW_OWN)),
    ],
)
async def list_tenant_audit_logs(
    tenant_slug: str,
    session: AsyncSession = Depends(get_db_session),
    action: Optional[str] = Query(default=None),
    actor_id: Optional[str] = Query(default=None),
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Query audit logs scoped to a specific tenant.

    Accessible by platform admins and tenant admins (with matching tenant).
    """
    # Resolve tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    query = select(AuditLog).where(AuditLog.tenant_id == tenant.id)
    count_query = select(func.count(AuditLog.id)).where(AuditLog.tenant_id == tenant.id)

    if action:
        query = query.where(AuditLog.action == action)
        count_query = count_query.where(AuditLog.action == action)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
        count_query = count_query.where(AuditLog.actor_id == actor_id)
    if start:
        query = query.where(AuditLog.timestamp >= start)
        count_query = count_query.where(AuditLog.timestamp >= start)
    if end:
        query = query.where(AuditLog.timestamp <= end)
        count_query = count_query.where(AuditLog.timestamp <= end)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    rows = result.scalars().all()

    return AuditLogListResponse(
        items=[_audit_row_to_item(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
