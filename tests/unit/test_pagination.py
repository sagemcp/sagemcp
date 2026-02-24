"""Tests for pagination helpers (offset, cursor, link-header, OData).

Verifies:
- Each paginator yields items from single-page and multi-page responses.
- paginate_offset handles both flat lists and nested results_key responses.
- paginate_link_header parses the Link: <url>; rel="next" header correctly.
- paginate_odata follows @odata.nextLink chains.
- collect_all_pages flattens an async generator and respects max_items.
- _parse_link_next correctly extracts the "next" URL from Link headers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from sage_mcp.connectors.pagination import (
    paginate_offset,
    paginate_cursor,
    paginate_link_header,
    paginate_odata,
    collect_all_pages,
    _parse_link_next,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_response(json_data, link_header=None):
    """Build a mock response object with .json() and .headers."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.headers = {"Link": link_header} if link_header else {}
    return resp


# ---------------------------------------------------------------------------
# paginate_offset
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.asyncio


class TestPaginateOffset:
    """Tests for offset-based (page/per_page) pagination."""

    async def test_single_page(self):
        """Single page with fewer items than per_page yields all items."""
        fetch_page = AsyncMock(
            return_value=make_response([{"id": 1}, {"id": 2}])
        )

        items = []
        async for item in paginate_offset(fetch_page, per_page=10):
            items.append(item)

        assert items == [{"id": 1}, {"id": 2}]
        assert fetch_page.await_count == 1

    async def test_multiple_pages(self):
        """Two pages: first full, second partial -- stops after second."""
        page1 = make_response([{"id": 1}, {"id": 2}])
        page2 = make_response([{"id": 3}])
        fetch_page = AsyncMock(side_effect=[page1, page2])

        items = []
        async for item in paginate_offset(fetch_page, per_page=2):
            items.append(item)

        assert items == [{"id": 1}, {"id": 2}, {"id": 3}]
        assert fetch_page.await_count == 2

    async def test_with_results_key(self):
        """Items nested under a key are extracted correctly."""
        fetch_page = AsyncMock(
            return_value=make_response({"results": [{"id": 1}]})
        )

        items = []
        async for item in paginate_offset(
            fetch_page, per_page=10, results_key="results"
        ):
            items.append(item)

        assert items == [{"id": 1}]

    async def test_empty_first_page(self):
        """Empty first page yields nothing."""
        fetch_page = AsyncMock(return_value=make_response([]))

        items = []
        async for item in paginate_offset(fetch_page, per_page=10):
            items.append(item)

        assert items == []
        assert fetch_page.await_count == 1

    async def test_custom_params(self):
        """Custom page_param and per_page_param names are used."""
        fetch_page = AsyncMock(
            return_value=make_response([{"id": 1}])
        )

        items = []
        async for item in paginate_offset(
            fetch_page,
            page_param="p",
            per_page_param="size",
            per_page=5,
            start_page=0,
        ):
            items.append(item)

        # Verify the params dict passed to fetch_page
        call_args = fetch_page.call_args_list[0]
        params = call_args[0][0]  # positional arg
        assert params == {"p": 0, "size": 5}


# ---------------------------------------------------------------------------
# paginate_cursor
# ---------------------------------------------------------------------------

class TestPaginateCursor:
    """Tests for cursor-based pagination."""

    async def test_single_page(self):
        """No next_cursor in response -- yields items and stops."""
        fetch_page = AsyncMock(
            return_value=make_response({"items": [{"id": 1}], "next_cursor": None})
        )

        items = []
        async for item in paginate_cursor(fetch_page):
            items.append(item)

        assert items == [{"id": 1}]
        assert fetch_page.await_count == 1

    async def test_multiple_pages(self):
        """Cursor chain with 2 pages."""
        page1 = make_response(
            {"items": [{"id": 1}], "next_cursor": "cursor_abc"}
        )
        page2 = make_response(
            {"items": [{"id": 2}], "next_cursor": None}
        )
        fetch_page = AsyncMock(side_effect=[page1, page2])

        items = []
        async for item in paginate_cursor(fetch_page):
            items.append(item)

        assert items == [{"id": 1}, {"id": 2}]
        assert fetch_page.await_count == 2

        # Second call should include cursor param
        second_call_params = fetch_page.call_args_list[1][0][0]
        assert second_call_params == {"cursor": "cursor_abc"}

    async def test_empty_items_stops(self):
        """Empty items list stops pagination even if cursor is present."""
        fetch_page = AsyncMock(
            return_value=make_response(
                {"items": [], "next_cursor": "should_not_follow"}
            )
        )

        items = []
        async for item in paginate_cursor(fetch_page):
            items.append(item)

        assert items == []
        assert fetch_page.await_count == 1


# ---------------------------------------------------------------------------
# paginate_link_header
# ---------------------------------------------------------------------------

