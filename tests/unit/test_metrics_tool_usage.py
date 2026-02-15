"""Unit tests for in-memory tool-usage counters and DB flush behavior."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from sage_mcp.observability import metrics


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _ExecResult:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount


class _Ctx:
    def __init__(self, *, scalar_value=None, exec_side_effect=None, commit_side_effect=None):
        self.execute = AsyncMock(side_effect=exec_side_effect or [])
        self.commit = AsyncMock(side_effect=commit_side_effect or [None])
        self.rollback = AsyncMock()
        self.add = Mock()
        self._scalar_value = scalar_value

    async def __aenter__(self):
        if self._scalar_value is not None:
            self.execute = AsyncMock(return_value=_FakeResult(self._scalar_value))
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _reset_metric_globals():
    metrics._tool_calls_day = None
    metrics._tool_calls_today_count = 0
    metrics._tool_calls_flushed_count = 0


@pytest.mark.asyncio
async def test_bootstrap_tool_calls_today_from_db(monkeypatch):
    _reset_metric_globals()
    monkeypatch.setattr(
        "sage_mcp.database.connection.get_db_context",
        lambda: _Ctx(scalar_value=11),
    )

    loaded = await metrics.bootstrap_tool_calls_today_from_db()

    assert loaded == 11
    assert metrics.get_tool_calls_today() == 11
    assert metrics._tool_calls_flushed_count == 11


@pytest.mark.asyncio
async def test_flush_tool_calls_today_to_db_persists_delta(monkeypatch):
    _reset_metric_globals()
    metrics._tool_calls_day = metrics.datetime.now(metrics.timezone.utc).date()
    metrics._tool_calls_today_count = 10
    metrics._tool_calls_flushed_count = 7

    ctx = _Ctx(exec_side_effect=[_ExecResult(rowcount=1)], commit_side_effect=[None])
    monkeypatch.setattr("sage_mcp.database.connection.get_db_context", lambda: ctx)

    flushed = await metrics.flush_tool_calls_today_to_db()

    assert flushed == 3
    assert metrics._tool_calls_flushed_count == 10
    assert ctx.execute.await_count == 1
    assert ctx.commit.await_count == 1


@pytest.mark.asyncio
async def test_flush_tool_calls_today_retries_on_integrity_error(monkeypatch):
    _reset_metric_globals()
    metrics._tool_calls_day = metrics.datetime.now(metrics.timezone.utc).date()
    metrics._tool_calls_today_count = 5
    metrics._tool_calls_flushed_count = 0

    ctx = _Ctx(
        exec_side_effect=[_ExecResult(rowcount=0), _ExecResult(rowcount=1)],
        commit_side_effect=[None, Exception("boom")],
    )

    class _IntegrityError(Exception):
        pass

    ctx.commit = AsyncMock(side_effect=[_IntegrityError("race"), None])
    monkeypatch.setattr("sage_mcp.database.connection.get_db_context", lambda: ctx)
    monkeypatch.setattr("sage_mcp.observability.metrics.IntegrityError", _IntegrityError, raising=False)

    # Monkeypatch module import target used inside function.
    import sqlalchemy.exc  # type: ignore

    monkeypatch.setattr(sqlalchemy.exc, "IntegrityError", _IntegrityError)

    flushed = await metrics.flush_tool_calls_today_to_db()

    assert flushed == 5
    assert ctx.add.call_count == 1
    assert ctx.rollback.await_count == 1
    assert ctx.execute.await_count == 2
    assert ctx.commit.await_count == 2
    assert metrics._tool_calls_flushed_count == 5
