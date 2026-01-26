"""Admin API routes for tenant and connector management."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_serializer
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_db_session
from ..models.connector import Connector, ConnectorType, ConnectorRuntimeType
from ..models.connector_tool_state import ConnectorToolState
from ..models.mcp_process import MCPProcess
from ..models.tenant import Tenant
from ..connectors.registry import connector_registry
from ..runtime import process_manager

router = APIRouter()


class TenantCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    contact_email: Optional[str] = None


class TenantResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: Optional[str]
    is_active: bool
    contact_email: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectorCreate(BaseModel):
    connector_type: ConnectorType
    name: str
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    # Runtime configuration for external MCP servers
    runtime_type: ConnectorRuntimeType = ConnectorRuntimeType.NATIVE
    runtime_command: Optional[str] = None  # JSON array as string, e.g., '["npx", "@modelcontextprotocol/server-github"]'
    runtime_env: Optional[Dict[str, Any]] = None
    package_path: Optional[str] = None


class ConnectorResponse(BaseModel):
    id: UUID
    connector_type: ConnectorType
    name: str
    description: Optional[str]
    is_enabled: bool
    configuration: Optional[Dict[str, Any]]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    # Runtime configuration
    runtime_type: ConnectorRuntimeType
    runtime_command: Optional[str]
    runtime_env: Optional[Dict[str, Any]]
    package_path: Optional[str]

    @field_serializer('connector_type')
    def serialize_connector_type(self, connector_type: ConnectorType, _info):
        """Serialize connector_type as lowercase for compatibility with integration-service."""
        return connector_type.value.lower()

    class Config:
        from_attributes = True


class ToolStateResponse(BaseModel):
    """Response model for a single tool state."""
    tool_name: str
    is_enabled: bool
    description: Optional[str] = None


class ToolsListResponse(BaseModel):
    """Response model for listing all tools."""
    tools: List[ToolStateResponse]
    summary: Dict[str, int]  # e.g., {"total": 24, "enabled": 20, "disabled": 4}


class ToolToggleRequest(BaseModel):
    """Request model for toggling a tool."""
    is_enabled: bool


class BulkToolUpdateRequest(BaseModel):
    """Request model for bulk tool updates."""
    tool_name: str
    is_enabled: bool


class BulkToolUpdatesRequest(BaseModel):
    """Request model for multiple bulk tool updates."""
    updates: List[BulkToolUpdateRequest]


class ProcessStatusResponse(BaseModel):
    """Response model for external MCP process status."""
    connector_id: UUID
    tenant_id: UUID
    pid: Optional[int]
    runtime_type: str
    status: str  # ProcessStatus enum value
    started_at: datetime
    last_health_check: Optional[datetime]
    error_message: Optional[str]
    restart_count: int

    class Config:
        from_attributes = True


async def populate_tools_for_connector(connector: Connector, session: AsyncSession):
    """Populate all tools for a connector when it's first created.

    This fetches all available tools from the connector plugin and creates
    ConnectorToolState records for each one (all enabled by default).

    Args:
        connector: The connector instance
        session: Database session
    """
    # Get connector plugin instance
    connector_plugin = connector_registry.get_connector(connector.connector_type)

    if not connector_plugin:
        # Connector type not registered, skip tool population
        return

    try:
        # Get all tools from the connector plugin
        # Note: OAuth credential may not be configured yet, so we pass None
        tools = await connector_plugin.get_tools(connector, oauth_cred=None)

        # Create ConnectorToolState records for each tool (all enabled by default)
        for tool in tools:
            tool_state = ConnectorToolState(
                id=uuid.uuid4(),
                connector_id=connector.id,
                tool_name=tool.name,
                is_enabled=True  # Default: all tools enabled
            )
            session.add(tool_state)

        await session.commit()

    except Exception as e:
        # If tool population fails, log but don't fail the connector creation
        # The connector is still usable, tools just won't have explicit state records
        print(f"Warning: Failed to populate tools for connector {connector.id}: {e}")
        await session.rollback()


@router.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(
    tenant_data: TenantCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """Create a new tenant."""
    # Check if tenant slug already exists
    from sqlalchemy import select

    existing = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tenant slug already exists")

    # Create new tenant
    tenant = Tenant(
        slug=tenant_data.slug,
        name=tenant_data.name,
        description=tenant_data.description,
        contact_email=tenant_data.contact_email
    )

    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    return tenant


@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    session: AsyncSession = Depends(get_db_session)
):
    """List all tenants."""
    from sqlalchemy import select

    result = await session.execute(select(Tenant))
    tenants = result.scalars().all()

    return list(tenants)


@router.get("/tenants/{tenant_slug}", response_model=TenantResponse)
async def get_tenant(
    tenant_slug: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get a specific tenant."""
    from sqlalchemy import select

    result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return tenant


