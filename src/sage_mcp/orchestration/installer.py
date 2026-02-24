"""Installation workflow for MCP servers from registry."""

import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_context
from ..models.connector import Connector, ConnectorRuntimeType
from ..models.mcp_server_registry import (
    MCPInstallation,
    MCPServerRegistry,
    RuntimeType,
)
from .base import ContainerConfig
from .factory import get_orchestrator
from .image_builder import BuildConfig, ImageBuilder

logger = logging.getLogger(__name__)


class ServerInstaller:
    """Installs MCP servers from registry to tenant environments."""

    def __init__(self):
        """Initialize server installer."""
        self.orchestrator = get_orchestrator()
        self.image_builder = ImageBuilder()

    async def install_server(
        self,
        registry_id: UUID,
        tenant_id: UUID,
        config_overrides: Optional[Dict] = None
    ) -> tuple[bool, str]:
        """Install MCP server from registry to tenant.

        Workflow:
        1. Fetch server from registry
        2. Check if image exists, build if needed
        3. Create connector in database
        4. Deploy pod/container
        5. Create installation record
        6. Verify deployment

        Args:
            registry_id: Registry server ID
            tenant_id: Tenant ID
            config_overrides: Optional configuration overrides

        Returns:
            Tuple of (success, connector_id_or_error_message)
        """
        logger.info(f"Installing server {registry_id} for tenant {tenant_id}")

        async with get_db_context() as session:
            try:
                # 1. Fetch server from registry
                server = await self._get_registry_server(session, registry_id)
                if not server:
                    return False, f"Server {registry_id} not found in registry"

                # 2. Check/Build image
                image_name = await self._ensure_image(server)
                if not image_name:
                    return False, "Failed to build server image"

                # 3. Create connector in database
                connector = await self._create_connector(
                    session,
                    tenant_id,
                    server,
                    registry_id,
                    image_name,
                    config_overrides
                )
                # Flush to ensure connector has an ID before deployment
                await session.flush()

                # 4. Deploy container/pod
                success, message = await self._deploy_server(
                    server,
                    connector,
                    image_name,
                    config_overrides
                )

                if not success:
                    # Rollback: delete connector
                    await session.delete(connector)
                    await session.commit()
                    return False, f"Deployment failed: {message}"

                # 5. Create installation record
                await self._create_installation_record(
                    session,
                    registry_id,
                    tenant_id,
                    connector.id,
                    server.latest_version
                )

                await session.commit()

                logger.info(
                    f"Successfully installed server {server.name} "
                    f"for tenant {tenant_id} (connector_id={connector.id})"
                )

                return True, str(connector.id)

            except Exception as e:
                logger.error(f"Installation failed: {e}")
                await session.rollback()
                return False, str(e)

    async def uninstall_server(
        self,
        connector_id: UUID,
        tenant_id: UUID
    ) -> tuple[bool, str]:
        """Uninstall MCP server.

        Args:
            connector_id: Connector ID
            tenant_id: Tenant ID

        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Uninstalling connector {connector_id} for tenant {tenant_id}")

        async with get_db_context() as session:
            try:
                # Get connector
                result = await session.execute(
                    select(Connector).where(
                        Connector.id == connector_id,
                        Connector.tenant_id == tenant_id
                    )
                )
                connector = result.scalar_one_or_none()

                if not connector:
                    return False, "Connector not found"

                # Delete pod/container
                container_name = self._get_container_name(connector)
                namespace = self._get_namespace(tenant_id)

                success = await self.orchestrator.delete_container(
                    container_name,
                    namespace
                )

                if not success:
                    logger.warning(f"Failed to delete container {container_name}")

                # Delete installation record
                await session.execute(
                    update(MCPInstallation)
                    .where(MCPInstallation.connector_id == connector_id)
                    .values(status="uninstalled")
                )

                # Delete connector
                await session.delete(connector)
                await session.commit()

                logger.info(f"Successfully uninstalled connector {connector_id}")
                return True, "Server uninstalled successfully"

            except Exception as e:
                logger.error(f"Uninstallation failed: {e}")
                await session.rollback()
                return False, str(e)

    async def get_installation_status(
        self,
        connector_id: UUID,
        tenant_id: UUID
    ) -> Optional[Dict]:
        """Get installation status.

        Args:
            connector_id: Connector ID
            tenant_id: Tenant ID

        Returns:
            Status dict or None if not found
        """
        async with get_db_context() as session:
            # Get connector
            result = await session.execute(
                select(Connector).where(
                    Connector.id == connector_id,
                    Connector.tenant_id == tenant_id
                )
            )
            connector = result.scalar_one_or_none()

            if not connector:
                return None

            # Get container status
            container_name = self._get_container_name(connector)
            namespace = self._get_namespace(tenant_id)

            container_info = await self.orchestrator.get_container_status(
                container_name,
                namespace
            )

            # Get installation record
            result = await session.execute(
                select(MCPInstallation).where(
                    MCPInstallation.connector_id == connector_id
                )
            )
            installation = result.scalar_one_or_none()

            return {
                "connector_id": str(connector.id),
                "name": connector.name,
                "status": connector.status.value,
                "container_status": container_info.status.value if container_info else "unknown",
                "container_ip": container_info.pod_ip if container_info else None,
                "installed_version": installation.installed_version if installation else None,
                "installed_at": installation.installed_at.isoformat() if installation else None,
                "last_health_check": installation.last_health_check.isoformat() if installation and installation.last_health_check else None,
            }

    async def _get_registry_server(
        self,
        session: AsyncSession,
        registry_id: UUID
    ) -> Optional[MCPServerRegistry]:
        """Fetch server from registry."""
        result = await session.execute(
            select(MCPServerRegistry).where(MCPServerRegistry.id == registry_id)
        )
        return result.scalar_one_or_none()

    async def _ensure_image(self, server: MCPServerRegistry) -> Optional[str]:
        """Ensure Docker image exists for server.

        Args:
            server: Registry server

        Returns:
            Image name or None if failed
        """
        # Check if image already built/specified
        if server.docker_image:
            logger.info(f"Using existing image: {server.docker_image}")
            return server.docker_image

        # For Phase 1 MVP: Use generic base images instead of building custom ones
        # This avoids complexity of Kaniko/BuildKit and works in Docker environments
        logger.info(f"Using generic base image for {server.name} ({server.runtime_type.value})")

        # Map runtime to base image
        base_images = {
            RuntimeType.NODEJS: "node:18-alpine",
            RuntimeType.PYTHON: "python:3.11-slim",
            RuntimeType.GO: "golang:1.21-alpine",
            RuntimeType.RUST: "rust:1.75-slim",
            RuntimeType.BINARY: "alpine:latest",
        }

        image_name = base_images.get(server.runtime_type, "alpine:latest")

        # Update registry with base image for future reference
        async with get_db_context() as session:
            await session.execute(
                update(MCPServerRegistry)
                .where(MCPServerRegistry.id == server.id)
                .values(docker_image=image_name)
            )
            await session.commit()

        logger.info(f"Will use base image: {image_name}")
        return image_name

    async def _create_connector(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        server: MCPServerRegistry,
        registry_id: UUID,
        image_name: str,
        config_overrides: Optional[Dict]
    ) -> Connector:
        """Create connector in database."""
        connector = Connector(
            id=uuid4(),
            tenant_id=tenant_id,
            connector_type=self._map_connector_type(server.name),
            name=server.display_name or server.name,
            description=server.description,
            is_enabled=True,
            configuration={
                "image": image_name,
                "runtime_type": server.runtime_type.value,
                "source_url": server.source_url,
                "registry_id": str(registry_id),
                "installed_version": server.latest_version,
                **(config_overrides or {}),
            },
            runtime_type=self._map_runtime_type(server.runtime_type),
        )

        session.add(connector)
        return connector

    async def _deploy_server(
        self,
        server: MCPServerRegistry,
        connector: Connector,
        image_name: str,
        config_overrides: Optional[Dict]
    ) -> tuple[bool, str]:
        """Deploy server as container/pod."""
        try:
            container_name = self._get_container_name(connector)
            namespace = self._get_namespace(connector.tenant_id)

            # Generate installation command based on source type and runtime
            install_cmd = self._generate_install_command(server)

            config = ContainerConfig(
                name=container_name,
                image=image_name,
                # Use sh -c to run install + start commands
                command=["/bin/sh", "-c", install_cmd],
                env={
                    "MCP_SERVER_NAME": server.name,
                    "MCP_SOURCE_URL": server.source_url,
                    "NPM_PACKAGE": server.npm_package_name or "",
                    "TENANT_ID": str(connector.tenant_id),
                    "CONNECTOR_ID": str(connector.id),
                    **(config_overrides.get("env", {}) if config_overrides else {}),
                },
                labels={
                    "app": "sage-mcp-server",
                    "tenant-id": str(connector.tenant_id),
                    "connector-id": str(connector.id),
                    "registry-id": str(server.id),
                },
                cpu_request="100m",
                cpu_limit="500m",
                memory_request="128Mi",
                memory_limit="512Mi",
            )

            await self.orchestrator.create_container(config, namespace)
            return True, "Deployment successful"

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return False, str(e)

    def _generate_install_command(self, server: MCPServerRegistry) -> str:
        """Generate installation command for the MCP server.

        Args:
            server: Registry server

        Returns:
            Shell command to install and run the server
        """
        if server.runtime_type == RuntimeType.NODEJS:
            if server.npm_package_name:
                # NPM package installation
                return f"""
                    npm install -g {server.npm_package_name} && \
                    npx {server.npm_package_name}
                """
            else:
                # Git clone for GitHub sources
                return f"""
                    apk add --no-cache git && \
                    git clone {server.source_url} /app && \
                    cd /app && \
                    npm install && \
                    npm start
                """

        elif server.runtime_type == RuntimeType.PYTHON:
            if server.source_type.value == "npm":  # pypi package
                return f"""
                    pip install --no-cache-dir {server.name} && \
                    python -m {server.name.replace('-', '_')}
                """
            else:
                # Git clone for GitHub sources
                return f"""
                    apt-get update && apt-get install -y git && \
                    git clone {server.source_url} /app && \
                    cd /app && \
                    pip install --no-cache-dir . && \
                    python -m mcp_server
                """

        else:
            # For other runtimes, just keep container running for manual setup
            return "tail -f /dev/null"

    async def _create_installation_record(
        self,
        session: AsyncSession,
        registry_id: UUID,
        tenant_id: UUID,
        connector_id: UUID,
        version: Optional[str]
    ):
        """Create installation record."""
        installation = MCPInstallation(
            id=uuid4(),
            registry_id=registry_id,
            tenant_id=tenant_id,
            connector_id=connector_id,
            installed_version=version,
            status="active",
            installed_at=datetime.utcnow(),
        )
        session.add(installation)

    def _get_container_name(self, connector: Connector) -> str:
        """Generate container name."""
        return f"mcp-{connector.tenant_id}-{connector.id}"[:63]

    def _get_namespace(self, tenant_id: UUID) -> str:
        """Get namespace for tenant."""
        return f"sage-mcp-tenant-{str(tenant_id)[:8]}"

    def _map_connector_type(self, server_name: str):
        """Map server name to connector type."""
        from ..models.connector import ConnectorType
        # All marketplace servers use CUSTOM type for external MCP servers
        return ConnectorType.CUSTOM

    def _map_runtime_type(self, runtime_type: RuntimeType) -> ConnectorRuntimeType:
        """Map registry runtime type to connector runtime type."""
        mapping = {
            RuntimeType.NODEJS: ConnectorRuntimeType.EXTERNAL_NODEJS,
            RuntimeType.PYTHON: ConnectorRuntimeType.EXTERNAL_PYTHON,
            RuntimeType.GO: ConnectorRuntimeType.EXTERNAL_GO,
            RuntimeType.RUST: ConnectorRuntimeType.EXTERNAL_CUSTOM,
            RuntimeType.BINARY: ConnectorRuntimeType.EXTERNAL_CUSTOM,
        }
        return mapping.get(runtime_type, ConnectorRuntimeType.EXTERNAL_CUSTOM)
