"""MCP transport layer for HTTP and WebSocket connections."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from .server import MCPServer

logger = logging.getLogger(__name__)

# Supported MCP protocol versions (newest first)
SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2024-11-05"]


def _error_response(message_id: Any, code: int, message: str) -> Dict[str, Any]:
    """Build a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }


def _negotiate_protocol_version(client_version: str) -> Optional[str]:
    """Negotiate protocol version.

    Returns the latest server-supported version that is <= client_version,
    or None if no compatible version exists.
    """
    for version in SUPPORTED_PROTOCOL_VERSIONS:
        if version <= client_version:
            return version
    return None


class MCPTransport:
    """Transport layer for MCP communication."""

    def __init__(self, tenant_slug: str, connector_id: str = None, user_token: str = None):
        self.tenant_slug = tenant_slug
        self.connector_id = connector_id
        self.user_token = user_token  # User-provided OAuth token (optional)
        logger.debug(
            "MCPTransport created - tenant: %s, connector: %s, has_user_token: %s",
            tenant_slug, connector_id, user_token is not None,
        )
        self.mcp_server = MCPServer(tenant_slug, connector_id, user_token)
        self.initialized = False

    async def initialize(self) -> bool:
        """Initialize the transport and MCP server."""
        if self.initialized:
            return True

        success = await self.mcp_server.initialize()
        if success:
            self.initialized = True

        return success

    async def handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connection for MCP protocol."""
        if not await self.initialize():
            await websocket.close(code=4004, reason="Tenant not found or inactive")
            return

        try:
            await websocket.accept()

            # Basic WebSocket message handling
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    # Check for extension method to set user token
                    method = message.get("method")
                    if method == "auth/setUserToken":
                        # Extension method to set user OAuth token for this session
                        token = message.get("params", {}).get("token")
                        if token:
                            self.user_token = token
                            self.mcp_server.user_token = token

                        # Acknowledge (notifications don't need response, but we send one for confirmation)
                        if "id" in message:
                            await websocket.send_text(json.dumps({
                                "jsonrpc": "2.0",
                                "id": message.get("id"),
                                "result": {"status": "token_set"}
                            }))
                        continue

                    # Handle the message through HTTP-style processing
                    response = await self.handle_http_message(message)

                    # Send response back through WebSocket only if there is a response
                    # (notifications return None and don't expect a response)
                    if response is not None:
                        await websocket.send_text(json.dumps(response))

                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps(
                        _error_response(None, -32700, "Parse error")
                    ))
                except Exception as e:
                    await websocket.send_text(json.dumps(
                        _error_response(None, -32603, f"Internal error: {str(e)}")
                    ))

        except Exception as e:
            logger.error("WebSocket error for tenant %s: %s", self.tenant_slug, e)
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except Exception:
                pass

    async def handle_sse(self, messages: asyncio.Queue):
        """Handle Server-Sent Events for MCP protocol."""
        if not await self.initialize():
            await messages.put({
                "error": "Tenant not found or inactive",
                "code": 4004
            })
            return

        try:
            # For now, handle SSE through message queue processing
            while True:
                try:
                    # Get message from queue (this would be from client)
                    message = await messages.get()
                    if message is None:  # Sentinel to close
                        break

                    # Process the message
                    response = await self.handle_http_message(message)

                    # Send response back through the queue only if there is a response
                    # (notifications return None and don't expect a response)
                    if response is not None:
                        await messages.put(response)

                except Exception as e:
                    logger.error("SSE message processing error: %s", e)
                    await messages.put({
                        "error": f"Internal server error: {str(e)}",
                        "code": 1011
                    })

        except Exception as e:
            logger.error("SSE error for tenant %s: %s", self.tenant_slug, e)
            await messages.put({
                "error": f"Internal server error: {str(e)}",
                "code": 1011
            })

    async def handle_http_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle single HTTP message for MCP protocol.

        Returns None for notifications (per JSON-RPC 2.0 spec, notifications
        don't receive responses).
        """
        if not await self.initialize():
            return _error_response(None, -32001, "Tenant not found or inactive")

        try:
            method = message.get("method")
            message_id = message.get("id")
            params = message.get("params", {})

            logger.debug("Received message: method=%s, id=%s", method, message_id)

            # Handle notifications (messages with no id)
            # Per JSON-RPC 2.0 spec: notifications MUST NOT have a response
            if message_id is None or "id" not in message:
                # Notifications are fire-and-forget; return None
                return None

            if method == "initialize":
                client_protocol = params.get("protocolVersion", "2024-11-05")
                negotiated = _negotiate_protocol_version(client_protocol)

                if negotiated is None:
                    return _error_response(
                        message_id,
                        -32602,
                        f"Unsupported protocol version: {client_protocol}. "
                        f"Supported: {', '.join(SUPPORTED_PROTOCOL_VERSIONS)}",
                    )

                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "protocolVersion": negotiated,
                        "capabilities": {
                            "tools": {"listChanged": True},
                            "resources": {"subscribe": True, "listChanged": True}
                        },
                        "serverInfo": {
                            "name": "sage-mcp",
                            "version": "0.1.0"
                        }
                    }
                }

            elif method == "tools/list":
                if hasattr(self.mcp_server.server, 'request_handlers'):
                    handlers = self.mcp_server.server.request_handlers

                    from mcp.types import ListToolsRequest
                    if ListToolsRequest in handlers:
                        handler = handlers[ListToolsRequest]
                        try:
                            request_obj = ListToolsRequest(method="tools/list", params=params or {})
                            result = await handler(request_obj)

                            clean_tools = []

                            tools_list = None
                            if hasattr(result, 'tools'):
                                tools_list = result.tools
                            elif hasattr(result, 'root') and hasattr(result.root, 'tools'):
                                tools_list = result.root.tools
                            elif isinstance(result, dict) and 'tools' in result:
                                tools_list = result['tools']

                            if tools_list:
                                for tool in tools_list:
                                    clean_tool = {
                                        "name": tool.name,
                                        "description": tool.description,
                                        "inputSchema": tool.inputSchema
                                    }
                                    if hasattr(tool, 'title') and tool.title is not None:
                                        clean_tool["title"] = tool.title
                                    if hasattr(tool, 'outputSchema') and tool.outputSchema is not None:
                                        clean_tool["outputSchema"] = tool.outputSchema
                                    clean_tools.append(clean_tool)

                            return {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "result": {
                                    "tools": clean_tools
                                }
                            }
                        except Exception as e:
                            return _error_response(message_id, -32603, f"Error listing tools: {str(e)}")

                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"tools": []}
                }

            elif method == "tools/call":
                if hasattr(self.mcp_server.server, 'request_handlers'):
                    handlers = self.mcp_server.server.request_handlers

                    from mcp.types import CallToolRequest
                    if CallToolRequest in handlers:
                        handler = handlers[CallToolRequest]
                        try:
                            request_obj = CallToolRequest(method="tools/call", params=params or {})
                            result = await handler(request_obj)

                            clean_content = []

                            content_list = None
                            if hasattr(result, 'content'):
                                content_list = result.content
                            elif hasattr(result, 'root') and hasattr(result.root, 'content'):
                                content_list = result.root.content
                            elif isinstance(result, dict) and 'content' in result:
                                content_list = result['content']

                            if content_list:
                                for content in content_list:
                                    clean_item = {
                                        "type": content.type,
                                        "text": content.text
                                    }
                                    clean_content.append(clean_item)

                            return {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "result": {
                                    "content": clean_content
                                }
                            }
                        except Exception as e:
                            return _error_response(message_id, -32603, f"Tool execution error: {str(e)}")

                return _error_response(message_id, -32601, "Tool call handler not found")

            elif method == "resources/list":
                if hasattr(self.mcp_server.server, 'request_handlers'):
                    handlers = self.mcp_server.server.request_handlers

                    from mcp.types import ListResourcesRequest
                    if ListResourcesRequest in handlers:
                        handler = handlers[ListResourcesRequest]
                        try:
                            request_obj = ListResourcesRequest(method="resources/list", params=params or {})
                            result = await handler(request_obj)

                            clean_resources = []

                            resources_list = None
                            if hasattr(result, 'resources'):
                                resources_list = result.resources
                            elif hasattr(result, 'root') and hasattr(result.root, 'resources'):
                                resources_list = result.root.resources
                            elif isinstance(result, dict) and 'resources' in result:
                                resources_list = result['resources']

                            if resources_list:
                                for resource in resources_list:
                                    clean_resource = {
                                        # Some MCP SDK implementations return AnyUrl for uri.
                                        # Convert to plain string to keep JSON serialization safe.
                                        "uri": str(resource.uri),
                                        "name": resource.name,
                                        "description": resource.description
                                    }
                                    clean_resources.append(clean_resource)

                            return {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "result": {
                                    "resources": clean_resources
                                }
                            }
                        except Exception as e:
                            return _error_response(message_id, -32603, f"Error listing resources: {str(e)}")

                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {"resources": []}
                }

            elif method == "resources/read":
                uri = params.get("uri")

                if hasattr(self.mcp_server.server, "request_handlers"):
                    handlers = self.mcp_server.server.request_handlers
                    from mcp.types import ReadResourceRequest

                    if ReadResourceRequest in handlers:
                        handler = handlers[ReadResourceRequest]
                        try:
                            request_obj = ReadResourceRequest(
                                method="resources/read",
                                params=params or {},
                            )
                            result = await handler(request_obj)

                            contents = None
                            if hasattr(result, "contents"):
                                contents = result.contents
                            elif hasattr(result, "root") and hasattr(result.root, "contents"):
                                contents = result.root.contents
                            elif isinstance(result, dict) and "contents" in result:
                                contents = result["contents"]

                            if contents is not None:
                                clean_contents = []
                                for content in contents:
                                    if isinstance(content, dict):
                                        safe_content = dict(content)
                                        if "uri" in safe_content:
                                            safe_content["uri"] = str(safe_content["uri"])
                                        # Ensure dict payload is JSON-serializable.
                                        try:
                                            json.dumps(safe_content)
                                        except TypeError:
                                            safe_content = json.loads(
                                                json.dumps(safe_content, default=str)
                                            )
                                        clean_contents.append(safe_content)
                                        continue

                                    clean_item = {
                                        "uri": str(getattr(content, "uri", "")),
                                        "mimeType": getattr(content, "mimeType", None),
                                    }
                                    if hasattr(content, "text"):
                                        clean_item["type"] = "text"
                                        clean_item["text"] = content.text
                                    elif hasattr(content, "blob"):
                                        clean_item["type"] = "blob"
                                        clean_item["blob"] = content.blob
                                    else:
                                        clean_item["type"] = "text"
                                        clean_item["text"] = str(content)
                                    clean_contents.append(clean_item)

                                return {
                                    "jsonrpc": "2.0",
                                    "id": message_id,
                                    "result": {"contents": clean_contents},
                                }
                        except Exception as e:
                            return _error_response(message_id, -32603, f"Error reading resource: {str(e)}")

                # Backward compatibility with older MCP SDK internals.
                if hasattr(self.mcp_server.server, "_read_resource_handlers"):
                    for handler in self.mcp_server.server._read_resource_handlers.values():
                        result = await handler(uri)
                        return {
                            "jsonrpc": "2.0",
                            "id": message_id,
                            "result": {"contents": [{"type": "text", "text": result}]},
                        }

                return _error_response(message_id, -32601, f"Resource not found: {uri}")

            else:
                return _error_response(message_id, -32601, f"Method not found: {method}")

        except Exception as e:
            return _error_response(message.get("id"), -32603, f"Internal error: {str(e)}")
