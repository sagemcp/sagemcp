"""Unit tests for external MCP runtime behavior."""

import asyncio
import json
import logging
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import AnyUrl, TypeAdapter

from sage_mcp.mcp.transport import MCPTransport
from sage_mcp.runtime.generic_connector import GenericMCPConnector
from sage_mcp.runtime.process_manager import MCPProcessManager


class _FakeTask:
    def cancel(self):
        return None


class _FakeProcess:
    def __init__(self):
        self.returncode = None
        self.stdin = object()
        self.stdout = object()
        self.stderr = object()
        self.pid = 12345

    def terminate(self):
        return None

    def kill(self):
        return None

    async def wait(self):
        return 0


class _FakeStdin:
    def __init__(self):
        self.buf = b""

    def write(self, data: bytes):
        self.buf += data

    async def drain(self):
        return None


@pytest.mark.asyncio
async def test_generic_connector_description_property():
    connector = GenericMCPConnector(runtime_type="external_python", command=["python", "server.py"])
    assert "external MCP server process" in connector.description


@pytest.mark.asyncio
async def test_generic_connector_npx_adds_yes_flag():
    connector = GenericMCPConnector(
        runtime_type="external_nodejs",
        command=["npx", "@modelcontextprotocol/server-github"],
    )

    fake_process = _FakeProcess()

    with patch("sage_mcp.runtime.generic_connector.shutil.which", return_value="/usr/bin/npx"), \
         patch("sage_mcp.runtime.generic_connector.asyncio.create_subprocess_exec", new=AsyncMock(return_value=fake_process)) as mock_exec, \
         patch.object(connector, "_initialize_mcp", new=AsyncMock()), \
         patch("sage_mcp.runtime.generic_connector.asyncio.sleep", new=AsyncMock()), \
         patch("sage_mcp.runtime.generic_connector.asyncio.create_task", side_effect=lambda coro: (coro.close(), _FakeTask())[1]):
        await connector.start_process("tenant-1", "connector-1")

    args = mock_exec.await_args.args
    assert args[0] == "/usr/bin/npx"
    assert args[1] == "-y"
    assert args[2] == "@modelcontextprotocol/server-github"


@pytest.mark.asyncio
async def test_generic_connector_uvx_sets_writable_cache_env():
    connector = GenericMCPConnector(runtime_type="external_python", command=["uvx", "server-name"])

    fake_process = _FakeProcess()

    with patch.dict("os.environ", {"HOME": "/does/not/exist"}, clear=True), \
         patch("sage_mcp.runtime.generic_connector.shutil.which", return_value="/usr/bin/uvx"), \
         patch("sage_mcp.runtime.generic_connector.asyncio.create_subprocess_exec", new=AsyncMock(return_value=fake_process)) as mock_exec, \
         patch.object(connector, "_initialize_mcp", new=AsyncMock()), \
         patch("sage_mcp.runtime.generic_connector.asyncio.sleep", new=AsyncMock()), \
         patch("sage_mcp.runtime.generic_connector.asyncio.create_task", side_effect=lambda coro: (coro.close(), _FakeTask())[1]):
        await connector.start_process("tenant-1", "connector-1")

    kwargs = mock_exec.await_args.kwargs
    env = kwargs["env"]
    assert env["HOME"] == "/tmp"
    assert env["XDG_CACHE_HOME"] == os.path.join("/tmp", ".cache")
    assert env["UV_CACHE_DIR"] == os.path.join(env["XDG_CACHE_HOME"], "uv")


@pytest.mark.asyncio
async def test_process_manager_normalizes_blank_package_path():
    manager = MCPProcessManager()
    manager._health_check_task = SimpleNamespace(done=lambda: False)
    manager._update_process_status = AsyncMock()

    fake_connector = SimpleNamespace(
        id="connector-1",
        tenant_id="tenant-1",
        runtime_type=SimpleNamespace(value="external_python"),
        runtime_command='["uvx", "server-name"]',
        runtime_env={},
        package_path="   ",
        configuration={},
    )

    fake_process_instance = Mock()
    fake_process_instance.start_process = AsyncMock()
    fake_process_instance.process = SimpleNamespace(pid=999)

    with patch("sage_mcp.runtime.process_manager.GenericMCPConnector", return_value=fake_process_instance) as mock_cls:
        await manager.get_or_create(fake_connector, oauth_cred=None)

    _, kwargs = mock_cls.call_args
    assert kwargs["working_dir"] is None


