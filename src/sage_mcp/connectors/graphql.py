"""Lightweight async GraphQL client for connectors.

Used by Linear (and future GraphQL APIs). Handles single queries and
Relay-style cursor pagination.
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from .exceptions import ConnectorAPIError

logger = logging.getLogger(__name__)


class GraphQLClient:
    """Async GraphQL client that uses the shared HTTP client with retry."""

    def __init__(
        self,
        endpoint: str,
        auth_header: str = "Authorization",
        auth_value: str = "",
    ):
        self.endpoint = endpoint
        self.auth_header = auth_header
        self.auth_value = auth_value

    async def execute(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a single GraphQL query.

        Args:
            query: GraphQL query string.
            variables: Optional query variables.

        Returns:
            The "data" portion of the response.

        Raises:
            ConnectorAPIError: If the response contains GraphQL errors.
        """
        from .http_client import get_http_client
        from .retry import retry_with_backoff

        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        async def _do_request():
            client = get_http_client()
            response = await client.post(
                self.endpoint,
                json=payload,
                headers={
                    self.auth_header: self.auth_value,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            return response

        response = await retry_with_backoff(_do_request)
        body = response.json()

        if "errors" in body and body["errors"]:
            error_messages = "; ".join(
                e.get("message", "Unknown error") for e in body["errors"]
            )
            raise ConnectorAPIError(
                f"GraphQL error: {error_messages}",
                status_code=response.status_code,
                response_body=str(body["errors"])[:500],
            )

        return body.get("data", {})

    async def paginate_connection(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        connection_path: str = "",
        page_size: int = 50,
        max_pages: int = 50,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Paginate a Relay-style GraphQL connection.

        Expects the query to accept $first (Int) and $after (String) variables,
        and the connection to have the shape:
            { nodes: [...], pageInfo: { hasNextPage, endCursor } }

        Args:
            query: GraphQL query with $first and $after variables.
            variables: Base variables (first/after will be injected).
            connection_path: Dot-separated path to the connection in the data,
                             e.g. "issues" or "team.issues".
            page_size: Number of items per page.
            max_pages: Safety limit on total pages fetched.

        Yields:
            Individual node dicts from the connection.
        """
        vars_ = dict(variables or {})
        vars_["first"] = page_size
        cursor: Optional[str] = None

        for _ in range(max_pages):
            if cursor:
                vars_["after"] = cursor
            elif "after" in vars_:
                del vars_["after"]

            data = await self.execute(query, vars_)

            # Navigate to the connection
            connection = data
            if connection_path:
                for key in connection_path.split("."):
                    connection = connection.get(key, {})

            nodes = connection.get("nodes", [])
            for node in nodes:
                yield node

            page_info = connection.get("pageInfo", {})
            if not page_info.get("hasNextPage") or not nodes:
                break

            cursor = page_info.get("endCursor")
            if not cursor:
                break

    async def collect_connection(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        connection_path: str = "",
        page_size: int = 50,
        max_items: int = 10_000,
    ) -> List[Dict[str, Any]]:
        """Collect all nodes from a Relay connection into a list."""
        items: List[Dict[str, Any]] = []
        async for node in self.paginate_connection(
            query, variables, connection_path, page_size
        ):
            items.append(node)
            if len(items) >= max_items:
                logger.warning("collect_connection hit max_items=%d", max_items)
                break
        return items
