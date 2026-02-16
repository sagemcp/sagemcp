"""Database migration utilities."""

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

from ..models.base import Base
from ..models.connector_tool_state import ConnectorToolState
from ..models.mcp_process import MCPProcess
from ..models.mcp_server_registry import MCPServerRegistry, DiscoveryJob, MCPInstallation
from ..models.tool_usage_daily import ToolUsageDaily
from .connection import db_manager


async def create_tables(engine: AsyncEngine = None):
    """Create all database tables."""
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables(engine: AsyncEngine = None):
    """Drop all database tables."""
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def upgrade_add_connector_tool_states(engine: AsyncEngine = None):
    """Migration: Add connector_tool_states table for tool-level enable/disable.

    This migration adds a new table to store individual tool states within connectors.
    Safe to run on existing databases - checks if table exists first.
    """
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    async with engine.begin() as conn:
        # Check if table already exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'connector_tool_states')"
        ))
        table_exists = result.scalar()

        if not table_exists:
            # Create only the connector_tool_states table
            await conn.run_sync(
                lambda sync_conn: ConnectorToolState.__table__.create(
                    sync_conn, checkfirst=True
                )
            )
            print("✓ Created connector_tool_states table")
        else:
            print("✓ connector_tool_states table already exists")


async def upgrade_add_external_mcp_runtime(engine: AsyncEngine = None):
    """Migration: Add external MCP runtime support to connectors table.

    This migration adds columns for external MCP server configuration:
    - runtime_type: Execution mode (native, external_python, external_nodejs, etc.)
    - runtime_command: Command to execute external MCP server
    - runtime_env: Environment variables for external MCP server
    - package_path: Working directory for external MCP server

    Also creates mcp_processes table for tracking external process states.
    Safe to run on existing databases - checks if columns/tables exist first.
    """
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    async with engine.begin() as conn:
        # Check if runtime_type column exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'connectors' "
            "AND column_name = 'runtime_type')"
        ))
        runtime_type_exists = result.scalar()

        if not runtime_type_exists:
            # Add new columns to connectors table
            await conn.execute(text(
                "ALTER TABLE connectors "
                "ADD COLUMN runtime_type VARCHAR(50) DEFAULT 'native' NOT NULL, "
                "ADD COLUMN runtime_command TEXT, "
                "ADD COLUMN runtime_env TEXT, "
                "ADD COLUMN package_path TEXT"
            ))

            # Create index on runtime_type
            await conn.execute(text(
                "CREATE INDEX ix_connectors_runtime_type ON connectors (runtime_type)"
            ))

            print("✓ Added external MCP runtime columns to connectors table")
        else:
            print("✓ External MCP runtime columns already exist")

        # Check if mcp_processes table exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'mcp_processes')"
        ))
        table_exists = result.scalar()

        if not table_exists:
            # Create mcp_processes table
            await conn.run_sync(
                lambda sync_conn: MCPProcess.__table__.create(
                    sync_conn, checkfirst=True
                )
            )
            print("✓ Created mcp_processes table")
        else:
            print("✓ mcp_processes table already exists")


async def upgrade_add_custom_connector_type(engine: AsyncEngine = None):
    """Migration: Add CUSTOM to ConnectorType enum.

    This allows external MCP servers to use the CUSTOM connector type.
    Safe to run on existing databases - checks if enum value exists first.
    """
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    async with engine.begin() as conn:
        # First check if the enum type exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connectortype')"
        ))
        enum_exists = result.scalar()

        if not enum_exists:
            print("✓ connectortype enum doesn't exist yet (will be created with tables)")
            return

        # Check if 'custom' already exists in the enum
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_enum e "
            "JOIN pg_type t ON e.enumtypid = t.oid "
            "WHERE t.typname = 'connectortype' AND e.enumlabel = 'custom')"
        ))
        custom_exists = result.scalar()

        if not custom_exists:
            # Add 'custom' to the enum
            await conn.execute(text(
                "ALTER TYPE connectortype ADD VALUE 'custom'"
            ))
            print("✓ Added 'custom' to connectortype enum")
        else:
            print("✓ 'custom' already exists in connectortype enum")


