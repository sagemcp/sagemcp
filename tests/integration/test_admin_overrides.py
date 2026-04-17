"""Integration tests for generic connector MCP overrides."""

import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from sage_mcp.connectors.registry import connector_registry


def _create_tenant_and_connector(client: TestClient):
    tenant_slug = f"override-tenant-{uuid.uuid4().hex[:8]}"
    tenant_resp = client.post(
        "/api/v1/admin/tenants",
        json={
            "slug": tenant_slug,
            "name": "Override Tenant",
            "description": "Tenant for override tests",
            "contact_email": "override@example.com",
        },
    )
    assert tenant_resp.status_code == 201

    connector_resp = client.post(
        f"/api/v1/admin/tenants/{tenant_slug}/connectors",
        json={
            "connector_type": "github",
            "name": "Override Connector",
            "description": "Connector for override tests",
            "configuration": {},
        },
    )
    assert connector_resp.status_code == 201
    return tenant_slug, connector_resp.json()


class _FakePlugin:
    @property
    def requires_oauth(self) -> bool:
        return False

    async def get_tools(self, connector, oauth_cred=None):
        return []

    async def get_resources(self, connector, oauth_cred=None):
        return []

    async def get_resource_templates(self, connector, oauth_cred=None):
        return []

    async def get_prompts(self, connector, oauth_cred=None):
        return []

    async def execute_tool(self, connector, tool_name, arguments, oauth_cred=None):
        return f"upstream:{tool_name}:{arguments}"

    async def read_resource(self, connector, resource_path, oauth_cred=None):
        return f"upstream-resource:{resource_path}"

    async def get_prompt(self, connector, prompt_name, arguments=None, oauth_cred=None):
        raise AssertionError("Local prompt override should resolve before upstream prompt")


def _mcp_post(client: TestClient, tenant_slug: str, connector_id: str, body: dict):
    return client.post(
        f"/api/v1/{tenant_slug}/connectors/{connector_id}/mcp",
        json=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )


