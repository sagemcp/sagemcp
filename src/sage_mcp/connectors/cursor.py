"""Cursor IDE connector implementation.

Provides 18 tools for managing Cursor team analytics, members, spending,
audit logs, and governance settings via the Cursor Business API.

Authentication: Basic Auth with API key as username (colon-terminated, no password).
API base: https://api2.cursor.sh
"""

import base64
import json
import logging
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import ApiKeyBaseConnector
from .registry import register_connector

logger = logging.getLogger(__name__)

CURSOR_API_BASE = "https://api2.cursor.sh"


@register_connector(ConnectorType.CURSOR)
class CursorConnector(ApiKeyBaseConnector):
    """Cursor IDE connector for team analytics, members, spending, and governance.

    Uses Cursor Business API with Basic Auth (API key as username, no password).
    All authenticated requests go through _make_cursor_request() which handles
    retry, connection pooling, and Basic Auth injection.
    """

    @property
    def display_name(self) -> str:
        return "Cursor"

    @property
    def description(self) -> str:
        return "Manage Cursor team analytics, members, spending, and audit logs"

    async def _make_cursor_request(
        self, method: str, url: str, connector: Connector, **kwargs: Any
    ) -> Any:
        """Make an authenticated HTTP request using Cursor Basic Auth.

        Cursor's API uses HTTP Basic Auth with the API key as the username
        and an empty password (key followed by a colon, base64-encoded).

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full request URL.
            connector: Connector instance containing the API key in configuration.
            **kwargs: Additional arguments passed to httpx.request().

        Returns:
            httpx.Response with status already checked.

        Raises:
            ConnectorAuthError: If API key is not configured.
        """
        from .http_client import get_http_client
        from .retry import retry_with_backoff
        from .exceptions import ConnectorAuthError

        api_key = self._get_api_key(connector)
        if not api_key:
            raise ConnectorAuthError("API key not configured")

        headers = kwargs.get("headers", {})
        credentials = base64.b64encode(f"{api_key}:".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
        kwargs["headers"] = headers

        async def _do_request():
            client = get_http_client()
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await retry_with_backoff(_do_request)

    async def get_tools(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Tool]:
        """Return the 18 Cursor tools with JSON Schema input definitions.

        Tool names follow the convention: cursor_{tool_name}.
        Cold path -- called once per tools/list request, result is cached by ServerPool.
        """
        date_range_schema = {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO 8601 format (e.g. 2024-01-01)",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in ISO 8601 format (e.g. 2024-01-31)",
                },
            },
            "required": ["start_date", "end_date"],
        }

        tools = [
            # ---- Analytics (11 tools) ----
            types.Tool(
                name="cursor_get_agent_edits",
                description="Get team agent edit analytics for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_get_tab_usage",
                description="Get team tab/autocomplete usage analytics for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_get_daily_active_users",
                description="Get daily active user counts for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_get_model_usage",
                description="Get model usage breakdown for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_get_top_file_extensions",
                description="Get top file extensions used by the team for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_get_mcp_adoption",
                description="Get MCP (Model Context Protocol) adoption analytics for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_get_commands_adoption",
                description="Get commands adoption analytics for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_get_leaderboard",
                description="Get team usage leaderboard for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_get_daily_usage_data",
                description="Get detailed daily usage data for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_get_usage_events",
                description="Get filtered usage events for specific users and event types",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in ISO 8601 format (e.g. 2024-01-01)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in ISO 8601 format (e.g. 2024-01-31)",
                        },
                        "user_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of user IDs to filter events for",
                        },
                        "event_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of event types to filter (e.g. agent_edit, tab_accept)",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
            types.Tool(
                name="cursor_get_client_versions",
                description="Get client version distribution for the team over a date range",
                inputSchema=date_range_schema,
            ),
            # ---- Admin & Billing (5 tools) ----
            types.Tool(
                name="cursor_list_members",
                description="List all members of the Cursor team",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="cursor_remove_member",
                description="Remove a member from the Cursor team by user ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The user ID of the member to remove",
                        },
                    },
                    "required": ["user_id"],
                },
            ),
            types.Tool(
                name="cursor_get_spending",
                description="Get team spending breakdown for a date range",
                inputSchema=date_range_schema,
            ),
            types.Tool(
                name="cursor_set_user_spend_limit",
                description="Set a spending limit in USD for a specific team member",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The user ID to set the spending limit for",
                        },
                        "limit_usd": {
                            "type": "number",
                            "description": "The spending limit in USD",
                        },
                    },
                    "required": ["user_id", "limit_usd"],
                },
            ),
            types.Tool(
                name="cursor_list_audit_events",
                description="List audit log events with optional pagination",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in ISO 8601 format (e.g. 2024-01-01)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in ISO 8601 format (e.g. 2024-01-31)",
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Number of results per page (default determined by API)",
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor from a previous response",
                        },
                    },
                    "required": [],
                },
            ),
            # ---- Governance (1 tool) ----
            types.Tool(
                name="cursor_get_repo_blocklists",
                description="Get the list of blocked repositories for the team",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            # ---- Normalized metrics (1 tool) ----
            types.Tool(
                name="cursor_get_normalized_metrics",
                description="Get normalized CodingToolMetrics for cross-tool comparison (DAU, spending, members)",
                inputSchema=date_range_schema,
            ),
        ]
        return tools

    async def get_resources(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Resource]:
        """Cursor connector does not expose any resources."""
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Dispatch a tool call to the appropriate handler.

        Hot path -- tool_name arrives WITHOUT the 'cursor_' prefix.
        All handlers return json.dumps(result, indent=2) strings.
        """
        dispatch = {
            "get_agent_edits": self._get_agent_edits,
            "get_tab_usage": self._get_tab_usage,
            "get_daily_active_users": self._get_daily_active_users,
            "get_model_usage": self._get_model_usage,
            "get_top_file_extensions": self._get_top_file_extensions,
            "get_mcp_adoption": self._get_mcp_adoption,
            "get_commands_adoption": self._get_commands_adoption,
            "get_leaderboard": self._get_leaderboard,
            "get_daily_usage_data": self._get_daily_usage_data,
            "get_usage_events": self._get_usage_events,
            "get_client_versions": self._get_client_versions,
            "list_members": self._list_members,
            "remove_member": self._remove_member,
            "get_spending": self._get_spending,
            "set_user_spend_limit": self._set_user_spend_limit,
            "list_audit_events": self._list_audit_events,
            "get_repo_blocklists": self._get_repo_blocklists,
            "get_normalized_metrics": self._get_normalized_metrics,
        }

        handler = dispatch.get(tool_name)
        if handler is None:
            return f"Unknown tool: {tool_name}"

        try:
            return await handler(arguments, connector)
        except Exception as e:
            logger.error(
                "Cursor tool '%s' failed: %s", tool_name, e, exc_info=True
            )
            return f"Error executing Cursor tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Cursor connector does not support resources."""
        return "Cursor connector does not support resources"

    # ------------------------------------------------------------------
    # Analytics tool handlers (11 tools)
    # ------------------------------------------------------------------

    async def _get_agent_edits(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /analytics/team/agent-edits -- team agent edit analytics."""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/analytics/team/agent-edits",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_tab_usage(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /analytics/team/tabs -- team tab/autocomplete usage."""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/analytics/team/tabs",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_daily_active_users(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /analytics/team/dau -- daily active user counts."""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/analytics/team/dau",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_model_usage(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /analytics/team/models -- model usage breakdown."""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/analytics/team/models",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_top_file_extensions(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /analytics/team/top-file-extensions -- top file extensions used."""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/analytics/team/top-file-extensions",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_mcp_adoption(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /analytics/team/mcp -- MCP adoption analytics."""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/analytics/team/mcp",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_commands_adoption(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /analytics/team/commands -- commands adoption analytics."""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/analytics/team/commands",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_leaderboard(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /analytics/team/leaderboard -- team usage leaderboard."""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/analytics/team/leaderboard",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_daily_usage_data(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /teams/daily-usage-data -- detailed daily usage data."""
        body = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "POST",
            f"{CURSOR_API_BASE}/teams/daily-usage-data",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_usage_events(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /teams/filtered-usage-events -- filtered usage events."""
        body: Dict[str, Any] = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        if "user_ids" in arguments:
            body["user_ids"] = arguments["user_ids"]
        if "event_types" in arguments:
            body["event_types"] = arguments["event_types"]

        response = await self._make_cursor_request(
            "POST",
            f"{CURSOR_API_BASE}/teams/filtered-usage-events",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_client_versions(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /analytics/team/client-versions -- client version distribution."""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/analytics/team/client-versions",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Admin & Billing tool handlers (5 tools)
    # ------------------------------------------------------------------

    async def _list_members(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /teams/members -- list all team members."""
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/teams/members",
            connector,
        )
        return json.dumps(response.json(), indent=2)

    async def _remove_member(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /teams/remove-member -- remove a member from the team."""
        body = {"user_id": arguments["user_id"]}
        response = await self._make_cursor_request(
            "POST",
            f"{CURSOR_API_BASE}/teams/remove-member",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_spending(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /teams/spend -- team spending breakdown."""
        body = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_cursor_request(
            "POST",
            f"{CURSOR_API_BASE}/teams/spend",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _set_user_spend_limit(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /teams/user-spend-limit -- set spending limit for a user."""
        body = {
            "user_id": arguments["user_id"],
            "limit_usd": arguments["limit_usd"],
        }
        response = await self._make_cursor_request(
            "POST",
            f"{CURSOR_API_BASE}/teams/user-spend-limit",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_audit_events(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /teams/audit-logs -- list audit log events with optional pagination."""
        params: Dict[str, Any] = {}
        if "start_date" in arguments:
            params["start_date"] = arguments["start_date"]
        if "end_date" in arguments:
            params["end_date"] = arguments["end_date"]
        if "per_page" in arguments:
            params["per_page"] = arguments["per_page"]
        if "cursor" in arguments:
            params["cursor"] = arguments["cursor"]

        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/teams/audit-logs",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Governance tool handlers (1 tool)
    # ------------------------------------------------------------------

    async def _get_repo_blocklists(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /settings/repo-blocklists/repos -- get blocked repositories."""
        response = await self._make_cursor_request(
            "GET",
            f"{CURSOR_API_BASE}/settings/repo-blocklists/repos",
            connector,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Normalized metrics tool handler (1 tool)
    # ------------------------------------------------------------------

    async def _get_normalized_metrics(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """Aggregate DAU, spending, and members into CodingToolMetrics.

        Calls three Cursor API endpoints in sequence:
        1. GET /analytics/team/dau -- daily active users
        2. POST /teams/spend -- spending data
        3. GET /teams/members -- team member list

        Fields that cannot be derived from the Cursor API are marked as
        unavailable in metadata["unavailable_fields"].
        """
        from .coding_tool_metrics import CodingToolMetrics

        start_date = arguments["start_date"]
        end_date = arguments["end_date"]
        period = f"{start_date}/{end_date}"

        unavailable_fields = [
            "total_suggestions",
            "total_acceptances",
            "acceptance_rate_pct",
            "total_lines_suggested",
            "total_lines_accepted",
            "total_chat_interactions",
            "inactive_seats",
            "cost_per_accepted_suggestion_usd",
            "usage_by_language",
            "usage_by_editor",
        ]

        # Fetch DAU data
        dau_value = None
        try:
            dau_response = await self._make_cursor_request(
                "GET",
                f"{CURSOR_API_BASE}/analytics/team/dau",
                connector,
                params={"start_date": start_date, "end_date": end_date},
            )
            dau_data = dau_response.json()
            # Extract the most recent DAU value from the response
            if isinstance(dau_data, list) and len(dau_data) > 0:
                # Take the last entry's count as the most recent DAU
                last_entry = dau_data[-1]
                dau_value = last_entry.get("count") or last_entry.get("dau") or last_entry.get("value")
            elif isinstance(dau_data, dict):
                dau_value = dau_data.get("dau") or dau_data.get("count") or dau_data.get("value")
        except Exception as e:
            logger.warning("Failed to fetch Cursor DAU data: %s", e)

        # Fetch spending data
        total_cost = None
        try:
            spend_response = await self._make_cursor_request(
                "POST",
                f"{CURSOR_API_BASE}/teams/spend",
                connector,
                json={"start_date": start_date, "end_date": end_date},
            )
            spend_data = spend_response.json()
            if isinstance(spend_data, dict):
                total_cost = spend_data.get("total") or spend_data.get("total_spend") or spend_data.get("total_usd")
            elif isinstance(spend_data, list):
                # Sum up individual entries if the response is a list
                total_cost = sum(
                    entry.get("amount", 0) or entry.get("spend", 0) or entry.get("cost", 0)
                    for entry in spend_data
                )
        except Exception as e:
            logger.warning("Failed to fetch Cursor spending data: %s", e)

        # Fetch members data
        total_seats = None
        active_seats = None
        try:
            members_response = await self._make_cursor_request(
                "GET",
                f"{CURSOR_API_BASE}/teams/members",
                connector,
            )
            members_data = members_response.json()
            if isinstance(members_data, list):
                total_seats = len(members_data)
                active_seats = sum(
                    1 for m in members_data
                    if m.get("status") == "active" or m.get("is_active", False)
                )
            elif isinstance(members_data, dict):
                members_list = members_data.get("members", [])
                total_seats = len(members_list)
                active_seats = sum(
                    1 for m in members_list
                    if m.get("status") == "active" or m.get("is_active", False)
                )
        except Exception as e:
            logger.warning("Failed to fetch Cursor members data: %s", e)

        # Compute derived metrics
        seat_utilization = None
        if total_seats and active_seats is not None and total_seats > 0:
            seat_utilization = round((active_seats / total_seats) * 100, 2)

        cost_per_user = None
        if total_cost is not None and active_seats and active_seats > 0:
            cost_per_user = round(total_cost / active_seats, 2)

        # Fetch model usage for usage_by_model breakdown
        usage_by_model = None
        try:
            model_response = await self._make_cursor_request(
                "GET",
                f"{CURSOR_API_BASE}/analytics/team/models",
                connector,
                params={"start_date": start_date, "end_date": end_date},
            )
            model_data = model_response.json()
            if isinstance(model_data, (list, dict)):
                usage_by_model = model_data
        except Exception as e:
            logger.warning("Failed to fetch Cursor model usage data: %s", e)

        metrics = CodingToolMetrics(
            tool_name="cursor",
            period=period,
            total_seats=total_seats,
            active_seats=active_seats,
            seat_utilization_pct=seat_utilization,
            daily_active_users=dau_value,
            total_cost_usd=total_cost,
            cost_per_user_usd=cost_per_user,
            usage_by_model=usage_by_model,
            metadata={"unavailable_fields": unavailable_fields},
        )

        return json.dumps(metrics.to_dict(), indent=2)