@router.post("/tenants/{tenant_slug}/connectors", response_model=ConnectorResponse, status_code=201)
async def create_connector(
    tenant_slug: str,
    connector_data: ConnectorCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """Create a new connector for a tenant."""
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Check if connector of this type already exists for this tenant
    # Only enforce uniqueness for built-in connectors, not CUSTOM connectors
    if connector_data.connector_type != ConnectorType.CUSTOM:
        existing_connector = await session.execute(
            select(Connector).where(
                Connector.tenant_id == tenant.id,
                Connector.connector_type == connector_data.connector_type.value
            )
        )
        if existing_connector.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"A {connector_data.connector_type.value} connector already exists for this tenant. Only one connector per type is allowed."
            )

    # Create connector
    connector = Connector(
        tenant_id=tenant.id,
        connector_type=connector_data.connector_type,
        name=connector_data.name,
        description=connector_data.description,
        configuration=connector_data.configuration,
        runtime_type=connector_data.runtime_type,
        runtime_command=connector_data.runtime_command,
        runtime_env=connector_data.runtime_env,
        package_path=connector_data.package_path
    )

    session.add(connector)

    try:
        await session.commit()
        await session.refresh(connector)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"A {connector_data.connector_type.value} connector already exists for this tenant. Only one connector per type is allowed."
        )

    # Auto-populate all tools for this connector (all enabled by default)
    await populate_tools_for_connector(connector, session)

    return connector


@router.get("/tenants/{tenant_slug}/connectors", response_model=List[ConnectorResponse])
async def list_connectors(
    tenant_slug: str,
    session: AsyncSession = Depends(get_db_session)
):
    """List connectors for a tenant."""
    from sqlalchemy import select

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connectors
    connector_result = await session.execute(
        select(Connector).where(Connector.tenant_id == tenant.id)
    )
    connectors = connector_result.scalars().all()

    return list(connectors)


