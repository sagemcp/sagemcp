"""Unit tests for MCPServer tool/resource routing behavior."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import AnyUrl, TypeAdapter

from sage_mcp.mcp.server import MCPServer
from sage_mcp.models.connector import ConnectorRuntimeType


def _connector(connector_type: str, runtime_type: ConnectorRuntimeType, is_enabled: bool = True):
    return SimpleNamespace(
        connector_type=SimpleNamespace(value=connector_type),
        runtime_type=runtime_type,
        is_enabled=is_enabled,
    )


def test_resolve_tool_target_single_connector_accepts_unprefixed_tool():
    server = MCPServer("tenant-a", "connector-a")
    conn = _connector("custom", ConnectorRuntimeType.EXTERNAL_NODEJS)
    server.connectors = [conn]

    resolved_conn, action = server._resolve_tool_target("list_workflows")

    assert resolved_conn is conn
    assert action == "list_workflows"


def test_resolve_tool_target_prefixed_tool_still_supported():
    server = MCPServer("tenant-a", "connector-a")
    conn = _connector("github", ConnectorRuntimeType.NATIVE)
    server.connectors = [conn]

    resolved_conn, action = server._resolve_tool_target("github_list_workflows")

    assert resolved_conn is conn
    assert action == "list_workflows"


def test_resolve_resource_target_single_external_connector_keeps_full_uri():
    server = MCPServer("tenant-a", "connector-a")
    conn = _connector("custom", ConnectorRuntimeType.EXTERNAL_NODEJS)
    server.connectors = [conn]

    resolved_conn, resource_arg = server._resolve_resource_target("n8n://workflows")

    assert resolved_conn is conn
    assert resource_arg == "n8n://workflows"


def test_resolve_resource_target_single_native_connector_uses_path_only():
    server = MCPServer("tenant-a", "connector-a")
    conn = _connector("github", ConnectorRuntimeType.NATIVE)
    server.connectors = [conn]

    resolved_conn, resource_arg = server._resolve_resource_target("workflows")

    assert resolved_conn is conn
    assert resource_arg == "workflows"


def test_resolve_resource_target_single_native_connector_rejects_unknown_scheme():
    server = MCPServer("tenant-a", "connector-a")
    conn = _connector("github", ConnectorRuntimeType.NATIVE)
    server.connectors = [conn]

    resolved_conn, resource_arg = server._resolve_resource_target("hass://entities")

    assert resolved_conn is None
    assert resource_arg is None


def test_resolve_resource_target_accepts_anyurl_for_external_connector():
    server = MCPServer("tenant-a", "connector-a")
    conn = _connector("custom", ConnectorRuntimeType.EXTERNAL_CUSTOM)
    server.connectors = [conn]

    any_url = TypeAdapter(AnyUrl).validate_python("hass://entities")
    resolved_conn, resource_arg = server._resolve_resource_target(any_url)

    assert resolved_conn is conn
    assert resource_arg == "hass://entities"


@pytest.mark.asyncio
async def test_increment_daily_tool_calls_retries_after_integrity_error(monkeypatch):
    server = MCPServer("tenant-a", "connector-a")

    class _Result:
        rowcount = 0

    class _Ctx:
        def __init__(self):
            self.execute = AsyncMock(side_effect=[_Result(), _Result()])
            self.commit = AsyncMock(side_effect=[Exception("integrity"), None])
            self.rollback = AsyncMock()
            self.add = Mock()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    ctx = _Ctx()

    class _IntegrityError(Exception):
        pass

    monkeypatch.setattr("sage_mcp.mcp.server.get_db_context", lambda: ctx)
    monkeypatch.setattr("sage_mcp.mcp.server.IntegrityError", _IntegrityError)
    ctx.commit = AsyncMock(side_effect=[_IntegrityError("race"), None])

    await server._increment_daily_tool_calls()

    assert ctx.add.call_count == 1
    assert ctx.rollback.await_count == 1
    assert ctx.execute.await_count == 2
    assert ctx.commit.await_count == 2
