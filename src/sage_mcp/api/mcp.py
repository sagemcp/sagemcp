"""MCP API routes for multi-tenant support."""

import asyncio
import json
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, WebSocket, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.encoders import jsonable_encoder

from ..mcp.transport import MCPTransport

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory message queues for routing responses to SSE streams
# Key: f"{tenant_slug}:{connector_id}"
_message_queues: Dict[str, asyncio.Queue] = {}


def _validate_origin(request: Request) -> Optional[Response]:
    """Validate Origin header if MCP_ALLOWED_ORIGINS is configured.

    Returns an error Response if origin is invalid, None if OK.
    """
    allowed = getattr(request.app.state, "mcp_allowed_origins", None)
    if allowed is None:
        return None  # No restriction configured

    origin = request.headers.get("origin")
    if origin and origin not in allowed:
        logger.warning("Rejected request from origin: %s", origin)
        return JSONResponse(
            status_code=403,
            content={"error": f"Origin not allowed: {origin}"},
        )
    return None


def _get_server_pool(request: Request):
    """Get the server pool from app state (may be None if disabled)."""
    return getattr(request.app.state, "server_pool", None)


def _get_session_manager(request: Request):
    """Get the session manager from app state (may be None if disabled)."""
    return getattr(request.app.state, "session_manager", None)


def _get_event_buffer_manager(request: Request):
    """Get the event buffer manager from app state (may be None if disabled)."""
    return getattr(request.app.state, "event_buffer_manager", None)


async def _get_transport(
    request: Request,
    tenant_slug: str,
    connector_id: str,
    user_token: Optional[str] = None,
) -> MCPTransport:
    """Get an MCPTransport, using server pool if available."""
    pool = _get_server_pool(request)
    if pool:
        server = await pool.get_or_create(tenant_slug, connector_id, user_token)
        if server:
            transport = MCPTransport(tenant_slug, connector_id, user_token)
            transport.mcp_server = server
            transport.initialized = True
            return transport

    # Fallback: create new transport directly
    return MCPTransport(tenant_slug, connector_id, user_token=user_token)


@router.websocket("/{tenant_slug}/connectors/{connector_id}/mcp")
async def mcp_websocket(websocket: WebSocket, tenant_slug: str, connector_id: str):
    """WebSocket endpoint for MCP protocol communication.

    Supports user-level OAuth tokens via extension message (recommended):
    Send this message after connection before 'initialize':
    {
      "jsonrpc": "2.0",
      "method": "auth/setUserToken",
      "params": {"token": "<user_token>"}
    }
    """
    user_token = websocket.query_params.get('token')

    transport = MCPTransport(tenant_slug, connector_id, user_token=user_token)

    await transport.handle_websocket(websocket)


@router.post("/{tenant_slug}/connectors/{connector_id}/mcp")
async def mcp_http_post(tenant_slug: str, connector_id: str, request: Request):
    """HTTP POST endpoint for MCP protocol communication (Streamable HTTP transport).

    Per MCP Streamable HTTP spec (2025-06-18):
    - For JSON-RPC notifications (no id): Returns 202 Accepted
    - For JSON-RPC responses (has id, is response): Returns 202 Accepted
    - For JSON-RPC requests (has id, is request): Returns application/json with response

    Supports Mcp-Session-Id header for session reuse.
    Supports JSON-RPC batching (array of messages).
    """
    # Validate Origin
    origin_error = _validate_origin(request)
    if origin_error:
        return origin_error

    # Validate Accept header
    accept_header = request.headers.get("accept", "")
    if "application/json" not in accept_header:
        raise HTTPException(
            status_code=400,
            detail="Accept header must include application/json"
        )

    # Validate Content-Type
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        raise HTTPException(
            status_code=400,
            detail="Content-Type must be application/json"
        )

    try:
        body = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Extract user token
    user_token = request.headers.get('x-user-oauth-token')
    if not user_token:
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            user_token = auth_header[7:]

    logger.debug("MCP POST from tenant=%s connector=%s", tenant_slug, connector_id)

    # JSON-RPC batching: detect array payload
    if isinstance(body, list):
        return await _handle_batch(request, tenant_slug, connector_id, body, user_token)

    # Single message
    return await _handle_single_message(request, tenant_slug, connector_id, body, user_token)


async def _handle_single_message(
    request: Request,
    tenant_slug: str,
    connector_id: str,
    message: dict,
    user_token: Optional[str],
) -> Response:
    """Handle a single JSON-RPC message."""
    message_id = message.get("id")
    method = message.get("method")
    is_response = "result" in message or "error" in message
    is_notification = method is not None and message_id is None
    is_request = method is not None and message_id is not None

    # Handle notifications and responses - return 202 Accepted
    if is_notification or is_response:
        return Response(status_code=202)

    if not is_request:
        error_response = {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {
                "code": -32600,
                "message": "Invalid Request: message must be a request, response, or notification"
            }
        }
        return JSONResponse(content=error_response, status_code=400)

    # Session management
    session_mgr = _get_session_manager(request)
    session_id = request.headers.get("mcp-session-id")

    # For non-initialize requests with session management enabled
    if session_mgr and method != "initialize" and session_id:
        entry = session_mgr.get_session(session_id)
        if entry is None:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid or expired session ID"},
            )
        # Reuse the pooled server from session
        transport = MCPTransport(tenant_slug, connector_id, user_token)
        transport.mcp_server = entry.server
        transport.initialized = True
        if user_token:
            entry.server.user_token = user_token
    else:
        # Create or get transport (using pool if available)
        transport = await _get_transport(request, tenant_slug, connector_id, user_token)

    # Process the request
    response = await transport.handle_http_message(message)

    if response is None:
        raise HTTPException(
            status_code=500,
            detail="Internal error: No response generated for request"
        )

    # For initialize requests: create session and add header
    headers = {}
    if method == "initialize" and session_mgr:
        new_session_id = session_mgr.create_session(
            tenant_slug, connector_id, transport.mcp_server,
            negotiated_version=response.get("result", {}).get("protocolVersion"),
        )
        headers["Mcp-Session-Id"] = new_session_id

    return JSONResponse(
        content=jsonable_encoder(response),
        media_type="application/json",
        headers=headers if headers else None,
    )


