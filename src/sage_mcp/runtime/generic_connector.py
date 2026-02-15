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
        self._stdout_buffer = b""
        self._stdout_buffer_max = 1024 * 1024  # 1MB safety cap
        self._stdio_framing = "json_line"

    @staticmethod
    def _classify_stderr_level(line: str) -> int:
        """Infer appropriate log level for external process stderr lines."""
        lowered = line.lower()
        if "[debug]" in lowered or " debug " in lowered or lowered.startswith("debug:"):
            return logging.DEBUG
        if "traceback" in lowered or "[error]" in lowered or " error " in lowered or lowered.startswith("error:"):
            return logging.ERROR
        if "[warning]" in lowered or " warning " in lowered or lowered.startswith("warning:"):
            return logging.WARNING
        if "[info]" in lowered or " info " in lowered or lowered.startswith("info:"):
            return logging.INFO
        # Many MCP SDK/server loggers write normal operational logs to stderr.
        # Default to INFO to avoid false warning noise in UI.
        return logging.INFO

    @property
    def display_name(self) -> str:
        """Display name for this connector."""
        return f"External MCP Server ({self.runtime_type})"

    @property
    def description(self) -> str:
        """Connector description."""
        return (
            "Runs an external MCP server process over stdio and proxies "
            "tools/resources into SageMCP."
        )

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

        if not self.command:
            raise Exception("runtime_command is required for external MCP connectors")

        # Pre-validate that the command executable exists on PATH
        cmd_name = str(self.command[0]).strip()
        if not cmd_name:
            raise Exception("runtime_command must start with a non-empty executable name")

        resolved_cmd = shutil.which(cmd_name)
        if not shutil.which(cmd_name):
            raise Exception(
                f"MCP server command '{cmd_name}' not found on PATH. "
                f"Ensure the runtime is installed (e.g., Node.js for npx, Python for uvx)."
            )
        exec_command = [resolved_cmd, *self.command[1:]]
        exec_name = os.path.basename(resolved_cmd)

        # npx can block waiting for install confirmation in non-interactive mode.
        if exec_name == "npx":
            has_yes_flag = any(arg in ("-y", "--yes") for arg in exec_command[1:])
            if not has_yes_flag:
                exec_command.insert(1, "-y")

        # Normalize and validate working directory.
        cwd = self.working_dir.strip() if self.working_dir else None
        if cwd == "":
            cwd = None
        if cwd and not os.path.isdir(cwd):
            raise Exception(f"Configured package_path does not exist in container: '{cwd}'")

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

        # Ensure HOME and cache paths are writable in containers where appuser home
        # may not exist or may not be writable.
        home_dir = process_env.get("HOME")
        if not home_dir or not os.path.isdir(home_dir) or not os.access(home_dir, os.W_OK):
            process_env["HOME"] = "/tmp"
            home_dir = "/tmp"

        xdg_cache_home = process_env.get("XDG_CACHE_HOME") or os.path.join(home_dir, ".cache")
        process_env["XDG_CACHE_HOME"] = xdg_cache_home

        # uvx uses uv cache under HOME/XDG cache by default; force a writable cache path.
        if exec_name == "uvx" and "UV_CACHE_DIR" not in process_env:
            process_env["UV_CACHE_DIR"] = os.path.join(xdg_cache_home, "uv")

        # Add user-defined config as environment variables
        if tenant_config:
            for key, value in tenant_config.items():
                # Convert config keys to uppercase environment variable format
                env_key = f"CONFIG_{key.upper()}"
                process_env[env_key] = str(value)

        # Start process
        try:
            self.process = await asyncio.create_subprocess_exec(
                *exec_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=cwd,
            )
        except Exception as e:
            raise Exception(
                f"Failed to start MCP server process: {str(e)} "
                f"(command={exec_command}, cwd={cwd})"
            )

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
            await self._initialize_mcp(exec_name=exec_name)
        except Exception as e:
            await self.stop_process()
            raise Exception(f"Failed to initialize MCP session: {str(e)}")

    async def _initialize_mcp(self, exec_name: Optional[str] = None):
        """Send MCP initialize request."""
        timeout = 90.0 if exec_name == "npx" else 30.0
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
            "clientInfo": {"name": "SageMCP", "version": "1.0.0"},
        }
        try:
            await self._send_request("initialize", init_params, timeout=timeout)
        except Exception as e:
            # Some MCP servers require MCP stdio Content-Length framing.
            # Retry initialize once with header framing for compatibility.
            if self._stdio_framing == "json_line":
                logger.info(
                    "Retrying MCP initialize with content_length framing for %s after error: %s",
                    self.runtime_type,
                    e,
                )
                self._stdio_framing = "content_length"
                await self._send_request("initialize", init_params, timeout=timeout)
            else:
                raise
        self._initialized = True

        # Send initialized notification
        await self._send_notification("notifications/initialized")

    async def _send_request(self, method: str, params: Dict, timeout: float = 30.0) -> Dict:
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
            response = await asyncio.wait_for(future, timeout=timeout)
            if "error" in response:
                error = response["error"]
                error_msg = error.get("message", "Unknown error")
                raise Exception(f"MCP error: {error_msg}")
            return response.get("result", {})
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            stderr_tail = "\n".join(self._stderr_buffer[-20:])
            if stderr_tail:
                raise Exception(f"MCP request timeout: {method}\nstderr:\n{stderr_tail}")
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

        if self._stdio_framing == "json_line":
            data = (json.dumps(message) + "\n").encode("utf-8")
        else:
            payload = json.dumps(message).encode("utf-8")
            header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
            data = header + payload
        try:
            self.process.stdin.write(data)
            await self.process.stdin.drain()
        except Exception as e:
            raise Exception(f"Failed to write to MCP server: {str(e)}")

    def _process_incoming_message(self, message: Dict):
        """Handle parsed JSON-RPC messages from stdout."""
        # Handle response to request
        if "id" in message and message["id"] in self._pending_requests:
            future = self._pending_requests.pop(message["id"])
            if not future.done():
                future.set_result(message)
        # Handle notifications; keep silent by default.

    def _try_parse_stdout_frames(self):
        """Parse as many framed/line JSON messages as possible from buffer."""
        while self._stdout_buffer:
            buf = self._stdout_buffer.lstrip(b"\r\n")
            if buf is not self._stdout_buffer:
                self._stdout_buffer = buf
            if not self._stdout_buffer:
                return

            # MCP stdio framing path: Content-Length headers + JSON body
            lower = self._stdout_buffer.lower()
            if lower.startswith(b"content-length:"):
                sep = self._stdout_buffer.find(b"\r\n\r\n")
                sep_len = 4
                if sep == -1:
                    sep = self._stdout_buffer.find(b"\n\n")
                    sep_len = 2
                if sep == -1:
                    return
                headers_blob = self._stdout_buffer[:sep].decode("ascii", errors="replace")
                content_length = None
                for header_line in headers_blob.replace("\r\n", "\n").split("\n"):
                    if ":" not in header_line:
                        continue
                    key, value = header_line.split(":", 1)
                    if key.strip().lower() == "content-length":
                        try:
                            content_length = int(value.strip())
                        except ValueError:
                            content_length = None
                        break

                if content_length is None:
                    logger.error("Invalid MCP frame header: %s", headers_blob)
                    self._stdout_buffer = self._stdout_buffer[sep + sep_len:]
                    continue

                start = sep + sep_len
                end = start + content_length
                if len(self._stdout_buffer) < end:
                    return

                payload = self._stdout_buffer[start:end]
                self._stdout_buffer = self._stdout_buffer[end:]
                try:
                    self._process_incoming_message(json.loads(payload.decode("utf-8")))
                except Exception as e:
                    logger.error("Error processing framed stdout payload: %s", e)
                continue

            # Backward-compat path: line-delimited JSON
            newline_idx = self._stdout_buffer.find(b"\n")
            if newline_idx == -1:
                return

            line = self._stdout_buffer[:newline_idx].decode("utf-8", errors="replace").strip()
            self._stdout_buffer = self._stdout_buffer[newline_idx + 1:]

            if not line:
                continue
            try:
                self._process_incoming_message(json.loads(line))
            except json.JSONDecodeError:
                # Non-JSON stdout text: ignore.
                continue
            except Exception as e:
                logger.error("Error processing stdout line: %s", e)

    async def _read_stdout(self):
        """Background task to read and parse stdout."""
        if not self.process or not self.process.stdout:
            return

        try:
            while True:
                chunk = await self.process.stdout.read(4096)
                if not chunk:
                    break

                self._stdout_buffer += chunk
                if len(self._stdout_buffer) > self._stdout_buffer_max:
                    logger.error(
                        "MCP stdout buffer exceeded %d bytes without a complete frame; trimming",
                        self._stdout_buffer_max,
                    )
                    self._stdout_buffer = self._stdout_buffer[-self._stdout_buffer_max:]

                self._try_parse_stdout_frames()
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
                    logger.log(
                        self._classify_stderr_level(stderr_line),
                        "MCP process log [%s]: %s",
                        self.runtime_type,
                        stderr_line,
                    )
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
            self._stdout_buffer = b""

    def __del__(self):
        """Cleanup on garbage collection."""
        if self.process and self.process.returncode is None:
            # Schedule cleanup (can't await in __del__)
            try:
                asyncio.create_task(self.stop_process())
            except RuntimeError:
                # Event loop might be closed
                pass