class TestPaginateLinkHeader:
    """Tests for Link header (rel=next) pagination."""

    async def test_single_page(self):
        """No Link header -- yields items from the single page."""
        fetch_page = AsyncMock(
            return_value=make_response([{"id": 1}, {"id": 2}])
        )

        items = []
        async for item in paginate_link_header(fetch_page):
            items.append(item)

        assert items == [{"id": 1}, {"id": 2}]
        assert fetch_page.await_count == 1

    async def test_multiple_pages(self):
        """Link: <url>; rel="next" triggers fetching the next page."""
        page1 = make_response(
            [{"id": 1}],
            link_header='<https://api.example.com/items?page=2>; rel="next"',
        )
        page2 = make_response([{"id": 2}])
        fetch_page = AsyncMock(side_effect=[page1, page2])

        items = []
        async for item in paginate_link_header(fetch_page):
            items.append(item)

        assert items == [{"id": 1}, {"id": 2}]
        assert fetch_page.await_count == 2

        # Second call should receive the next URL
        second_call_url = fetch_page.call_args_list[1][0][0]
        assert second_call_url == "https://api.example.com/items?page=2"

    async def test_with_results_key(self):
        """Items nested under a key with Link header pagination."""
        page1 = make_response(
            {"data": [{"id": 1}]},
            link_header='<https://api.example.com/p2>; rel="next"',
        )
        page2 = make_response({"data": [{"id": 2}]})
        fetch_page = AsyncMock(side_effect=[page1, page2])

        items = []
        async for item in paginate_link_header(
            fetch_page, results_key="data"
        ):
            items.append(item)

        assert items == [{"id": 1}, {"id": 2}]


# ---------------------------------------------------------------------------
# paginate_odata
# ---------------------------------------------------------------------------

class TestPaginateOdata:
    """Tests for Microsoft Graph @odata.nextLink pagination."""

    async def test_single_page(self):
        """No @odata.nextLink -- yields items and stops."""
        fetch_page = AsyncMock(
            return_value=make_response({"value": [{"id": 1}]})
        )

        items = []
        async for item in paginate_odata(fetch_page):
            items.append(item)

        assert items == [{"id": 1}]
        assert fetch_page.await_count == 1

    async def test_multiple_pages(self):
        """@odata.nextLink chain with 2 pages."""
        page1 = make_response(
            {
                "value": [{"id": 1}],
                "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/messages?$skip=10",
            }
        )
        page2 = make_response({"value": [{"id": 2}]})
        fetch_page = AsyncMock(side_effect=[page1, page2])

        items = []
        async for item in paginate_odata(fetch_page):
            items.append(item)

        assert items == [{"id": 1}, {"id": 2}]
        assert fetch_page.await_count == 2

        # Second call receives the nextLink URL
        second_url = fetch_page.call_args_list[1][0][0]
        assert second_url == "https://graph.microsoft.com/v1.0/me/messages?$skip=10"

    async def test_empty_value_stops(self):
        """Empty value list stops even if nextLink is present."""
        fetch_page = AsyncMock(
            return_value=make_response(
                {"value": [], "@odata.nextLink": "https://example.com/next"}
            )
        )

        items = []
        async for item in paginate_odata(fetch_page):
            items.append(item)

        assert items == []
        assert fetch_page.await_count == 1


# ---------------------------------------------------------------------------
# collect_all_pages
# ---------------------------------------------------------------------------

class TestCollectAllPages:
    """Tests for collect_all_pages helper."""

    async def test_collect_items(self):
        """Collects all items from an async generator into a list."""
        async def gen():
            for i in range(5):
                yield {"id": i}

        items = await collect_all_pages(gen())
        assert len(items) == 5
        assert items == [{"id": i} for i in range(5)]

    async def test_max_items_limit(self):
        """Stops collecting at max_items."""
        async def gen():
            for i in range(100):
                yield {"id": i}

        items = await collect_all_pages(gen(), max_items=3)
        assert len(items) == 3
        assert items == [{"id": 0}, {"id": 1}, {"id": 2}]

    async def test_empty_generator(self):
        """Empty generator returns empty list."""
        async def gen():
            return
            yield  # noqa: unreachable -- makes this an async generator

        items = await collect_all_pages(gen())
        assert items == []


# ---------------------------------------------------------------------------
# _parse_link_next
# ---------------------------------------------------------------------------

class TestParseLinkNext:
    """Tests for _parse_link_next helper."""

    def test_next_link(self):
        """Extracts the 'next' URL from a Link header."""
        header = '<https://api.github.com/repos?page=2>; rel="next"'
        assert _parse_link_next(header) == "https://api.github.com/repos?page=2"

    def test_multiple_rels(self):
        """Extracts 'next' when multiple rel values are present."""
        header = (
            '<https://api.github.com/repos?page=3>; rel="next", '
            '<https://api.github.com/repos?page=1>; rel="prev", '
            '<https://api.github.com/repos?page=10>; rel="last"'
        )
        assert _parse_link_next(header) == "https://api.github.com/repos?page=3"

    def test_no_next(self):
        """Returns None when no rel="next" is present."""
        header = '<https://api.github.com/repos?page=1>; rel="prev"'
        assert _parse_link_next(header) is None

    def test_empty_header(self):
        """Returns None for empty string."""
        assert _parse_link_next("") is None

    def test_single_quote_rel(self):
        """Handles rel='next' with single quotes."""
        header = "<https://example.com/p2>; rel='next'"
        assert _parse_link_next(header) == "https://example.com/p2"
