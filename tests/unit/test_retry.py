"""Tests for retry_with_backoff and supporting functions.

Verifies:
- First-call success returns immediately with no retry.
- Retryable HTTP status codes (429, 500, 502, 503, 504) are retried up to max_retries.
- Auth failures (401, 403) are NEVER retried and raise ConnectorAuthError.
- 404 raises ConnectorNotFoundError without retry.
- Connection/timeout errors (httpx.ConnectError, httpx.TimeoutException) are retried.
- Retry-After header is respected for 429 responses.
- Retry exhaustion raises the correct domain exception.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from sage_mcp.connectors.retry import (
    retry_with_backoff,
    _parse_retry_after,
    _compute_delay,
)
from sage_mcp.connectors.exceptions import (
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorAPIError,
    ConnectorTimeoutError,
    ConnectorNotFoundError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_http_error(status_code: int, retry_after=None) -> httpx.HTTPStatusError:
    """Build a mock httpx.HTTPStatusError with the given status code."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.text = f"Error {status_code}"
    response.headers = (
        {"Retry-After": str(retry_after)} if retry_after else {}
    )
    request = MagicMock(spec=httpx.Request)
    return httpx.HTTPStatusError(
        f"{status_code}", request=request, response=response
    )


# Patch asyncio.sleep globally for all tests so we never actually wait.
pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Success / no-retry cases
# ---------------------------------------------------------------------------

@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_success_no_retry(mock_sleep):
    """Function succeeds on first call -- no retry, returns result."""
    fn = AsyncMock(return_value="ok")

    result = await retry_with_backoff(fn, max_retries=3)

    assert result == "ok"
    assert fn.await_count == 1
    mock_sleep.assert_not_awaited()


# ---------------------------------------------------------------------------
# Retryable HTTP status codes
# ---------------------------------------------------------------------------

@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_retry_on_500(mock_sleep):
    """500 triggers retry; succeeds on second attempt."""
    fn = AsyncMock(side_effect=[_make_http_error(500), "ok"])

    result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01)

    assert result == "ok"
    assert fn.await_count == 2
    assert mock_sleep.await_count == 1


@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_retry_on_502(mock_sleep):
    """502 is retryable -- verify it is retried."""
    fn = AsyncMock(side_effect=[_make_http_error(502), "ok"])

    result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01)

    assert result == "ok"
    assert fn.await_count == 2


@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_retry_on_429(mock_sleep):
    """429 is retried; succeeds after two failures."""
    fn = AsyncMock(
        side_effect=[_make_http_error(429), _make_http_error(429), "ok"]
    )

    result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01)

    assert result == "ok"
    assert fn.await_count == 3
    assert mock_sleep.await_count == 2


# ---------------------------------------------------------------------------
# Auth failures -- never retried
# ---------------------------------------------------------------------------

@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_auth_error_401_no_retry(mock_sleep):
    """401 raises ConnectorAuthError immediately with no retry."""
    fn = AsyncMock(side_effect=_make_http_error(401))

    with pytest.raises(ConnectorAuthError, match="Authentication failed"):
        await retry_with_backoff(fn, max_retries=3)

    assert fn.await_count == 1
    mock_sleep.assert_not_awaited()


@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_auth_error_403_no_retry(mock_sleep):
    """403 raises ConnectorAuthError immediately with no retry."""
    fn = AsyncMock(side_effect=_make_http_error(403))

    with pytest.raises(ConnectorAuthError, match="Authentication failed"):
        await retry_with_backoff(fn, max_retries=3)

    assert fn.await_count == 1
    mock_sleep.assert_not_awaited()


# ---------------------------------------------------------------------------
# 404 -- mapped to ConnectorNotFoundError, not retried
# ---------------------------------------------------------------------------

@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_404_raises_not_found(mock_sleep):
    """404 raises ConnectorNotFoundError on first attempt, no retry."""
    fn = AsyncMock(side_effect=_make_http_error(404))

    with pytest.raises(ConnectorNotFoundError, match="Not found"):
        await retry_with_backoff(fn, max_retries=3)

    # 404 is NOT in RETRYABLE_STATUS_CODES, so it falls through to the
    # exhausted-retries branch on the first attempt (attempt 0, which is
    # also < max_retries, but 404 is not retryable).
    assert fn.await_count == 1
    mock_sleep.assert_not_awaited()


# ---------------------------------------------------------------------------
# Retry exhaustion
# ---------------------------------------------------------------------------

@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_max_retries_exhausted_429(mock_sleep):
    """429 exhausts retries and raises ConnectorRateLimitError."""
    fn = AsyncMock(side_effect=_make_http_error(429))

    with pytest.raises(ConnectorRateLimitError, match="Rate limited"):
        await retry_with_backoff(fn, max_retries=2, base_delay=0.01)

    # Initial attempt + 2 retries = 3 calls
    assert fn.await_count == 3
    assert mock_sleep.await_count == 2


