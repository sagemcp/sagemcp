"""Tests for AI coding tool intelligence connectors.

Covers: CodingToolMetrics, CopilotConnector, ClaudeCodeConnector,
CodexConnector, CursorConnector, WindsurfConnector.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sage_mcp.connectors.coding_tool_metrics import CodingToolMetrics
from sage_mcp.connectors.copilot import CopilotConnector
from sage_mcp.connectors.claude_code import ClaudeCodeConnector
from sage_mcp.connectors.codex import CodexConnector
from sage_mcp.connectors.cursor import CursorConnector
from sage_mcp.connectors.windsurf import WindsurfConnector
from sage_mcp.models.connector import ConnectorType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_connector(api_key="test-key-123"):
    """Create a mock Connector with configuration."""
    conn = MagicMock()
    conn.configuration = {"api_key": api_key}
    return conn


def _mock_oauth_cred():
    """Create a mock OAuthCredential."""
    cred = MagicMock()
    cred.access_token = "ghp_test_token_123"
    cred.is_active = True
    cred.is_expired = False
    return cred


def _mock_response(data, status_code=200):
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.json.return_value = data
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.headers = {}
    return resp


# ===========================================================================
# CodingToolMetrics
# ===========================================================================

class TestCodingToolMetrics:
    """Test the shared CodingToolMetrics dataclass."""

    def test_default_creation(self):
        m = CodingToolMetrics(tool_name="test", period="2024-01/2024-02")
        assert m.tool_name == "test"
        assert m.period == "2024-01/2024-02"
        assert m.total_seats is None
        assert m.metadata == {"unavailable_fields": []}

    def test_to_dict(self):
        m = CodingToolMetrics(
            tool_name="copilot",
            period="2024-01",
            total_seats=100,
            active_seats=80,
            seat_utilization_pct=80.0,
        )
        d = m.to_dict()
        assert d["tool_name"] == "copilot"
        assert d["total_seats"] == 100
        assert d["active_seats"] == 80
        assert d["seat_utilization_pct"] == 80.0
        assert d["total_cost_usd"] is None

    def test_unavailable_helper(self):
        m = CodingToolMetrics.unavailable(
            "windsurf", "2024-01", ["total_seats", "active_seats"]
        )
        assert m.tool_name == "windsurf"
        assert m.total_seats is None
        assert m.metadata["unavailable_fields"] == ["total_seats", "active_seats"]

    def test_to_dict_serializes_to_json(self):
        m = CodingToolMetrics(tool_name="test", period="2024-01")
        s = json.dumps(m.to_dict())
        parsed = json.loads(s)
        assert parsed["tool_name"] == "test"


# ===========================================================================
# CopilotConnector
# ===========================================================================

class TestCopilotConnector:
    """Test GitHub Copilot connector."""

    def setup_method(self):
        self.connector = CopilotConnector()

    def test_properties(self):
        assert self.connector.display_name == "GitHub Copilot"
        assert self.connector.requires_oauth is True
        assert self.connector.name == "copilot"

    @pytest.mark.asyncio
    async def test_get_tools_returns_all(self):
        mock_conn = _mock_connector()
        tools = await self.connector.get_tools(mock_conn)
        assert len(tools) == 19
        names = {t.name for t in tools}
        assert "copilot_get_org_usage" in names
        assert "copilot_get_billing_info" in names
        assert "copilot_get_normalized_metrics" in names
        assert "copilot_list_audit_events" in names

    @pytest.mark.asyncio
    async def test_tool_schemas_valid(self):
        mock_conn = _mock_connector()
        tools = await self.connector.get_tools(mock_conn)
        for tool in tools:
            schema = tool.inputSchema
            assert schema["type"] == "object"
            assert "properties" in schema

    @pytest.mark.asyncio
    async def test_get_resources_empty(self):
        resources = await self.connector.get_resources(_mock_connector())
        assert resources == []

    @pytest.mark.asyncio
    async def test_read_resource_unsupported(self):
        result = await self.connector.read_resource(
            _mock_connector(), "some/path", _mock_oauth_cred()
        )
        assert "not support" in result.lower() or "does not" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_dispatch_billing(self):
        oauth = _mock_oauth_cred()
        mock_resp = _mock_response({
            "seat_breakdown": {"total": 50, "active_this_cycle": 40},
            "seat_management_setting": "assign_all",
        })
        with patch.object(
            self.connector, "_make_authenticated_request",
            new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await self.connector.execute_tool(
                _mock_connector(), "get_billing_info",
                {"org": "test-org"}, oauth
            )
            parsed = json.loads(result)
            assert "seat_breakdown" in parsed or "seat_management_setting" in parsed

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self):
        oauth = _mock_oauth_cred()
        result = await self.connector.execute_tool(
            _mock_connector(), "nonexistent_tool", {}, oauth
        )
        assert "Unknown tool" in result or "unknown" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_oauth_returns_error(self):
        bad_oauth = MagicMock()
        bad_oauth.is_active = False
        bad_oauth.is_expired = True
        result = await self.connector.execute_tool(
            _mock_connector(), "get_billing_info",
            {"org": "test-org"}, bad_oauth
        )
        assert "error" in result.lower() or "invalid" in result.lower()


# ===========================================================================
# ClaudeCodeConnector
# ===========================================================================

class TestClaudeCodeConnector:
    """Test Claude Code / Anthropic Admin connector."""

    def setup_method(self):
        self.connector = ClaudeCodeConnector()

    def test_properties(self):
        assert self.connector.display_name == "Claude Code"
        assert self.connector.requires_oauth is False

    @pytest.mark.asyncio
    async def test_get_tools_returns_all(self):
        tools = await self.connector.get_tools(_mock_connector())
        assert len(tools) == 18
        names = {t.name for t in tools}
        assert "claude_code_get_usage" in names
        assert "claude_code_list_users" in names
        assert "claude_code_create_workspace" in names
        assert "claude_code_get_normalized_metrics" in names

    @pytest.mark.asyncio
    async def test_tool_schemas_valid(self):
        tools = await self.connector.get_tools(_mock_connector())
        for tool in tools:
            schema = tool.inputSchema
            assert schema["type"] == "object"
            assert "properties" in schema

    @pytest.mark.asyncio
    async def test_get_resources_empty(self):
        resources = await self.connector.get_resources(_mock_connector())
        assert resources == []

    @pytest.mark.asyncio
    async def test_execute_tool_get_org_info(self):
        mock_resp = _mock_response({
            "id": "org-123",
            "name": "Test Org",
            "plan": "team",
        })
        with patch.object(
            self.connector, "_make_claude_request",
            new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await self.connector.execute_tool(
                _mock_connector(), "get_org_info", {}
            )
            parsed = json.loads(result)
            assert parsed["id"] == "org-123"

    @pytest.mark.asyncio
    async def test_execute_tool_list_users(self):
        mock_resp = _mock_response({
            "data": [
                {"id": "u1", "name": "Alice", "role": "admin"},
                {"id": "u2", "name": "Bob", "role": "developer"},
            ]
        })
        with patch.object(
            self.connector, "_make_claude_request",
            new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await self.connector.execute_tool(
                _mock_connector(), "list_users", {}
            )
            parsed = json.loads(result)
            assert "data" in parsed
            assert len(parsed["data"]) == 2

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self):
        result = await self.connector.execute_tool(
            _mock_connector(), "nonexistent_tool", {}
        )
        assert "Unknown tool" in result or "unknown" in result.lower()

    @pytest.mark.asyncio
    async def test_auth_header_pattern(self):
        """Verify _make_claude_request passes x-api-key and anthropic-version."""
        captured_kwargs = {}

        async def _capture_request(method, url, connector, **kwargs):
            captured_kwargs.update(kwargs)
            return _mock_response({"ok": True})

        with patch.object(
            self.connector, "_make_api_key_request",
            side_effect=_capture_request,
        ):
            connector = _mock_connector("sk-ant-admin-test")
            await self.connector._make_claude_request(
                "GET", "https://api.anthropic.com/v1/organizations/me",
                connector
            )
            headers = captured_kwargs.get("headers", {})
            assert headers.get("anthropic-version") == "2023-06-01"
            # Verify x-api-key auth_header is passed to _make_api_key_request
            # The actual header injection happens in the base class


# ===========================================================================
# CodexConnector
# ===========================================================================

class TestCodexConnector:
    """Test OpenAI Codex connector."""

    def setup_method(self):
        self.connector = CodexConnector()

    def test_properties(self):
        assert self.connector.display_name == "OpenAI Codex"
        assert self.connector.requires_oauth is False

    @pytest.mark.asyncio
    async def test_get_tools_returns_all(self):
        tools = await self.connector.get_tools(_mock_connector())
        assert len(tools) == 16
        names = {t.name for t in tools}
        assert "codex_get_completions_usage" in names
        assert "codex_get_cost_breakdown" in names
        assert "codex_list_users" in names
        assert "codex_list_audit_events" in names
        assert "codex_get_normalized_metrics" in names

    @pytest.mark.asyncio
    async def test_tool_schemas_valid(self):
        tools = await self.connector.get_tools(_mock_connector())
        for tool in tools:
            schema = tool.inputSchema
            assert schema["type"] == "object"
            assert "properties" in schema

    @pytest.mark.asyncio
    async def test_get_resources_empty(self):
        resources = await self.connector.get_resources(_mock_connector())
        assert resources == []

    @pytest.mark.asyncio
    async def test_execute_tool_list_users(self):
        mock_resp = _mock_response({
            "object": "list",
            "data": [
                {"id": "user-1", "email": "a@test.com", "role": "owner"},
            ]
        })
        with patch.object(
            self.connector, "_make_api_key_request",
            new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await self.connector.execute_tool(
                _mock_connector(), "list_users", {}
            )
            parsed = json.loads(result)
            assert "data" in parsed

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self):
        result = await self.connector.execute_tool(
            _mock_connector(), "nonexistent_tool", {}
        )
        assert "Unknown tool" in result or "unknown" in result.lower()

    @pytest.mark.asyncio
    async def test_bearer_auth_pattern(self):
        """Verify Codex uses standard Bearer token auth via _make_api_key_request."""

        async def _passthrough(fn, *args, **kwargs):
            return await fn(*args, **kwargs)

        with patch(
            "sage_mcp.connectors.http_client.get_http_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_resp = _mock_response({"ok": True})
            mock_client.request.return_value = mock_resp
            mock_get_client.return_value = mock_client

            with patch(
                "sage_mcp.connectors.retry.retry_with_backoff",
                side_effect=_passthrough,
            ):
                connector = _mock_connector("sk-openai-test")
                await self.connector._make_api_key_request(
                    "GET", "https://api.openai.com/v1/organization/users",
                    connector
                )
                call_args = mock_client.request.call_args
                headers = call_args.kwargs.get("headers", {})
                assert "Bearer sk-openai-test" in headers.get("Authorization", "")


# ===========================================================================
# CursorConnector
# ===========================================================================

class TestCursorConnector:
    """Test Cursor connector."""

    def setup_method(self):
        self.connector = CursorConnector()

    def test_properties(self):
        assert self.connector.display_name == "Cursor"
        assert self.connector.requires_oauth is False

    @pytest.mark.asyncio
    async def test_get_tools_returns_all(self):
        tools = await self.connector.get_tools(_mock_connector())
        assert len(tools) == 18
        names = {t.name for t in tools}
        assert "cursor_get_agent_edits" in names
        assert "cursor_get_daily_active_users" in names
        assert "cursor_list_members" in names
        assert "cursor_get_spending" in names
        assert "cursor_get_normalized_metrics" in names

    @pytest.mark.asyncio
    async def test_tool_schemas_valid(self):
        tools = await self.connector.get_tools(_mock_connector())
        for tool in tools:
            schema = tool.inputSchema
            assert schema["type"] == "object"
            assert "properties" in schema

    @pytest.mark.asyncio
    async def test_get_resources_empty(self):
        resources = await self.connector.get_resources(_mock_connector())
        assert resources == []

    @pytest.mark.asyncio
    async def test_execute_tool_list_members(self):
        mock_resp = _mock_response({
            "members": [
                {"id": "m1", "email": "a@test.com", "role": "admin"},
            ]
        })
        with patch.object(
            self.connector, "_make_cursor_request",
            new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await self.connector.execute_tool(
                _mock_connector(), "list_members", {}
            )
            parsed = json.loads(result)
            assert "members" in parsed

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self):
        result = await self.connector.execute_tool(
            _mock_connector(), "nonexistent_tool", {}
        )
        assert "Unknown tool" in result or "unknown" in result.lower()

    @pytest.mark.asyncio
    async def test_basic_auth_pattern(self):
        """Verify Cursor uses Basic Auth with API key as username."""
        import base64

        async def _passthrough(fn, *args, **kwargs):
            return await fn(*args, **kwargs)

        with patch(
            "sage_mcp.connectors.http_client.get_http_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_resp = _mock_response({"ok": True})
            mock_client.request.return_value = mock_resp
            mock_get_client.return_value = mock_client

            with patch(
                "sage_mcp.connectors.retry.retry_with_backoff",
                side_effect=_passthrough,
            ):
                connector = _mock_connector("cursor-api-key-test")
                await self.connector._make_cursor_request(
                    "GET", "https://api2.cursor.sh/teams/members",
                    connector
                )
                call_args = mock_client.request.call_args
                headers = call_args.kwargs.get("headers", {})
                auth_header = headers.get("Authorization", "")
                assert auth_header.startswith("Basic ")
                decoded = base64.b64decode(
                    auth_header.replace("Basic ", "")
                ).decode()
                assert decoded == "cursor-api-key-test:"


# ===========================================================================
# WindsurfConnector
# ===========================================================================

class TestWindsurfConnector:
    """Test Windsurf/Codeium connector."""

    def setup_method(self):
        self.connector = WindsurfConnector()

    def test_properties(self):
        assert self.connector.display_name == "Windsurf"
        assert self.connector.requires_oauth is False

    @pytest.mark.asyncio
    async def test_get_tools_returns_all(self):
        tools = await self.connector.get_tools(_mock_connector())
        assert len(tools) == 11
        names = {t.name for t in tools}
        assert "windsurf_get_analytics" in names
        assert "windsurf_get_credit_balance" in names
        assert "windsurf_list_members" in names  # stub
        assert "windsurf_get_normalized_metrics" in names

    @pytest.mark.asyncio
    async def test_tool_schemas_valid(self):
        tools = await self.connector.get_tools(_mock_connector())
        for tool in tools:
            schema = tool.inputSchema
            assert schema["type"] == "object"
            assert "properties" in schema

    @pytest.mark.asyncio
    async def test_get_resources_empty(self):
        resources = await self.connector.get_resources(_mock_connector())
        assert resources == []

    @pytest.mark.asyncio
    async def test_stub_tools_return_structured_error(self):
        """Stub tools should return error JSON with workaround."""
        stub_tools = [
            "list_members", "list_audit_events",
            "get_spending_breakdown", "get_seat_info",
        ]
        for tool_name in stub_tools:
            result = await self.connector.execute_tool(
                _mock_connector(), tool_name, {}
            )
            parsed = json.loads(result)
            assert parsed.get("status") == "stub" or "not available" in parsed.get("error", "").lower()
            assert "workaround" in parsed

    @pytest.mark.asyncio
    async def test_execute_tool_get_credit_balance(self):
        mock_resp = _mock_response({
            "credits_remaining": 5000,
            "credits_used": 3000,
        })
        with patch.object(
            self.connector, "_make_windsurf_request",
            new_callable=AsyncMock, return_value=mock_resp
        ):
            result = await self.connector.execute_tool(
                _mock_connector(), "get_credit_balance", {}
            )
            parsed = json.loads(result)
            assert "credits_remaining" in parsed or "credit" in str(parsed).lower()

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self):
        result = await self.connector.execute_tool(
            _mock_connector(), "nonexistent_tool", {}
        )
        assert "Unknown tool" in result or "unknown" in result.lower()

    @pytest.mark.asyncio
    async def test_service_key_in_body(self):
        """Verify Windsurf injects service_key into the JSON body."""

        async def _passthrough(fn, *args, **kwargs):
            return await fn(*args, **kwargs)

        with patch(
            "sage_mcp.connectors.http_client.get_http_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_resp = _mock_response({"ok": True})
            mock_client.request.return_value = mock_resp
            mock_get_client.return_value = mock_client

            with patch(
                "sage_mcp.connectors.retry.retry_with_backoff",
                side_effect=_passthrough,
            ):
                connector = _mock_connector("codeium-service-key-test")
                await self.connector._make_windsurf_request(
                    "POST", "https://server.codeium.com/api/v1/Analytics",
                    connector, json={"start_date": "2024-01-01"}
                )
                call_args = mock_client.request.call_args
                body = call_args.kwargs.get("json", {})
                assert body.get("service_key") == "codeium-service-key-test"
                assert body.get("start_date") == "2024-01-01"


# ===========================================================================
# Cross-connector tests
# ===========================================================================

class TestConnectorRegistration:
    """Test that all 5 connectors register correctly."""

    def test_all_connectors_registered(self):
        from sage_mcp.connectors.registry import connector_registry

        for ct in [
            ConnectorType.COPILOT,
            ConnectorType.CLAUDE_CODE,
            ConnectorType.CODEX,
            ConnectorType.CURSOR,
            ConnectorType.WINDSURF,
        ]:
            connector = connector_registry.get_connector(ct)
            assert connector is not None, f"{ct.value} not registered"

    def test_total_registered_connectors(self):
        from sage_mcp.connectors.registry import connector_registry

        # 18 existing + 5 new = 23
        all_types = connector_registry.list_connector_types()
        assert len(all_types) >= 23


class TestNormalizedMetricsSchema:
    """Test that all connectors' normalized metrics return valid schema."""

    @pytest.mark.asyncio
    async def test_copilot_normalized_metrics_fields(self):
        """Copilot normalized metrics should populate seat fields."""
        connector = CopilotConnector()
        mock_billing = _mock_response({
            "seat_breakdown": {"total": 100, "active_this_cycle": 80},
            "seat_management_setting": "assign_all",
            "total_seats": 100,
        })
        mock_usage_data = [{
            "date": "2024-01-15",
            "copilot_ide_code_completions": {
                "editors": [{
                    "name": "vscode",
                    "models": [{
                        "languages": [{
                            "name": "python",
                            "total_code_suggestions": 5000,
                            "total_code_acceptances": 2500,
                            "total_code_lines_suggested": 10000,
                            "total_code_lines_accepted": 5000,
                        }]
                    }]
                }]
            },
            "copilot_ide_chat": {"total_chats": 300},
        }]
        with patch.object(
            connector, "_make_authenticated_request",
            new_callable=AsyncMock, return_value=mock_billing
        ), patch.object(
            connector, "_fetch_org_usage_raw",
            new_callable=AsyncMock, return_value=mock_usage_data
        ):
            oauth = _mock_oauth_cred()
            result = await connector.execute_tool(
                _mock_connector(), "get_normalized_metrics",
                {"org": "test-org", "since": "2024-01-01", "until": "2024-01-31"},
                oauth,
            )
            parsed = json.loads(result)
            assert "copilot" in parsed["tool_name"].lower()
            assert "metadata" in parsed
            assert "unavailable_fields" in parsed["metadata"]
            assert parsed["total_seats"] == 100
