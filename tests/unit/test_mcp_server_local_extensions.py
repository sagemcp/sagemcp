"""Unit tests for MCPServer local augmentation behavior."""

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from mcp import types
from mcp.types import GetPromptRequest, ListPromptsRequest, ReadResourceRequest

from sage_mcp.mcp.server import MCPServer
from sage_mcp.models.connector import ConnectorRuntimeType, ConnectorType


def _connector(connector_type: str, runtime_type: ConnectorRuntimeType):
    return SimpleNamespace(
        id="connector-1",
        tenant_id="tenant-1",
        name=f"{connector_type}-connector",
        connector_type=ConnectorType(connector_type),
        runtime_type=runtime_type,
        is_enabled=True,
    )


@dataclass
class _LocalResourceResult:
    handled: bool
    content: types.TextResourceContents | None = None


@pytest.mark.asyncio
async def test_execute_local_tool_tries_requested_name_before_stripped_action(monkeypatch):
    server = MCPServer("tenant-a", "connector-a")
    connector = _connector("custom", ConnectorRuntimeType.EXTERNAL_NODEJS)

    fake_catalog = SimpleNamespace(
        execute_virtual_tool=AsyncMock(
            side_effect=[
                SimpleNamespace(handled=False, result=None),
                SimpleNamespace(handled=True, result="local-result"),
            ]
        )
    )
    monkeypatch.setattr(server, "_get_local_catalog", lambda _connector: fake_catalog)
    monkeypatch.setattr(server, "_execute_tool", AsyncMock(return_value="upstream-result"))

    result = await server._execute_local_tool(
        connector,
        requested_name="custom_list_workflows",
        action="list_workflows",
        arguments={"limit": 5},
    )

    assert result == "local-result"
    assert fake_catalog.execute_virtual_tool.await_args_list[0].args[0] == "custom_list_workflows"
    assert fake_catalog.execute_virtual_tool.await_args_list[1].args[0] == "list_workflows"


@pytest.mark.asyncio
async def test_get_prompt_prefers_local_prompt(monkeypatch):
    server = MCPServer("tenant-a", "connector-a")
    server.connectors = [_connector("custom", ConnectorRuntimeType.EXTERNAL_NODEJS)]

    monkeypatch.setattr("sage_mcp.mcp.server.record_tool_call", lambda **kwargs: None)
    local_prompt = types.GetPromptResult(
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text="local prompt"),
            )
        ]
    )
    monkeypatch.setattr(server, "_get_local_prompt", AsyncMock(return_value=local_prompt))
    upstream_prompt = AsyncMock()
    monkeypatch.setattr(server, "_get_connector_prompt", upstream_prompt)

    handler = server.server.request_handlers[GetPromptRequest]
    result = await handler(
        GetPromptRequest(
            method="prompts/get",
            params={"name": "triage_issue", "arguments": {"issue_number": "97"}},
        )
    )

    assert result.root.messages[0].content.text == "local prompt"
    upstream_prompt.assert_not_called()


@pytest.mark.asyncio
async def test_list_prompts_returns_local_prompts_when_upstream_connector_is_unavailable(monkeypatch):
    server = MCPServer("tenant-a", "connector-a")
    connector = _connector("github", ConnectorRuntimeType.NATIVE)
    server.connectors = [connector]

    monkeypatch.setattr(
        "sage_mcp.mcp.server.connector_registry.get_connector",
        lambda _connector_type: SimpleNamespace(requires_oauth=True),
    )
    monkeypatch.setattr(
        "sage_mcp.mcp.server.connector_registry.get_connector_for_config",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(server, "_get_oauth_credential", AsyncMock(return_value=None))
    fake_catalog = SimpleNamespace(
        list_prompts=AsyncMock(
            return_value=[
                types.Prompt(name="triage_issue", description="Local prompt"),
            ]
        )
    )
    monkeypatch.setattr(server, "_get_local_catalog", lambda _connector: fake_catalog)

    handler = server.server.request_handlers[ListPromptsRequest]
    result = await handler(ListPromptsRequest(method="prompts/list", params={}))

    assert result.root.prompts[0].name == "triage_issue"


@pytest.mark.asyncio
async def test_read_resource_prefers_local_override_before_uri_routing(monkeypatch):
    server = MCPServer("tenant-a", "connector-a")
    connector = _connector("github", ConnectorRuntimeType.NATIVE)
    server.connectors = [connector]

    monkeypatch.setattr(
        server,
        "_read_local_resource",
        AsyncMock(return_value=SimpleNamespace(content="# Local Guide", mime_type="text/plain")),
    )
    upstream_read = AsyncMock(return_value="upstream resource")
    monkeypatch.setattr(server, "_read_connector_resource", upstream_read)

    handler = server.server.request_handlers[ReadResourceRequest]
    result = await handler(
        ReadResourceRequest(
            method="resources/read",
            params={"uri": "docs://guide"},
        )
    )

    assert result.root.contents[0].text == "# Local Guide"
    upstream_read.assert_not_called()


@pytest.mark.asyncio
async def test_read_resource_preserves_local_override_mime_type(monkeypatch):
    server = MCPServer("tenant-a", "connector-a")
    connector = _connector("github", ConnectorRuntimeType.NATIVE)
    server.connectors = [connector]

    fake_catalog = SimpleNamespace(
        read_local_resource=AsyncMock(
            return_value=_LocalResourceResult(
                handled=True,
                content=types.TextResourceContents(
                    uri="docs://guide",
                    mimeType="text/markdown",
                    text="# Local Guide",
                ),
            )
        )
    )
    monkeypatch.setattr(server, "_get_local_catalog", lambda _connector: fake_catalog)
    monkeypatch.setattr(server, "_read_connector_resource", AsyncMock(return_value="upstream resource"))

    handler = server.server.request_handlers[ReadResourceRequest]
    result = await handler(
        ReadResourceRequest(
            method="resources/read",
            params={"uri": "docs://guide"},
        )
    )

    assert result.root.contents[0].mimeType == "text/markdown"
