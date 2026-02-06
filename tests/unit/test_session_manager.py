"""Tests for SessionManager."""

import asyncio
import time
from unittest.mock import MagicMock

import pytest

from sage_mcp.mcp.session import SessionManager, SessionEntry


@pytest.fixture
def session_mgr():
    """Create a session manager for testing."""
    return SessionManager(ttl_seconds=5, max_sessions_per_key=2, reap_interval=600)


@pytest.fixture
def mock_server():
    """Create a mock MCPServer."""
    return MagicMock()


class TestSessionManager:
    """Test SessionManager class."""

    def test_initialization(self, session_mgr):
        """Test session manager initializes correctly."""
        assert session_mgr.active_session_count == 0
        assert session_mgr.ttl_seconds == 5
        assert session_mgr.max_sessions_per_key == 2

    @pytest.mark.asyncio
    async def test_create_session(self, session_mgr, mock_server):
        """Test creating a session returns a valid session ID."""
        session_id = session_mgr.create_session("tenant-a", "conn-1", mock_server)

        assert session_id is not None
        assert len(session_id) == 32  # UUID4 hex
        assert session_mgr.active_session_count == 1

    @pytest.mark.asyncio
    async def test_create_session_with_version(self, session_mgr, mock_server):
        """Test creating a session with negotiated version."""
        session_id = session_mgr.create_session(
            "tenant-a", "conn-1", mock_server,
            negotiated_version="2025-06-18"
        )

        entry = session_mgr.get_session(session_id)
        assert entry is not None
        assert entry.negotiated_version == "2025-06-18"

    @pytest.mark.asyncio
    async def test_get_session(self, session_mgr, mock_server):
        """Test getting an existing session."""
        session_id = session_mgr.create_session("tenant-a", "conn-1", mock_server)

        entry = session_mgr.get_session(session_id)

        assert entry is not None
        assert entry.session_id == session_id
        assert entry.tenant_slug == "tenant-a"
        assert entry.connector_id == "conn-1"
        assert entry.server is mock_server

    def test_get_nonexistent_session(self, session_mgr):
        """Test getting a session that doesn't exist."""
        entry = session_mgr.get_session("nonexistent-session-id")
        assert entry is None

    @pytest.mark.asyncio
    async def test_get_expired_session(self, session_mgr, mock_server):
        """Test that expired sessions return None."""
        session_id = session_mgr.create_session("tenant-a", "conn-1", mock_server)

        # Manually expire the session
        session_mgr.sessions[session_id].last_access = time.monotonic() - 10

        entry = session_mgr.get_session(session_id)
        assert entry is None
        assert session_mgr.active_session_count == 0

    @pytest.mark.asyncio
    async def test_get_session_updates_last_access(self, session_mgr, mock_server):
        """Test that getting a session updates last_access."""
        session_id = session_mgr.create_session("tenant-a", "conn-1", mock_server)
        entry = session_mgr.sessions[session_id]
        original_access = entry.last_access

        # Small sleep to ensure time difference
        await asyncio.sleep(0.01)

        entry = session_mgr.get_session(session_id)
        assert entry.last_access > original_access

    @pytest.mark.asyncio
    async def test_close_session(self, session_mgr, mock_server):
        """Test closing a session."""
        session_id = session_mgr.create_session("tenant-a", "conn-1", mock_server)
        assert session_mgr.active_session_count == 1

        session_mgr.close_session(session_id)
        assert session_mgr.active_session_count == 0

    def test_close_nonexistent_session(self, session_mgr):
        """Test closing a session that doesn't exist is a no-op."""
        session_mgr.close_session("nonexistent-session-id")
        assert session_mgr.active_session_count == 0

    @pytest.mark.asyncio
    async def test_max_sessions_per_key_evicts_oldest(self, session_mgr, mock_server):
        """Test that exceeding max sessions per key evicts the oldest."""
        s1 = session_mgr.create_session("tenant-a", "conn-1", mock_server)
        s2 = session_mgr.create_session("tenant-a", "conn-1", mock_server)

        # Both should exist
        assert session_mgr.active_session_count == 2

        # Creating a 3rd should evict s1
        s3 = session_mgr.create_session("tenant-a", "conn-1", mock_server)

        assert session_mgr.active_session_count == 2
        assert session_mgr.get_session(s1) is None
        assert session_mgr.get_session(s2) is not None
        assert session_mgr.get_session(s3) is not None

    @pytest.mark.asyncio
    async def test_max_sessions_per_key_independent(self, session_mgr, mock_server):
        """Test that session limits are per tenant+connector pair."""
        session_mgr.create_session("tenant-a", "conn-1", mock_server)
        session_mgr.create_session("tenant-a", "conn-1", mock_server)
        session_mgr.create_session("tenant-b", "conn-1", mock_server)
        session_mgr.create_session("tenant-b", "conn-1", mock_server)

        assert session_mgr.active_session_count == 4

    @pytest.mark.asyncio
    async def test_unique_session_ids(self, session_mgr, mock_server):
        """Test that all session IDs are unique."""
        ids = set()
        for _ in range(50):
            sid = session_mgr.create_session("tenant-a", "conn-1", mock_server)
            ids.add(sid)
            # Allow evictions to happen, but IDs should still be unique

        assert len(ids) == 50

    @pytest.mark.asyncio
    async def test_shutdown_clears_sessions(self, session_mgr, mock_server):
        """Test that shutdown clears all sessions."""
        session_mgr.create_session("tenant-a", "conn-1", mock_server)
        session_mgr.create_session("tenant-b", "conn-2", mock_server)

        await session_mgr.shutdown()

        assert session_mgr.active_session_count == 0
        assert session_mgr._shutdown is True
