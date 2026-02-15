"""Integration tests for admin tools endpoints with external connectors."""

import json
import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from mcp import types

from sage_mcp.connectors.registry import connector_registry


def _create_tenant_and_external_connector(client: TestClient):
    tenant_slug = f"external-tools-tenant-{uuid.uuid4().hex[:8]}"
    tenant_data = {
        "slug": tenant_slug,
        "name": "External Tools Tenant",
        "description": "Tenant for external tools tests",
        "contact_email": "external-tools@example.com",
    }
    tenant_resp = client.post("/api/v1/admin/tenants", json=tenant_data)
    assert tenant_resp.status_code == 201

    connector_data = {
        "connector_type": "custom",
        "name": "External MCP Connector",
        "description": "External MCP connector for tests",
        "runtime_type": "external_python",
        "runtime_command": '["uvx", "fake-mcp-server"]',
        "runtime_env": {},
        "configuration": {},
    }
    connector_resp = client.post(
        f"/api/v1/admin/tenants/{tenant_slug}/connectors",
        json=connector_data,
    )
    assert connector_resp.status_code == 201
    return tenant_slug, connector_resp.json()


class _FakeExternalPlugin:
    @property
    def requires_oauth(self) -> bool:
        return False

    async def get_tools(self, connector, oauth_cred=None):
        return [
            types.Tool(
                name="external_test_tool",
                description="Tool from fake external connector",
                inputSchema={"type": "object", "properties": {}},
            )
        ]


class TestAdminToolsExternalEndpoints:
    def test_list_tools_for_external_connector(self, client: TestClient, monkeypatch):
        tenant_slug, connector = _create_tenant_and_external_connector(client)

        resolver = AsyncMock(return_value=_FakeExternalPlugin())
        monkeypatch.setattr(connector_registry, "get_connector_for_config", resolver)

        response = client.get(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/tools"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["total"] == 1
        assert payload["tools"][0]["tool_name"] == "external_test_tool"
        assert payload["tools"][0]["is_enabled"] is True
        resolver.assert_awaited_once()

    def test_legacy_list_tools_endpoint_matches_tenant_scoped(self, client: TestClient, monkeypatch):
        tenant_slug, connector = _create_tenant_and_external_connector(client)

        resolver = AsyncMock(return_value=_FakeExternalPlugin())
        monkeypatch.setattr(connector_registry, "get_connector_for_config", resolver)

        scoped = client.get(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/tools"
        )
        legacy = client.get(f"/api/v1/admin/connectors/{connector['id']}/tools")

        assert scoped.status_code == 200
        assert legacy.status_code == 200
        assert json.loads(scoped.text) == json.loads(legacy.text)
