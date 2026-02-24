"""Admin API for log streaming and retrieval."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from ..models.api_key import APIKeyScope
from ..security.auth import require_scope

router = APIRouter()


@router.get("/logs/recent", dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))])
async def recent_logs(
    request: Request,
    count: int = Query(default=100, le=1000),
    level: Optional[str] = Query(default=None),
    tenant_slug: Optional[str] = Query(default=None),
    connector_id: Optional[str] = Query(default=None),
):
    """Get recent log entries from the ring buffer."""
    broadcaster = getattr(request.app.state, "log_broadcaster", None)
    if broadcaster is None:
        return []

    entries = broadcaster.get_recent(count)

    # Apply filters
    if level:
        level_upper = level.upper()
        entries = [e for e in entries if e.level == level_upper]
    if tenant_slug:
        entries = [e for e in entries if e.tenant_slug == tenant_slug]
    if connector_id:
        entries = [e for e in entries if e.connector_id == connector_id]

    return [e.to_dict() for e in entries]


@router.get("/logs/stream", dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))])
async def stream_logs(
    request: Request,
    level: Optional[str] = Query(default=None),
    tenant_slug: Optional[str] = Query(default=None),
    connector_id: Optional[str] = Query(default=None),
):
    """Stream log entries via SSE."""
    broadcaster = getattr(request.app.state, "log_broadcaster", None)
    if broadcaster is None:
        return StreamingResponse(
            iter([]),
            media_type="text/event-stream",
        )

    queue = broadcaster.subscribe()

    async def event_generator():
        try:
            # Send initial keepalive
            yield "event: connected\ndata: {}\n\n"

            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # Apply filters
                    if level and entry.level != level.upper():
                        continue
                    if tenant_slug and entry.tenant_slug != tenant_slug:
                        continue
                    if connector_id and entry.connector_id != connector_id:
                        continue

                    data = json.dumps(entry.to_dict())
                    yield f"event: log\ndata: {data}\n\n"

                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"

        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
