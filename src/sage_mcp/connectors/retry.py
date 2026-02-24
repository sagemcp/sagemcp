"""Retry with exponential backoff for connector HTTP requests.

Transparent to callers — wrap any async callable and it retries on transient failures.
"""

import asyncio
import logging
import random
from typing import Any, Callable, Awaitable, Set

import httpx

from .exceptions import (
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorAPIError,
    ConnectorTimeoutError,
)

logger = logging.getLogger(__name__)

# Status codes that trigger a retry
RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}

# Status codes that should NOT be retried (auth failures)
AUTH_FAILURE_CODES: Set[int] = {401, 403}

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 30.0


async def retry_with_backoff(
    fn: Callable[..., Awaitable[Any]],
    *args: Any,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    **kwargs: Any,
) -> Any:
    """Execute an async function with retry and exponential backoff.

    Retries on:
      - HTTP 429, 500, 502, 503, 504
      - httpx.ConnectError, httpx.TimeoutException

    Never retries:
      - HTTP 401, 403 (raises ConnectorAuthError immediately)

    On 429, uses Retry-After header if present, else exponential backoff.
    Uses full jitter: delay = random(0, min(max_delay, base_delay * 2^attempt)).

    Args:
        fn: Async callable to execute.
        max_retries: Maximum number of retry attempts (default 3).
        base_delay: Base delay in seconds (default 1.0).
        max_delay: Maximum delay cap in seconds (default 30.0).

    Returns:
        The result of fn(*args, **kwargs).

    Raises:
        ConnectorAuthError: On 401/403 (never retried).
        ConnectorRateLimitError: On 429 after exhausting retries.
        ConnectorAPIError: On other HTTP errors after exhausting retries.
        ConnectorTimeoutError: On timeout after exhausting retries.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await fn(*args, **kwargs)

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code

            # Never retry auth failures
            if status in AUTH_FAILURE_CODES:
                raise ConnectorAuthError(
                    f"Authentication failed: HTTP {status}"
                ) from exc

            # Retryable status
            if status in RETRYABLE_STATUS_CODES and attempt < max_retries:
                delay = _compute_delay(
                    attempt, base_delay, max_delay, exc.response
                )
                logger.warning(
                    "Retryable HTTP %d (attempt %d/%d), waiting %.1fs",
                    status,
                    attempt + 1,
                    max_retries,
                    delay,
                )
                last_exception = exc
                await asyncio.sleep(delay)
                continue

            # Exhausted retries or non-retryable status
            if status == 429:
                retry_after = _parse_retry_after(exc.response)
                raise ConnectorRateLimitError(
                    "Rate limited: HTTP 429",
                    retry_after=retry_after,
                ) from exc
            if status == 404:
                from .exceptions import ConnectorNotFoundError

                raise ConnectorNotFoundError(
                    "Not found: HTTP 404"
                ) from exc
            raise ConnectorAPIError(
                f"API error: HTTP {status}",
                status_code=status,
                response_body=exc.response.text[:500],
            ) from exc

        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            if attempt < max_retries:
                delay = _compute_delay(attempt, base_delay, max_delay)
                logger.warning(
                    "Connection error (attempt %d/%d), waiting %.1fs: %s",
                    attempt + 1,
                    max_retries,
                    delay,
                    type(exc).__name__,
                )
                last_exception = exc
                await asyncio.sleep(delay)
                continue

            raise ConnectorTimeoutError(
                f"Request failed after {max_retries} retries: {type(exc).__name__}"
            ) from exc

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception  # pragma: no cover


def _compute_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    response: httpx.Response | None = None,
) -> float:
    """Compute retry delay with full jitter.

    On 429, prefers the Retry-After header value if present.
    """
    if response is not None:
        retry_after = _parse_retry_after(response)
        if retry_after is not None:
            return min(retry_after, max_delay)

    # Full jitter: uniform random in [0, min(max_delay, base * 2^attempt)]
    exp_delay = base_delay * (2**attempt)
    return random.uniform(0, min(exp_delay, max_delay))


def _parse_retry_after(response: httpx.Response) -> float | None:
    """Parse Retry-After header (seconds only, not HTTP-date)."""
    value = response.headers.get("Retry-After") or response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
