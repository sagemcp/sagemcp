"""Server pool with LRU eviction for caching initialized MCPServer instances.

Eliminates per-request DB queries and MCPServer allocation overhead by caching
initialized instances keyed by (tenant_slug, connector_id).

Design decisions:
- user_token is NOT part of cache key (different users share the same pooled
  server; token is updated per-request on the cached instance)
- asyncio.Lock only on cache-miss path (not on hits)
- LRU eviction when at capacity; TTL-based reaping in background task
- Memory: ~5KB per entry = ~15MB for 3,000 instances
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from .server import MCPServer

logger = logging.getLogger(__name__)


@dataclass
class PoolEntry:
    """A cached MCPServer entry with metadata."""
    server: MCPServer
    last_access: float = field(default_factory=time.monotonic)
    created_at: float = field(default_factory=time.monotonic)
    hit_count: int = 0


class ServerPool:
    """LRU pool of initialized MCPServer instances.

    Caches MCPServer instances keyed by "tenant_slug:connector_id" to avoid
    repeated DB queries and initialization on every request.
    """

    def __init__(
        self,
        max_size: int = 5000,
        ttl_seconds: float = 1800,
        reap_interval: float = 60,
    ):
        self._pool: Dict[str, PoolEntry] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._reap_interval = reap_interval
        self._lock = asyncio.Lock()
        self._reaper_task: Optional[asyncio.Task] = None
        self._shutdown = False

        # Metrics counters
        self.hits = 0
        self.misses = 0

    def _key(self, tenant_slug: str, connector_id: str) -> str:
        return f"{tenant_slug}:{connector_id}"

    async def get_or_create(
        self,
        tenant_slug: str,
        connector_id: str,
        user_token: Optional[str] = None,
    ) -> Optional[MCPServer]:
        """Get a cached MCPServer or create and cache a new one.

        Args:
            tenant_slug: Tenant identifier
            connector_id: Connector identifier
            user_token: User-provided OAuth token (updated per-request, not cached)

        Returns:
            Initialized MCPServer, or None if initialization fails
        """
        key = self._key(tenant_slug, connector_id)

        # Fast path: cache hit (no lock needed in single-threaded asyncio)
        entry = self._pool.get(key)
        if entry is not None:
            now = time.monotonic()
            # Check TTL
            if (now - entry.created_at) < self.ttl_seconds:
                entry.last_access = now
                entry.hit_count += 1
                self.hits += 1
                # Update user token per-request
                if user_token is not None:
                    entry.server.user_token = user_token
                logger.debug("Pool hit for %s (hits: %d)", key, entry.hit_count)
                return entry.server
            else:
                # Expired, remove it
                del self._pool[key]

        # Slow path: cache miss, create new server under lock
        self.misses += 1
        async with self._lock:
            # Double-check after acquiring lock
            entry = self._pool.get(key)
            if entry is not None:
                now = time.monotonic()
                if (now - entry.created_at) < self.ttl_seconds:
                    entry.last_access = now
                    entry.hit_count += 1
                    if user_token is not None:
                        entry.server.user_token = user_token
                    return entry.server
                else:
                    del self._pool[key]

            # Create and initialize new server
            server = MCPServer(tenant_slug, connector_id, user_token)
            success = await server.initialize()
            if not success:
                logger.debug("Pool miss: initialization failed for %s", key)
                return None

            # Evict LRU if at capacity
            if len(self._pool) >= self.max_size:
                self._evict_lru()

            self._pool[key] = PoolEntry(server=server)
            logger.debug("Pool miss: created new entry for %s (pool size: %d)", key, len(self._pool))

            # Start reaper if not running
            if self._reaper_task is None or self._reaper_task.done():
                self._reaper_task = asyncio.create_task(self._reaper_loop())

            return server

    def invalidate(self, tenant_slug: str, connector_id: str):
        """Remove a specific entry from the pool.

        Called when tool states or connector config changes via admin API.
        """
        key = self._key(tenant_slug, connector_id)
        entry = self._pool.pop(key, None)
        if entry:
            logger.debug("Invalidated pool entry: %s", key)

    def invalidate_tenant(self, tenant_slug: str):
        """Remove all entries for a tenant from the pool."""
        prefix = f"{tenant_slug}:"
        keys_to_remove = [k for k in self._pool if k.startswith(prefix)]
        for key in keys_to_remove:
            del self._pool[key]
        if keys_to_remove:
            logger.debug("Invalidated %d pool entries for tenant %s", len(keys_to_remove), tenant_slug)

    def _evict_lru(self):
        """Evict the least recently used entry."""
        if not self._pool:
            return
        lru_key = min(self._pool, key=lambda k: self._pool[k].last_access)
        del self._pool[lru_key]
        logger.debug("Evicted LRU entry: %s", lru_key)

    async def _reaper_loop(self):
        """Background task to clean up expired entries."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self._reap_interval)
                now = time.monotonic()
                expired = [
                    key for key, entry in self._pool.items()
                    if (now - entry.created_at) >= self.ttl_seconds
                ]
                for key in expired:
                    del self._pool[key]
                if expired:
                    logger.debug("Reaped %d expired pool entries", len(expired))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in pool reaper: %s", e)

    @property
    def size(self) -> int:
        """Current number of entries in the pool."""
        return len(self._pool)

    async def shutdown(self):
        """Shut down the pool and cancel background tasks."""
        self._shutdown = True
        if self._reaper_task and not self._reaper_task.done():
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                pass
        self._pool.clear()