@pytest.mark.asyncio
async def test_process_manager_infers_nodejs_runtime_from_npx_command():
    manager = MCPProcessManager()
    manager._health_check_task = SimpleNamespace(done=lambda: False)
    manager._update_process_status = AsyncMock()

    fake_connector = SimpleNamespace(
        id="connector-1",
        tenant_id="tenant-1",
        runtime_type=SimpleNamespace(value="external_python"),
        runtime_command='["npx", "@modelcontextprotocol/server-filesystem"]',
        runtime_env={},
        package_path=None,
        configuration={},
    )

    fake_process_instance = Mock()
    fake_process_instance.start_process = AsyncMock()
    fake_process_instance.process = SimpleNamespace(pid=123)

    with patch("sage_mcp.runtime.process_manager.GenericMCPConnector", return_value=fake_process_instance):
        await manager.get_or_create(fake_connector, oauth_cred=None)

    # First call is terminal error path guard for start failure; second is RUNNING update.
    running_call = manager._update_process_status.await_args_list[-1]
    assert running_call.kwargs["runtime_type"] == "external_nodejs"


@pytest.mark.asyncio
async def test_process_manager_rejects_blank_runtime_command_executable():
    manager = MCPProcessManager()

    bad_connector = SimpleNamespace(
        id="connector-1",
        tenant_id="tenant-1",
        runtime_type=SimpleNamespace(value="external_python"),
        runtime_command='["   "]',
        runtime_env={},
        package_path=None,
        configuration={},
    )

    with pytest.raises(Exception, match="runtime_command must start with a non-empty executable name"):
        await manager.get_or_create(bad_connector, oauth_cred=None)


@pytest.mark.asyncio
async def test_process_manager_protocol_probe_falls_back_to_tools_list():
    manager = MCPProcessManager()
    fake_connector = SimpleNamespace(
        _send_request=AsyncMock(side_effect=[Exception("no resources"), {}]),
    )

    await manager._protocol_probe(fake_connector)

    assert fake_connector._send_request.await_count == 2
    assert fake_connector._send_request.await_args_list[0].args == ("resources/list", {})
    assert fake_connector._send_request.await_args_list[1].args == ("tools/list", {})


@pytest.mark.asyncio
async def test_process_manager_health_check_skips_probe_within_interval():
    manager = MCPProcessManager()
    manager.protocol_probe_interval = 300
    manager._protocol_probe = AsyncMock(return_value=None)

    key = "tenant-1:connector-1"
    now = asyncio.get_running_loop().time()
    manager._health_state[key] = {
        "last_protocol_probe_at": now,
        "consecutive_failures": 0,
    }
    fake_connector = SimpleNamespace(process=SimpleNamespace(returncode=None))

    is_healthy = await manager._is_healthy(key, fake_connector)

    assert is_healthy is True
    manager._protocol_probe.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_manager_health_check_uses_failure_threshold():
    manager = MCPProcessManager()
    manager.protocol_probe_interval = 0
    manager.health_failure_threshold = 3
    manager._protocol_probe = AsyncMock(side_effect=Exception("probe failed"))

    key = "tenant-1:connector-1"
    fake_connector = SimpleNamespace(process=SimpleNamespace(returncode=None))

    assert await manager._is_healthy(key, fake_connector) is True
    assert await manager._is_healthy(key, fake_connector) is True
    assert await manager._is_healthy(key, fake_connector) is False


@pytest.mark.asyncio
async def test_transport_resources_list_serializes_anyurl_uri():
    transport = MCPTransport("tenant-a", "conn-1")
    transport.initialized = True

    any_url = TypeAdapter(AnyUrl).validate_python("https://example.com/resource")
    fake_resource = SimpleNamespace(uri=any_url, name="example", description="desc")
    fake_result = SimpleNamespace(resources=[fake_resource])

    async def handler(_request):
        return fake_result

    from mcp.types import ListResourcesRequest

    transport.mcp_server = SimpleNamespace(
        server=SimpleNamespace(request_handlers={ListResourcesRequest: handler})
    )

    response = await transport.handle_http_message(
        {"jsonrpc": "2.0", "id": "1", "method": "resources/list", "params": {}}
    )

    resource = response["result"]["resources"][0]
    assert isinstance(resource["uri"], str)
    assert resource["uri"] == "https://example.com/resource"
    # Ensure the full payload can be JSON-serialized.
    json.dumps(response)


@pytest.mark.asyncio
async def test_transport_resources_read_uses_request_handler():
    transport = MCPTransport("tenant-a", "conn-1")
    transport.initialized = True

    fake_content = SimpleNamespace(
        uri="n8n://workflows",
        mimeType="text/plain",
        text='{"ok": true}',
    )
    fake_result = SimpleNamespace(contents=[fake_content])

    async def handler(_request):
        return fake_result

    from mcp.types import ReadResourceRequest

    transport.mcp_server = SimpleNamespace(
        server=SimpleNamespace(request_handlers={ReadResourceRequest: handler})
    )

    response = await transport.handle_http_message(
        {"jsonrpc": "2.0", "id": "1", "method": "resources/read", "params": {"uri": "n8n://workflows"}}
    )

    assert response["result"]["contents"][0]["uri"] == "n8n://workflows"
    assert response["result"]["contents"][0]["text"] == '{"ok": true}'


