"""SSE event buffer for resumable streams.

Per-session ring buffer keyed by monotonically increasing event ID.
Supports Last-Event-ID-based replay for stream resumption.

Capacity: 100 events per session (configurable)
Memory: ~100 bytes/event * 100 events * 3,000 sessions = ~30MB
"""

import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    """An SSE event with a monotonic ID."""
    event_id: int
    event_type: str
    data: str


class EventBuffer:
    """Ring buffer of SSE events for a single session."""

    def __init__(self, capacity: int = 100):
        self._events: OrderedDict[int, SSEEvent] = OrderedDict()
        self._capacity = capacity
        self._next_id = 1

    def append(self, event_type: str, data: str) -> int:
        """Append an event to the buffer.

        Returns:
            The assigned event ID.
        """
        event_id = self._next_id
        self._next_id += 1

        self._events[event_id] = SSEEvent(
            event_id=event_id,
            event_type=event_type,
            data=data,
        )

        # Evict oldest if over capacity
        while len(self._events) > self._capacity:
            self._events.popitem(last=False)

        return event_id

    def replay_from(self, last_event_id: int) -> List[SSEEvent]:
        """Get all events after the given last_event_id.

        Args:
            last_event_id: The last event ID the client received.

        Returns:
            List of events with IDs > last_event_id, in order.
        """
        return [
            event for eid, event in self._events.items()
            if eid > last_event_id
        ]

    @property
    def latest_id(self) -> int:
        """The most recent event ID, or 0 if empty."""
        if self._events:
            return next(reversed(self._events))
        return 0

    @property
    def size(self) -> int:
        """Number of events in the buffer."""
        return len(self._events)


class EventBufferManager:
    """Manages event buffers for all sessions."""

    def __init__(self, default_capacity: int = 100):
        self._buffers: Dict[str, EventBuffer] = {}
        self._default_capacity = default_capacity

    def get_or_create(self, session_id: str) -> EventBuffer:
        """Get or create an event buffer for a session."""
        buf = self._buffers.get(session_id)
        if buf is None:
            buf = EventBuffer(capacity=self._default_capacity)
            self._buffers[session_id] = buf
        return buf

    def remove(self, session_id: str):
        """Remove a session's event buffer."""
        self._buffers.pop(session_id, None)

    def cleanup_sessions(self, active_session_ids: set):
        """Remove buffers for sessions that no longer exist."""
        orphaned = [sid for sid in self._buffers if sid not in active_session_ids]
        for sid in orphaned:
            del self._buffers[sid]
        if orphaned:
            logger.debug("Cleaned up %d orphaned event buffers", len(orphaned))

    @property
    def size(self) -> int:
        """Number of active event buffers."""
        return len(self._buffers)
