"""MCP API routes for multi-tenant support."""

import asyncio
import json
from typing import Dict

from fastapi import APIRouter, HTTPException, Request, WebSocket, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.encoders import jsonable_encoder

from ..mcp.transport import MCPTransport

router = APIRouter()

# Simple in-memory message queues for routing responses to SSE streams
# Key: f"{tenant_slug}:{connector_id}"
_message_queues: Dict[str, asyncio.Queue] = {}


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

    Legacy support: Query parameter (not recommended for security):
    ws://host/api/v1/{tenant_slug}/connectors/{connector_id}/mcp?token=<user_token>
    """
    # Legacy: Extract user token from query parameter if provided
    # Note: Query params are deprecated for tokens due to security concerns
    user_token = websocket.query_params.get('token')

    # Create transport for this specific connector with optional user token
    transport = MCPTransport(tenant_slug, connector_id, user_token=user_token)

    # Handle the WebSocket connection
    # User can also set/update token via auth/setUserToken extension message
    await transport.handle_websocket(websocket)


@router.post("/{tenant_slug}/connectors/{connector_id}/mcp")
async def mcp_http_post(tenant_slug: str, connector_id: str, request: Request):
    """HTTP POST endpoint for MCP protocol communication (Streamable HTTP transport).

    Per MCP Streamable HTTP spec (2025-06-18):
    - For JSON-RPC notifications (no id): Returns 202 Accepted
    - For JSON-RPC responses (has id, is response): Returns 202 Accepted
    - For JSON-RPC requests (has id, is request): Returns application/json with response

    Client MUST include Accept header with application/json and text/event-stream.

    Supports user-level OAuth tokens via custom header:
    X-User-OAuth-Token: <user_token>

    Note: User tokens are for external APIs (GitHub, Slack, etc.),
    separate from MCP protocol-level authentication.
    """
    # Validate Accept header
    accept_header = request.headers.get("accept", "")
    if "application/json" not in accept_header:
        raise HTTPException(
            status_code=400,
            detail="Accept header must include application/json"
        )

    try:
        # Parse the JSON-RPC message
        message = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Extract user token from custom header if provided
    # Using custom header to avoid conflict with MCP protocol auth
    user_token = request.headers.get('x-user-oauth-token')

    # DEBUG: Log header extraction
    print(f"DEBUG [mcp.py]: Received headers: {dict(request.headers)}")
    print(f"DEBUG [mcp.py]: Extracted user_token from X-User-OAuth-Token: {user_token is not None} (length: {len(user_token) if user_token else 0})")

    # Fallback: also support Authorization header for backward compatibility
    if not user_token:
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            user_token = auth_header[7:]
            print(f"DEBUG [mcp.py]: Fallback - Extracted user_token from Authorization header: {user_token is not None}")

    # Determine message type
    message_id = message.get("id")
    method = message.get("method")
    is_response = "result" in message or "error" in message
    is_notification = method is not None and message_id is None
    is_request = method is not None and message_id is not None

    # Handle notifications and responses - return 202 Accepted
    if is_notification or is_response:
        # For notifications: acknowledge receipt
        # For responses: acknowledge receipt (responses are from server answering client's earlier request)
        return Response(status_code=202)

    # Handle requests - process and return JSON response
    if is_request:
        # Create transport for this specific connector with optional user token
        transport = MCPTransport(tenant_slug, connector_id, user_token=user_token)

        # Process the request
        response = await transport.handle_http_message(message)

        if response is None:
            # This shouldn't happen for requests, but handle gracefully
            raise HTTPException(
                status_code=500,
                detail="Internal error: No response generated for request"
            )

        # Return JSON response directly
        return JSONResponse(
            content=jsonable_encoder(response),
            media_type="application/json"
        )

    # Invalid message format
    error_response = {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {
            "code": -32600,
            "message": "Invalid Request: message must be a request, response, or notification"
        }
    }
    return JSONResponse(content=error_response, status_code=400)


@router.get("/{tenant_slug}/connectors/{connector_id}/mcp")
async def mcp_http_get(tenant_slug: str, connector_id: str):
    """HTTP GET endpoint for MCP protocol communication (Streamable HTTP transport).

    This is OPTIONAL per the MCP spec. It provides an SSE stream for server-initiated
    messages (requests and notifications) that are NOT in response to a client request.

    Per MCP spec (2025-06-18):
    - Server MAY provide this endpoint or return 405 Method Not Allowed
    - Messages on this stream SHOULD be unrelated to any client request
    - Server MUST NOT send JSON-RPC responses here (unless resuming a stream)

    This implementation provides the GET endpoint to support server-initiated messages
    such as notifications about resource changes, progress updates, etc.

    Client MUST include Accept: text/event-stream header.
    """
    async def event_stream():
        # Create transport for this specific connector
        transport = MCPTransport(tenant_slug, connector_id)

        # Initialize the transport
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

        # Get or create message queue for server-initiated messages
        queue_key = f"{tenant_slug}:{connector_id}:server_initiated"
        if queue_key not in _message_queues:
            _message_queues[queue_key] = asyncio.Queue()

        message_queue = _message_queues[queue_key]

        try:
            # Listen for server-initiated messages to send via SSE
            while True:
                try:
                    # Wait for message with timeout to allow periodic heartbeats
                    message = await asyncio.wait_for(message_queue.get(), timeout=30.0)

                    # Send message as SSE event
                    # Per MCP spec: all messages use event type "message"
                    yield f"event: message\ndata: {json.dumps(message)}\n\n"

                except asyncio.TimeoutError:
                    # Send heartbeat comment to keep connection alive
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
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control, Last-Event-ID",
            "Access-Control-Expose-Headers": "Content-Type"
        }
    )


@router.get("/{tenant_slug}/connectors/{connector_id}/mcp/sse")
async def mcp_sse(tenant_slug: str, connector_id: str):
    """DEPRECATED: Old HTTP+SSE endpoint (protocol version 2024-11-05).

    This endpoint is from the deprecated HTTP+SSE transport pattern.
    For backwards compatibility with older clients.

    Modern clients should use:
    - POST to /{tenant_slug}/connectors/{connector_id}/mcp for requests
    - GET to /{tenant_slug}/connectors/{connector_id}/mcp for server-initiated messages (optional)
    """

    async def event_stream():
        # Send endpoint event for backwards compatibility
        yield f"event: endpoint\ndata: {json.dumps({'type': 'endpoint'})}\n\n"

        # Create transport for this specific connector
        transport = MCPTransport(tenant_slug, connector_id)

        # Initialize the transport
        if not await transport.initialize():
            yield f"event: error\ndata: {json.dumps({'error': 'Tenant not found or inactive', 'code': 4004})}\n\n"
            return

        try:
            # Keep connection alive with periodic heartbeats
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
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/{tenant_slug}/connectors/{connector_id}/mcp/info")
async def mcp_info(tenant_slug: str, connector_id: str):
    """Get MCP server information for a specific connector."""
    # Create transport to check if connector exists
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
        "protocol_version": "2024-11-05",
        "capabilities": {
            "tools": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "prompts": {"listChanged": True}
        }
    }
