"""Claude Code / Anthropic Admin connector implementation.

Provides organization management tools for Anthropic accounts via the
Anthropic Admin API (https://api.anthropic.com). Authenticates with an
x-api-key header and requires the anthropic-version header on every request.

19 tools across four groups:
  - Org Stats & Analytics (4): usage reports, cost breakdown, code analytics, org info
  - Admin & Access Management (10): users, invites, workspaces, API keys
  - Workspace Management (3): create workspace, list/add members
  - Normalized Metrics (1): cross-tool CodingToolMetrics aggregation
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

API_BASE = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"


@register_connector(ConnectorType.CLAUDE_CODE)
class ClaudeCodeConnector(ApiKeyBaseConnector):
    """Anthropic Admin API connector for managing organization usage, users,
    workspaces, and API keys.

    Auth: x-api-key header with org-level admin API key stored in
    connector.configuration["api_key"]. Every request includes the
    anthropic-version header.
    """

    @property
    def display_name(self) -> str:
        return "Claude Code"

    @property
    def description(self) -> str:
        return "Manage Anthropic organization usage, users, workspaces, and API keys"

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    async def _make_claude_request(self, method: str, url: str, connector: Connector, **kwargs) -> Any:
        """Make an authenticated request to the Anthropic Admin API.

        Injects the required anthropic-version header, then delegates to
        ApiKeyBaseConnector._make_api_key_request with x-api-key auth.
        """
        headers = kwargs.get("headers", {})
        headers["anthropic-version"] = ANTHROPIC_VERSION
        kwargs["headers"] = headers
        return await self._make_api_key_request(
            method, url, connector,
            auth_header="x-api-key", auth_prefix="",
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    async def get_tools(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Tool]:
        """Return all 19 Claude Code admin tools.

        Tool definitions are static; this method allocates the list once per
        call. At ~2 KB for 19 tools this is well within the per-instance
        memory budget.
        """
        return [
            # ---- Org Stats & Analytics (4) ----
            types.Tool(
                name="claude_code_get_usage",
                description="Get message usage data for the Anthropic organization",
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
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number for pagination",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 30,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
            types.Tool(
                name="claude_code_get_cost_breakdown",
                description="Get cost breakdown data for the Anthropic organization",
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
                name="claude_code_get_code_analytics",
                description="Get Claude Code specific analytics for the organization",
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
                name="claude_code_get_org_info",
                description="Get information about the current Anthropic organization",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            # ---- Admin & Access Management (10) ----
            types.Tool(
                name="claude_code_list_users",
                description="List users in the Anthropic organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number for pagination",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 30,
                            "description": "Number of results per page",
                        },
                    },
                },
            ),
            types.Tool(
                name="claude_code_update_user_role",
                description="Update a user's role in the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The user ID to update",
                        },
                        "role": {
                            "type": "string",
                            "description": "New role for the user (e.g. admin, member)",
                        },
                    },
                    "required": ["user_id", "role"],
                },
            ),
            types.Tool(
                name="claude_code_remove_user",
                description="Remove a user from the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The user ID to remove",
                        },
                    },
                    "required": ["user_id"],
                },
            ),
            types.Tool(
                name="claude_code_list_invites",
                description="List pending invitations for the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number for pagination",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 30,
                            "description": "Number of results per page",
                        },
                    },
                },
            ),
            types.Tool(
                name="claude_code_create_invite",
                description="Invite a user to the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email address of the user to invite",
                        },
                        "role": {
                            "type": "string",
                            "description": "Role to assign (e.g. admin, member)",
                        },
                    },
                    "required": ["email", "role"],
                },
            ),
            types.Tool(
                name="claude_code_delete_invite",
                description="Delete a pending invitation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "invite_id": {
                            "type": "string",
                            "description": "The invitation ID to delete",
                        },
                    },
                    "required": ["invite_id"],
                },
            ),
            types.Tool(
                name="claude_code_list_workspaces",
                description="List workspaces in the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number for pagination",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 30,
                            "description": "Number of results per page",
                        },
                    },
                },
            ),
            types.Tool(
                name="claude_code_get_workspace",
                description="Get details of a specific workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "The workspace ID to retrieve",
                        },
                    },
                    "required": ["workspace_id"],
                },
            ),
            types.Tool(
                name="claude_code_list_api_keys",
                description="List API keys for the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number for pagination",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 30,
                            "description": "Number of results per page",
                        },
                    },
                },
            ),
            types.Tool(
                name="claude_code_update_api_key",
                description="Update an API key's name or status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "api_key_id": {
                            "type": "string",
                            "description": "The API key ID to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New display name for the API key",
                        },
                        "status": {
                            "type": "string",
                            "description": "New status (e.g. active, disabled)",
                        },
                    },
                    "required": ["api_key_id"],
                },
            ),
            # ---- Workspace Management (3) ----
            types.Tool(
                name="claude_code_create_workspace",
                description="Create a new workspace in the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the workspace",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional description of the workspace",
                        },
                    },
                    "required": ["name"],
                },
            ),
            types.Tool(
                name="claude_code_list_workspace_members",
                description="List members of a specific workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "The workspace ID",
                        },
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number for pagination",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 30,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["workspace_id"],
                },
            ),
            types.Tool(
                name="claude_code_add_workspace_member",
                description="Add a member to a workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "The workspace ID",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "The user ID to add",
                        },
                        "role": {
                            "type": "string",
                            "description": "Role within the workspace (e.g. admin, member)",
                        },
                    },
                    "required": ["workspace_id", "user_id"],
                },
            ),
            # ---- Normalized Metrics (1) ----
            types.Tool(
                name="claude_code_get_normalized_metrics",
                description="Get normalized CodingToolMetrics by aggregating usage, cost, and code analytics data for cross-tool comparison",
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

    # ------------------------------------------------------------------
    # Resources (not supported)
    # ------------------------------------------------------------------

    async def get_resources(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Resource]:
        return []

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Dispatch a tool call to the appropriate handler.

        ``tool_name`` arrives with the connector prefix already stripped
        (e.g. "get_usage" not "claude_code_get_usage").
        """
        try:
            if tool_name == "get_usage":
                return await self._get_usage(arguments, connector)
            elif tool_name == "get_cost_breakdown":
                return await self._get_cost_breakdown(arguments, connector)
            elif tool_name == "get_code_analytics":
                return await self._get_code_analytics(arguments, connector)
            elif tool_name == "get_org_info":
                return await self._get_org_info(arguments, connector)
            elif tool_name == "list_users":
                return await self._list_users(arguments, connector)
            elif tool_name == "update_user_role":
                return await self._update_user_role(arguments, connector)
            elif tool_name == "remove_user":
                return await self._remove_user(arguments, connector)
            elif tool_name == "list_invites":
                return await self._list_invites(arguments, connector)
            elif tool_name == "create_invite":
                return await self._create_invite(arguments, connector)
            elif tool_name == "delete_invite":
                return await self._delete_invite(arguments, connector)
            elif tool_name == "list_workspaces":
                return await self._list_workspaces(arguments, connector)
            elif tool_name == "get_workspace":
                return await self._get_workspace(arguments, connector)
            elif tool_name == "list_api_keys":
                return await self._list_api_keys(arguments, connector)
            elif tool_name == "update_api_key":
                return await self._update_api_key(arguments, connector)
            elif tool_name == "create_workspace":
                return await self._create_workspace(arguments, connector)
            elif tool_name == "list_workspace_members":
                return await self._list_workspace_members(arguments, connector)
            elif tool_name == "add_workspace_member":
                return await self._add_workspace_member(arguments, connector)
            elif tool_name == "get_normalized_metrics":
                return await self._get_normalized_metrics(arguments, connector)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            logger.exception("Error executing Claude Code tool '%s'", tool_name)
            return f"Error executing Claude Code tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        return "Claude Code connector does not support resources"

    # ------------------------------------------------------------------
    # Org Stats & Analytics
    # ------------------------------------------------------------------

    async def _get_usage(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/usage_report/messages"""
        params: Dict[str, Any] = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }
        if "page" in arguments:
            params["page"] = arguments["page"]
        if "per_page" in arguments:
            params["per_page"] = arguments["per_page"]

        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/usage_report/messages",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_cost_breakdown(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/cost_report"""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }

        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/cost_report",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_code_analytics(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/usage_report/claude_code"""
        params = {
            "start_date": arguments["start_date"],
            "end_date": arguments["end_date"],
        }

        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/usage_report/claude_code",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_org_info(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/me"""
        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/me",
            connector,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Admin & Access Management
    # ------------------------------------------------------------------

    async def _list_users(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/users"""
        params: Dict[str, Any] = {}
        if "page" in arguments:
            params["page"] = arguments["page"]
        if "per_page" in arguments:
            params["per_page"] = arguments["per_page"]

        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/users",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _update_user_role(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """POST /v1/organizations/users/{user_id}"""
        user_id = arguments["user_id"]
        body = {"role": arguments["role"]}

        response = await self._make_claude_request(
            "POST",
            f"{API_BASE}/v1/organizations/users/{user_id}",
            connector,
            json=body,
        )
        data = response.json()
        data["message"] = "User role updated successfully"
        return json.dumps(data, indent=2)

    async def _remove_user(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """DELETE /v1/organizations/users/{user_id}"""
        user_id = arguments["user_id"]

        await self._make_claude_request(
            "DELETE",
            f"{API_BASE}/v1/organizations/users/{user_id}",
            connector,
        )
        return json.dumps({"user_id": user_id, "message": "User removed successfully"}, indent=2)

    async def _list_invites(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/invites"""
        params: Dict[str, Any] = {}
        if "page" in arguments:
            params["page"] = arguments["page"]
        if "per_page" in arguments:
            params["per_page"] = arguments["per_page"]

        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/invites",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _create_invite(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """POST /v1/organizations/invites"""
        body = {
            "email": arguments["email"],
            "role": arguments["role"],
        }

        response = await self._make_claude_request(
            "POST",
            f"{API_BASE}/v1/organizations/invites",
            connector,
            json=body,
        )
        data = response.json()
        data["message"] = "Invite created successfully"
        return json.dumps(data, indent=2)

    async def _delete_invite(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """DELETE /v1/organizations/invites/{invite_id}"""
        invite_id = arguments["invite_id"]

        await self._make_claude_request(
            "DELETE",
            f"{API_BASE}/v1/organizations/invites/{invite_id}",
            connector,
        )
        return json.dumps({"invite_id": invite_id, "message": "Invite deleted successfully"}, indent=2)

    async def _list_workspaces(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/workspaces"""
        params: Dict[str, Any] = {}
        if "page" in arguments:
            params["page"] = arguments["page"]
        if "per_page" in arguments:
            params["per_page"] = arguments["per_page"]

        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/workspaces",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_workspace(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/workspaces/{workspace_id}"""
        workspace_id = arguments["workspace_id"]

        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/workspaces/{workspace_id}",
            connector,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_api_keys(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/api_keys"""
        params: Dict[str, Any] = {}
        if "page" in arguments:
            params["page"] = arguments["page"]
        if "per_page" in arguments:
            params["per_page"] = arguments["per_page"]

        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/api_keys",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _update_api_key(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """POST /v1/organizations/api_keys/{api_key_id}"""
        api_key_id = arguments["api_key_id"]
        body: Dict[str, Any] = {}
        if "name" in arguments:
            body["name"] = arguments["name"]
        if "status" in arguments:
            body["status"] = arguments["status"]

        response = await self._make_claude_request(
            "POST",
            f"{API_BASE}/v1/organizations/api_keys/{api_key_id}",
            connector,
            json=body,
        )
        data = response.json()
        data["message"] = "API key updated successfully"
        return json.dumps(data, indent=2)

    # ------------------------------------------------------------------
    # Workspace Management
    # ------------------------------------------------------------------

    async def _create_workspace(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """POST /v1/organizations/workspaces"""
        body: Dict[str, Any] = {"name": arguments["name"]}
        if "description" in arguments:
            body["description"] = arguments["description"]

        response = await self._make_claude_request(
            "POST",
            f"{API_BASE}/v1/organizations/workspaces",
            connector,
            json=body,
        )
        data = response.json()
        data["message"] = "Workspace created successfully"
        return json.dumps(data, indent=2)

    async def _list_workspace_members(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """GET /v1/organizations/workspaces/{workspace_id}/members"""
        workspace_id = arguments["workspace_id"]
        params: Dict[str, Any] = {}
        if "page" in arguments:
            params["page"] = arguments["page"]
        if "per_page" in arguments:
            params["per_page"] = arguments["per_page"]

        response = await self._make_claude_request(
            "GET",
            f"{API_BASE}/v1/organizations/workspaces/{workspace_id}/members",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _add_workspace_member(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """POST /v1/organizations/workspaces/{workspace_id}/members"""
        workspace_id = arguments["workspace_id"]
        body: Dict[str, Any] = {"user_id": arguments["user_id"]}
        if "role" in arguments:
            body["role"] = arguments["role"]

        response = await self._make_claude_request(
            "POST",
            f"{API_BASE}/v1/organizations/workspaces/{workspace_id}/members",
            connector,
            json=body,
        )
        data = response.json()
        data["message"] = "Member added to workspace successfully"
        return json.dumps(data, indent=2)

    # ------------------------------------------------------------------
    # Normalized Metrics
    # ------------------------------------------------------------------

    async def _get_normalized_metrics(self, arguments: Dict[str, Any], connector: Connector) -> str:
        """Aggregate usage, cost, and code analytics into CodingToolMetrics.

        Calls three Anthropic endpoints in sequence (usage, cost, code
        analytics), maps available fields into the normalized schema, and
        records unavailable fields in metadata.
        """
        from .coding_tool_metrics import CodingToolMetrics

        start_date = arguments["start_date"]
        end_date = arguments["end_date"]
        period = f"{start_date}/{end_date}"

        # Fetch all three data sources; each may fail independently.
        usage_data: Optional[Dict[str, Any]] = None
        cost_data: Optional[Dict[str, Any]] = None
        code_data: Optional[Dict[str, Any]] = None

        try:
            resp = await self._make_claude_request(
                "GET",
                f"{API_BASE}/v1/organizations/usage_report/messages",
                connector,
                params={"start_date": start_date, "end_date": end_date},
            )
            usage_data = resp.json()
        except Exception as e:
            logger.warning("Failed to fetch usage data for normalized metrics: %s", e)

        try:
            resp = await self._make_claude_request(
                "GET",
                f"{API_BASE}/v1/organizations/cost_report",
                connector,
                params={"start_date": start_date, "end_date": end_date},
            )
            cost_data = resp.json()
        except Exception as e:
            logger.warning("Failed to fetch cost data for normalized metrics: %s", e)

        try:
            resp = await self._make_claude_request(
                "GET",
                f"{API_BASE}/v1/organizations/usage_report/claude_code",
                connector,
                params={"start_date": start_date, "end_date": end_date},
            )
            code_data = resp.json()
        except Exception as e:
            logger.warning("Failed to fetch code analytics for normalized metrics: %s", e)

        # Build the normalized metrics object.
        unavailable: List[str] = []

        # -- Cost metrics --
        total_cost_usd: Optional[float] = None
        if cost_data and "total_cost" in cost_data:
            try:
                total_cost_usd = float(cost_data["total_cost"])
            except (ValueError, TypeError):
                unavailable.append("total_cost_usd")
        else:
            unavailable.append("total_cost_usd")

        # -- Usage metrics --
        total_chat_interactions: Optional[int] = None
        daily_active_users: Optional[int] = None
        if usage_data:
            if "total_messages" in usage_data:
                try:
                    total_chat_interactions = int(usage_data["total_messages"])
                except (ValueError, TypeError):
                    unavailable.append("total_chat_interactions")
            else:
                unavailable.append("total_chat_interactions")

            if "daily_active_users" in usage_data:
                try:
                    daily_active_users = int(usage_data["daily_active_users"])
                except (ValueError, TypeError):
                    unavailable.append("daily_active_users")
            else:
                unavailable.append("daily_active_users")
        else:
            unavailable.extend(["total_chat_interactions", "daily_active_users"])

        # -- Seat metrics (from code analytics if available) --
        total_seats: Optional[int] = None
        active_seats: Optional[int] = None
        seat_utilization_pct: Optional[float] = None
        inactive_seats: Optional[int] = None
        if code_data:
            if "total_seats" in code_data:
                try:
                    total_seats = int(code_data["total_seats"])
                except (ValueError, TypeError):
                    unavailable.append("total_seats")
            else:
                unavailable.append("total_seats")

            if "active_seats" in code_data:
                try:
                    active_seats = int(code_data["active_seats"])
                except (ValueError, TypeError):
                    unavailable.append("active_seats")
            else:
                unavailable.append("active_seats")

            # Derived: utilization and inactive seats
            if total_seats is not None and active_seats is not None and total_seats > 0:
                seat_utilization_pct = round((active_seats / total_seats) * 100, 2)
                inactive_seats = total_seats - active_seats
            else:
                if "seat_utilization_pct" not in unavailable:
                    unavailable.append("seat_utilization_pct")
                if "inactive_seats" not in unavailable:
                    unavailable.append("inactive_seats")
        else:
            unavailable.extend(["total_seats", "active_seats", "seat_utilization_pct", "inactive_seats"])

        # -- Usage by model (from code analytics if available) --
        usage_by_model: Optional[Dict[str, Any]] = None
        if code_data and "usage_by_model" in code_data:
            usage_by_model = code_data["usage_by_model"]
        else:
            unavailable.append("usage_by_model")

        # -- Cost per user --
        cost_per_user_usd: Optional[float] = None
        if total_cost_usd is not None and active_seats is not None and active_seats > 0:
            cost_per_user_usd = round(total_cost_usd / active_seats, 2)
        else:
            unavailable.append("cost_per_user_usd")

        # -- Fields not available from Anthropic API --
        always_unavailable = [
            "total_suggestions",
            "total_acceptances",
            "acceptance_rate_pct",
            "total_lines_suggested",
            "total_lines_accepted",
            "cost_per_accepted_suggestion_usd",
            "usage_by_language",
            "usage_by_editor",
        ]
        unavailable.extend(always_unavailable)

        metrics = CodingToolMetrics(
            tool_name="claude_code",
            period=period,
            total_seats=total_seats,
            active_seats=active_seats,
            seat_utilization_pct=seat_utilization_pct,
            inactive_seats=inactive_seats,
            total_chat_interactions=total_chat_interactions,
            daily_active_users=daily_active_users,
            total_cost_usd=total_cost_usd,
            cost_per_user_usd=cost_per_user_usd,
            usage_by_model=usage_by_model,
            metadata={"unavailable_fields": unavailable},
        )

        return json.dumps(metrics.to_dict(), indent=2)
