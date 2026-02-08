"""Pagination helpers for connector HTTP APIs.

Async generators for common pagination patterns. Opt-in utility — existing
connectors don't need to change.
"""

import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


async def paginate_offset(
    fetch_page: Callable[..., Any],
    *,
    page_param: str = "page",
    per_page_param: str = "per_page",
    per_page: int = 100,
    start_page: int = 1,
    results_key: Optional[str] = None,
    max_pages: int = 50,
) -> AsyncIterator[Dict[str, Any]]:
    """Paginate APIs that use page/per_page offset pagination (GitLab, Bitbucket).

    Args:
        fetch_page: Async callable(params: dict) -> httpx.Response
        page_param: Query parameter name for page number.
        per_page_param: Query parameter name for page size.
        per_page: Items per page.
        start_page: First page number (usually 1).
        results_key: If set, extract items from response_json[results_key].
                     If None, the response JSON is expected to be a list.
        max_pages: Safety limit on total pages fetched.
    """
    page = start_page
    for _ in range(max_pages):
        params = {page_param: page, per_page_param: per_page}
        response = await fetch_page(params)
        data = response.json()

        items = data[results_key] if results_key else data
        if not items:
            break

        for item in items:
            yield item

        if len(items) < per_page:
            break

        page += 1


async def paginate_cursor(
    fetch_page: Callable[..., Any],
    *,
    cursor_param: str = "cursor",
    results_key: str = "items",
    cursor_key: str = "next_cursor",
    max_pages: int = 50,
) -> AsyncIterator[Dict[str, Any]]:
    """Paginate APIs that use cursor/token pagination (Slack, Discord, Gmail).

    Args:
        fetch_page: Async callable(params: dict) -> httpx.Response
        cursor_param: Query parameter name for the cursor.
        results_key: Key in response JSON containing the items list.
        cursor_key: Key in response JSON containing the next cursor.
        max_pages: Safety limit.
    """
    cursor: Optional[str] = None
    for _ in range(max_pages):
        params = {}
        if cursor:
            params[cursor_param] = cursor

        response = await fetch_page(params)
        data = response.json()

        items = data.get(results_key, [])
        for item in items:
            yield item

        cursor = data.get(cursor_key)
        if not cursor or not items:
            break


async def paginate_link_header(
    fetch_page: Callable[..., Any],
    *,
    initial_url: Optional[str] = None,
    results_key: Optional[str] = None,
    max_pages: int = 50,
) -> AsyncIterator[Dict[str, Any]]:
    """Paginate APIs that use Link rel="next" header (GitHub, GitLab).

    Args:
        fetch_page: Async callable(url: str | None) -> httpx.Response.
                    When url is None, fetch the first page.
        results_key: If set, extract items from response_json[results_key].
        max_pages: Safety limit.
    """
    url = initial_url
    for _ in range(max_pages):
        response = await fetch_page(url)
        data = response.json()

        items = data[results_key] if results_key else data
        if not items:
            break

        for item in items:
            yield item

        # Parse Link header for next URL
        next_url = _parse_link_next(response.headers.get("Link", ""))
        if not next_url:
            break
        url = next_url


async def paginate_odata(
    fetch_page: Callable[..., Any],
    *,
    results_key: str = "value",
    max_pages: int = 50,
) -> AsyncIterator[Dict[str, Any]]:
    """Paginate Microsoft Graph APIs using @odata.nextLink.

    Args:
        fetch_page: Async callable(url: str | None) -> httpx.Response.
                    When url is None, fetch the first page.
        results_key: Key containing items (default "value").
        max_pages: Safety limit.
    """
    url: Optional[str] = None
    for _ in range(max_pages):
        response = await fetch_page(url)
        data = response.json()

        items = data.get(results_key, [])
        for item in items:
            yield item

        next_link = data.get("@odata.nextLink")
        if not next_link or not items:
            break
        url = next_link


async def collect_all_pages(
    paginator: AsyncIterator[Dict[str, Any]],
    max_items: int = 10_000,
) -> List[Dict[str, Any]]:
    """Flatten any async paginator into a list.

    Args:
        paginator: An async iterator yielding items.
        max_items: Safety cap on total items collected.

    Returns:
        List of all items.
    """
    items: List[Dict[str, Any]] = []
    async for item in paginator:
        items.append(item)
        if len(items) >= max_items:
            logger.warning("collect_all_pages hit max_items=%d", max_items)
            break
    return items


def _parse_link_next(link_header: str) -> Optional[str]:
    """Extract the 'next' URL from a Link header.

    Example: '<https://api.example.com/items?page=2>; rel="next"'
    """
    if not link_header:
        return None

    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part or "rel='next'" in part:
            # Extract URL between < and >
            start = part.find("<")
            end = part.find(">")
            if start != -1 and end != -1:
                return part[start + 1 : end]
    return None