class TestAdminOverridesAPI:
    def test_admin_endpoints_disable_http_caching(self, client: TestClient):
        tenant_slug, connector = _create_tenant_and_connector(client)

        response = client.get(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides"
        )

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"
        assert response.headers["Surrogate-Control"] == "no-store"

    def test_mcp_http_endpoints_disable_http_caching(self, client: TestClient, monkeypatch):
        tenant_slug, connector = _create_tenant_and_connector(client)

        fake_plugin = _FakePlugin()
        monkeypatch.setattr(connector_registry, "get_connector", lambda _connector_type: fake_plugin)
        monkeypatch.setattr(
            connector_registry,
            "get_connector_for_config",
            AsyncMock(return_value=fake_plugin),
        )

        response = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {"jsonrpc": "2.0", "id": 0, "method": "resources/list"},
        )

        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["Expires"] == "0"
        assert response.headers["Surrogate-Control"] == "no-store"

    def test_crud_connector_overrides(self, client: TestClient):
        tenant_slug, connector = _create_tenant_and_connector(client)

        create_resp = client.post(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides",
            json={
                "target_kind": "prompt",
                "identifier": "triage_issue",
                "payload_text": "Triage issue {issue_number}",
                "metadata_json": {"description": "Prompt for issue triage"},
                "is_enabled": True,
            },
        )
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["identifier"] == "triage_issue"
        assert created["target_kind"] == "prompt"

        list_resp = client.get(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides"
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        patch_resp = client.patch(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides/{created['id']}",
            json={"payload_text": "Updated prompt"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["payload_text"] == "Updated prompt"

        get_resp = client.get(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides/{created['id']}"
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["payload_text"] == "Updated prompt"

        delete_resp = client.delete(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides/{created['id']}"
        )
        assert delete_resp.status_code == 204

        final_list = client.get(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides"
        )
        assert final_list.status_code == 200
        assert final_list.json() == []

    def test_mcp_uses_created_overrides_for_list_and_execution(
        self,
        client: TestClient,
        monkeypatch,
    ):
        tenant_slug, connector = _create_tenant_and_connector(client)

        fake_plugin = _FakePlugin()
        monkeypatch.setattr(connector_registry, "get_connector", lambda _connector_type: fake_plugin)
        monkeypatch.setattr(
            connector_registry,
            "get_connector_for_config",
            AsyncMock(return_value=fake_plugin),
        )

        override_payloads = [
            {
                "target_kind": "resource",
                "identifier": "docs://guide",
                "payload_text": "# Local Guide",
                "metadata_json": {"name": "guide", "mimeType": "text/markdown"},
            },
            {
                "target_kind": "prompt",
                "identifier": "triage_issue",
                "payload_text": "Triage issue now",
                "metadata_json": {"description": "Prompt description"},
            },
            {
                "target_kind": "tool",
                "identifier": "safe_tool",
                "payload_text": "",
                "metadata_json": {
                    "description": "Safe wrapper",
                    "targetToolName": "base_tool",
                    "inputSchema": {"type": "object", "properties": {}},
                    "fixedArguments": {"mode": "safe"},
                },
            },
        ]
        for payload in override_payloads:
            response = client.post(
                f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides",
                json=payload,
            )
            assert response.status_code == 201

        tools_list = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
        assert tools_list.status_code == 200
        assert tools_list.json()["result"]["tools"][0]["name"] == "safe_tool"

        tool_call = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "safe_tool", "arguments": {}},
            },
        )
        assert tool_call.status_code == 200
        assert "upstream:base_tool" in tool_call.json()["result"]["content"][0]["text"]
        assert "'mode': 'safe'" in tool_call.json()["result"]["content"][0]["text"]

        resources_list = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {"jsonrpc": "2.0", "id": 3, "method": "resources/list"},
        )
        assert resources_list.status_code == 200
        assert resources_list.json()["result"]["resources"][0]["uri"] == "docs://guide"

        resource_read = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "resources/read",
                "params": {"uri": "docs://guide"},
            },
        )
        assert resource_read.status_code == 200
        assert resource_read.json()["result"]["contents"][0]["text"] == "# Local Guide"

        prompts_list = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {"jsonrpc": "2.0", "id": 5, "method": "prompts/list"},
        )
        assert prompts_list.status_code == 200
        assert prompts_list.json()["result"]["prompts"][0]["name"] == "triage_issue"

        prompt_get = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "prompts/get",
                "params": {"name": "triage_issue", "arguments": {}},
            },
        )
        assert prompt_get.status_code == 200
        assert prompt_get.json()["result"]["messages"][0]["content"]["text"] == "Triage issue now"

    def test_patch_and_delete_resource_override_are_visible_to_followup_reads(
        self,
        client: TestClient,
        monkeypatch,
    ):
        tenant_slug, connector = _create_tenant_and_connector(client)

        fake_plugin = _FakePlugin()
        monkeypatch.setattr(connector_registry, "get_connector", lambda _connector_type: fake_plugin)
        monkeypatch.setattr(
            connector_registry,
            "get_connector_for_config",
            AsyncMock(return_value=fake_plugin),
        )

        create_resp = client.post(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides",
            json={
                "target_kind": "resource",
                "identifier": "docs://guide",
                "payload_text": "# Local Guide",
                "metadata_json": {
                    "name": "guide",
                    "description": "Initial guide",
                    "mimeType": "text/markdown",
                },
                "is_enabled": True,
            },
        )
        assert create_resp.status_code == 201
        created = create_resp.json()

        patch_resp = client.patch(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides/{created['id']}",
            json={
                "payload_text": "# Updated Guide",
                "metadata_json": {
                    "name": "guide",
                    "description": "Updated guide",
                    "mimeType": "text/markdown",
                },
            },
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["payload_text"] == "# Updated Guide"

        get_resp = client.get(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides/{created['id']}"
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["payload_text"] == "# Updated Guide"

        read_after_patch = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "resources/read",
                "params": {"uri": "docs://guide"},
            },
        )
        assert read_after_patch.status_code == 200
        assert read_after_patch.json()["result"]["contents"][0]["text"] == "# Updated Guide"

        delete_resp = client.delete(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides/{created['id']}"
        )
        assert delete_resp.status_code == 204

        list_after_delete = client.get(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides"
        )
        assert list_after_delete.status_code == 200
        assert list_after_delete.json() == []

        get_after_delete = client.get(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides/{created['id']}"
        )
        assert get_after_delete.status_code == 404

        resources_list_after_delete = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {"jsonrpc": "2.0", "id": 8, "method": "resources/list"},
        )
        assert resources_list_after_delete.status_code == 200
        assert resources_list_after_delete.json()["result"]["resources"] == []

    def test_resource_override_read_preserves_metadata_mime_type(
        self,
        client: TestClient,
        monkeypatch,
    ):
        tenant_slug, connector = _create_tenant_and_connector(client)

        fake_plugin = _FakePlugin()
        monkeypatch.setattr(connector_registry, "get_connector", lambda _connector_type: fake_plugin)
        monkeypatch.setattr(
            connector_registry,
            "get_connector_for_config",
            AsyncMock(return_value=fake_plugin),
        )

        create_resp = client.post(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides",
            json={
                "target_kind": "resource",
                "identifier": "docs://guide",
                "payload_text": "# Local Guide",
                "metadata_json": {
                    "name": "guide",
                    "description": "Guide",
                    "mimeType": "text/markdown",
                },
                "is_enabled": True,
            },
        )
        assert create_resp.status_code == 201

        resource_read = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "resources/read",
                "params": {"uri": "docs://guide"},
            },
        )
        assert resource_read.status_code == 200
        assert resource_read.json()["result"]["contents"][0]["mimeType"] == "text/markdown"

    def test_prompt_get_reports_missing_required_arguments_cleanly(
        self,
        client: TestClient,
        monkeypatch,
    ):
        tenant_slug, connector = _create_tenant_and_connector(client)

        fake_plugin = _FakePlugin()
        monkeypatch.setattr(connector_registry, "get_connector", lambda _connector_type: fake_plugin)
        monkeypatch.setattr(
            connector_registry,
            "get_connector_for_config",
            AsyncMock(return_value=fake_plugin),
        )

        create_resp = client.post(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides",
            json={
                "target_kind": "prompt",
                "identifier": "test_prompt",
                "payload_text": "Prompt for {id}",
                "metadata_json": {
                    "description": "Prompt requiring id",
                    "arguments": [{"name": "id", "required": True}],
                },
                "is_enabled": True,
            },
        )
        assert create_resp.status_code == 201

        prompt_get = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "prompts/get",
                "params": {"name": "test_prompt", "arguments": {}},
            },
        )
        assert prompt_get.status_code == 200
        assert "Missing required prompt arguments: id" in prompt_get.json()["error"]["message"]

    def test_create_prompt_override_rejects_malformed_argument_metadata(
        self,
        client: TestClient,
    ):
        tenant_slug, connector = _create_tenant_and_connector(client)

        create_resp = client.post(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides",
            json={
                "target_kind": "prompt",
                "identifier": "bad_prompt",
                "payload_text": "Prompt body",
                "metadata_json": {
                    "arguments": [{"required": True}],
                },
                "is_enabled": True,
            },
        )

        assert create_resp.status_code == 422
        assert "name must be a non-empty string" in create_resp.json()["detail"]

    def test_create_prompt_override_infers_argument_metadata_from_payload(
        self,
        client: TestClient,
        monkeypatch,
    ):
        tenant_slug, connector = _create_tenant_and_connector(client)

        fake_plugin = _FakePlugin()
        monkeypatch.setattr(connector_registry, "get_connector", lambda _connector_type: fake_plugin)
        monkeypatch.setattr(
            connector_registry,
            "get_connector_for_config",
            AsyncMock(return_value=fake_plugin),
        )

        create_resp = client.post(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides",
            json={
                "target_kind": "prompt",
                "identifier": "inferred_prompt",
                "payload_text": "Prompt for {id}",
                "metadata_json": {
                    "description": "Prompt requiring inferred id",
                },
                "is_enabled": True,
            },
        )

        assert create_resp.status_code == 201
        assert create_resp.json()["metadata_json"]["arguments"] == [{"name": "id", "required": True}]

        prompts_list = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {"jsonrpc": "2.0", "id": 11, "method": "prompts/list"},
        )
        assert prompts_list.status_code == 200
        assert prompts_list.json()["result"]["prompts"][0]["arguments"] == [
            {"name": "id", "required": True}
        ]

        prompt_get = _mcp_post(
            client,
            tenant_slug,
            connector["id"],
            {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "prompts/get",
                "params": {"name": "inferred_prompt", "arguments": {}},
            },
        )
        assert prompt_get.status_code == 200
        assert "Missing required prompt arguments: id" in prompt_get.json()["error"]["message"]

    def test_create_prompt_override_does_not_persist_empty_arguments_metadata(
        self,
        client: TestClient,
    ):
        tenant_slug, connector = _create_tenant_and_connector(client)

        create_resp = client.post(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides",
            json={
                "target_kind": "prompt",
                "identifier": "plain_prompt",
                "payload_text": "Prompt body",
                "metadata_json": {
                    "description": "Prompt without variables",
                },
                "is_enabled": True,
            },
        )

        assert create_resp.status_code == 201
        assert create_resp.json()["metadata_json"] == {"description": "Prompt without variables"}

    def test_update_prompt_override_rejects_malformed_argument_metadata(
        self,
        client: TestClient,
    ):
        tenant_slug, connector = _create_tenant_and_connector(client)

        create_resp = client.post(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides",
            json={
                "target_kind": "prompt",
                "identifier": "good_prompt",
                "payload_text": "Prompt body",
                "metadata_json": {
                    "arguments": [{"name": "id", "required": True}],
                },
                "is_enabled": True,
            },
        )
        assert create_resp.status_code == 201
        created = create_resp.json()

        patch_resp = client.patch(
            f"/api/v1/admin/tenants/{tenant_slug}/connectors/{connector['id']}/overrides/{created['id']}",
            json={
                "metadata_json": {
                    "arguments": [{"name": 42}],
                },
            },
        )

        assert patch_resp.status_code == 422
        assert "name must be a non-empty string" in patch_resp.json()["detail"]
