"""MCP Server implementation for multi-tenant support."""

import logging
from typing import Any, Dict, List, Optional

from mcp import types
from mcp.server import Server
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_context
from ..models.tenant import Tenant
from ..models.connector import Connector
from ..models.connector_tool_state import ConnectorToolState
from ..models.oauth_credential import OAuthCredential
from ..connectors.registry import connector_registry

logger = logging.getLogger(__name__)


class MCPServer:
    """Multi-tenant MCP server implementation."""

    def __init__(self, tenant_slug: str, connector_id: str = None, user_token: str = None):
        self.tenant_slug = tenant_slug
        self.connector_id = connector_id
        self.user_token = user_token  # User-provided OAuth token (optional)
        logger.debug(
            "MCPServer created - tenant: %s, connector: %s, has_user_token: %s",
            tenant_slug, connector_id, user_token is not None,
        )
        self.tenant: Optional[Tenant] = None
        self.connector: Optional[Connector] = None  # Single connector
        self.connectors: List[Connector] = []  # For backward compatibility, will contain single connector
        self.server = Server("sage-mcp")
        self._tool_states_cache: Optional[Dict[str, bool]] = None
        self._setup_handlers()

    async def initialize(self) -> bool:
        """Initialize the MCP server for a specific connector."""
        async with get_db_context() as session:
            # Load tenant
            tenant = await self._get_tenant(session, self.tenant_slug)
            if not tenant or not tenant.is_active:
                return False

            self.tenant = tenant

            # Load specific connector by ID
            if self.connector_id:
                connector = await self._get_connector_by_id(session, self.connector_id, tenant.id)
                if not connector or not connector.is_enabled:
                    return False

                self.connector = connector
                self.connectors = [connector]  # For backward compatibility with existing handlers

                # Pre-populate tool states cache
                await self._load_tool_states_cache(session, connector.id)
            else:
                # Fallback: Load all enabled connectors for this tenant (for backward compatibility)
                self.connectors = await self._get_tenant_connectors(session, tenant.id)

            return True

    async def _load_tool_states_cache(self, session: AsyncSession, connector_id):
        """Load tool states into cache during initialization."""
        result = await session.execute(
            select(ConnectorToolState.tool_name, ConnectorToolState.is_enabled)
            .where(ConnectorToolState.connector_id == connector_id)
        )
        self._tool_states_cache = {name: enabled for name, enabled in result.all()}
        logger.debug("Cached %d tool states", len(self._tool_states_cache))

    def refresh_tool_states(self):
        """Invalidate the tool states cache so it's reloaded on next access."""
        self._tool_states_cache = None

    def _setup_handlers(self):
        """Set up MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools based on tenant's connectors."""
            logger.debug("handle_list_tools called for tenant %s", self.tenant_slug)

            tools = []

            for connector in self.connectors:
                if not connector.is_enabled:
                    continue

                connector_tools = await self._get_connector_tools(connector)
                tools.extend(connector_tools)

            logger.debug("Returning %d total tools", len(tools))
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]] = None
        ) -> List[types.TextContent]:
            """Handle tool calls."""
            if not arguments:
                arguments = {}

            # Parse tool name to determine connector and action
            connector = None
            action = None

            # Try to match tool name against connector types (longest match first)
            sorted_connectors = sorted(self.connectors, key=lambda c: len(c.connector_type.value), reverse=True)

            for conn in sorted_connectors:
                if conn.is_enabled:
                    connector_prefix = conn.connector_type.value.lower() + "_"
                    if name.lower().startswith(connector_prefix):
                        connector = conn
                        action = name[len(connector_prefix):]
                        break

            if not connector or not action:
                return [types.TextContent(
                    type="text",
                    text=f"Connector not found or not enabled for tool: {name}"
                )]

            logger.info("Tool call: %s (connector=%s, action=%s)", name, connector.connector_type.value, action)

            # Execute the tool call
            try:
                result = await self._execute_tool(connector, action, arguments)
                return [types.TextContent(type="text", text=result)]
            except Exception as e:
                logger.error("Tool execution failed: %s — %s", name, str(e))
                return [types.TextContent(
                    type="text",
                    text=f"Error executing tool: {str(e)}"
                )]

        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """List available resources."""
            resources = []

            for connector in self.connectors:
                if not connector.is_enabled:
                    continue

                connector_resources = await self._get_connector_resources(connector)
                resources.extend(connector_resources)

            return resources

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read a specific resource."""
            try:
                scheme, path = uri.split("://", 1)

                connector = None
                for conn in self.connectors:
                    if conn.connector_type.value == scheme and conn.is_enabled:
                        connector = conn
                        break

                if not connector:
                    raise ValueError(f"Connector not found: {scheme}")

                return await self._read_connector_resource(connector, path)

            except Exception as e:
                raise ValueError(f"Error reading resource {uri}: {str(e)}")

    async def _get_tenant(self, session: AsyncSession, tenant_slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        result = await session.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        return result.scalar_one_or_none()

    async def _get_connector_by_id(self, session: AsyncSession, connector_id: str, tenant_id: str) -> Optional[Connector]:
        """Get a specific connector by ID."""
        import uuid

        try:
            connector_uuid = uuid.UUID(connector_id)
        except ValueError:
            return None

        result = await session.execute(
            select(Connector).where(
                Connector.id == connector_uuid,
                Connector.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def _get_tenant_connectors(self, session: AsyncSession, tenant_id: str) -> List[Connector]:
        """Get enabled connectors for a tenant."""
        result = await session.execute(
            select(Connector).where(
                Connector.tenant_id == tenant_id,
                Connector.is_enabled
            )
        )
        return list(result.scalars().all())

    async def _get_connector_tools(self, connector: Connector) -> List[types.Tool]:
        """Get tools for a specific connector, filtered by enabled state."""
        logger.debug("Getting tools for connector %s (%s)", connector.name, connector.connector_type.value)

        # Get OAuth credential first (needed for get_connector_for_config on external connectors)
        oauth_cred = None
        connector_plugin = connector_registry.get_connector(connector.connector_type)

        # For native connectors, check if oauth is needed before fetching
        needs_oauth = connector_plugin.requires_oauth if connector_plugin else True
        if needs_oauth:
            oauth_cred = await self._get_oauth_credential(connector.tenant_id, connector.connector_type.value)

        # Use async routing method that supports both native and external connectors
        connector_plugin = await connector_registry.get_connector_for_config(connector, oauth_cred)
        if not connector_plugin:
            logger.debug("No connector plugin found for %s", connector.connector_type.value)
            return []

        try:
            all_tools = await connector_plugin.get_tools(connector, oauth_cred)
            logger.debug("Got %d tools from connector", len(all_tools))

            # Use cached tool states if available, otherwise fetch from DB
            tool_states = self._tool_states_cache
            if tool_states is None:
                async with get_db_context() as session:
                    result = await session.execute(
                        select(ConnectorToolState.tool_name, ConnectorToolState.is_enabled)
                        .where(ConnectorToolState.connector_id == connector.id)
                    )
                    tool_states = {name: enabled for name, enabled in result.all()}
                    self._tool_states_cache = tool_states

            # Filter tools based on database state (default to enabled if no DB record)
            enabled_tools = [
                tool for tool in all_tools
                if tool_states.get(tool.name, True)
            ]

            logger.debug("Returning %d enabled tools (filtered from %d)", len(enabled_tools), len(all_tools))
            return enabled_tools
        except Exception as e:
            logger.error("Error getting tools for %s: %s", connector.connector_type.value, e, exc_info=True)
            return []

    async def _get_connector_resources(self, connector: Connector) -> List[types.Resource]:
        """Get resources for a specific connector."""
        oauth_cred = None
        connector_plugin = connector_registry.get_connector(connector.connector_type)
        needs_oauth = connector_plugin.requires_oauth if connector_plugin else True
        if needs_oauth:
            oauth_cred = await self._get_oauth_credential(connector.tenant_id, connector.connector_type.value)

        connector_plugin = await connector_registry.get_connector_for_config(connector, oauth_cred)
        if not connector_plugin:
            return []

        try:
            return await connector_plugin.get_resources(connector, oauth_cred)
        except Exception as e:
            logger.error("Error getting resources for %s: %s", connector.connector_type.value, e)
            return []

    async def _execute_tool(self, connector: Connector, action: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool action for a connector."""
        oauth_cred = None
        connector_plugin = connector_registry.get_connector(connector.connector_type)
        needs_oauth = connector_plugin.requires_oauth if connector_plugin else True
        if needs_oauth:
            oauth_cred = await self._get_oauth_credential(connector.tenant_id, connector.connector_type.value)

        logger.info("Executing tool %s on connector %s (has_oauth=%s)", action, connector.connector_type.value, oauth_cred is not None)

        connector_plugin = await connector_registry.get_connector_for_config(connector, oauth_cred)
        if not connector_plugin:
            return f"Connector plugin not found: {connector.connector_type.value}"

        try:
            return await connector_plugin.execute_tool(connector, action, arguments, oauth_cred)
        except Exception as e:
            logger.error("Tool %s on %s failed: %s", action, connector.connector_type.value, str(e))
            return f"Error executing tool: {str(e)}"

    async def _read_connector_resource(self, connector: Connector, path: str) -> str:
        """Read a resource from a connector."""
        oauth_cred = None
        connector_plugin = connector_registry.get_connector(connector.connector_type)
        needs_oauth = connector_plugin.requires_oauth if connector_plugin else True
        if needs_oauth:
            oauth_cred = await self._get_oauth_credential(connector.tenant_id, connector.connector_type.value)

        connector_plugin = await connector_registry.get_connector_for_config(connector, oauth_cred)
        if not connector_plugin:
            return f"Connector plugin not found: {connector.connector_type.value}"

        try:
            return await connector_plugin.read_resource(connector, path, oauth_cred)
        except Exception as e:
            return f"Error reading resource: {str(e)}"

    async def _get_oauth_credential(self, tenant_id: str, provider: str) -> Optional[OAuthCredential]:
        """Get OAuth credential for a tenant and provider.

        Priority order:
        1. User-provided token (passed in request) - if available, create temp credential
        2. Tenant-level credential (stored in database) - fallback option
        """
        logger.debug("Getting OAuth credential for provider=%s, tenant_id=%s", provider, tenant_id)

        # If user token provided, create a temporary OAuthCredential with it
        if self.user_token:
            logger.info("Using user-provided OAuth token for provider=%s (length=%d)", provider, len(self.user_token))
            temp_cred = OAuthCredential(
                provider=provider,
                tenant_id=tenant_id,
                provider_user_id="user_provided",
                access_token=self.user_token,
                token_type="Bearer",
                is_active=True,
                expires_at=None
            )
            return temp_cred

        # Fallback to tenant-level credential from database
        provider_lower = provider.lower()
        logger.info("No user token, querying DB for tenant-level credential: provider=%s", provider_lower)

        async with get_db_context() as session:
            from sqlalchemy import func

            result = await session.execute(
                select(OAuthCredential).where(
                    OAuthCredential.tenant_id == tenant_id,
                    func.lower(OAuthCredential.provider) == provider_lower,
                    OAuthCredential.is_active.is_(True)
                )
            )
            cred = result.scalar_one_or_none()
            logger.info("DB credential lookup: provider=%s result=%s", provider_lower, "found" if cred else "NOT_FOUND")
            return cred