async def upgrade_add_runtime_type_values(engine: AsyncEngine = None):
    """Migration: Add all ConnectorRuntimeType values to enum.

    Adds external_python, external_nodejs, external_go, external_custom values.
    Safe to run on existing databases - checks if each value exists first.
    """
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    runtime_values = [
        'native', 'external_python', 'external_nodejs',
        'external_go', 'external_custom'
    ]

    async with engine.begin() as conn:
        # Check if enum type exists first
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connectorruntimetype')"
        ))
        enum_exists = result.scalar()

        if not enum_exists:
            # Create the enum type with all values
            values_str = "', '".join(runtime_values)
            await conn.execute(text(
                "CREATE TYPE connectorruntimetype AS ENUM ('" + values_str + "')"
            ))
            print("✓ Created connectorruntimetype enum with all values")
            return

        # Enum exists, add missing values
        for value in runtime_values:
            # Check if value already exists in the enum
            result = await conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'connectorruntimetype' AND e.enumlabel = :value)"
            ), {"value": value})
            value_exists = result.scalar()

            if not value_exists:
                # Add value to the enum
                await conn.execute(text(
                    f"ALTER TYPE connectorruntimetype ADD VALUE '{value}'"
                ))
                print(f"✓ Added '{value}' to connectorruntimetype enum")
            else:
                print(f"✓ '{value}' already exists in connectorruntimetype enum")


async def upgrade_add_process_status_values(engine: AsyncEngine = None):
    """Migration: Add all ProcessStatus values to enum.

    Adds starting, running, stopped, error, restarting values.
    Safe to run on existing databases - checks if each value exists first.
    """
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    status_values = ['starting', 'running', 'stopped', 'error', 'restarting']

    async with engine.begin() as conn:
        # Check if enum type exists first
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'processstatus')"
        ))
        enum_exists = result.scalar()

        if not enum_exists:
            # Create the enum type with all values
            values_str = "', '".join(status_values)
            await conn.execute(text(
                "CREATE TYPE processstatus AS ENUM ('" + values_str + "')"
            ))
            print("✓ Created processstatus enum with all values")
            return

        # Enum exists, add missing values
        for value in status_values:
            # Check if value already exists in the enum
            result = await conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM pg_enum e "
                "JOIN pg_type t ON e.enumtypid = t.oid "
                "WHERE t.typname = 'processstatus' AND e.enumlabel = :value)"
            ), {"value": value})
            value_exists = result.scalar()

            if not value_exists:
                # Add value to the enum
                await conn.execute(text(
                    f"ALTER TYPE processstatus ADD VALUE '{value}'"
                ))
                print(f"✓ Added '{value}' to processstatus enum")
            else:
                print(f"✓ '{value}' already exists in processstatus enum")


async def upgrade_remove_connector_unique_constraint(engine: AsyncEngine = None):
    """Migration: Remove unique constraint on connector_type to allow multiple custom connectors.

    The unique constraint (tenant_id, connector_type) prevents multiple connectors
    of the same type per tenant. This is fine for built-in connectors (github, jira, etc.)
    but we need to allow multiple CUSTOM connectors per tenant.

    Safe to run on existing databases - checks if constraint exists first.
    """
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    async with engine.begin() as conn:
        # Check if constraint exists
        result = await conn.execute(text(
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE table_name = 'connectors' "
            "AND constraint_type = 'UNIQUE' "
            "AND constraint_name = 'uq_tenant_connector_type'"
        ))
        constraint_exists = result.scalar_one_or_none()

        if constraint_exists:
            # Drop the constraint
            await conn.execute(text(
                "ALTER TABLE connectors DROP CONSTRAINT uq_tenant_connector_type"
            ))
            print("✓ Dropped unique constraint uq_tenant_connector_type from connectors table")
        else:
            print("✓ Unique constraint uq_tenant_connector_type does not exist")


