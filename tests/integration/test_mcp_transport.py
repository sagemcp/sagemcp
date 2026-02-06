"""Integration tests for MCP HTTP transport with session management."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sage_mcp.mcp.event_buffer import EventBuffer, EventBufferManager


class TestMCPHTTPPost:
    """Test MCP HTTP POST endpoint."""

    def test_missing_accept_header(self, client: TestClient):
        """Test that missing Accept header returns 400."""
        response = client.post(
            "/api/v1/test-tenant/connectors/abc-123/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"Content-Type": "application/json"},
        )
        # Accept header must include application/json
        assert response.status_code == 400

    def test_missing_content_type(self, client: TestClient):
        """Test that missing Content-Type returns 400."""
        response = client.post(
            "/api/v1/test-tenant/connectors/abc-123/mcp",
            content=b'{"jsonrpc": "2.0", "id": 1}',
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 400

    def test_invalid_json(self, client: TestClient):
        """Test that invalid JSON returns 400."""
        response = client.post(
            "/api/v1/test-tenant/connectors/abc-123/mcp",
            content=b"not json",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 400

    def test_notification_returns_202(self, client: TestClient):
        """Test that JSON-RPC notifications return 202."""
        response = client.post(
            "/api/v1/test-tenant/connectors/abc-123/mcp",
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 202

    def test_invalid_request_message(self, client: TestClient):
        """Test that messages without method or result/error return 400."""
        response = client.post(
            "/api/v1/test-tenant/connectors/abc-123/mcp",
            json={"jsonrpc": "2.0", "id": 1},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 400

    def test_batch_empty_returns_empty_array(self, client: TestClient):
        """Test that empty batch returns empty array."""
        response = client.post(
            "/api/v1/test-tenant/connectors/abc-123/mcp",
            json=[],
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_batch_all_notifications_returns_202(self, client: TestClient):
        """Test that batch of only notifications returns 202."""
        response = client.post(
            "/api/v1/test-tenant/connectors/abc-123/mcp",
            json=[
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "method": "notifications/cancelled"},
            ],
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 202


class TestEventBuffer:
    """Test SSE event buffer."""

    def test_append_and_replay(self):
        """Test appending events and replaying from a given ID."""
        buf = EventBuffer(capacity=10)

        id1 = buf.append("message", '{"a":1}')
        id2 = buf.append("message", '{"a":2}')
        id3 = buf.append("message", '{"a":3}')

        assert id1 == 1
        assert id2 == 2
        assert id3 == 3

        events = buf.replay_from(1)
        assert len(events) == 2
        assert events[0].event_id == 2
        assert events[1].event_id == 3

    def test_replay_from_zero(self):
        """Test replaying all events from 0."""
        buf = EventBuffer(capacity=10)
        buf.append("message", "data1")
        buf.append("message", "data2")

        events = buf.replay_from(0)
        assert len(events) == 2

    def test_replay_from_latest(self):
        """Test replaying from the latest ID returns empty."""
        buf = EventBuffer(capacity=10)
        buf.append("message", "data1")
        buf.append("message", "data2")

        events = buf.replay_from(2)
        assert len(events) == 0

    def test_ring_buffer_eviction(self):
        """Test that oldest events are evicted at capacity."""
        buf = EventBuffer(capacity=3)

        buf.append("message", "data1")
        buf.append("message", "data2")
        buf.append("message", "data3")
        buf.append("message", "data4")  # Should evict data1

        assert buf.size == 3
        events = buf.replay_from(0)
        assert len(events) == 3
        assert events[0].event_id == 2  # data1 (id=1) was evicted

    def test_latest_id(self):
        """Test latest_id property."""
        buf = EventBuffer(capacity=10)
        assert buf.latest_id == 0

        buf.append("message", "data1")
        assert buf.latest_id == 1

        buf.append("message", "data2")
        assert buf.latest_id == 2

    def test_size(self):
        """Test size property."""
        buf = EventBuffer(capacity=10)
        assert buf.size == 0

        buf.append("message", "data1")
        assert buf.size == 1

    def test_event_types_preserved(self):
        """Test that event types are preserved."""
        buf = EventBuffer(capacity=10)
        buf.append("message", "data1")
        buf.append("error", "data2")

        events = buf.replay_from(0)
        assert events[0].event_type == "message"
        assert events[1].event_type == "error"


class TestEventBufferManager:
    """Test EventBufferManager class."""

    def test_get_or_create(self):
        """Test getting or creating a buffer."""
        mgr = EventBufferManager()

        buf1 = mgr.get_or_create("session-1")
        buf2 = mgr.get_or_create("session-1")

        assert buf1 is buf2
        assert mgr.size == 1

    def test_separate_sessions(self):
        """Test that different sessions get separate buffers."""
        mgr = EventBufferManager()

        buf1 = mgr.get_or_create("session-1")
        buf2 = mgr.get_or_create("session-2")

        assert buf1 is not buf2
        assert mgr.size == 2

    def test_remove(self):
        """Test removing a session buffer."""
        mgr = EventBufferManager()
        mgr.get_or_create("session-1")
        mgr.get_or_create("session-2")

        mgr.remove("session-1")

        assert mgr.size == 1

    def test_remove_nonexistent(self):
        """Test removing a nonexistent session is a no-op."""
        mgr = EventBufferManager()
        mgr.remove("nonexistent")
        assert mgr.size == 0

    def test_cleanup_sessions(self):
        """Test cleaning up orphaned session buffers."""
        mgr = EventBufferManager()
        mgr.get_or_create("session-1")
        mgr.get_or_create("session-2")
        mgr.get_or_create("session-3")

        active = {"session-1", "session-3"}
        mgr.cleanup_sessions(active)

        assert mgr.size == 2

    def test_default_capacity(self):
        """Test that buffers use the manager's default capacity."""
        mgr = EventBufferManager(default_capacity=5)
        buf = mgr.get_or_create("session-1")

        # Fill to capacity
        for i in range(10):
            buf.append("message", f"data-{i}")

        assert buf.size == 5
