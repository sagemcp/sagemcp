"""Log broadcast infrastructure for streaming logs to the admin UI.

Maintains a ring buffer of recent log entries and allows multiple SSE
subscribers to receive real-time log events.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Set


@dataclass
class LogEntry:
    """A structured log entry."""
    timestamp: float
    level: str
    message: str
    logger_name: str
    tenant_slug: Optional[str] = None
    connector_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "logger": self.logger_name,
            "tenant_slug": self.tenant_slug,
            "connector_id": self.connector_id,
            **self.extra,
        }


class LogBroadcaster:
    """Broadcasts log entries to SSE subscribers with a ring buffer for history."""

    def __init__(self, max_history: int = 1000):
        self._history: Deque[LogEntry] = deque(maxlen=max_history)
        self._subscribers: Set[asyncio.Queue] = set()

    def push(self, entry: LogEntry):
        """Push a log entry to the ring buffer and all subscribers."""
        self._history.append(entry)
        dead_queues = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(entry)
            except asyncio.QueueFull:
                dead_queues.append(queue)
        for q in dead_queues:
            self._subscribers.discard(q)

    def get_recent(self, count: int = 100) -> List[LogEntry]:
        """Get the most recent log entries from the ring buffer."""
        entries = list(self._history)
        return entries[-count:]

    def subscribe(self) -> asyncio.Queue:
        """Create a new subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Remove a subscriber queue."""
        self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


class BroadcastHandler(logging.Handler):
    """A logging.Handler that pushes log records to a LogBroadcaster."""

    def __init__(self, broadcaster: LogBroadcaster):
        super().__init__()
        self.broadcaster = broadcaster

    def emit(self, record: logging.LogRecord):
        # Extract tenant/connector context from record extras
        tenant_slug = getattr(record, "tenant_slug", None)
        connector_id = getattr(record, "connector_id", None)

        entry = LogEntry(
            timestamp=record.created,
            level=record.levelname,
            message=record.getMessage(),
            logger_name=record.name,
            tenant_slug=tenant_slug,
            connector_id=connector_id,
        )
        self.broadcaster.push(entry)