async def upgrade_add_mcp_server_registry(engine: AsyncEngine = None):
    """Migration: Add MCP Server Registry tables for discovery and marketplace.

    This migration adds three new tables:
    1. mcp_server_registry - Catalog of discovered MCP servers from NPM, GitHub, etc.
    2. discovery_jobs - Track background discovery job status
    3. mcp_installations - Track per-tenant MCP server installations

    Also adds new columns to connectors table:
    - registry_id: Link to mcp_server_registry for installed servers
    - installed_version: Track installed version

    Safe to run on existing databases - checks if tables/columns exist first.
    """
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    async with engine.begin() as conn:
        # Check if mcp_server_registry table exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'mcp_server_registry')"
        ))
        registry_exists = result.scalar()

        if not registry_exists:
            # Create mcp_server_registry table
            await conn.run_sync(
                lambda sync_conn: MCPServerRegistry.__table__.create(
                    sync_conn, checkfirst=True
                )
            )
            print("✓ Created mcp_server_registry table")
        else:
            print("✓ mcp_server_registry table already exists")

        # Check if discovery_jobs table exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'discovery_jobs')"
        ))
        jobs_exists = result.scalar()

        if not jobs_exists:
            # Create discovery_jobs table
            await conn.run_sync(
                lambda sync_conn: DiscoveryJob.__table__.create(
                    sync_conn, checkfirst=True
                )
            )
            print("✓ Created discovery_jobs table")
        else:
            print("✓ discovery_jobs table already exists")

        # Check if mcp_installations table exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = 'mcp_installations')"
        ))
        installations_exists = result.scalar()

        if not installations_exists:
            # Create mcp_installations table
            await conn.run_sync(
                lambda sync_conn: MCPInstallation.__table__.create(
                    sync_conn, checkfirst=True
                )
            )
            print("✓ Created mcp_installations table")
        else:
            print("✓ mcp_installations table already exists")

        # Add registry_id and installed_version columns to connectors table
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'connectors' "
            "AND column_name = 'registry_id')"
        ))
        registry_id_exists = result.scalar()

        if not registry_id_exists:
            await conn.execute(text(
                "ALTER TABLE connectors "
                "ADD COLUMN registry_id UUID, "
                "ADD COLUMN installed_version VARCHAR(50)"
            ))
            print("✓ Added registry_id and installed_version columns to connectors table")
        else:
            print("✓ registry_id column already exists in connectors table")


async def upgrade_add_missing_connector_types(engine: AsyncEngine = None):
    """Migration: Add missing ConnectorType enum values.

    The Python ConnectorType enum has grown to include google_calendar,
    google_sheets, gmail, google_slides, bitbucket, zoom, outlook, excel,
    powerpoint, copilot, claude_code, codex, cursor, windsurf — but the
    PostgreSQL connectortype enum was never updated.

    Safe to run on existing databases - checks each value individually.
    """
    if engine is None:
        if not db_manager.engine:
            db_manager.initialize()
        engine = db_manager.engine

    # All values that should exist in the enum (from ConnectorType)
    expected_values = [
        'github', 'gitlab', 'bitbucket',
        'google_docs', 'google_calendar', 'google_sheets', 'gmail', 'google_slides',
        'notion', 'confluence',
        'jira', 'linear',
        'slack', 'teams', 'discord', 'zoom',
        'outlook', 'excel', 'powerpoint',
        'copilot', 'claude_code', 'codex', 'cursor', 'windsurf',
        'custom',
    ]

    async with engine.begin() as conn:
        # Check if enum type exists
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'connectortype')"
        ))
        enum_exists = result.scalar()

        if not enum_exists:
            print("✓ connectortype enum doesn't exist yet (will be created with tables)")
            return

        # Get current enum values
        result = await conn.execute(text(
            "SELECT e.enumlabel FROM pg_enum e "
            "JOIN pg_type t ON e.enumtypid = t.oid "
            "WHERE t.typname = 'connectortype'"
        ))
        existing_values = {row[0] for row in result.fetchall()}

        added = 0
        for value in expected_values:
            if value not in existing_values:
                await conn.execute(text(
                    f"ALTER TYPE connectortype ADD VALUE '{value}'"
                ))
                print(f"✓ Added '{value}' to connectortype enum")
                added += 1

        if added == 0:
            print("✓ All connector types already exist in connectortype enum")
