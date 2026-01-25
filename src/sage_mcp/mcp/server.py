"""MCP Server implementation for multi-tenant support."""

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


class MCPServer:
    """Multi-tenant MCP server implementation."""

    def __init__(self, tenant_slug: str, connector_id: str = None, user_token: str = None):
        self.tenant_slug = tenant_slug
        self.connector_id = connector_id
        self.user_token = user_token  # User-provided OAuth token (optional)
        self.tenant: Optional[Tenant] = None
        self.connector: Optional[Connector] = None  # Single connector
        self.connectors: List[Connector] = []  # For backward compatibility, will contain single connector
        self.server = Server("sage-mcp")
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
            else:
                # Fallback: Load all enabled connectors for this tenant (for backward compatibility)
                self.connectors = await self._get_tenant_connectors(session, tenant.id)

            return True

    def _setup_handlers(self):
        """Set up MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools based on tenant's connectors."""
            print(f"DEBUG: handle_list_tools called for tenant {self.tenant_slug}")
            print(f"DEBUG: Found {len(self.connectors)} connectors")

            tools = []

            for connector in self.connectors:
                print(f"DEBUG: Processing connector {connector.name} (enabled: {connector.is_enabled})")
                if not connector.is_enabled:
                    print(f"DEBUG: Skipping disabled connector {connector.name}")
                    continue

                connector_tools = await self._get_connector_tools(connector)
                tools.extend(connector_tools)

            print(f"DEBUG: Returning {len(tools)} total tools")
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]] = None
        ) -> List[types.TextContent]:
            """Handle tool calls."""
            if not arguments:
                arguments = {}

            # Parse tool name to determine connector and action
            # Expected format: connectortype_action (e.g., github_list_repositories, google_docs_list_documents)
            # We need to match against actual connector types since they may contain underscores
            connector = None
            action = None

            # Try to match tool name against connector types (longest match first)
            # Sort by length descending to match longer connector types first (e.g., "google_docs" before "google")
            sorted_connectors = sorted(self.connectors, key=lambda c: len(c.connector_type.value), reverse=True)

            for conn in sorted_connectors:
                if conn.is_enabled:
                    connector_prefix = conn.connector_type.value + "_"
                    if name.startswith(connector_prefix):
                        connector = conn
                        action = name[len(connector_prefix):]
                        break

            if not connector or not action:
                return [types.TextContent(
                    type="text",
                    text=f"Connector not found or not enabled for tool: {name}"
                )]

            # Execute the tool call
            try:
                result = await self._execute_tool(connector, action, arguments)
                return [types.TextContent(type="text", text=result)]
            except Exception as e:
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
            # Parse URI to determine connector and resource
            # Format: connector_type://resource_path
            try:
                scheme, path = uri.split("://", 1)

                # Find the appropriate connector
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
        from sqlalchemy import select

        result = await session.execute(
            select(Tenant).where(Tenant.slug == tenant_slug)
        )
        return result.scalar_one_or_none()

    async def _get_connector_by_id(self, session: AsyncSession, connector_id: str, tenant_id: str) -> Optional[Connector]:
        """Get a specific connector by ID."""
        from sqlalchemy import select
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
        from sqlalchemy import select

        result = await session.execute(
            select(Connector).where(
                Connector.tenant_id == tenant_id,
                Connector.is_enabled
            )
        )
        return list(result.scalars().all())

    async def _get_connector_tools(self, connector: Connector) -> List[types.Tool]:
        """Get tools for a specific connector, filtered by enabled state."""
        print(f"DEBUG: Getting tools for connector {connector.name} ({connector.connector_type.value})")

        # Use new routing method that supports both native and external connectors
        connector_plugin = connector_registry.get_connector_for_config(connector)
        if not connector_plugin:
            print(f"DEBUG: No connector plugin found for {connector.connector_type.value}")
            return []

        print(f"DEBUG: Found connector plugin: {connector_plugin.name}")

        # Get OAuth credentials if needed
        oauth_cred = None
        if connector_plugin.requires_oauth:
            print(f"DEBUG: Connector requires OAuth, fetching credentials for {connector.connector_type.value}")
            oauth_cred = await self._get_oauth_credential(connector.tenant_id, connector.connector_type.value)
            if oauth_cred:
                print(f"DEBUG: Found OAuth credential for {oauth_cred.provider}")
            else:
                print(f"DEBUG: No OAuth credential found for {connector.connector_type.value}")

        try:
            # Get all tools from connector plugin (source of truth)
            all_tools = await connector_plugin.get_tools(connector, oauth_cred)
            print(f"DEBUG: Got {len(all_tools)} tools from connector")

            # Fetch tool states from database
            async with get_db_context() as session:
                result = await session.execute(
                    select(ConnectorToolState.tool_name, ConnectorToolState.is_enabled)
                    .where(ConnectorToolState.connector_id == connector.id)
                )
                tool_states = {name: enabled for name, enabled in result.all()}

            print(f"DEBUG: Found {len(tool_states)} tool states in database")

            # Filter tools based on database state
            # Default to enabled if no DB record exists (fallback for new tools)
            enabled_tools = [
                tool for tool in all_tools
                if tool_states.get(tool.name, True)  # Default True if no DB record
            ]

            print(f"DEBUG: Returning {len(enabled_tools)} enabled tools (filtered from {len(all_tools)})")

            for tool in enabled_tools:
                print(f"DEBUG: Enabled tool: {tool.name}")

            return enabled_tools
        except Exception as e:
            print(f"Error getting tools for {connector.connector_type.value}: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _get_connector_resources(self, connector: Connector) -> List[types.Resource]:
        """Get resources for a specific connector."""
        # Use new routing method that supports both native and external connectors
        connector_plugin = connector_registry.get_connector_for_config(connector)
        if not connector_plugin:
            return []

        # Get OAuth credentials if needed
        oauth_cred = None
        if connector_plugin.requires_oauth:
            oauth_cred = await self._get_oauth_credential(connector.tenant_id, connector.connector_type.value)

        try:
            return await connector_plugin.get_resources(connector, oauth_cred)
        except Exception as e:
            print(f"Error getting resources for {connector.connector_type.value}: {e}")
            return []

    async def _execute_tool(self, connector: Connector, action: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool action for a connector."""
        # Use new routing method that supports both native and external connectors
        connector_plugin = connector_registry.get_connector_for_config(connector)
        if not connector_plugin:
            return f"Connector plugin not found: {connector.connector_type.value}"

        # Get OAuth credentials if needed
        oauth_cred = None
        if connector_plugin.requires_oauth:
            oauth_cred = await self._get_oauth_credential(connector.tenant_id, connector.connector_type.value)

        try:
            return await connector_plugin.execute_tool(connector, action, arguments, oauth_cred)
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    async def _read_connector_resource(self, connector: Connector, path: str) -> str:
        """Read a resource from a connector."""
        # Use new routing method that supports both native and external connectors
        connector_plugin = connector_registry.get_connector_for_config(connector)
        if not connector_plugin:
            return f"Connector plugin not found: {connector.connector_type.value}"

        # Get OAuth credentials if needed
        oauth_cred = None
        if connector_plugin.requires_oauth:
            oauth_cred = await self._get_oauth_credential(connector.tenant_id, connector.connector_type.value)

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
        # If user token provided, create a temporary OAuthCredential with it
        if self.user_token:
            # Create a temporary OAuthCredential object with the user's token
            # This avoids database lookup and uses the user's personal OAuth identity
            temp_cred = OAuthCredential(
                provider=provider,
                tenant_id=tenant_id,
                provider_user_id="user_provided",  # Placeholder for user-provided tokens
                access_token=self.user_token,
                token_type="Bearer",
                is_active=True,
                expires_at=None  # User tokens don't have expiration managed by us
            )
            return temp_cred

        # Fallback to tenant-level credential from database
        async with get_db_context() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(OAuthCredential).where(
                    OAuthCredential.tenant_id == tenant_id,
                    OAuthCredential.provider == provider,
                    OAuthCredential.is_active.is_(True)
                )
            )
            return result.scalar_one_or_none()
