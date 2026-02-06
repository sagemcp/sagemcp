"""Tests for ServerPool with LRU eviction."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sage_mcp.mcp.pool import ServerPool, PoolEntry


@pytest.fixture
def pool():
    """Create a small pool for testing."""
    return ServerPool(max_size=3, ttl_seconds=5, reap_interval=600)


@pytest.fixture
def mock_server():
    """Create a mock MCPServer."""
    server = MagicMock()
    server.user_token = None
    return server


class TestServerPool:
    """Test ServerPool class."""

    def test_pool_initialization(self, pool):
        """Test pool starts empty with correct settings."""
        assert pool.size == 0
        assert pool.max_size == 3
        assert pool.ttl_seconds == 5
        assert pool.hits == 0
        assert pool.misses == 0

    @pytest.mark.asyncio
    async def test_cache_miss_creates_entry(self, pool):
        """Test that a cache miss creates and caches a new server."""
        with patch("sage_mcp.mcp.pool.MCPServer") as MockServer:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.user_token = None
            MockServer.return_value = mock_instance

            server = await pool.get_or_create("tenant-a", "conn-1")

            assert server is mock_instance
            assert pool.size == 1
            assert pool.misses == 1
            assert pool.hits == 0

    @pytest.mark.asyncio
    async def test_cache_hit_returns_same_server(self, pool):
        """Test that a cache hit returns the same server instance."""
        with patch("sage_mcp.mcp.pool.MCPServer") as MockServer:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.user_token = None
            MockServer.return_value = mock_instance

            server1 = await pool.get_or_create("tenant-a", "conn-1")
            server2 = await pool.get_or_create("tenant-a", "conn-1")

            assert server1 is server2
            assert pool.size == 1
            assert pool.hits == 1
            assert pool.misses == 1

    @pytest.mark.asyncio
    async def test_cache_hit_updates_user_token(self, pool):
        """Test that cache hit updates user_token per-request."""
        with patch("sage_mcp.mcp.pool.MCPServer") as MockServer:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.user_token = None
            MockServer.return_value = mock_instance

            # First call is a miss — creates the server
            await pool.get_or_create("tenant-a", "conn-1")
            assert pool.misses == 1

            # Second call is a hit — should update user_token on the cached instance
            await pool.get_or_create("tenant-a", "conn-1", user_token="token-1")
            assert mock_instance.user_token == "token-1"
            assert pool.hits == 1

            # Third call is a hit — should update token again
            await pool.get_or_create("tenant-a", "conn-1", user_token="token-2")
            assert mock_instance.user_token == "token-2"

    @pytest.mark.asyncio
    async def test_lru_eviction(self, pool):
        """Test LRU eviction when pool is at capacity."""
        servers = []
        with patch("sage_mcp.mcp.pool.MCPServer") as MockServer:
            for i in range(4):
                mock_instance = MagicMock()
                mock_instance.initialize = AsyncMock(return_value=True)
                mock_instance.user_token = None
                MockServer.return_value = mock_instance
                server = await pool.get_or_create(f"tenant-{i}", "conn-1")
                servers.append(server)

        # Pool max_size is 3, so 4th entry should have evicted the LRU (oldest)
        assert pool.size == 3
        assert pool.misses == 4

    @pytest.mark.asyncio
    async def test_ttl_expiry(self, pool):
        """Test that expired entries are not returned."""
        with patch("sage_mcp.mcp.pool.MCPServer") as MockServer:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.user_token = None
            MockServer.return_value = mock_instance

            await pool.get_or_create("tenant-a", "conn-1")
            assert pool.size == 1

            # Manually expire the entry
            key = pool._key("tenant-a", "conn-1")
            pool._pool[key].created_at = time.monotonic() - 10  # 10s ago, TTL is 5s

            # New mock for re-creation
            mock_instance2 = MagicMock()
            mock_instance2.initialize = AsyncMock(return_value=True)
            mock_instance2.user_token = None
            MockServer.return_value = mock_instance2

            server = await pool.get_or_create("tenant-a", "conn-1")
            assert server is mock_instance2
            assert pool.misses == 2  # Both were misses

    @pytest.mark.asyncio
    async def test_initialization_failure_returns_none(self, pool):
        """Test that failed initialization returns None and doesn't cache."""
        with patch("sage_mcp.mcp.pool.MCPServer") as MockServer:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=False)
            MockServer.return_value = mock_instance

            server = await pool.get_or_create("tenant-a", "conn-1")

            assert server is None
            assert pool.size == 0

    def test_invalidate_specific_entry(self, pool):
        """Test invalidating a specific entry."""
        pool._pool["tenant-a:conn-1"] = PoolEntry(server=MagicMock())
        pool._pool["tenant-a:conn-2"] = PoolEntry(server=MagicMock())

        pool.invalidate("tenant-a", "conn-1")

        assert pool.size == 1
        assert "tenant-a:conn-1" not in pool._pool
        assert "tenant-a:conn-2" in pool._pool

    def test_invalidate_nonexistent_entry(self, pool):
        """Test invalidating an entry that doesn't exist is a no-op."""
        pool.invalidate("tenant-a", "conn-1")
        assert pool.size == 0

    def test_invalidate_tenant(self, pool):
        """Test invalidating all entries for a tenant."""
        pool._pool["tenant-a:conn-1"] = PoolEntry(server=MagicMock())
        pool._pool["tenant-a:conn-2"] = PoolEntry(server=MagicMock())
        pool._pool["tenant-b:conn-1"] = PoolEntry(server=MagicMock())

        pool.invalidate_tenant("tenant-a")

        assert pool.size == 1
        assert "tenant-b:conn-1" in pool._pool

    @pytest.mark.asyncio
    async def test_shutdown_clears_pool(self, pool):
        """Test that shutdown clears all entries."""
        pool._pool["tenant-a:conn-1"] = PoolEntry(server=MagicMock())
        pool._pool["tenant-a:conn-2"] = PoolEntry(server=MagicMock())

        await pool.shutdown()

        assert pool.size == 0
        assert pool._shutdown is True

    def test_key_generation(self, pool):
        """Test cache key format."""
        assert pool._key("my-tenant", "abc-123") == "my-tenant:abc-123"

    def test_evict_lru_picks_oldest_access(self, pool):
        """Test that eviction removes the entry with oldest last_access."""
        now = time.monotonic()
        pool._pool["a:1"] = PoolEntry(server=MagicMock(), last_access=now - 100)
        pool._pool["b:1"] = PoolEntry(server=MagicMock(), last_access=now - 50)
        pool._pool["c:1"] = PoolEntry(server=MagicMock(), last_access=now)

        pool._evict_lru()

        assert pool.size == 2
        assert "a:1" not in pool._pool
        assert "b:1" in pool._pool
        assert "c:1" in pool._pool
