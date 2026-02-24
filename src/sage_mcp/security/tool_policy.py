"""Global tool policy enforcement — hot-path safe, pure in-memory lookup.

All active policies are cached in a module-level list with TTL.
``check_tool_policy()`` is a pure function: zero I/O, zero DB queries.
``load_policies()`` is the async loader called periodically or on cache miss.
``invalidate_policy_cache()`` is called by admin mutation endpoints.
"""

import fnmatch
import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lightweight cache entry (avoids importing ORM model on hot path)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _CachedPolicy:
    """Minimal projection of GlobalToolPolicy for in-memory evaluation."""

    pattern: str
    action: str  # "block" or "warn"
    reason: str
    connector_type: Optional[str]  # None means applies to all connectors


@dataclass(frozen=True, slots=True)
class PolicyResult:
    """Result of evaluating a tool name against global policies."""

    allowed: bool
    action: str  # "allow", "block", or "warn"
    reason: str


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_CACHE_TTL: float = 60.0  # seconds

_cached_policies: List[_CachedPolicy] = []
_cache_loaded_at: float = 0.0

# Sentinel for "never loaded"
_RESULT_ALLOWED = PolicyResult(allowed=True, action="allow", reason="")


def invalidate_policy_cache() -> None:
    """Force the next ``check_tool_policy`` caller to see a stale cache.

    The actual reload happens lazily via ``load_policies()`` on the next
    request that detects the TTL has expired, or eagerly if the caller
    awaits ``load_policies()`` immediately after this call.
    """
    global _cache_loaded_at
    _cache_loaded_at = 0.0


async def load_policies(session: AsyncSession) -> None:
    """Fetch active policies from DB and populate the module-level cache.

    Called at startup and after cache invalidation.  This is the ONLY
    function in this module that performs I/O.
    """
    global _cached_policies, _cache_loaded_at

    from ..models.tool_policy import GlobalToolPolicy

    result = await session.execute(
        select(GlobalToolPolicy).where(GlobalToolPolicy.is_active.is_(True))
    )
    rows = result.scalars().all()

    _cached_policies = [
        _CachedPolicy(
            pattern=row.tool_name_pattern,
            action=row.action.value,
            reason=row.reason or "",
            connector_type=row.connector_type,
        )
        for row in rows
    ]
    _cache_loaded_at = time.monotonic()
    logger.debug("Loaded %d active tool policies into cache", len(_cached_policies))


def is_cache_stale() -> bool:
    """Return True if the policy cache needs a refresh."""
    return (time.monotonic() - _cache_loaded_at) > _CACHE_TTL


def check_tool_policy(
    tool_name: str,
    connector_type: Optional[str] = None,
) -> PolicyResult:
    """Evaluate *tool_name* against cached global policies.

    **HOT PATH** — pure function, zero I/O, zero allocations on the
    happy path (no matching policy → returns singleton ``_RESULT_ALLOWED``).

    Matching logic:
    1. Iterate cached policies (typically <100 entries).
    2. Skip policies scoped to a different connector type.
    3. Use ``fnmatch.fnmatch`` for glob matching.
    4. First ``block`` match wins immediately.
    5. A ``warn`` match is noted but does not short-circuit.
    6. If no block/warn matched, return allowed.
    """
    warn_result: Optional[PolicyResult] = None

    for policy in _cached_policies:
        # Skip policies scoped to a different connector type
        if policy.connector_type and connector_type:
            if policy.connector_type.lower() != connector_type.lower():
                continue

        if fnmatch.fnmatch(tool_name, policy.pattern):
            if policy.action == "block":
                return PolicyResult(
                    allowed=False,
                    action="block",
                    reason=policy.reason,
                )
            if policy.action == "warn" and warn_result is None:
                warn_result = PolicyResult(
                    allowed=True,
                    action="warn",
                    reason=policy.reason,
                )

    return warn_result if warn_result is not None else _RESULT_ALLOWED
