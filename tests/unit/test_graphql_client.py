"""Tests for GraphQLClient (execute, paginate_connection, collect_connection).

Verifies:
- execute() returns the "data" portion of a successful response.
- Variables are included in the request payload when provided.
- GraphQL-level errors ({"errors": [...]}) raise ConnectorAPIError.
- paginate_connection yields nodes across single and multiple pages.
- collect_connection respects max_items.
- The shared HTTP client and retry_with_backoff are used internally.

Note: get_http_client and retry_with_backoff are lazily imported inside
GraphQLClient.execute(), so we patch them at their source modules:
  - sage_mcp.connectors.http_client.get_http_client
  - sage_mcp.connectors.retry.asyncio.sleep (to prevent actual delays)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sage_mcp.connectors.graphql import GraphQLClient
from sage_mcp.connectors.exceptions import ConnectorAPIError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(json_data, status_code=200):
    """Build a mock httpx.Response-like object.

    The mock has .json(), .status_code, and .raise_for_status() (no-op).
    This matches what retry_with_backoff's inner _do_request returns.
    """
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()  # no-op by default
    return resp


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------

class TestGraphQLClientExecute:
    """Tests for GraphQLClient.execute()."""

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_execute_success(self, mock_get_client):
        """Successful query returns the 'data' portion."""
        mock_client = AsyncMock()
        mock_response = _make_response({"data": {"viewer": {"login": "sage"}}})
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        result = await client.execute("query { viewer { login } }")

        assert result == {"viewer": {"login": "sage"}}
        mock_client.post.assert_awaited_once()

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_execute_with_variables(self, mock_get_client):
        """Variables are passed in the request payload."""
        mock_client = AsyncMock()
        mock_response = _make_response({"data": {"issue": {"title": "Bug"}}})
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        result = await client.execute(
            "query($id: ID!) { issue(id: $id) { title } }",
            variables={"id": "123"},
        )

        assert result == {"issue": {"title": "Bug"}}

        # Verify the payload sent to post()
        call_kwargs = mock_client.post.call_args
        json_payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert json_payload["variables"] == {"id": "123"}
        assert "query" in json_payload

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_execute_graphql_error(self, mock_get_client):
        """GraphQL errors in response raise ConnectorAPIError."""
        mock_client = AsyncMock()
        mock_response = _make_response({
            "data": None,
            "errors": [
                {"message": "Field 'foo' not found"},
                {"message": "Syntax error"},
            ],
        })
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        with pytest.raises(ConnectorAPIError, match="GraphQL error"):
            await client.execute("query { foo }")

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_execute_empty_data(self, mock_get_client):
        """Response without 'data' key returns empty dict."""
        mock_client = AsyncMock()
        mock_response = _make_response({"something_else": True})
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        result = await client.execute("query { viewer { login } }")
        assert result == {}

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_execute_custom_auth_header(self, mock_get_client):
        """Custom auth_header name is used in the request."""
        mock_client = AsyncMock()
        mock_response = _make_response({"data": {"ok": True}})
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_header="X-API-Key",
            auth_value="key-abc",
        )

        await client.execute("query { ok }")

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        assert headers["X-API-Key"] == "key-abc"

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_execute_no_variables_omitted_from_payload(self, mock_get_client):
        """When variables is None, 'variables' key is absent from payload."""
        mock_client = AsyncMock()
        mock_response = _make_response({"data": {"ok": True}})
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        await client.execute("query { ok }")

        call_kwargs = mock_client.post.call_args
        json_payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "variables" not in json_payload


# ---------------------------------------------------------------------------
# paginate_connection
# ---------------------------------------------------------------------------

class TestGraphQLClientPaginateConnection:
    """Tests for Relay-style cursor pagination."""

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_single_page(self, mock_get_client):
        """hasNextPage=False yields all nodes and stops."""
        mock_client = AsyncMock()
        mock_response = _make_response({
            "data": {
                "issues": {
                    "nodes": [{"id": "1"}, {"id": "2"}],
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": "cursor1",
                    },
                }
            }
        })
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        nodes = []
        async for node in client.paginate_connection(
            "query($first: Int, $after: String) { issues(first: $first, after: $after) { nodes { id } pageInfo { hasNextPage endCursor } } }",
            connection_path="issues",
        ):
            nodes.append(node)

        assert nodes == [{"id": "1"}, {"id": "2"}]
        assert mock_client.post.await_count == 1

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_multiple_pages(self, mock_get_client):
        """Two pages with cursor advancement."""
        mock_client = AsyncMock()
        page1_response = _make_response({
            "data": {
                "issues": {
                    "nodes": [{"id": "1"}],
                    "pageInfo": {
                        "hasNextPage": True,
                        "endCursor": "cursor_after_1",
                    },
                }
            }
        })
        page2_response = _make_response({
            "data": {
                "issues": {
                    "nodes": [{"id": "2"}],
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": "cursor_after_2",
                    },
                }
            }
        })
        mock_client.post.side_effect = [page1_response, page2_response]
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        nodes = []
        async for node in client.paginate_connection(
            "query($first: Int, $after: String) { issues { nodes { id } pageInfo { hasNextPage endCursor } } }",
            connection_path="issues",
        ):
            nodes.append(node)

        assert nodes == [{"id": "1"}, {"id": "2"}]
        assert mock_client.post.await_count == 2

        # Verify the second call includes "after" variable
        second_call_kwargs = mock_client.post.call_args_list[1]
        json_payload = (
            second_call_kwargs.kwargs.get("json")
            or second_call_kwargs[1].get("json")
        )
        assert json_payload["variables"]["after"] == "cursor_after_1"

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_nested_connection_path(self, mock_get_client):
        """Dot-separated connection_path navigates nested data."""
        mock_client = AsyncMock()
        mock_response = _make_response({
            "data": {
                "team": {
                    "issues": {
                        "nodes": [{"id": "deep"}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        })
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        nodes = []
        async for node in client.paginate_connection(
            "query { team { issues { nodes { id } pageInfo { hasNextPage endCursor } } } }",
            connection_path="team.issues",
        ):
            nodes.append(node)

        assert nodes == [{"id": "deep"}]

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_empty_nodes(self, mock_get_client):
        """Empty nodes list yields nothing."""
        mock_client = AsyncMock()
        mock_response = _make_response({
            "data": {
                "issues": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        })
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        nodes = []
        async for node in client.paginate_connection(
            "query { issues { nodes { id } pageInfo { hasNextPage endCursor } } }",
            connection_path="issues",
        ):
            nodes.append(node)

        assert nodes == []


# ---------------------------------------------------------------------------
# collect_connection
# ---------------------------------------------------------------------------

class TestGraphQLClientCollectConnection:
    """Tests for collect_connection (convenience wrapper)."""

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_collect_all_nodes(self, mock_get_client):
        """Collects all nodes into a list."""
        mock_client = AsyncMock()
        mock_response = _make_response({
            "data": {
                "issues": {
                    "nodes": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        })
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        items = await client.collect_connection(
            "query { issues { nodes { id } pageInfo { hasNextPage endCursor } } }",
            connection_path="issues",
        )

        assert len(items) == 3
        assert items == [{"id": "1"}, {"id": "2"}, {"id": "3"}]

    @patch("sage_mcp.connectors.http_client.get_http_client")
    async def test_collect_connection_max_items(self, mock_get_client):
        """Stops collecting at max_items."""
        mock_client = AsyncMock()
        mock_response = _make_response({
            "data": {
                "issues": {
                    "nodes": [
                        {"id": "1"}, {"id": "2"}, {"id": "3"},
                        {"id": "4"}, {"id": "5"},
                    ],
                    "pageInfo": {"hasNextPage": True, "endCursor": "c1"},
                }
            }
        })
        mock_client.post.return_value = mock_response
        mock_get_client.return_value = mock_client

        client = GraphQLClient(
            endpoint="https://api.example.com/graphql",
            auth_value="Bearer token123",
        )

        items = await client.collect_connection(
            "query { issues { nodes { id } pageInfo { hasNextPage endCursor } } }",
            connection_path="issues",
            max_items=2,
        )

        assert len(items) == 2
        assert items == [{"id": "1"}, {"id": "2"}]
