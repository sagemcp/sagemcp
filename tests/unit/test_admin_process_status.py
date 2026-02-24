"""Unit tests for admin process status reconciliation."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from sage_mcp.api.admin import get_process_status, restart_process
from sage_mcp.models.connector import ConnectorRuntimeType
from sage_mcp.models.mcp_process import ProcessStatus
from sage_mcp.runtime import process_manager


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ExecResult:
    def __init__(self, rowcount: int):
        self.rowcount = rowcount


@pytest.mark.asyncio
async def test_get_process_status_reconciles_stale_running_record():
    connector_id = uuid4()
    tenant_id = uuid4()
    process_id = 4321
    started_at = datetime.now(timezone.utc)

    connector = SimpleNamespace(
        id=connector_id,
        tenant_id=tenant_id,
        runtime_type=ConnectorRuntimeType.EXTERNAL_PYTHON,
    )
    process = SimpleNamespace(
        connector_id=connector_id,
        tenant_id=tenant_id,
        pid=process_id,
        runtime_type="external_python",
        status=ProcessStatus.RUNNING,
        started_at=started_at,
        last_health_check=started_at,
        error_message="old init error",
        restart_count=0,
    )
    session = SimpleNamespace(
        execute=AsyncMock(side_effect=[_Result(connector), _Result(process)]),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )

    original_processes = process_manager.processes
    process_manager.processes = {}
    try:
        response = await get_process_status(str(connector_id), session=session)
    finally:
        process_manager.processes = original_processes

    assert response is None
    assert process.pid is None
    assert process.last_health_check is None
    assert process.error_message is None
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(process)


@pytest.mark.asyncio
async def test_restart_process_increments_restart_count():
    connector_id = uuid4()
    tenant_id = uuid4()
    connector = SimpleNamespace(
        id=connector_id,
        tenant_id=tenant_id,
        name="Test Connector",
        runtime_type=ConnectorRuntimeType.EXTERNAL_PYTHON,
    )
    session = SimpleNamespace(
        execute=AsyncMock(side_effect=[_Result(connector), _ExecResult(rowcount=1)]),
        commit=AsyncMock(),
        add=AsyncMock(),
    )

    original_terminate = process_manager.terminate
    mocked_terminate = AsyncMock()
    process_manager.terminate = mocked_terminate
    try:
        response = await restart_process(str(connector_id), session=session)
    finally:
        process_manager.terminate = original_terminate

    assert response["success"] is True
    mocked_terminate.assert_awaited_once_with(str(tenant_id), str(connector_id))
    session.commit.assert_awaited_once()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_get_process_status_keeps_running_when_process_is_live():
    connector_id = uuid4()
    tenant_id = uuid4()
    process_id = 9876
    started_at = datetime.now(timezone.utc)

    connector = SimpleNamespace(
        id=connector_id,
        tenant_id=tenant_id,
        runtime_type=ConnectorRuntimeType.EXTERNAL_PYTHON,
    )
    process = SimpleNamespace(
        connector_id=connector_id,
        tenant_id=tenant_id,
        pid=process_id,
        runtime_type="external_python",
        status=ProcessStatus.RUNNING,
        started_at=started_at,
        last_health_check=started_at,
        error_message=None,
        restart_count=1,
    )
    session = SimpleNamespace(
        execute=AsyncMock(side_effect=[_Result(connector), _Result(process)]),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )

    original_processes = process_manager.processes
    process_manager.processes = {
        f"{tenant_id}:{connector_id}": SimpleNamespace(
            process=SimpleNamespace(returncode=None)
        )
    }
    try:
        response = await get_process_status(str(connector_id), session=session)
    finally:
        process_manager.processes = original_processes

    assert response is not None
    assert response.status == ProcessStatus.RUNNING.value
    assert response.pid == process_id
    session.commit.assert_not_awaited()
    session.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_process_status_normalizes_stopped_metadata():
    connector_id = uuid4()
    tenant_id = uuid4()
    started_at = datetime.now(timezone.utc)

    connector = SimpleNamespace(
        id=connector_id,
        tenant_id=tenant_id,
        runtime_type=ConnectorRuntimeType.EXTERNAL_PYTHON,
    )
    process = SimpleNamespace(
        connector_id=connector_id,
        tenant_id=tenant_id,
        pid=28,
        runtime_type="external_python",
        status=ProcessStatus.STOPPED,
        started_at=started_at,
        last_health_check=started_at,
        error_message="stale",
        restart_count=1,
    )
    session = SimpleNamespace(
        execute=AsyncMock(side_effect=[_Result(connector), _Result(process)]),
        commit=AsyncMock(),
        refresh=AsyncMock(),
    )

    original_processes = process_manager.processes
    process_manager.processes = {}
    try:
        response = await get_process_status(str(connector_id), session=session)
    finally:
        process_manager.processes = original_processes

    assert response is None
    assert process.pid is None
    assert process.last_health_check is None
    assert process.error_message is None
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(process)
