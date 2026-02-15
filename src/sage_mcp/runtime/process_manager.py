"""Process manager for external MCP server lifecycle management."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select, update

from .generic_connector import GenericMCPConnector
from ..database.connection import get_db_context
from ..models.connector import Connector
from ..models.mcp_process import MCPProcess, ProcessStatus
from ..models.oauth_credential import OAuthCredential

logger = logging.getLogger(__name__)


class MCPProcessManager:
    """Singleton manager for all external MCP processes.

    Responsibilities:
    - Start and stop external MCP server processes
    - Track process states in database
    - Perform periodic health checks
    - Auto-restart failed processes
    - Cleanup on shutdown
    """

    def __init__(self):
        """Initialize the process manager."""
        self.processes: Dict[str, GenericMCPConnector] = {}  # key: tenant_id:connector_id
        self.health_check_interval = 30  # seconds
        self.protocol_probe_interval = 300  # seconds
        self.health_failure_threshold = 3
        self._health_state: Dict[str, Dict[str, Any]] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False

    def _get_key(self, tenant_id: str, connector_id: str) -> str:
        """Generate unique key for process.

        Args:
            tenant_id: Tenant ID
            connector_id: Connector ID

        Returns:
            Unique key string
        """
        return f"{tenant_id}:{connector_id}"

    @staticmethod
    def _coerce_uuid(value):
        """Best-effort UUID coercion for DB filters/assignments."""
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except Exception:
            return value

    @staticmethod
    def _infer_runtime_type(executable: str, configured_runtime_type: str) -> str:
        """Infer runtime type from executable name, fallback to configured value."""
        exec_name = os.path.basename(str(executable or "")).lower()
        if exec_name in {"npx", "node", "npm", "pnpm", "yarn"}:
            return "external_nodejs"
        if exec_name in {"python", "python3", "uvx", "uv", "pip", "pipx"}:
            return "external_python"
        return configured_runtime_type

    async def get_or_create(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> GenericMCPConnector:
        """Get existing process or start new one.

        Args:
            connector: Connector configuration
            oauth_cred: OAuth credentials (optional)

        Returns:
            GenericMCPConnector instance

        Raises:
            Exception: If process fails to start
        """
        key = self._get_key(str(connector.tenant_id), str(connector.id))

        # Return existing if healthy
        if key in self.processes:
            process = self.processes[key]
            if await self._is_healthy(key, process):
                return process
            else:
                # Unhealthy, restart
                await self.terminate(str(connector.tenant_id), str(connector.id))

        # Parse runtime command
        try:
            command = json.loads(connector.runtime_command) if connector.runtime_command else []
        except json.JSONDecodeError:
            raise Exception(f"Invalid runtime_command JSON: {connector.runtime_command}")

        if not isinstance(command, list) or not command:
            raise Exception("runtime_command is required for external MCP connectors")
        if not isinstance(command[0], str) or not command[0].strip():
            raise Exception("runtime_command must start with a non-empty executable name")
        detected_runtime_type = self._infer_runtime_type(
            command[0], connector.runtime_type.value
        )

        # Normalize package_path: treat empty strings as unset.
        working_dir = connector.package_path.strip() if connector.package_path else None
        if working_dir == "":
            working_dir = None

        # Create new process
        process = GenericMCPConnector(
            runtime_type=connector.runtime_type.value,
            command=command,
            env=connector.runtime_env or {},
            working_dir=working_dir,
        )

        # Start the process
        try:
            await process.start_process(
                tenant_id=str(connector.tenant_id),
                connector_id=str(connector.id),
                oauth_token=oauth_cred.access_token if oauth_cred else None,
                tenant_config=connector.configuration,
            )
        except Exception as e:
            # Update database with error
            await self._update_process_status(
                connector.tenant_id,
                connector.id,
                ProcessStatus.ERROR,
                error_message=str(e),
                runtime_type=detected_runtime_type,
            )
            raise

        # Store process
        self.processes[key] = process

        # Update database with running status
        await self._update_process_status(
            connector.tenant_id,
            connector.id,
            ProcessStatus.RUNNING,
            pid=process.process.pid if process.process else None,
            runtime_type=detected_runtime_type,
        )

        # Start health check task if not running
        if not self._health_check_task or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())

        return process

    async def terminate(self, tenant_id: str, connector_id: str):
        """Terminate external MCP server process.

        Args:
            tenant_id: Tenant ID
            connector_id: Connector ID
        """
        key = self._get_key(tenant_id, connector_id)
        if key in self.processes:
            process = self.processes[key]
            await process.stop_process()
            del self.processes[key]
            self._health_state.pop(key, None)

            # Update database
            await self._update_process_status(
                tenant_id, connector_id, ProcessStatus.STOPPED
            )

    async def terminate_all(self):
        """Terminate all external MCP server processes."""
        self._shutdown = True

        # Cancel health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Terminate all processes
        for key in list(self.processes.keys()):
            tenant_id, connector_id = key.split(":")
            await self.terminate(tenant_id, connector_id)

    async def _protocol_probe(self, process: GenericMCPConnector) -> None:
        """Run a lightweight MCP protocol-level probe."""
        try:
            await process._send_request("resources/list", {})
        except Exception:
            # Some servers may not implement resources. Fall back to tools list.
            await process._send_request("tools/list", {})

    async def _is_healthy(self, key: str, process: GenericMCPConnector) -> bool:
        """Check if process is healthy.

        Args:
            key: Process key (tenant_id:connector_id)
            process: GenericMCPConnector instance

        Returns:
            True if healthy, False otherwise
        """
        if not process.process or process.process.returncode is not None:
            return False

        loop = asyncio.get_running_loop()
        now = loop.time()
        state = self._health_state.setdefault(
            key,
            {"last_protocol_probe_at": 0.0, "consecutive_failures": 0},
        )

        # Cheap fast path: avoid expensive probes every interval.
        if (now - float(state["last_protocol_probe_at"])) < self.protocol_probe_interval:
            return True

        try:
            await asyncio.wait_for(self._protocol_probe(process), timeout=5.0)
            state["last_protocol_probe_at"] = now
            state["consecutive_failures"] = 0
            return True
        except Exception as e:
            state["last_protocol_probe_at"] = now
            state["consecutive_failures"] = int(state["consecutive_failures"]) + 1
            logger.warning(
                "Protocol probe failed for %s (%d/%d): %s",
                key,
                state["consecutive_failures"],
                self.health_failure_threshold,
                e,
            )
            return state["consecutive_failures"] < self.health_failure_threshold

    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.health_check_interval)

                for key, process in list(self.processes.items()):
                    if not await self._is_healthy(key, process):
                        tenant_id, connector_id = key.split(":")

                        # Get restart count from database
                        async with get_db_context() as session:
                            result = await session.execute(
                                select(MCPProcess).where(
                                    MCPProcess.tenant_id == tenant_id,
                                    MCPProcess.connector_id == connector_id,
                                )
                            )
                            mcp_process = result.scalar_one_or_none()
                            restart_count = (
                                mcp_process.restart_count if mcp_process else 0
                            )

                        # Check restart limit (max 3 restarts)
                        if restart_count >= 3:
                            # Too many restarts, mark as error
                            await self._update_process_status(
                                tenant_id,
                                connector_id,
                                ProcessStatus.ERROR,
                                error_message="Max restart limit reached (3)",
                            )
                            # Remove from active processes
                            await self.terminate(tenant_id, connector_id)
                            continue

                        # Attempt restart
                        try:
                            # Get connector and OAuth credentials
                            async with get_db_context() as session:
                                result = await session.execute(
                                    select(Connector).where(Connector.id == connector_id)
                                )
                                connector = result.scalar_one_or_none()

                                if not connector:
                                    await self.terminate(tenant_id, connector_id)
                                    continue

                                # Get OAuth credential
                                result = await session.execute(
                                    select(OAuthCredential).where(
                                        OAuthCredential.tenant_id == tenant_id,
                                        OAuthCredential.provider
                                        == connector.connector_type.value,
                                        OAuthCredential.is_active.is_(True),
                                    )
                                )
                                oauth_cred = result.scalar_one_or_none()

                            # Terminate old process
                            await self.terminate(tenant_id, connector_id)

                            # Update status to restarting
                            await self._update_process_status(
                                tenant_id,
                                connector_id,
                                ProcessStatus.RESTARTING,
                                restart_count=restart_count + 1,
                            )

                            # Start new process
                            await self.get_or_create(connector, oauth_cred)

                        except Exception as e:
                            # Restart failed
                            await self._update_process_status(
                                tenant_id,
                                connector_id,
                                ProcessStatus.ERROR,
                                error_message=f"Restart failed: {str(e)}",
                                restart_count=restart_count + 1,
                            )
                            await self.terminate(tenant_id, connector_id)

                    else:
                        # Update last health check time
                        tenant_id, connector_id = key.split(":")
                        async with get_db_context() as session:
                            await session.execute(
                                update(MCPProcess)
                                .where(
                                    MCPProcess.tenant_id == tenant_id,
                                    MCPProcess.connector_id == connector_id,
                                )
                                .values(last_health_check=datetime.utcnow())
                            )
                            await session.commit()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in health check loop: %s", e)

    async def _update_process_status(
        self,
        tenant_id: str,
        connector_id: str,
        status: ProcessStatus,
        pid: Optional[int] = None,
        error_message: Optional[str] = None,
        restart_count: Optional[int] = None,
        runtime_type: Optional[str] = None,
    ):
        """Update process status in database.

        Args:
            tenant_id: Tenant ID
            connector_id: Connector ID
            status: Process status
            pid: Process ID (optional)
            error_message: Error message (optional)
            restart_count: Restart count (optional)
            runtime_type: Runtime type label to persist (optional)
        """
        async with get_db_context() as session:
            tenant_uuid = self._coerce_uuid(tenant_id)
            connector_uuid = self._coerce_uuid(connector_id)

            # Check if record exists
            result = await session.execute(
                select(MCPProcess).where(
                    MCPProcess.tenant_id == tenant_uuid,
                    MCPProcess.connector_id == connector_uuid,
                )
            )
            mcp_process = result.scalar_one_or_none()

            if mcp_process:
                # Update existing record
                update_values = {"status": status}
                if pid is not None:
                    update_values["pid"] = pid
                elif status != ProcessStatus.RUNNING:
                    update_values["pid"] = None
                if error_message is not None:
                    update_values["error_message"] = error_message
                elif status in {
                    ProcessStatus.STARTING,
                    ProcessStatus.RUNNING,
                    ProcessStatus.RESTARTING,
                    ProcessStatus.STOPPED,
                }:
                    # Clear stale error after successful recovery/start/stop.
                    update_values["error_message"] = None
                if restart_count is not None:
                    update_values["restart_count"] = restart_count
                if runtime_type is not None:
                    update_values["runtime_type"] = runtime_type
                if status == ProcessStatus.RUNNING:
                    update_values["started_at"] = datetime.utcnow()
                    update_values["last_health_check"] = datetime.utcnow()

                await session.execute(
                    update(MCPProcess)
                    .where(
                        MCPProcess.tenant_id == tenant_uuid,
                        MCPProcess.connector_id == connector_uuid,
                    )
                    .values(**update_values)
                )
            else:
                # Create new record
                result = await session.execute(
                    select(Connector).where(Connector.id == connector_uuid)
                )
                connector = result.scalar_one_or_none()

                persisted_runtime_type = runtime_type or (
                    connector.runtime_type.value if connector else "external_custom"
                )

                new_process = MCPProcess(
                    connector_id=connector_uuid,
                    tenant_id=tenant_uuid,
                    pid=pid,
                    runtime_type=persisted_runtime_type,
                    status=status,
                    started_at=datetime.utcnow(),
                    last_health_check=(
                        datetime.utcnow()
                        if status == ProcessStatus.RUNNING
                        else None
                    ),
                    error_message=error_message,
                    restart_count=restart_count or 0,
                )
                session.add(new_process)

            await session.commit()


# Global singleton instance
process_manager = MCPProcessManager()
