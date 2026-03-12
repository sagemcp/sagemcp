"""Unit tests for ad-hoc migrations."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from sage_mcp.database.migrations import upgrade_add_connector_local_mcp_entities
from sage_mcp.models.base import Base
from sage_mcp.models.connector import Connector, ConnectorType
from sage_mcp.models.connector_mcp_override import ConnectorMCPOverride
from sage_mcp.models.tenant import Tenant


@pytest.mark.asyncio
async def test_upgrade_add_connector_local_mcp_entities_preserves_existing_rows():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        tenant = Tenant(
            id=uuid.uuid4(),
            slug="migration-tenant",
            name="Migration Tenant",
            is_active=True,
        )
        connector = Connector(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            connector_type=ConnectorType.GITHUB,
            name="Migration Connector",
            is_enabled=True,
            configuration={},
        )
        override = ConnectorMCPOverride(
            id=uuid.uuid4(),
            connector_id=connector.id,
            target_kind="prompt",
            identifier="triage_issue",
            payload_text="Triage {id}",
            metadata_json={"arguments": [{"name": "id", "required": True}]},
            is_enabled=True,
        )
        session.add_all([tenant, connector, override])
        await session.commit()

    await upgrade_add_connector_local_mcp_entities(engine)

    async with session_factory() as session:
        result = await session.execute(select(ConnectorMCPOverride))
        overrides = result.scalars().all()
        assert len(overrides) == 1
        assert overrides[0].identifier == "triage_issue"

    await engine.dispose()
