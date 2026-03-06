"""Unit tests for the audit logging system."""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from sage_mcp.models.audit_log import AuditLog, ActorType
from sage_mcp.security.auth import AuthContext
from sage_mcp.models.api_key import APIKeyScope


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestAuditLogModel:
    """Test AuditLog model properties."""

    def test_actor_type_enum_values(self):
        assert ActorType.USER == "user"
        assert ActorType.API_KEY == "api_key"
        assert ActorType.SYSTEM == "system"

    def test_audit_log_repr(self):
        log = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            actor_id="key-123",
            actor_type="api_key",
            action="tenant.create",
            resource_type="tenant",
            resource_id="abc-123",
        )
        assert "tenant.create" in repr(log)
        assert "key-123" in repr(log)

    def test_audit_log_tablename(self):
        assert AuditLog.__tablename__ == "audit_logs"


# ---------------------------------------------------------------------------
# record_audit helper tests
# ---------------------------------------------------------------------------

class TestRecordAudit:
    """Test the fire-and-forget record_audit helper."""

    def _make_auth(self, key_id="key-1", scope=APIKeyScope.PLATFORM_ADMIN, tenant_id=None):
        return AuthContext(key_id=key_id, name="test", scope=scope, tenant_id=tenant_id)

    def _make_request(self, ip="127.0.0.1", ua="test-agent"):
        req = MagicMock()
        req.client.host = ip
        req.headers = {"user-agent": ua}
        return req

    @pytest.mark.asyncio
    async def test_record_audit_creates_task(self):
        """record_audit must schedule a background task, not block."""
        from sage_mcp.security.audit import record_audit

        auth = self._make_auth()
        req = self._make_request()

        with patch("sage_mcp.security.audit._persist_audit_event", new_callable=AsyncMock) as mock_persist:
            with patch("sage_mcp.security.audit.asyncio.create_task") as mock_create:
                mock_create.return_value = MagicMock()  # fake task
                record_audit("tenant.create", auth, req, resource_type="tenant")
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_audit_extracts_auth_fields(self):
        """Actor ID and type are correctly extracted from AuthContext."""
        from sage_mcp.security.audit import record_audit

        auth = self._make_auth(key_id="my-key-id")
        req = self._make_request(ip="10.0.0.1", ua="curl/7.0")

        with patch("sage_mcp.security.audit._persist_audit_event", new_callable=AsyncMock) as mock_persist:
            with patch("sage_mcp.security.audit.asyncio.create_task", side_effect=lambda coro: asyncio.ensure_future(coro)):
                record_audit(
                    "connector.delete", auth, req,
                    resource_type="connector",
                    resource_id="conn-1",
                    tenant_id="tid-1",
                    details={"name": "github"},
                )
                # Let the task run
                await asyncio.sleep(0.05)

            mock_persist.assert_awaited_once()
            call_kwargs = mock_persist.call_args
            assert call_kwargs.kwargs["actor_id"] == "my-key-id"
            assert call_kwargs.kwargs["actor_type"] == "api_key"
            assert call_kwargs.kwargs["ip_address"] == "10.0.0.1"
            assert call_kwargs.kwargs["user_agent"] == "curl/7.0"
            assert call_kwargs.kwargs["resource_type"] == "connector"
            assert call_kwargs.kwargs["resource_id"] == "conn-1"
            assert call_kwargs.kwargs["tenant_id"] == "tid-1"

    @pytest.mark.asyncio
    async def test_record_audit_anonymous_when_no_auth(self):
        """When auth is None, actor_id should be 'anonymous'."""
        from sage_mcp.security.audit import record_audit

        req = self._make_request()

        with patch("sage_mcp.security.audit._persist_audit_event", new_callable=AsyncMock) as mock_persist:
            with patch("sage_mcp.security.audit.asyncio.create_task", side_effect=lambda coro: asyncio.ensure_future(coro)):
                record_audit("system.startup", None, req)
                await asyncio.sleep(0.05)

            mock_persist.assert_awaited_once()
            assert mock_persist.call_args.kwargs["actor_id"] == "anonymous"
            assert mock_persist.call_args.kwargs["actor_type"] == "system"

    @pytest.mark.asyncio
    async def test_record_audit_no_request(self):
        """When request is None, IP and UA should be None."""
        from sage_mcp.security.audit import record_audit

        auth = self._make_auth()

        with patch("sage_mcp.security.audit._persist_audit_event", new_callable=AsyncMock) as mock_persist:
            with patch("sage_mcp.security.audit.asyncio.create_task", side_effect=lambda coro: asyncio.ensure_future(coro)):
                record_audit("test.action", auth, None)
                await asyncio.sleep(0.05)

            mock_persist.assert_awaited_once()
            assert mock_persist.call_args.kwargs["ip_address"] is None
            assert mock_persist.call_args.kwargs["user_agent"] is None

    @pytest.mark.asyncio
    async def test_persist_audit_event_db_error_does_not_propagate(self):
        """DB failures inside _persist_audit_event must be swallowed (logged, not raised)."""
        from sage_mcp.security.audit import _persist_audit_event

        with patch("sage_mcp.security.audit.get_db_context") as mock_ctx:
            # Make the context manager raise
            mock_session = AsyncMock()
            mock_session.commit.side_effect = Exception("DB down")
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            # Should not raise
            await _persist_audit_event(
                action="test.action",
                actor_id="x",
                actor_type="system",
                ip_address=None,
                user_agent=None,
                resource_type=None,
                resource_id=None,
                tenant_id=None,
                details=None,
            )

    @pytest.mark.asyncio
    async def test_persist_audit_event_writes_to_db(self):
        """_persist_audit_event should add an AuditLog and commit."""
        from sage_mcp.security.audit import _persist_audit_event

        mock_session = AsyncMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_ctx():
            yield mock_session

        with patch("sage_mcp.security.audit.get_db_context", fake_ctx):
            await _persist_audit_event(
                action="tenant.create",
                actor_id="key-1",
                actor_type="api_key",
                ip_address="1.2.3.4",
                user_agent="test",
                resource_type="tenant",
                resource_id="t-1",
                tenant_id=None,
                details={"slug": "acme"},
            )

        mock_session.add.assert_called_once()
        added_obj = mock_session.add.call_args[0][0]
        assert isinstance(added_obj, AuditLog)
        assert added_obj.action == "tenant.create"
        assert added_obj.actor_id == "key-1"
        assert added_obj.details == {"slug": "acme"}
        mock_session.commit.assert_awaited_once()
