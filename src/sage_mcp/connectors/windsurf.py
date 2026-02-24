"""Windsurf/Codeium connector implementation.

Provides 11 tools for managing Windsurf/Codeium team analytics, usage
configuration, credit balance, and normalized cross-tool metrics.

Windsurf uses a non-standard auth model: the service API key is injected into
the JSON request body as ``service_key`` rather than passed via HTTP headers.
All endpoints are POST-only on the Codeium server API.

API reference: https://codeium.com/api (enterprise/team tier required)
Confirmed endpoints: /Analytics, /UserPageAnalytics, /CascadeAnalytics,
    /GetUsageConfig, /UsageConfig, /GetTeamCreditBalance
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import ApiKeyBaseConnector
from .registry import register_connector

logger = logging.getLogger(__name__)

WINDSURF_API_BASE = "https://server.codeium.com/api/v1"


@register_connector(ConnectorType.WINDSURF)
class WindsurfConnector(ApiKeyBaseConnector):
    """Windsurf/Codeium connector for team analytics, usage config, and credits.

    Uses Codeium's server API with service_key injected into the JSON body.
    All authenticated requests go through _make_windsurf_request() which
    handles retry, connection pooling, and key injection.
    """

    @property
    def display_name(self) -> str:
        return "Windsurf"

    @property
    def description(self) -> str:
        return "Manage Windsurf/Codeium team analytics, usage configuration, and credits"

    async def get_tools(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Tool]:
        """Return the 11 Windsurf tools with JSON Schema input definitions.

        Tool names follow the convention: windsurf_{tool_name}.
        Cold path -- called once per tools/list request, result is cached by ServerPool.
        """
        tools = [
            # ----------------------------------------------------------
            # Confirmed API endpoints (6 tools)
            # ----------------------------------------------------------
            types.Tool(
                name="windsurf_get_analytics",
                description="Get team-wide analytics for Windsurf/Codeium usage over a date range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format",
                        },
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "List of metric names to retrieve "
                                "(e.g. ['completions', 'active_users', 'acceptance_rate'])"
                            ),
                        },
                    },
                    "required": ["start_date", "end_date", "metrics"],
                },
            ),
            types.Tool(
                name="windsurf_get_user_analytics",
                description="Get per-user analytics for a specific team member over a date range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "The Codeium user ID to get analytics for",
                        },
                    },
                    "required": ["start_date", "end_date", "user_id"],
                },
            ),
            types.Tool(
                name="windsurf_get_cascade_analytics",
                description="Get Cascade (AI agent) usage analytics over a date range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
            types.Tool(
                name="windsurf_get_usage_config",
                description="Get the current Windsurf/Codeium usage configuration for the team",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="windsurf_set_usage_config",
                description="Update Windsurf/Codeium usage configuration settings for the team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "config": {
                            "type": "object",
                            "description": "Configuration settings to update (key-value pairs)",
                        },
                    },
                    "required": ["config"],
                },
            ),
            types.Tool(
                name="windsurf_get_credit_balance",
                description="Get the team's current Windsurf/Codeium credit balance",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            # ----------------------------------------------------------
            # Stub tools -- APIs not publicly documented (4 tools)
            # ----------------------------------------------------------
            types.Tool(
                name="windsurf_list_members",
                description=(
                    "List team members (stub -- API not publicly available, "
                    "returns workaround instructions)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="windsurf_list_audit_events",
                description=(
                    "List audit events (stub -- API not publicly available, "
                    "returns workaround instructions)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="windsurf_get_spending_breakdown",
                description=(
                    "Get detailed spending breakdown (stub -- API not publicly available, "
                    "returns workaround instructions)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="windsurf_get_seat_info",
                description=(
                    "Get team seat allocation info (stub -- API not publicly available, "
                    "returns workaround instructions)"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            # ----------------------------------------------------------
            # Normalized cross-tool metrics (1 tool)
            # ----------------------------------------------------------
            types.Tool(
                name="windsurf_get_normalized_metrics",
                description=(
                    "Get normalized CodingToolMetrics for cross-tool comparison. "
                    "Aggregates analytics and credit data into a standard schema. "
                    "Many fields will be unavailable due to Windsurf API limitations."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
        ]
        return tools

    async def get_resources(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Resource]:
        """Windsurf connector does not expose any browsable resources."""
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Dispatch a tool call to the appropriate handler.

        Hot path -- tool_name arrives WITHOUT the 'windsurf_' prefix.
        All handlers return json.dumps(result, indent=2) strings.
        """
        # Dispatch table -- avoids elif chain for cleaner profiling
        dispatch = {
            "get_analytics": self._get_analytics,
            "get_user_analytics": self._get_user_analytics,
            "get_cascade_analytics": self._get_cascade_analytics,
            "get_usage_config": self._get_usage_config,
            "set_usage_config": self._set_usage_config,
            "get_credit_balance": self._get_credit_balance,
            "list_members": self._list_members,
            "list_audit_events": self._list_audit_events,
            "get_spending_breakdown": self._get_spending_breakdown,
            "get_seat_info": self._get_seat_info,
            "get_normalized_metrics": self._get_normalized_metrics,
        }

        handler = dispatch.get(tool_name)
        if handler is None:
            return f"Unknown tool: {tool_name}"

        try:
            return await handler(arguments, connector)
        except Exception as e:
            logger.error(
                "Windsurf tool '%s' failed: %s", tool_name, e, exc_info=True
            )
            return f"Error executing Windsurf tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Windsurf connector does not support resources."""
        return "Windsurf connector does not support resources"

    # ------------------------------------------------------------------
    # Auth helper -- Windsurf injects service_key into JSON body
    # ------------------------------------------------------------------

    async def _make_windsurf_request(
        self,
        method: str,
        url: str,
        connector: Connector,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated request to the Codeium server API.

        Windsurf uses a non-standard auth model: the API key (service_key) is
        injected directly into the JSON request body rather than sent as an
        HTTP header. Every endpoint is POST-only.

        Uses the shared httpx client with connection pooling and automatic
        retry on transient failures (429, 5xx, connection errors).

        Args:
            method: HTTP method (always "POST" for Windsurf).
            url: Full request URL.
            connector: Connector instance with api_key in configuration.
            **kwargs: Additional arguments passed to httpx.request().

        Returns:
            httpx.Response with status already checked.

        Raises:
            ConnectorAuthError: If api_key is not configured.
            ConnectorRateLimitError: On 429 after exhausting retries.
            ConnectorAPIError: On other HTTP errors after exhausting retries.
        """
        from .http_client import get_http_client
        from .retry import retry_with_backoff
        from .exceptions import ConnectorAuthError

        api_key = self._get_api_key(connector)
        if not api_key:
            raise ConnectorAuthError("API key not configured")

        # Inject service_key into the JSON body
        body = kwargs.get("json", {}) or {}
        body["service_key"] = api_key
        kwargs["json"] = body

        headers = kwargs.get("headers", {})
        headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers

        async def _do_request():
            client = get_http_client()
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return await retry_with_backoff(_do_request)

    # ------------------------------------------------------------------
    # Confirmed API endpoint handlers (6 tools)
    # ------------------------------------------------------------------

    async def _get_analytics(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /Analytics -- get team-wide analytics.

        Body: start_date, end_date, metrics (array of metric name strings).
        """
        body = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
            "metrics": arguments["metrics"],
        }
        response = await self._make_windsurf_request(
            "POST",
            f"{WINDSURF_API_BASE}/Analytics",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_user_analytics(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /UserPageAnalytics -- get per-user analytics.

        Body: start_date, end_date, user_id.
        """
        body = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
            "user_id": arguments["user_id"],
        }
        response = await self._make_windsurf_request(
            "POST",
            f"{WINDSURF_API_BASE}/UserPageAnalytics",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_cascade_analytics(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /CascadeAnalytics -- get Cascade (agent) usage analytics.

        Body: start_date, end_date.
        """
        body = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        response = await self._make_windsurf_request(
            "POST",
            f"{WINDSURF_API_BASE}/CascadeAnalytics",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_usage_config(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /GetUsageConfig -- get current usage configuration.

        Body: service_key only (injected by _make_windsurf_request).
        """
        response = await self._make_windsurf_request(
            "POST",
            f"{WINDSURF_API_BASE}/GetUsageConfig",
            connector,
        )
        return json.dumps(response.json(), indent=2)

    async def _set_usage_config(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /UsageConfig -- update usage configuration.

        Body: config (object with settings to update).
        """
        body = {
            "config": arguments["config"],
        }
        response = await self._make_windsurf_request(
            "POST",
            f"{WINDSURF_API_BASE}/UsageConfig",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_credit_balance(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /GetTeamCreditBalance -- get team credit balance.

        Body: service_key only (injected by _make_windsurf_request).
        """
        response = await self._make_windsurf_request(
            "POST",
            f"{WINDSURF_API_BASE}/GetTeamCreditBalance",
            connector,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Stub tool handlers (4 tools) -- APIs not publicly documented
    # ------------------------------------------------------------------

    async def _list_members(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """Stub -- member listing API is not publicly available."""
        return json.dumps(
            {
                "error": "API not available",
                "status": "stub",
                "workaround": (
                    "Export member list from Windsurf team settings "
                    "dashboard at https://codeium.com/team"
                ),
            },
            indent=2,
        )

    async def _list_audit_events(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """Stub -- audit events API is not publicly available."""
        return json.dumps(
            {
                "error": "API not available",
                "status": "stub",
                "workaround": (
                    "Contact Codeium enterprise support for audit log exports"
                ),
            },
            indent=2,
        )

    async def _get_spending_breakdown(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """Stub -- spending breakdown API is not publicly available."""
        return json.dumps(
            {
                "error": "API not available",
                "status": "stub",
                "workaround": (
                    "Use windsurf_get_credit_balance for aggregate credit data, "
                    "or check billing in Codeium dashboard"
                ),
            },
            indent=2,
        )

    async def _get_seat_info(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """Stub -- seat info API is not publicly available."""
        return json.dumps(
            {
                "error": "API not available",
                "status": "stub",
                "workaround": (
                    "Check team seat information in Windsurf dashboard "
                    "at https://codeium.com/team/settings"
                ),
            },
            indent=2,
        )

    # ------------------------------------------------------------------
    # Normalized cross-tool metrics
    # ------------------------------------------------------------------

    async def _get_normalized_metrics(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """Aggregate analytics + credit data into CodingToolMetrics.

        Calls the analytics and credit balance endpoints, then maps available
        fields into the normalized schema. Windsurf's API surface is limited,
        so many fields will be None with their names listed in
        metadata["unavailable_fields"].

        Returns:
            JSON string of CodingToolMetrics.to_dict().
        """
        from .coding_tool_metrics import CodingToolMetrics

        start_date = arguments["start_date"]
        end_date = arguments["end_date"]
        period = f"{start_date}/{end_date}"

        unavailable_fields = [
            "total_seats",
            "active_seats",
            "seat_utilization_pct",
            "inactive_seats",
            "total_suggestions",
            "total_acceptances",
            "acceptance_rate_pct",
            "total_lines_suggested",
            "total_lines_accepted",
            "cost_per_user_usd",
            "cost_per_accepted_suggestion_usd",
            "usage_by_language",
            "usage_by_editor",
        ]

        # Fetch analytics data -- request broad metrics
        analytics_data = {}
        try:
            analytics_body = {
                "start_date": start_date,
                "end_date": end_date,
                "metrics": [
                    "completions",
                    "active_users",
                    "acceptance_rate",
                    "chat_interactions",
                ],
            }
            response = await self._make_windsurf_request(
                "POST",
                f"{WINDSURF_API_BASE}/Analytics",
                connector,
                json=analytics_body,
            )
            analytics_data = response.json()
        except Exception as e:
            logger.warning("Failed to fetch Windsurf analytics for normalized metrics: %s", e)

        # Fetch credit balance
        credit_data = {}
        try:
            response = await self._make_windsurf_request(
                "POST",
                f"{WINDSURF_API_BASE}/GetTeamCreditBalance",
                connector,
            )
            credit_data = response.json()
        except Exception as e:
            logger.warning("Failed to fetch Windsurf credit balance for normalized metrics: %s", e)

        # Map available data into CodingToolMetrics fields.
        # The analytics response structure varies; extract what we can.
        total_chat_interactions = analytics_data.get("chat_interactions")
        daily_active_users = analytics_data.get("active_users")
        total_cost_usd = credit_data.get("total_credits_used")
        usage_by_model = analytics_data.get("usage_by_model")

        metrics = CodingToolMetrics(
            tool_name="windsurf",
            period=period,
            total_chat_interactions=total_chat_interactions,
            daily_active_users=daily_active_users,
            total_cost_usd=total_cost_usd,
            usage_by_model=usage_by_model,
            metadata={
                "unavailable_fields": unavailable_fields,
                "raw_analytics": analytics_data,
                "raw_credit_balance": credit_data,
            },
        )

        return json.dumps(metrics.to_dict(), indent=2)