async def _handle_batch(
    request: Request,
    tenant_slug: str,
    connector_id: str,
    messages: list,
    user_token: Optional[str],
) -> Response:
    """Handle a JSON-RPC batch (array of messages).

    Returns an array of responses for requests, and 202 for notifications.
    """
    if not messages:
        return JSONResponse(content=[], media_type="application/json")

    transport = await _get_transport(request, tenant_slug, connector_id, user_token)

    responses = []
    has_requests = False

    for message in messages:
        if not isinstance(message, dict):
            responses.append({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": "Invalid Request"}
            })
            has_requests = True
            continue

        message_id = message.get("id")
        method = message.get("method")
        is_notification = method is not None and message_id is None

        if is_notification:
            # Notifications in a batch don't produce responses
            continue

        has_requests = True
        resp = await transport.handle_http_message(message)
        if resp is not None:
            responses.append(resp)

    if not has_requests:
        # All notifications, return 202
        return Response(status_code=202)

    return JSONResponse(
        content=jsonable_encoder(responses),
        media_type="application/json",
    )


@router.get("/{tenant_slug}/connectors/{connector_id}/mcp")
async def mcp_http_get(tenant_slug: str, connector_id: str, request: Request):
    """HTTP GET endpoint for SSE server-initiated messages.

    Supports Last-Event-ID header for resumable streams.
    """
    # Validate Origin
    origin_error = _validate_origin(request)
    if origin_error:
        return origin_error

    session_id = request.headers.get("mcp-session-id")
    last_event_id_str = request.headers.get("last-event-id")

    async def event_stream():
        transport = MCPTransport(tenant_slug, connector_id)

        if not await transport.initialize():
            error_msg = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32001,
                    "message": "Tenant not found or inactive"
                }
            }
            yield f"event: message\ndata: {json.dumps(error_msg)}\n\n"
            return

        # Replay buffered events if Last-Event-ID provided
        buf_mgr = _get_event_buffer_manager(request)
        if buf_mgr and session_id and last_event_id_str:
            try:
                last_event_id = int(last_event_id_str)
                buf = buf_mgr.get_or_create(session_id)
                for event in buf.replay_from(last_event_id):
                    yield f"id: {event.event_id}\nevent: {event.event_type}\ndata: {event.data}\n\n"
            except (ValueError, TypeError):
                pass

        # Get or create message queue for server-initiated messages
        queue_key = f"{tenant_slug}:{connector_id}:server_initiated"
        if queue_key not in _message_queues:
            _message_queues[queue_key] = asyncio.Queue()

        message_queue = _message_queues[queue_key]

        try:
            while True:
                try:
                    message = await asyncio.wait_for(message_queue.get(), timeout=30.0)

                    data = json.dumps(message)

                    # Buffer the event if session-aware
                    event_id_str = ""
                    if buf_mgr and session_id:
                        buf = buf_mgr.get_or_create(session_id)
                        eid = buf.append("message", data)
                        event_id_str = f"id: {eid}\n"

                    yield f"{event_id_str}event: message\ndata: {data}\n\n"

                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"

        except asyncio.CancelledError:
            pass
        except Exception as e:
            error_msg = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"SSE stream error: {str(e)}"
                }
            }
            yield f"event: message\ndata: {json.dumps(error_msg)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control, Last-Event-ID, Mcp-Session-Id",
            "Access-Control-Expose-Headers": "Content-Type, Mcp-Session-Id"
        }
    )


@router.get("/{tenant_slug}/connectors/{connector_id}/mcp/sse")
async def mcp_sse(tenant_slug: str, connector_id: str):
    """DEPRECATED: Old HTTP+SSE endpoint (protocol version 2024-11-05)."""

    async def event_stream():
        yield f"event: endpoint\ndata: {json.dumps({'type': 'endpoint'})}\n\n"

        transport = MCPTransport(tenant_slug, connector_id)

        if not await transport.initialize():
            yield f"event: error\ndata: {json.dumps({'error': 'Tenant not found or inactive', 'code': 4004})}\n\n"
            return

        try:
            while True:
                await asyncio.sleep(15)
                yield f"event: heartbeat\ndata: {json.dumps({'timestamp': asyncio.get_event_loop().time()})}\n\n"

        except asyncio.CancelledError:
            pass
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e), 'code': 1011})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/{tenant_slug}/connectors/{connector_id}/mcp/info")
async def mcp_info(tenant_slug: str, connector_id: str):
    """Get MCP server information for a specific connector."""
    transport = MCPTransport(tenant_slug, connector_id)

    if not await transport.initialize():
        raise HTTPException(status_code=404, detail="Connector not found or inactive")

    return {
        "tenant": tenant_slug,
        "connector_id": connector_id,
        "connector_type": transport.mcp_server.connector.connector_type.value if transport.mcp_server.connector else None,
        "connector_name": transport.mcp_server.connector.name if transport.mcp_server.connector else None,
        "server_name": "sage-mcp",
        "server_version": "0.1.0",
        "protocol_version": "2025-06-18",
        "capabilities": {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "prompts": {"listChanged": True}
        }
    }
