"""Tests for MCP protocol version negotiation."""

import pytest

from sage_mcp.mcp.transport import (
    _negotiate_protocol_version,
    _error_response,
    SUPPORTED_PROTOCOL_VERSIONS,
    MCPTransport,
)


class TestProtocolVersionNegotiation:
    """Test protocol version negotiation logic."""

    def test_supported_versions_order(self):
        """Test that supported versions are in descending order."""
        assert SUPPORTED_PROTOCOL_VERSIONS == sorted(SUPPORTED_PROTOCOL_VERSIONS, reverse=True)

    def test_negotiate_exact_match_latest(self):
        """Test negotiating with the latest supported version."""
        result = _negotiate_protocol_version("2025-06-18")
        assert result == "2025-06-18"

    def test_negotiate_exact_match_older(self):
        """Test negotiating with an older supported version."""
        result = _negotiate_protocol_version("2024-11-05")
        assert result == "2024-11-05"

    def test_negotiate_newer_than_latest(self):
        """Test client with a newer version than server supports."""
        result = _negotiate_protocol_version("2026-01-01")
        assert result == "2025-06-18"  # Returns latest supported

    def test_negotiate_between_versions(self):
        """Test client version between two supported versions."""
        result = _negotiate_protocol_version("2025-01-01")
        # "2025-01-01" > "2024-11-05" but < "2025-06-18"
        assert result == "2024-11-05"

    def test_negotiate_too_old(self):
        """Test client with a version older than any supported."""
        result = _negotiate_protocol_version("2023-01-01")
        assert result is None

    def test_negotiate_empty_string(self):
        """Test negotiating with empty string."""
        result = _negotiate_protocol_version("")
        assert result is None


class TestErrorResponse:
    """Test JSON-RPC error response helper."""

    def test_error_response_format(self):
        """Test error response has correct JSON-RPC 2.0 format."""
        resp = _error_response(1, -32600, "Invalid Request")

        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert resp["error"]["code"] == -32600
        assert resp["error"]["message"] == "Invalid Request"

    def test_error_response_with_none_id(self):
        """Test error response with None message ID."""
        resp = _error_response(None, -32700, "Parse error")

        assert resp["id"] is None
        assert resp["error"]["code"] == -32700

    def test_error_response_with_string_id(self):
        """Test error response with string message ID."""
        resp = _error_response("abc-123", -32601, "Method not found")

        assert resp["id"] == "abc-123"


class TestMCPTransportHandleMessage:
    """Test MCPTransport message handling for protocol compliance."""

    @pytest.mark.asyncio
    async def test_notification_returns_none(self):
        """Test that notifications (no id) return None."""
        transport = MCPTransport("tenant-a", "conn-1")
        transport.initialized = True
        transport.mcp_server = pytest.importorskip("unittest.mock").MagicMock()

        result = await transport.handle_http_message({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })

        assert result is None

    @pytest.mark.asyncio
    async def test_initialize_returns_negotiated_version(self):
        """Test that initialize returns properly negotiated version."""
        transport = MCPTransport("tenant-a", "conn-1")
        transport.initialized = True
        transport.mcp_server = pytest.importorskip("unittest.mock").MagicMock()

        result = await transport.handle_http_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"}
        })

        assert result["id"] == 1
        assert result["result"]["protocolVersion"] == "2025-06-18"
        assert "capabilities" in result["result"]
        assert "serverInfo" in result["result"]

    @pytest.mark.asyncio
    async def test_initialize_with_old_version(self):
        """Test that initialize negotiates down to older version."""
        transport = MCPTransport("tenant-a", "conn-1")
        transport.initialized = True
        transport.mcp_server = pytest.importorskip("unittest.mock").MagicMock()

        result = await transport.handle_http_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        })

        assert result["result"]["protocolVersion"] == "2024-11-05"

    @pytest.mark.asyncio
    async def test_initialize_unsupported_version(self):
        """Test that initialize rejects unsupported versions."""
        transport = MCPTransport("tenant-a", "conn-1")
        transport.initialized = True
        transport.mcp_server = pytest.importorskip("unittest.mock").MagicMock()

        result = await transport.handle_http_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2023-01-01"}
        })

        assert "error" in result
        assert result["error"]["code"] == -32602
        assert "Unsupported" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_unknown_method_returns_error(self):
        """Test that unknown methods return method-not-found error."""
        transport = MCPTransport("tenant-a", "conn-1")
        transport.initialized = True
        transport.mcp_server = pytest.importorskip("unittest.mock").MagicMock()

        result = await transport.handle_http_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown/method"
        })

        assert "error" in result
        assert result["error"]["code"] == -32601
