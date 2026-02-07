"""Generic connector that wraps external MCP server processes."""

import asyncio
import json
import logging
import os
import shutil
from typing import Any, Dict, List, Optional

from mcp import types

from ..connectors.base import BaseConnector
from ..models.connector import Connector
from ..models.oauth_credential import OAuthCredential

logger = logging.getLogger(__name__)


class GenericMCPConnector(BaseConnector):
    """Wraps an external MCP server process with stdio communication.

    This connector enables SageMCP to host any external MCP server implementation
    (Python, Node.js, Go, etc.) by communicating over stdin/stdout using the
    MCP protocol.

    Key features:
    - Spawns external process with configurable command
    - JSON-RPC 2.0 communication over stdio
    - OAuth token injection via environment variables
    - Automatic process initialization
    - Error handling and process cleanup
    """

    def __init__(
        self,
        runtime_type: str,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
    ):
        """Initialize the generic MCP connector.

        Args:
            runtime_type: Type of runtime (external_python, external_nodejs, etc.)
            command: Command to execute (e.g., ["npx", "@modelcontextprotocol/server-github"])
            env: Environment variables to pass to the process
            working_dir: Working directory for the process
        """
        super().__init__()
        self.runtime_type = runtime_type
        self.command = command
        self.env = env or {}
        self.working_dir = working_dir
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 0
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._initialized = False
        self._read_task: Optional[asyncio.Task] = None
        self._stderr_task: Optional[asyncio.Task] = None
        self._stderr_buffer: List[str] = []
        self._stderr_buffer_max = 50

    @property
    def display_name(self) -> str:
        """Display name for this connector."""
        return f"External MCP Server ({self.runtime_type})"

    @property
    def requires_oauth(self) -> bool:
        """Whether this connector requires OAuth credentials."""
        # Most external MCP servers require OAuth, but this could be configurable
        return True

    async def start_process(
        self,
        tenant_id: str,
        connector_id: str,
        oauth_token: Optional[str] = None,
        tenant_config: Optional[Dict] = None,
    ):
        """Start the external MCP server process.

        Args:
            tenant_id: ID of the tenant
            connector_id: ID of the connector
            oauth_token: OAuth access token to inject
            tenant_config: Additional configuration from connector.configuration
        """
        if self.process and self.process.returncode is None:
            return  # Already running

        # Pre-validate that the command executable exists on PATH
        cmd_name = self.command[0]
        if not shutil.which(cmd_name):
            raise Exception(
                f"MCP server command '{cmd_name}' not found on PATH. "
                f"Ensure the runtime is installed (e.g., Node.js for npx, Python for uvx)."
            )

        # Prepare environment with SageMCP injections
        process_env = {
            **os.environ.copy(),  # Inherit system environment
            **self.env,  # User-defined environment variables
            # OAuth credentials
            "OAUTH_TOKEN": oauth_token or "",
            "ACCESS_TOKEN": oauth_token or "",  # Alternative name for compatibility
            # Tenant context
            "TENANT_ID": tenant_id,
            "CONNECTOR_ID": connector_id,
            # SageMCP-specific
            "SAGEMCP_MODE": "hosted",
            "SAGEMCP_API_BASE": os.getenv("BASE_URL", "http://localhost:8000"),
        }

        # Add user-defined config as environment variables
        if tenant_config:
            for key, value in tenant_config.items():
                # Convert config keys to uppercase environment variable format
                env_key = f"CONFIG_{key.upper()}"
                process_env[env_key] = str(value)

        # Start process
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=self.working_dir,
            )
        except Exception as e:
            raise Exception(f"Failed to start MCP server process: {str(e)}")

        # Start background tasks to read stdout and stderr
        self._read_task = asyncio.create_task(self._read_stdout())
        self._stderr_task = asyncio.create_task(self._read_stderr())

        # Adaptive startup wait: poll for process readiness
        # Fast poll (100ms) for the first second, then slow poll (500ms) up to 30s
        elapsed = 0.0
        while elapsed < 30.0:
            if self.process.returncode is not None:
                stderr_tail = "\n".join(self._stderr_buffer[-20:])
                msg = (
                    f"MCP server process died with code {self.process.returncode}\n"
                    f"stderr:\n{stderr_tail}"
                ) if stderr_tail else (
                    f"MCP server process died with code {self.process.returncode}"
                    f" (no stderr captured)"
                )
                raise Exception(msg)
            # Once we've waited at least 200ms, assume process is alive enough to proceed
            if elapsed >= 0.2:
                break
            interval = 0.1 if elapsed < 1.0 else 0.5
            await asyncio.sleep(interval)
            elapsed += interval

        # Initialize MCP session
        try:
            await self._initialize_mcp()
        except Exception as e:
            await self.stop_process()
            raise Exception(f"Failed to initialize MCP session: {str(e)}")

    async def _initialize_mcp(self):
        """Send MCP initialize request."""
        await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                "clientInfo": {"name": "SageMCP", "version": "1.0.0"},
            },
        )
        self._initialized = True

        # Send initialized notification
        await self._send_notification("notifications/initialized")

    async def _send_request(self, method: str, params: Dict) -> Dict:
        """Send JSON-RPC request and wait for response.

        Args:
            method: JSON-RPC method name
            params: Parameters for the method

        Returns:
            Result from the response

        Raises:
            Exception: If request fails or times out
        """
        self.request_id += 1
        request_id = str(self.request_id)

        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}

        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future

        # Send request
        await self._write_message(message)

        # Wait for response (with timeout)
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            if "error" in response:
                error = response["error"]
                error_msg = error.get("message", "Unknown error")
                raise Exception(f"MCP error: {error_msg}")
            return response.get("result", {})
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise Exception(f"MCP request timeout: {method}")

    async def _send_notification(self, method: str, params: Optional[Dict] = None):
        """Send JSON-RPC notification (no response expected).

        Args:
            method: JSON-RPC method name
            params: Optional parameters for the method
        """
        message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        await self._write_message(message)

    async def _write_message(self, message: Dict):
        """Write JSON-RPC message to process stdin.

        Args:
            message: JSON-RPC message to send

        Raises:
            Exception: If process not started or write fails
        """
        if not self.process or not self.process.stdin:
            raise Exception("Process not started")

        data = json.dumps(message) + "\n"
        try:
            self.process.stdin.write(data.encode())
            await self.process.stdin.drain()
        except Exception as e:
            raise Exception(f"Failed to write to MCP server: {str(e)}")

    async def _read_stdout(self):
        """Background task to read and parse stdout."""
        if not self.process or not self.process.stdout:
            return

        try:
            async for line in self.process.stdout:
                try:
                    line_str = line.decode().strip()
                    if not line_str:
                        continue

                    message = json.loads(line_str)

                    # Handle response to request
                    if "id" in message and message["id"] in self._pending_requests:
                        future = self._pending_requests.pop(message["id"])
                        if not future.done():
                            future.set_result(message)

                    # Handle notification from server
                    elif "method" in message:
                        # Log notifications (tools/listChanged, etc.)
                        pass  # Could log here if needed

                except json.JSONDecodeError:
                    # Not JSON, might be debug output
                    pass
                except Exception as e:
                    logger.error("Error processing MCP message: %s", e)
        except Exception as e:
            logger.error("Error reading stdout: %s", e)

    async def _read_stderr(self):
        """Background task to read and buffer stderr."""
        if not self.process or not self.process.stderr:
            return

        try:
            async for line in self.process.stderr:
                stderr_line = line.decode().strip()
                if stderr_line:
                    logger.warning("MCP stderr [%s]: %s", self.runtime_type, stderr_line)
                    if len(self._stderr_buffer) < self._stderr_buffer_max:
                        self._stderr_buffer.append(stderr_line)
        except Exception:
            pass

    async def get_tools(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Tool]:
        """Get tools from external MCP server.

        Args:
            connector: Connector configuration
            oauth_cred: OAuth credentials (optional)

        Returns:
            List of available tools
        """
        if not self._initialized:
            await self.start_process(
                tenant_id=str(connector.tenant_id),
                connector_id=str(connector.id),
                oauth_token=oauth_cred.access_token if oauth_cred else None,
                tenant_config=connector.configuration,
            )

        # Request tools from external server
        response = await self._send_request("tools/list", {})

        # Convert to MCP types
        tools = []
        for tool_data in response.get("tools", []):
            tools.append(
                types.Tool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    inputSchema=tool_data.get("inputSchema", {}),
                )
            )

        return tools

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Execute tool in external MCP server.

        Args:
            connector: Connector configuration
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            oauth_cred: OAuth credentials (optional)

        Returns:
            Tool execution result as string
        """
        if not self._initialized:
            await self.start_process(
                tenant_id=str(connector.tenant_id),
                connector_id=str(connector.id),
                oauth_token=oauth_cred.access_token if oauth_cred else None,
                tenant_config=connector.configuration,
            )

        # Call tool in external server
        response = await self._send_request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )

        # Format result
        content = response.get("content", [])
        if content and isinstance(content, list) and len(content) > 0:
            if isinstance(content[0], dict) and "text" in content[0]:
                return content[0]["text"]
            return json.dumps(content[0])

        return json.dumps(response)

    async def get_resources(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Resource]:
        """Get resources from external MCP server.

        Args:
            connector: Connector configuration
            oauth_cred: OAuth credentials (optional)

        Returns:
            List of available resources
        """
        if not self._initialized:
            await self.start_process(
                tenant_id=str(connector.tenant_id),
                connector_id=str(connector.id),
                oauth_token=oauth_cred.access_token if oauth_cred else None,
                tenant_config=connector.configuration,
            )

        response = await self._send_request("resources/list", {})

        resources = []
        for res_data in response.get("resources", []):
            resources.append(
                types.Resource(
                    uri=res_data["uri"],
                    name=res_data["name"],
                    description=res_data.get("description"),
                    mimeType=res_data.get("mimeType"),
                )
            )

        return resources

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Read resource from external MCP server.

        Args:
            connector: Connector configuration
            resource_path: Resource URI to read
            oauth_cred: OAuth credentials (optional)

        Returns:
            Resource content as string
        """
        if not self._initialized:
            await self.start_process(
                tenant_id=str(connector.tenant_id),
                connector_id=str(connector.id),
                oauth_token=oauth_cred.access_token if oauth_cred else None,
                tenant_config=connector.configuration,
            )

        response = await self._send_request("resources/read", {"uri": resource_path})

        contents = response.get("contents", [])
        if contents and isinstance(contents, list) and len(contents) > 0:
            if isinstance(contents[0], dict) and "text" in contents[0]:
                return contents[0]["text"]

        return json.dumps(response)

    async def stop_process(self):
        """Stop the external MCP server process."""
        if self.process:
            # Cancel background tasks
            if self._read_task:
                self._read_task.cancel()
            if self._stderr_task:
                self._stderr_task.cancel()

            # Terminate process gracefully
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown fails
                self.process.kill()
                await self.process.wait()
            except Exception:
                pass

            self.process = None
            self._initialized = False
            self._pending_requests.clear()
            self._stderr_buffer.clear()

    def __del__(self):
        """Cleanup on garbage collection."""
        if self.process and self.process.returncode is None:
            # Schedule cleanup (can't await in __del__)
            try:
                asyncio.create_task(self.stop_process())
            except RuntimeError:
                # Event loop might be closed
                pass
