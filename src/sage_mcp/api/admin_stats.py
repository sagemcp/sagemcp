"""Admin stats endpoint for dashboard metrics."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from ..models.tenant import Tenant
from ..models.connector import Connector
from ..observability.metrics import get_tool_calls_today
from .mcp import get_recent_active_session_count

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats")
async def get_platform_stats(request: Request):
    """Return aggregated platform stats for the dashboard.

    Reads from server_pool, session_manager, and DB to provide
    a single snapshot of platform health.
    """
    from ..database.connection import get_db_context

    # Query DB for tenant and connector counts
    async with get_db_context() as session:
        tenant_count = (await session.execute(select(func.count(Tenant.id)))).scalar() or 0
        connector_count = (await session.execute(select(func.count(Connector.id)))).scalar() or 0

    # Pool stats
    pool = getattr(request.app.state, "server_pool", None)
    if pool:
        active_instances = pool.size
        pool_hits = pool.hits
        pool_misses = pool.misses
    else:
        # Active instances is pool-only. Show 0 when pool is disabled.
        active_instances = 0
        pool_hits = 0
        pool_misses = 0

    # Session stats
    sm = getattr(request.app.state, "session_manager", None)
    # If session manager is disabled, fall back to recently active MCP clients.
    active_sessions = (
        sm.active_session_count
        if sm
        else get_recent_active_session_count(request.app, ttl_seconds=60.0)
    )

    return {
        "tenants": tenant_count,
        "connectors": connector_count,
        "active_instances": active_instances,
        "active_sessions": active_sessions,
        "pool_hits": pool_hits,
        "pool_misses": pool_misses,
        "tool_calls_today": get_tool_calls_today(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
