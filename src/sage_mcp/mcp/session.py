"""MCP Session Manager for Mcp-Session-Id header handling.

Manages session lifecycle per the MCP spec (2025-06-18):
- HTTP POST `initialize` creates a session and returns Mcp-Session-Id
- Subsequent requests use the session header to reuse pooled MCPServer
- Sessions expire after inactivity (configurable TTL)
- WebSocket connections have implicit sessions tied to connection lifetime
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from .server import MCPServer

logger = logging.getLogger(__name__)


@dataclass
class SessionEntry:
    """A session entry tracking an MCP session."""
    session_id: str
    tenant_slug: str
    connector_id: str
    server: MCPServer
    created_at: float = field(default_factory=time.monotonic)
    last_access: float = field(default_factory=time.monotonic)
    negotiated_version: Optional[str] = None


class SessionManager:
    """Manages MCP sessions for Streamable HTTP transport.

    Sessions are keyed by session_id (UUID4 hex string) and map to
    initialized MCPServer instances.
    """

    def __init__(
        self,
        ttl_seconds: float = 1800,
        max_sessions_per_key: int = 10,
        reap_interval: float = 60,
    ):
        self.sessions: Dict[str, SessionEntry] = {}
        self.ttl_seconds = ttl_seconds
        self.max_sessions_per_key = max_sessions_per_key
        self._reap_interval = reap_interval
        self._reaper_task: Optional[asyncio.Task] = None
        self._shutdown = False

    def create_session(
        self,
        tenant_slug: str,
        connector_id: str,
        server: MCPServer,
        negotiated_version: Optional[str] = None,
    ) -> str:
        """Create a new session.

        Args:
            tenant_slug: Tenant identifier
            connector_id: Connector identifier
            server: Initialized MCPServer instance
            negotiated_version: Negotiated protocol version

        Returns:
            Session ID (UUID4 hex string)

        Raises:
            ValueError: If max sessions per tenant+connector exceeded
        """
        # Check limit per tenant+connector
        key_prefix = f"{tenant_slug}:{connector_id}"
        existing_count = sum(
            1 for entry in self.sessions.values()
            if entry.tenant_slug == tenant_slug and entry.connector_id == connector_id
        )
        if existing_count >= self.max_sessions_per_key:
            # Evict oldest session for this key
            oldest = min(
                (e for e in self.sessions.values()
                 if e.tenant_slug == tenant_slug and e.connector_id == connector_id),
                key=lambda e: e.last_access,
            )
            del self.sessions[oldest.session_id]
            logger.debug("Evicted oldest session %s for %s", oldest.session_id, key_prefix)

        session_id = uuid.uuid4().hex
        self.sessions[session_id] = SessionEntry(
            session_id=session_id,
            tenant_slug=tenant_slug,
            connector_id=connector_id,
            server=server,
            negotiated_version=negotiated_version,
        )

        logger.debug("Created session %s for %s", session_id, key_prefix)

        # Start reaper if not running
        if self._reaper_task is None or self._reaper_task.done():
            self._reaper_task = asyncio.create_task(self._reaper_loop())

        return session_id

    def get_session(self, session_id: str) -> Optional[SessionEntry]:
        """Get session by ID, updating last access time.

        Returns None if session doesn't exist or is expired.
        """
        entry = self.sessions.get(session_id)
        if entry is None:
            return None

        now = time.monotonic()
        if (now - entry.last_access) >= self.ttl_seconds:
            del self.sessions[session_id]
            logger.debug("Session %s expired", session_id)
            return None

        entry.last_access = now
        return entry

    def close_session(self, session_id: str):
        """Close and remove a session."""
        entry = self.sessions.pop(session_id, None)
        if entry:
            logger.debug("Closed session %s", session_id)

    @property
    def active_session_count(self) -> int:
        """Number of active sessions."""
        return len(self.sessions)

    async def _reaper_loop(self):
        """Background task to clean up expired sessions."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self._reap_interval)
                now = time.monotonic()
                expired = [
                    sid for sid, entry in self.sessions.items()
                    if (now - entry.last_access) >= self.ttl_seconds
                ]
                for sid in expired:
                    del self.sessions[sid]
                if expired:
                    logger.debug("Reaped %d expired sessions", len(expired))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in session reaper: %s", e)

    async def shutdown(self):
        """Shut down the session manager."""
        self._shutdown = True
        if self._reaper_task and not self._reaper_task.done():
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                pass
        self.sessions.clear()