@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_max_retries_exhausted_500(mock_sleep):
    """500 exhausts retries and raises ConnectorAPIError."""
    fn = AsyncMock(side_effect=_make_http_error(500))

    with pytest.raises(ConnectorAPIError, match="API error"):
        await retry_with_backoff(fn, max_retries=2, base_delay=0.01)

    assert fn.await_count == 3
    assert mock_sleep.await_count == 2


@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_max_retries_exhausted_429_preserves_retry_after(mock_sleep):
    """When 429 exhausts retries, retry_after is set on the exception."""
    fn = AsyncMock(side_effect=_make_http_error(429, retry_after=60))

    with pytest.raises(ConnectorRateLimitError) as exc_info:
        await retry_with_backoff(fn, max_retries=1, base_delay=0.01)

    assert exc_info.value.retry_after == 60.0


# ---------------------------------------------------------------------------
# Connection / timeout errors
# ---------------------------------------------------------------------------

@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_connection_error_retry(mock_sleep):
    """httpx.ConnectError is retried; succeeds on second attempt."""
    request = MagicMock(spec=httpx.Request)
    fn = AsyncMock(
        side_effect=[httpx.ConnectError("refused", request=request), "ok"]
    )

    result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01)

    assert result == "ok"
    assert fn.await_count == 2
    assert mock_sleep.await_count == 1


@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_timeout_error_retry(mock_sleep):
    """httpx.TimeoutException is retried; succeeds on second attempt."""
    fn = AsyncMock(
        side_effect=[httpx.TimeoutException("timed out"), "ok"]
    )

    result = await retry_with_backoff(fn, max_retries=3, base_delay=0.01)

    assert result == "ok"
    assert fn.await_count == 2


@patch("sage_mcp.connectors.retry.asyncio.sleep", new_callable=AsyncMock)
async def test_timeout_exhausted(mock_sleep):
    """Timeout exhausts retries and raises ConnectorTimeoutError."""
    fn = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(ConnectorTimeoutError, match="Request failed after"):
        await retry_with_backoff(fn, max_retries=2, base_delay=0.01)

    assert fn.await_count == 3
    assert mock_sleep.await_count == 2


# ---------------------------------------------------------------------------
# _parse_retry_after
# ---------------------------------------------------------------------------

class TestParseRetryAfter:
    """Unit tests for _parse_retry_after helper."""

    def test_valid_integer(self):
        """Numeric Retry-After header is parsed to float."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "120"}
        assert _parse_retry_after(response) == 120.0

    def test_valid_float(self):
        """Float Retry-After header is parsed correctly."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "1.5"}
        assert _parse_retry_after(response) == 1.5

    def test_missing_header(self):
        """Missing Retry-After returns None."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {}
        assert _parse_retry_after(response) is None

    def test_invalid_value(self):
        """Non-numeric Retry-After returns None (HTTP-date not supported)."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "Wed, 21 Oct 2025 07:28:00 GMT"}
        assert _parse_retry_after(response) is None

    def test_lowercase_header(self):
        """Retry-after (lowercase) is also accepted."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"retry-after": "30"}
        assert _parse_retry_after(response) == 30.0


# ---------------------------------------------------------------------------
# _compute_delay
# ---------------------------------------------------------------------------

class TestComputeDelay:
    """Unit tests for _compute_delay helper."""

    def test_exponential_backoff_without_response(self):
        """Without a response, delay uses full-jitter exponential backoff."""
        # attempt 0 -> base_delay * 2^0 = 1.0 -> uniform(0, 1.0)
        delay = _compute_delay(attempt=0, base_delay=1.0, max_delay=30.0)
        assert 0 <= delay <= 1.0

        # attempt 2 -> base_delay * 2^2 = 4.0 -> uniform(0, 4.0)
        delay = _compute_delay(attempt=2, base_delay=1.0, max_delay=30.0)
        assert 0 <= delay <= 4.0

    def test_delay_capped_at_max_delay(self):
        """Exponential backoff is capped at max_delay."""
        # attempt 10 -> base_delay * 2^10 = 1024.0, but max_delay is 5.0
        delay = _compute_delay(attempt=10, base_delay=1.0, max_delay=5.0)
        assert 0 <= delay <= 5.0

    def test_retry_after_header_used(self):
        """When response has Retry-After, that value is used instead of jitter."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "10"}

        delay = _compute_delay(
            attempt=0, base_delay=1.0, max_delay=30.0, response=response
        )
        assert delay == 10.0

    def test_retry_after_capped_at_max_delay(self):
        """Retry-After is capped at max_delay."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "60"}

        delay = _compute_delay(
            attempt=0, base_delay=1.0, max_delay=5.0, response=response
        )
        assert delay == 5.0

    def test_invalid_retry_after_falls_back_to_jitter(self):
        """Invalid Retry-After falls back to exponential backoff."""
        response = MagicMock(spec=httpx.Response)
        response.headers = {"Retry-After": "not-a-number"}

        delay = _compute_delay(
            attempt=0, base_delay=1.0, max_delay=30.0, response=response
        )
        # Falls back to jitter: uniform(0, 1.0)
        assert 0 <= delay <= 1.0
