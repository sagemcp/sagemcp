"""MCP transport layer for HTTP and WebSocket connections."""

import asyncio
import json
from typing import Any, Dict

from fastapi import WebSocket, WebSocketDisconnect

from .server import MCPServer


class MCPTransport:
    """Transport layer for MCP communication."""

    def __init__(self, tenant_slug: str, connector_id: str = None, user_token: str = None):
        self.tenant_slug = tenant_slug
        self.connector_id = connector_id
        self.user_token = user_token  # User-provided OAuth token (optional)
        print(f"DEBUG [transport.py]: MCPTransport created - tenant: {tenant_slug}, connector: {connector_id}, has_user_token: {user_token is not None}")
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
                    await websocket.send_text(json.dumps({
                        "error": {"code": -32700, "message": "Parse error"}
                    }))
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                    }))

        except Exception as e:
            print(f"WebSocket error for tenant {self.tenant_slug}: {e}")
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
                    print(f"SSE message processing error: {e}")
                    await messages.put({
                        "error": f"Internal server error: {str(e)}",
                        "code": 1011
                    })

        except Exception as e:
            print(f"SSE error for tenant {self.tenant_slug}: {e}")
            await messages.put({
                "error": f"Internal server error: {str(e)}",
                "code": 1011
            })

    async def handle_http_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle single HTTP message for MCP protocol."""
        if not await self.initialize():
            return {
                "error": {
                    "code": -32001,
                    "message": "Tenant not found or inactive"
                }
            }

        try:
            # Handle different MCP message types
            method = message.get("method")
            message_id = message.get("id")
            params = message.get("params", {})

            # DEBUG: Log incoming message
            print(f"DEBUG: Received message: method={method}, id={message_id}, has_id_key={'id' in message}")

            # Handle notifications (messages with no id or id=null)
            # Per JSON-RPC spec, notifications don't expect responses, but Claude's
            # HTTP transport requires valid JSON-RPC responses with an id field
            if message_id is None or ('id' not in message):
                # Handle notification methods - return success acknowledgment
                # Use id=1 as a placeholder since notifications don't have ids but Claude requires one
                if method == "notifications/initialized":
                    # Client has finished initialization
                    return {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "result": {}
                    }
                elif method and method.startswith("notifications/"):
                    # Other notifications - acknowledge receipt
                    return {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "result": {}
                    }
                # If it's not a notification method but has null id, treat it as malformed
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request: missing id for non-notification method"
                        }
                    }

            if method == "initialize":
                # Handle initialization - use the client's protocol version
                client_protocol = params.get("protocolVersion", "2024-11-05")

                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "protocolVersion": client_protocol,  # Echo client's version
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
                # List tools using the request_handlers approach
                # Access the request handlers directly
                if hasattr(self.mcp_server.server, 'request_handlers'):
                    handlers = self.mcp_server.server.request_handlers

                    # Look for the ListToolsRequest handler
                    from mcp.types import ListToolsRequest
                    if ListToolsRequest in handlers:
                        handler = handlers[ListToolsRequest]
                        try:
                            # Create the request object
                            request_obj = ListToolsRequest(method="tools/list", params=params or {})
                            result = await handler(request_obj)

                            # Clean up the result to match MCP spec - remove null fields
                            clean_tools = []

                            # Try to get tools from the result
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
                                    # Only include non-null optional fields
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
                            return {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {
                                    "code": -32603,
                                    "message": f"Error listing tools: {str(e)}"
                                }
                            }

                # Fallback: empty tools list
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "tools": []
                    }
                }

            elif method == "tools/call":
                # Call a tool using request_handlers
                if hasattr(self.mcp_server.server, 'request_handlers'):
                    handlers = self.mcp_server.server.request_handlers

                    from mcp.types import CallToolRequest
                    if CallToolRequest in handlers:
                        handler = handlers[CallToolRequest]
                        try:
                            # Create the request object
                            request_obj = CallToolRequest(method="tools/call", params=params or {})
                            result = await handler(request_obj)

                            # Clean up the result format
                            clean_content = []

                            # Try to get content from the result
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
                            return {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {
                                    "code": -32603,
                                    "message": f"Tool execution error: {str(e)}"
                                }
                            }

                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": "Tool call handler not found"
                    }
                }

            elif method == "resources/list":
                # List resources using request_handlers
                if hasattr(self.mcp_server.server, 'request_handlers'):
                    handlers = self.mcp_server.server.request_handlers

                    from mcp.types import ListResourcesRequest
                    if ListResourcesRequest in handlers:
                        handler = handlers[ListResourcesRequest]
                        try:
                            request_obj = ListResourcesRequest(method="resources/list", params=params or {})
                            result = await handler(request_obj)

                            # Clean up the result format
                            clean_resources = []

                            # Try to get resources from the result
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
                                        "uri": resource.uri,
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
                            return {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {
                                    "code": -32603,
                                    "message": f"Error listing resources: {str(e)}"
                                }
                            }

                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "resources": []
                    }
                }

            elif method == "resources/read":
                # Read a resource
                uri = params.get("uri")

                if hasattr(self.mcp_server.server, '_read_resource_handlers'):
                    for handler in self.mcp_server.server._read_resource_handlers.values():
                        result = await handler(uri)
                        return {
                            "jsonrpc": "2.0",
                            "id": message_id,
                            "result": {
                                "contents": [{"type": "text", "text": result}]
                            }
                        }

                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": f"Resource not found: {uri}"
                    }
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
