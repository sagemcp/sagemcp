"""Unit tests for MCP transport prompt and resource-template support."""

from unittest.mock import AsyncMock

import pytest
from mcp import types
from mcp.types import ListPromptsRequest, ListResourceTemplatesRequest, ReadResourceRequest

from sage_mcp.mcp.transport import MCPTransport


@pytest.mark.asyncio
async def test_initialize_advertises_prompt_capability(monkeypatch):
    transport = MCPTransport("tenant-a", "connector-a")
    monkeypatch.setattr(transport, "initialize", AsyncMock(return_value=True))

    response = await transport.handle_http_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        }
    )

    assert response["result"]["capabilities"]["prompts"] == {"listChanged": True}


@pytest.mark.asyncio
async def test_prompts_list_serializes_prompt_models(monkeypatch):
    transport = MCPTransport("tenant-a", "connector-a")
    monkeypatch.setattr(transport, "initialize", AsyncMock(return_value=True))

    async def list_prompts_handler(_request):
        return types.ListPromptsResult(
            prompts=[
                types.Prompt(
                    name="triage_issue",
                    description="Triage a GitHub issue",
                    arguments=[types.PromptArgument(name="issue_number", required=True)],
                )
            ]
        )

    transport.mcp_server.server.request_handlers = {
        ListPromptsRequest: list_prompts_handler
    }

    response = await transport.handle_http_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "prompts/list",
            "params": {},
        }
    )

    assert response["result"]["prompts"][0]["name"] == "triage_issue"
    assert response["result"]["prompts"][0]["arguments"][0]["name"] == "issue_number"


@pytest.mark.asyncio
async def test_resource_templates_list_serializes_templates(monkeypatch):
    transport = MCPTransport("tenant-a", "connector-a")
    monkeypatch.setattr(transport, "initialize", AsyncMock(return_value=True))

    async def list_templates_handler(_request):
        return types.ListResourceTemplatesResult(
            resourceTemplates=[
                types.ResourceTemplate(
                    name="issue_summary",
                    uriTemplate="sagemcp://github/issues/{owner}/{repo}/{issue_number}",
                    description="Tool-backed issue summary",
                )
            ]
        )

    transport.mcp_server.server.request_handlers = {
        ListResourceTemplatesRequest: list_templates_handler
    }

    response = await transport.handle_http_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "resources/templates/list",
            "params": {},
        }
    )

    assert response["result"]["resourceTemplates"][0]["name"] == "issue_summary"
    assert response["result"]["resourceTemplates"][0]["uriTemplate"].startswith("sagemcp://")


@pytest.mark.asyncio
async def test_resources_read_wraps_plain_text_result(monkeypatch):
    transport = MCPTransport("tenant-a", "connector-a")
    monkeypatch.setattr(transport, "initialize", AsyncMock(return_value=True))

    async def read_resource_handler(_request):
        return "# Local Guide"

    transport.mcp_server.server.request_handlers = {
        ReadResourceRequest: read_resource_handler
    }

    response = await transport.handle_http_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {"uri": "docs://guide"},
        }
    )

    assert response["result"]["contents"][0]["uri"] == "docs://guide"
    assert response["result"]["contents"][0]["text"] == "# Local Guide"