@router.delete("/tenants/{tenant_slug}")
async def delete_tenant(
    tenant_slug: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Delete a tenant and all its connectors."""
    from sqlalchemy import select, delete

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Delete all connectors for this tenant first
    await session.execute(
        delete(Connector).where(Connector.tenant_id == tenant.id)
    )

    # Delete the tenant
    await session.execute(
        delete(Tenant).where(Tenant.id == tenant.id)
    )

    await session.commit()

    return {
        "message": (
            f"Tenant '{tenant_slug}' and all its connectors "
            "have been deleted"
        )
    }


@router.put("/tenants/{tenant_slug}", response_model=TenantResponse)
async def update_tenant(
    tenant_slug: str,
    tenant_data: TenantCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """Update a tenant."""
    from sqlalchemy import select, update

    # Check if tenant exists
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Update tenant
    await session.execute(
        update(Tenant)
        .where(Tenant.slug == tenant_slug)
        .values(
            name=tenant_data.name,
            description=tenant_data.description,
            contact_email=tenant_data.contact_email
        )
    )

    await session.commit()
    await session.refresh(tenant)

    return tenant


@router.get(
    "/tenants/{tenant_slug}/connectors/{connector_id}",
    response_model=ConnectorResponse
)
async def get_connector(
    tenant_slug: str,
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get a specific connector."""
    from sqlalchemy import select

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    return connector


@router.put(
    "/tenants/{tenant_slug}/connectors/{connector_id}",
    response_model=ConnectorResponse
)
async def update_connector(
    tenant_slug: str,
    connector_id: str,
    connector_data: ConnectorCreate,
    session: AsyncSession = Depends(get_db_session)
):
    """Update a connector."""
    from sqlalchemy import select, update

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Update connector
    await session.execute(
        update(Connector)
        .where(Connector.id == connector_id)
        .values(
            connector_type=connector_data.connector_type,
            name=connector_data.name,
            description=connector_data.description,
            configuration=connector_data.configuration
        )
    )

    await session.commit()
    await session.refresh(connector)

    return connector


@router.delete("/tenants/{tenant_slug}/connectors/{connector_id}")
async def delete_connector(
    tenant_slug: str,
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Delete a connector."""
    from sqlalchemy import select, delete

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Delete connector
    await session.execute(
        delete(Connector).where(Connector.id == connector_id)
    )

    await session.commit()

    return {
        "message": f"Connector '{connector.name}' has been deleted"
    }


@router.patch(
    "/tenants/{tenant_slug}/connectors/{connector_id}/toggle",
    response_model=ConnectorResponse
)
async def toggle_connector(
    tenant_slug: str,
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Toggle connector enabled/disabled status."""
    from sqlalchemy import select, update

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Toggle enabled status
    new_status = not connector.is_enabled
    await session.execute(
        update(Connector)
        .where(Connector.id == connector_id)
        .values(is_enabled=new_status)
    )

    await session.commit()
    await session.refresh(connector)

    return connector


# =====================================================
# Tool Management Endpoints
# =====================================================

@router.get(
    "/tenants/{tenant_slug}/connectors/{connector_id}/tools",
    response_model=ToolsListResponse
)
async def list_connector_tools(
    tenant_slug: str,
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """List all tools for a connector with their enabled/disabled state."""
    from sqlalchemy import select

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Get connector plugin to fetch tool definitions
    connector_plugin = connector_registry.get_connector(connector.connector_type)
    if not connector_plugin:
        raise HTTPException(status_code=404, detail="Connector plugin not found")

    # Get all tools from connector plugin (source of truth for definitions)
    try:
        all_tools = await connector_plugin.get_tools(connector, oauth_cred=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tools: {str(e)}")

    # Get tool states from database
    tool_states_result = await session.execute(
        select(ConnectorToolState).where(ConnectorToolState.connector_id == connector.id)
    )
    tool_states = {state.tool_name: state for state in tool_states_result.scalars().all()}

    # Build response
    tools_response = []
    enabled_count = 0
    disabled_count = 0

    for tool in all_tools:
        state = tool_states.get(tool.name)
        is_enabled = state.is_enabled if state else True  # Default to enabled

        if is_enabled:
            enabled_count += 1
        else:
            disabled_count += 1

        tools_response.append(ToolStateResponse(
            tool_name=tool.name,
            is_enabled=is_enabled,
            description=tool.description
        ))

    return ToolsListResponse(
        tools=tools_response,
        summary={
            "total": len(tools_response),
            "enabled": enabled_count,
            "disabled": disabled_count
        }
    )


@router.patch(
    "/tenants/{tenant_slug}/connectors/{connector_id}/tools/{tool_name}",
    response_model=ToolStateResponse
)
async def toggle_tool(
    tenant_slug: str,
    connector_id: str,
    tool_name: str,
    request: ToolToggleRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Toggle a specific tool's enabled/disabled state."""
    from sqlalchemy import select

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Get or create tool state
    tool_state_result = await session.execute(
        select(ConnectorToolState).where(
            ConnectorToolState.connector_id == connector.id,
            ConnectorToolState.tool_name == tool_name
        )
    )
    tool_state = tool_state_result.scalar_one_or_none()

    if tool_state:
        # Update existing state
        tool_state.is_enabled = request.is_enabled
    else:
        # Create new state
        tool_state = ConnectorToolState(
            id=uuid.uuid4(),
            connector_id=connector.id,
            tool_name=tool_name,
            is_enabled=request.is_enabled
        )
        session.add(tool_state)

    await session.commit()
    await session.refresh(tool_state)

    return ToolStateResponse(
        tool_name=tool_state.tool_name,
        is_enabled=tool_state.is_enabled
    )


@router.post(
    "/tenants/{tenant_slug}/connectors/{connector_id}/tools/bulk-update",
    response_model=Dict[str, Any]
)
async def bulk_update_tools(
    tenant_slug: str,
    connector_id: str,
    request: BulkToolUpdatesRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Bulk update multiple tools' enabled/disabled state."""
    from sqlalchemy import select

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Process each update
    updated_count = 0
    for update in request.updates:
        # Get or create tool state
        tool_state_result = await session.execute(
            select(ConnectorToolState).where(
                ConnectorToolState.connector_id == connector.id,
                ConnectorToolState.tool_name == update.tool_name
            )
        )
        tool_state = tool_state_result.scalar_one_or_none()

        if tool_state:
            tool_state.is_enabled = update.is_enabled
        else:
            tool_state = ConnectorToolState(
                id=uuid.uuid4(),
                connector_id=connector.id,
                tool_name=update.tool_name,
                is_enabled=update.is_enabled
            )
            session.add(tool_state)

        updated_count += 1

    await session.commit()

    return {
        "success": True,
        "updated_count": updated_count,
        "message": f"Updated {updated_count} tools"
    }


@router.post(
    "/tenants/{tenant_slug}/connectors/{connector_id}/tools/enable-all",
    response_model=Dict[str, Any]
)
async def enable_all_tools(
    tenant_slug: str,
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Enable all tools for a connector."""
    from sqlalchemy import select, update

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Update all tool states to enabled
    result = await session.execute(
        update(ConnectorToolState)
        .where(ConnectorToolState.connector_id == connector.id)
        .values(is_enabled=True)
    )

    await session.commit()

    return {
        "success": True,
        "updated_count": result.rowcount,
        "message": f"Enabled {result.rowcount} tools"
    }


@router.post(
    "/tenants/{tenant_slug}/connectors/{connector_id}/tools/disable-all",
    response_model=Dict[str, Any]
)
async def disable_all_tools(
    tenant_slug: str,
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Disable all tools for a connector."""
    from sqlalchemy import select, update

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Update all tool states to disabled
    result = await session.execute(
        update(ConnectorToolState)
        .where(ConnectorToolState.connector_id == connector.id)
        .values(is_enabled=False)
    )

    await session.commit()

    return {
        "success": True,
        "updated_count": result.rowcount,
        "message": f"Disabled {result.rowcount} tools"
    }


@router.post(
    "/tenants/{tenant_slug}/connectors/{connector_id}/tools/sync",
    response_model=Dict[str, Any]
)
async def sync_connector_tools(
    tenant_slug: str,
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Sync tools for a connector - detect new tools from code and remove orphaned tools.

    This endpoint:
    1. Fetches all tools from the connector plugin (source of truth)
    2. Compares with existing tool states in database
    3. Adds new tools (enabled by default)
    4. Removes orphaned tools (tools deleted from code)
    5. Returns a summary of changes
    """
    from sqlalchemy import select, delete

    # Get tenant
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.slug == tenant_slug)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.tenant_id == tenant.id
        )
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Get connector plugin
    connector_plugin = connector_registry.get_connector(connector.connector_type)
    if not connector_plugin:
        raise HTTPException(status_code=404, detail="Connector plugin not found")

    # Get all tools from connector plugin (source of truth)
    try:
        all_tools = await connector_plugin.get_tools(connector, oauth_cred=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tools: {str(e)}")

    code_tool_names = {tool.name for tool in all_tools}

    # Get existing tool states from database
    db_tools_result = await session.execute(
        select(ConnectorToolState).where(ConnectorToolState.connector_id == connector.id)
    )
    db_tools = {tool.tool_name: tool for tool in db_tools_result.scalars().all()}
    db_tool_names = set(db_tools.keys())

    # Find new tools (in code but not in DB)
    new_tool_names = code_tool_names - db_tool_names

    # Find orphaned tools (in DB but not in code)
    orphaned_tool_names = db_tool_names - code_tool_names

    # Add new tools to database (enabled by default)
    added_tools = []
    for tool_name in new_tool_names:
        tool_state = ConnectorToolState(
            id=uuid.uuid4(),
            connector_id=connector.id,
            tool_name=tool_name,
            is_enabled=True
        )
        session.add(tool_state)
        added_tools.append(tool_name)

    # Remove orphaned tools from database
    removed_tools = []
    if orphaned_tool_names:
        for tool_name in orphaned_tool_names:
            await session.execute(
                delete(ConnectorToolState).where(
                    ConnectorToolState.connector_id == connector.id,
                    ConnectorToolState.tool_name == tool_name
                )
            )
            removed_tools.append(tool_name)

    await session.commit()

    # Calculate unchanged count
    unchanged_count = len(code_tool_names & db_tool_names)

    return {
        "success": True,
        "added": added_tools,
        "removed": removed_tools,
        "unchanged": unchanged_count,
        "summary": f"Added {len(added_tools)} tools, removed {len(removed_tools)} tools, {unchanged_count} unchanged"
    }


# =====================================================
# External MCP Process Management Endpoints
# =====================================================

@router.get(
    "/connectors/{connector_id}/process/status",
    response_model=Optional[ProcessStatusResponse]
)
async def get_process_status(
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get the status of an external MCP server process."""
    from sqlalchemy import select

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(Connector.id == connector_id)
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Check if this is an external MCP connector
    if connector.runtime_type == ConnectorRuntimeType.NATIVE:
        raise HTTPException(
            status_code=400,
            detail="This connector is a native connector, not an external MCP server"
        )

    # Get process status from database
    process_result = await session.execute(
        select(MCPProcess).where(
            MCPProcess.connector_id == connector.id,
            MCPProcess.tenant_id == connector.tenant_id
        )
    )
    process = process_result.scalar_one_or_none()

    if not process:
        return None

    return ProcessStatusResponse(
        connector_id=process.connector_id,
        tenant_id=process.tenant_id,
        pid=process.pid,
        runtime_type=process.runtime_type,
        status=process.status.value,
        started_at=process.started_at,
        last_health_check=process.last_health_check,
        error_message=process.error_message,
        restart_count=process.restart_count
    )


@router.post("/connectors/{connector_id}/process/restart")
async def restart_process(
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Restart an external MCP server process."""
    from sqlalchemy import select

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(Connector.id == connector_id)
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Check if this is an external MCP connector
    if connector.runtime_type == ConnectorRuntimeType.NATIVE:
        raise HTTPException(
            status_code=400,
            detail="This connector is a native connector, not an external MCP server"
        )

    # Terminate the existing process
    try:
        await process_manager.terminate(str(connector.tenant_id), str(connector.id))
    except Exception as e:
        print(f"Warning: Failed to terminate process: {e}")

    # Process will be restarted on next request via process_manager.get_or_create()
    return {
        "success": True,
        "message": f"Process restart initiated for connector {connector.name}. "
                   "It will start on the next tool request."
    }


@router.delete("/connectors/{connector_id}/process")
async def terminate_process(
    connector_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Terminate an external MCP server process."""
    from sqlalchemy import select

    # Get connector
    connector_result = await session.execute(
        select(Connector).where(Connector.id == connector_id)
    )
    connector = connector_result.scalar_one_or_none()

    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    # Check if this is an external MCP connector
    if connector.runtime_type == ConnectorRuntimeType.NATIVE:
        raise HTTPException(
            status_code=400,
            detail="This connector is a native connector, not an external MCP server"
        )

    # Terminate the process
    try:
        await process_manager.terminate(str(connector.tenant_id), str(connector.id))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to terminate process: {str(e)}"
        )

    return {
        "success": True,
        "message": f"Process terminated for connector {connector.name}"
    }