@pytest.mark.asyncio
async def test_transport_resources_read_serializes_dict_anyurl_uri():
    transport = MCPTransport("tenant-a", "conn-1")
    transport.initialized = True

    any_url = TypeAdapter(AnyUrl).validate_python("hass://entities")
    fake_result = SimpleNamespace(contents=[{"uri": any_url, "type": "text", "text": "ok"}])

    async def handler(_request):
        return fake_result

    from mcp.types import ReadResourceRequest

    transport.mcp_server = SimpleNamespace(
        server=SimpleNamespace(request_handlers={ReadResourceRequest: handler})
    )

    response = await transport.handle_http_message(
        {"jsonrpc": "2.0", "id": "1", "method": "resources/read", "params": {"uri": "hass://entities"}}
    )

    assert response["result"]["contents"][0]["uri"] == "hass://entities"


def test_generic_connector_stderr_level_classification():
    connector = GenericMCPConnector(runtime_type="external_python", command=["python", "server.py"])

    assert connector._classify_stderr_level("[DEBUG] Request: GET /workflows/abc") == logging.DEBUG
    assert connector._classify_stderr_level("INFO:mcp.server.lowlevel.server:Processing request") == logging.INFO
    assert connector._classify_stderr_level("WARNING:something noisy") == logging.WARNING
    assert connector._classify_stderr_level("ERROR: failed to start") == logging.ERROR


def test_generic_connector_parses_content_length_frames():
    connector = GenericMCPConnector(runtime_type="external_python", command=["python", "server.py"])

    future = SimpleNamespace(done=lambda: False, set_result=Mock())
    connector._pending_requests["1"] = future
    payload = b'{"jsonrpc":"2.0","id":"1","result":{"ok":true}}'
    connector._stdout_buffer = (
        b"Content-Length: " + str(len(payload)).encode("ascii") + b"\r\n\r\n" + payload
    )

    connector._try_parse_stdout_frames()

    assert connector._stdout_buffer == b""
    future.set_result.assert_called_once()


@pytest.mark.asyncio
async def test_generic_connector_write_message_uses_json_lines_by_default():
    connector = GenericMCPConnector(runtime_type="external_python", command=["python", "server.py"])
    fake_stdin = _FakeStdin()
    connector.process = SimpleNamespace(stdin=fake_stdin, returncode=0)

    await connector._write_message({"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}})

    assert fake_stdin.buf.endswith(b"\n")
    payload = json.loads(fake_stdin.buf.decode("utf-8"))
    assert payload["method"] == "tools/list"


@pytest.mark.asyncio
async def test_generic_connector_write_message_uses_content_length_when_selected():
    connector = GenericMCPConnector(runtime_type="external_python", command=["python", "server.py"])
    connector._stdio_framing = "content_length"
    fake_stdin = _FakeStdin()
    connector.process = SimpleNamespace(stdin=fake_stdin, returncode=0)

    await connector._write_message({"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}})

    header, payload_bytes = fake_stdin.buf.split(b"\r\n\r\n", 1)
    assert header.startswith(b"Content-Length:")
    payload = json.loads(payload_bytes.decode("utf-8"))
    assert payload["method"] == "tools/list"


def test_generic_connector_parses_content_length_frames_with_lf_separator():
    connector = GenericMCPConnector(runtime_type="external_python", command=["python", "server.py"])

    future = SimpleNamespace(done=lambda: False, set_result=Mock())
    connector._pending_requests["1"] = future
    payload = b'{"jsonrpc":"2.0","id":"1","result":{"ok":true}}'
    connector._stdout_buffer = (
        b"Content-Length: " + str(len(payload)).encode("ascii") + b"\n\n" + payload
    )

    connector._try_parse_stdout_frames()

    assert connector._stdout_buffer == b""
    future.set_result.assert_called_once()


@pytest.mark.asyncio
async def test_generic_connector_initialize_falls_back_to_content_length_framing():
    connector = GenericMCPConnector(runtime_type="external_python", command=["python", "server.py"])
    connector._send_notification = AsyncMock()
    connector._send_request = AsyncMock(side_effect=[Exception("init timeout"), {}])

    await connector._initialize_mcp(exec_name="uvx")

    assert connector._initialized is True
    assert connector._stdio_framing == "content_length"
    assert connector._send_request.await_count == 2
    connector._send_notification.assert_awaited_once_with("notifications/initialized")
