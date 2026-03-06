"""Fire-and-forget audit logging for security-sensitive actions.

``record_audit()`` schedules a background task via ``asyncio.create_task()``
so audit I/O never blocks the request hot path.  If the DB write fails the
error is logged but never propagated to the caller.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request

from ..database.connection import get_db_context
from ..models.audit_log import AuditLog
from .auth import AuthContext

logger = logging.getLogger(__name__)


async def _persist_audit_event(
    action: str,
    actor_id: str,
    actor_type: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
    resource_type: Optional[str],
    resource_id: Optional[str],
    tenant_id: Optional[str],
    details: Optional[dict],
) -> None:
    """Write a single audit row.  Runs inside a fire-and-forget task."""
    try:
        async with get_db_context() as session:
            entry = AuditLog(
                id=uuid.uuid4(),
                timestamp=datetime.now(timezone.utc),
                actor_id=actor_id,
                actor_type=actor_type,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            session.add(entry)
            await session.commit()
    except Exception:
        logger.exception("Failed to persist audit event action=%s", action)


def record_audit(
    action: str,
    auth_context: Optional[AuthContext],
    request: Optional[Request],
    *,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Schedule an audit log entry in the background.

    This is a synchronous function that creates an ``asyncio.Task`` — it must
    be called from within an active event loop (i.e. inside an async endpoint).
    The audit write will never block the caller or propagate exceptions.

    Args:
        action: Dot-delimited action string, e.g. ``"tenant.create"``.
        auth_context: The resolved auth context (``None`` when auth disabled).
        request: The incoming ``Request`` (for IP / User-Agent extraction).
        resource_type: E.g. ``"tenant"``, ``"connector"``, ``"api_key"``.
        resource_id: ID of the resource acted upon.
        tenant_id: UUID string of the tenant scope (if applicable).
        details: Optional JSON-serialisable dict with extra context.
    """
    if auth_context is not None:
        actor_id = auth_context.key_id
        actor_type = "api_key"
    else:
        actor_id = "anonymous"
        actor_type = "system"

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    if request is not None:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    asyncio.create_task(
        _persist_audit_event(
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            details=details,
        )
    )
