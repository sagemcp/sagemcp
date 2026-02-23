"""Admin session introspection endpoints."""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query

from ..models.api_key import APIKeyScope
from ..security.auth import require_scope

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/sessions", dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))])
async def list_sessions(
    request: Request,
    tenant_slug: Optional[str] = Query(None, description="Filter by tenant slug"),
):
    """List active MCP sessions.

    Returns session metadata from the in-memory SessionManager.
    """
    sm = getattr(request.app.state, "session_manager", None)
    if sm is None:
        return []

    now = time.monotonic()
    sessions = []
    for entry in sm.sessions.values():
        if tenant_slug and entry.tenant_slug != tenant_slug:
            continue
        sessions.append({
            "session_id": entry.session_id,
            "tenant_slug": entry.tenant_slug,
            "connector_id": entry.connector_id,
            "created_at": round(now - entry.created_at, 1),
            "last_access": round(now - entry.last_access, 1),
            "negotiated_version": entry.negotiated_version,
        })

    return sessions


@router.delete("/sessions/{session_id}", dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))])
async def terminate_session(request: Request, session_id: str):
    """Terminate an active MCP session."""
    sm = getattr(request.app.state, "session_manager", None)
    if sm is None:
        raise HTTPException(status_code=404, detail="Session management is disabled")

    entry = sm.sessions.get(session_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Session not found")

    sm.close_session(session_id)
    return {"status": "terminated", "session_id": session_id}
