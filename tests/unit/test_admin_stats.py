"""Unit tests for dashboard admin stats."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from sage_mcp.api.admin_stats import get_platform_stats
from sage_mcp.api import mcp as mcp_api
from sage_mcp.runtime import process_manager


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_get_platform_stats_uses_process_fallbacks(monkeypatch):
    fake_session = SimpleNamespace(
        execute=AsyncMock(side_effect=[_FakeResult(1), _FakeResult(3), _FakeResult(7)])
    )
    monkeypatch.setattr(
        "sage_mcp.database.connection.get_db_context",
        lambda: _FakeContext(fake_session),
    )

    original_processes = process_manager.processes
    process_manager.processes = {
        "t1:c1": object(),
        "t1:c2": object(),
    }
    try:
        request = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(server_pool=None, session_manager=None)
            )
        )
        stats = await get_platform_stats(request)
    finally:
        process_manager.processes = original_processes

    assert stats["tenants"] == 1
    assert stats["connectors"] == 3
    assert stats["active_instances"] == 0
    assert stats["active_sessions"] == 0
    assert stats["tool_calls_today"] == 7


@pytest.mark.asyncio
async def test_get_platform_stats_uses_recent_activity_when_sessions_disabled(monkeypatch):
    fake_session = SimpleNamespace(
        execute=AsyncMock(side_effect=[_FakeResult(1), _FakeResult(1), _FakeResult(2)])
    )
    monkeypatch.setattr(
        "sage_mcp.database.connection.get_db_context",
        lambda: _FakeContext(fake_session),
    )

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                server_pool=None,
                session_manager=None,
                mcp_recent_activity={"t:c:k:u": 999999999.0},
            )
        )
    )

    # Mock monotonic to keep the fake activity entry within TTL.
    monkeypatch.setattr("time.monotonic", lambda: 1000000000.0)

    stats = await get_platform_stats(request)
    assert stats["active_sessions"] == 1


def test_record_websocket_activity_counts_toward_recent_sessions(monkeypatch):
    app = SimpleNamespace(state=SimpleNamespace())
    ws = SimpleNamespace(
        app=app,
        headers={
            "mcp-session-id": "session-1",
            "user-agent": "ws-client",
        },
        client=SimpleNamespace(host="127.0.0.1"),
    )

    monkeypatch.setattr("time.monotonic", lambda: 1234.0)
    mcp_api._record_websocket_activity(ws, "tenant-a", "connector-a")

    assert mcp_api.get_recent_active_session_count(app, ttl_seconds=60.0) == 1
