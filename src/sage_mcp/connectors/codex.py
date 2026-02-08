"""OpenAI Codex / OpenAI Admin connector implementation.

Provides access to the OpenAI organization administration API for managing
usage analytics, costs, users, projects, invites, audit logs, and service
accounts. Authenticates via an organization-scoped Admin API key (Bearer token).

API reference: https://platform.openai.com/docs/api-reference/organization
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import ApiKeyBaseConnector
from .coding_tool_metrics import CodingToolMetrics
from .registry import register_connector

logger = logging.getLogger(__name__)

API_BASE = "https://api.openai.com"


@register_connector(ConnectorType.CODEX)
class CodexConnector(ApiKeyBaseConnector):
    """OpenAI Codex connector for organization administration and usage analytics."""

    @property
    def display_name(self) -> str:
        return "OpenAI Codex"

    @property
    def description(self) -> str:
        return "Manage OpenAI organization usage, costs, users, projects, and audit logs"

    async def get_tools(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Tool]:
        """Return the 17 tools exposed by this connector.

        Tool metadata is static and could be cached, but the list construction
        cost is negligible (~0.1ms) relative to the network round-trip.
        """
        return [
            # ------------------------------------------------------------------
            # Usage & Cost Analytics (4 tools)
            # ------------------------------------------------------------------
            types.Tool(
                name="codex_get_completions_usage",
                description="Get completions usage data for the organization, broken down by time buckets and optional grouping dimensions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_time": {
                            "type": "integer",
                            "description": "Start time as a Unix timestamp (seconds since epoch). Required."
                        },
                        "end_time": {
                            "type": "integer",
                            "description": "End time as a Unix timestamp. Defaults to the current time if omitted."
                        },
                        "bucket_width": {
                            "type": "string",
                            "enum": ["1m", "1h", "1d"],
                            "description": "Width of each time bucket: 1 minute, 1 hour, or 1 day."
                        },
                        "project_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by project IDs."
                        },
                        "user_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by user IDs."
                        },
                        "api_key_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by API key IDs."
                        },
                        "models": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by model names (e.g. gpt-4o, o3-mini)."
                        },
                        "group_by": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["project_id", "user_id", "api_key_id", "model"]
                            },
                            "description": "Dimensions to group results by."
                        }
                    },
                    "required": ["start_time"]
                }
            ),
            types.Tool(
                name="codex_get_cost_breakdown",
                description="Get cost data for the organization, broken down by time buckets and optional grouping dimensions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_time": {
                            "type": "integer",
                            "description": "Start time as a Unix timestamp (seconds since epoch). Required."
                        },
                        "end_time": {
                            "type": "integer",
                            "description": "End time as a Unix timestamp."
                        },
                        "bucket_width": {
                            "type": "string",
                            "enum": ["1m", "1h", "1d"],
                            "description": "Width of each time bucket."
                        },
                        "project_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by project IDs."
                        },
                        "group_by": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["project_id", "line_item"]
                            },
                            "description": "Dimensions to group results by."
                        }
                    },
                    "required": ["start_time"]
                }
            ),
            types.Tool(
                name="codex_get_embeddings_usage",
                description="Get embeddings usage data for the organization, broken down by time buckets and optional grouping dimensions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_time": {
                            "type": "integer",
                            "description": "Start time as a Unix timestamp (seconds since epoch). Required."
                        },
                        "end_time": {
                            "type": "integer",
                            "description": "End time as a Unix timestamp."
                        },
                        "bucket_width": {
                            "type": "string",
                            "enum": ["1m", "1h", "1d"],
                            "description": "Width of each time bucket."
                        },
                        "project_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by project IDs."
                        },
                        "user_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by user IDs."
                        },
                        "api_key_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by API key IDs."
                        },
                        "models": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by model names."
                        },
                        "group_by": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["project_id", "user_id", "api_key_id", "model"]
                            },
                            "description": "Dimensions to group results by."
                        }
                    },
                    "required": ["start_time"]
                }
            ),
            types.Tool(
                name="codex_get_code_interpreter_usage",
                description="Get Code Interpreter session usage data for the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_time": {
                            "type": "integer",
                            "description": "Start time as a Unix timestamp (seconds since epoch). Required."
                        },
                        "end_time": {
                            "type": "integer",
                            "description": "End time as a Unix timestamp."
                        },
                        "bucket_width": {
                            "type": "string",
                            "enum": ["1m", "1h", "1d"],
                            "description": "Width of each time bucket."
                        },
                        "project_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by project IDs."
                        },
                        "group_by": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["project_id"]
                            },
                            "description": "Dimensions to group results by."
                        }
                    },
                    "required": ["start_time"]
                }
            ),
            # ------------------------------------------------------------------
            # Admin & Access Management (9 tools)
            # ------------------------------------------------------------------
            types.Tool(
                name="codex_list_users",
                description="List all users in the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of users to return (default 20)."
                        },
                        "after": {
                            "type": "string",
                            "description": "Cursor for pagination; pass the 'after' value from a previous response."
                        }
                    }
                }
            ),
            types.Tool(
                name="codex_modify_user",
                description="Modify a user's role in the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The ID of the user to modify."
                        },
                        "role": {
                            "type": "string",
                            "enum": ["owner", "reader"],
                            "description": "The new role for the user."
                        }
                    },
                    "required": ["user_id", "role"]
                }
            ),
            types.Tool(
                name="codex_delete_user",
                description="Remove a user from the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The ID of the user to remove."
                        }
                    },
                    "required": ["user_id"]
                }
            ),
            types.Tool(
                name="codex_list_invites",
                description="List pending invitations in the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of invites to return."
                        },
                        "after": {
                            "type": "string",
                            "description": "Cursor for pagination."
                        }
                    }
                }
            ),
            types.Tool(
                name="codex_create_invite",
                description="Invite a new user to the organization by email",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The email address of the person to invite."
                        },
                        "role": {
                            "type": "string",
                            "enum": ["owner", "reader"],
                            "description": "The role to assign to the invited user."
                        }
                    },
                    "required": ["email", "role"]
                }
            ),
            types.Tool(
                name="codex_list_projects",
                description="List all projects in the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of projects to return."
                        },
                        "after": {
                            "type": "string",
                            "description": "Cursor for pagination."
                        },
                        "include_archived": {
                            "type": "boolean",
                            "description": "Whether to include archived projects."
                        }
                    }
                }
            ),
            types.Tool(
                name="codex_get_project",
                description="Get details of a specific project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project to retrieve."
                        }
                    },
                    "required": ["project_id"]
                }
            ),
            types.Tool(
                name="codex_create_project",
                description="Create a new project in the organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the project to create."
                        }
                    },
                    "required": ["name"]
                }
            ),
            types.Tool(
                name="codex_list_project_api_keys",
                description="List API keys associated with a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of API keys to return."
                        },
                        "after": {
                            "type": "string",
                            "description": "Cursor for pagination."
                        }
                    },
                    "required": ["project_id"]
                }
            ),
            # ------------------------------------------------------------------
            # Governance (2 tools)
            # ------------------------------------------------------------------
            types.Tool(
                name="codex_list_audit_events",
                description="List audit log events for the organization, with optional filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "effective_at_start": {
                            "type": "integer",
                            "description": "Return events on or after this Unix timestamp."
                        },
                        "effective_at_end": {
                            "type": "integer",
                            "description": "Return events before this Unix timestamp."
                        },
                        "project_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by project IDs."
                        },
                        "event_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by event types (e.g. 'api_key.created')."
                        },
                        "actor_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by actor (user) IDs."
                        },
                        "actor_emails": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by actor email addresses."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of events to return."
                        },
                        "after": {
                            "type": "string",
                            "description": "Cursor for pagination."
                        }
                    }
                }
            ),
            types.Tool(
                name="codex_list_service_accounts",
                description="List service accounts for a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The ID of the project."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of service accounts to return."
                        },
                        "after": {
                            "type": "string",
                            "description": "Cursor for pagination."
                        }
                    },
                    "required": ["project_id"]
                }
            ),
            # ------------------------------------------------------------------
            # Normalized metrics (1 tool)
            # ------------------------------------------------------------------
            types.Tool(
                name="codex_get_normalized_metrics",
                description="Get normalized CodingToolMetrics for cross-tool comparison. Combines completions usage and cost data into a standard schema.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_time": {
                            "type": "integer",
                            "description": "Start time as a Unix timestamp (seconds since epoch). Required."
                        },
                        "end_time": {
                            "type": "integer",
                            "description": "End time as a Unix timestamp. Defaults to the current time if omitted."
                        }
                    },
                    "required": ["start_time"]
                }
            ),
        ]

    async def get_resources(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Resource]:
        """Codex connector exposes no browsable resources."""
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Dispatch a tool call to the appropriate handler.

        ``tool_name`` arrives with the ``codex_`` prefix already stripped by the
        MCP server layer (e.g. "get_completions_usage", not
        "codex_get_completions_usage").
        """
        api_key = self._get_api_key(connector)
        if not api_key:
            return "Error: OpenAI Admin API key is not configured. Set it in the connector configuration."

        try:
            # Usage & Cost Analytics
            if tool_name == "get_completions_usage":
                return await self._get_completions_usage(arguments, connector)
            elif tool_name == "get_cost_breakdown":
                return await self._get_cost_breakdown(arguments, connector)
            elif tool_name == "get_embeddings_usage":
                return await self._get_embeddings_usage(arguments, connector)
            elif tool_name == "get_code_interpreter_usage":
                return await self._get_code_interpreter_usage(arguments, connector)
            # Admin & Access Management
            elif tool_name == "list_users":
                return await self._list_users(arguments, connector)
            elif tool_name == "modify_user":
                return await self._modify_user(arguments, connector)
            elif tool_name == "delete_user":
                return await self._delete_user(arguments, connector)
            elif tool_name == "list_invites":
                return await self._list_invites(arguments, connector)
            elif tool_name == "create_invite":
                return await self._create_invite(arguments, connector)
            elif tool_name == "list_projects":
                return await self._list_projects(arguments, connector)
            elif tool_name == "get_project":
                return await self._get_project(arguments, connector)
            elif tool_name == "create_project":
                return await self._create_project(arguments, connector)
            elif tool_name == "list_project_api_keys":
                return await self._list_project_api_keys(arguments, connector)
            # Governance
            elif tool_name == "list_audit_events":
                return await self._list_audit_events(arguments, connector)
            elif tool_name == "list_service_accounts":
                return await self._list_service_accounts(arguments, connector)
            # Normalized metrics
            elif tool_name == "get_normalized_metrics":
                return await self._get_normalized_metrics(arguments, connector)
            else:
                return f"Error: Unknown tool '{tool_name}'"
        except Exception as e:
            logger.exception("Codex tool '%s' failed", tool_name)
            return f"Error executing {tool_name}: {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Codex connector does not support resources."""
        return "Codex connector does not support resources"

    # ------------------------------------------------------------------
    # Usage & Cost Analytics handlers
    # ------------------------------------------------------------------

    async def _get_completions_usage(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/usage/completions"""
        params: Dict[str, Any] = {"start_time": arguments["start_time"]}
        if "end_time" in arguments:
            params["end_time"] = arguments["end_time"]
        if "bucket_width" in arguments:
            params["bucket_width"] = arguments["bucket_width"]
        if "project_ids" in arguments:
            params["project_ids"] = arguments["project_ids"]
        if "user_ids" in arguments:
            params["user_ids"] = arguments["user_ids"]
        if "api_key_ids" in arguments:
            params["api_key_ids"] = arguments["api_key_ids"]
        if "models" in arguments:
            params["models"] = arguments["models"]
        if "group_by" in arguments:
            params["group_by"] = arguments["group_by"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/usage/completions",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_cost_breakdown(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/costs"""
        params: Dict[str, Any] = {"start_time": arguments["start_time"]}
        if "end_time" in arguments:
            params["end_time"] = arguments["end_time"]
        if "bucket_width" in arguments:
            params["bucket_width"] = arguments["bucket_width"]
        if "project_ids" in arguments:
            params["project_ids"] = arguments["project_ids"]
        if "group_by" in arguments:
            params["group_by"] = arguments["group_by"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/costs",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_embeddings_usage(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/usage/embeddings"""
        params: Dict[str, Any] = {"start_time": arguments["start_time"]}
        if "end_time" in arguments:
            params["end_time"] = arguments["end_time"]
        if "bucket_width" in arguments:
            params["bucket_width"] = arguments["bucket_width"]
        if "project_ids" in arguments:
            params["project_ids"] = arguments["project_ids"]
        if "user_ids" in arguments:
            params["user_ids"] = arguments["user_ids"]
        if "api_key_ids" in arguments:
            params["api_key_ids"] = arguments["api_key_ids"]
        if "models" in arguments:
            params["models"] = arguments["models"]
        if "group_by" in arguments:
            params["group_by"] = arguments["group_by"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/usage/embeddings",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_code_interpreter_usage(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/usage/code_interpreter_sessions"""
        params: Dict[str, Any] = {"start_time": arguments["start_time"]}
        if "end_time" in arguments:
            params["end_time"] = arguments["end_time"]
        if "bucket_width" in arguments:
            params["bucket_width"] = arguments["bucket_width"]
        if "project_ids" in arguments:
            params["project_ids"] = arguments["project_ids"]
        if "group_by" in arguments:
            params["group_by"] = arguments["group_by"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/usage/code_interpreter_sessions",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Admin & Access Management handlers
    # ------------------------------------------------------------------

    async def _list_users(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/users"""
        params: Dict[str, Any] = {}
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "after" in arguments:
            params["after"] = arguments["after"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/users",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _modify_user(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /v1/organization/users/{user_id}"""
        user_id = arguments["user_id"]
        body = {"role": arguments["role"]}

        response = await self._make_api_key_request(
            "POST",
            f"{API_BASE}/v1/organization/users/{user_id}",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _delete_user(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """DELETE /v1/organization/users/{user_id}"""
        user_id = arguments["user_id"]

        response = await self._make_api_key_request(
            "DELETE",
            f"{API_BASE}/v1/organization/users/{user_id}",
            connector,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_invites(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/invites"""
        params: Dict[str, Any] = {}
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "after" in arguments:
            params["after"] = arguments["after"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/invites",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _create_invite(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /v1/organization/invites"""
        body = {
            "email": arguments["email"],
            "role": arguments["role"],
        }

        response = await self._make_api_key_request(
            "POST",
            f"{API_BASE}/v1/organization/invites",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_projects(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/projects"""
        params: Dict[str, Any] = {}
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "after" in arguments:
            params["after"] = arguments["after"]
        if "include_archived" in arguments:
            params["include_archived"] = arguments["include_archived"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/projects",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_project(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/projects/{project_id}"""
        project_id = arguments["project_id"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/projects/{project_id}",
            connector,
        )
        return json.dumps(response.json(), indent=2)

    async def _create_project(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """POST /v1/organization/projects"""
        body = {"name": arguments["name"]}

        response = await self._make_api_key_request(
            "POST",
            f"{API_BASE}/v1/organization/projects",
            connector,
            json=body,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_project_api_keys(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/projects/{project_id}/api_keys"""
        project_id = arguments["project_id"]
        params: Dict[str, Any] = {}
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "after" in arguments:
            params["after"] = arguments["after"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/projects/{project_id}/api_keys",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Governance handlers
    # ------------------------------------------------------------------

    async def _list_audit_events(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/audit_logs"""
        params: Dict[str, Any] = {}
        if "effective_at_start" in arguments:
            params["effective_at.gte"] = arguments["effective_at_start"]
        if "effective_at_end" in arguments:
            params["effective_at.lt"] = arguments["effective_at_end"]
        if "project_ids" in arguments:
            params["project_ids"] = arguments["project_ids"]
        if "event_types" in arguments:
            params["event_types"] = arguments["event_types"]
        if "actor_ids" in arguments:
            params["actor_ids"] = arguments["actor_ids"]
        if "actor_emails" in arguments:
            params["actor_emails"] = arguments["actor_emails"]
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "after" in arguments:
            params["after"] = arguments["after"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/audit_logs",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_service_accounts(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """GET /v1/organization/projects/{project_id}/service_accounts"""
        project_id = arguments["project_id"]
        params: Dict[str, Any] = {}
        if "limit" in arguments:
            params["limit"] = arguments["limit"]
        if "after" in arguments:
            params["after"] = arguments["after"]

        response = await self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/projects/{project_id}/service_accounts",
            connector,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Normalized metrics handler
    # ------------------------------------------------------------------

    async def _get_normalized_metrics(
        self, arguments: Dict[str, Any], connector: Connector
    ) -> str:
        """Build CodingToolMetrics from completions usage + costs data.

        Fetches both endpoints concurrently, then maps the OpenAI response
        fields into the normalized schema. Fields that have no equivalent in
        the OpenAI Admin API (e.g. seat counts, suggestion acceptance rates)
        are left as None and listed in metadata["unavailable_fields"].
        """
        import asyncio
        import time

        start_time = arguments["start_time"]
        end_time = arguments.get("end_time", int(time.time()))

        # Fetch completions usage and costs concurrently to cut latency.
        usage_params: Dict[str, Any] = {
            "start_time": start_time,
            "end_time": end_time,
            "bucket_width": "1d",
        }
        cost_params: Dict[str, Any] = {
            "start_time": start_time,
            "end_time": end_time,
            "bucket_width": "1d",
        }

        usage_coro = self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/usage/completions",
            connector,
            params=usage_params,
        )
        cost_coro = self._make_api_key_request(
            "GET",
            f"{API_BASE}/v1/organization/costs",
            connector,
            params=cost_params,
        )

        usage_response, cost_response = await asyncio.gather(
            usage_coro, cost_coro, return_exceptions=True
        )

        # Process usage data
        total_requests = 0
        total_input_tokens = 0
        total_output_tokens = 0
        usage_by_model: Dict[str, Any] = {}

        if not isinstance(usage_response, Exception):
            usage_data = usage_response.json()
            for bucket in usage_data.get("data", []):
                for result in bucket.get("results", []):
                    num_requests = result.get("num_model_requests", 0)
                    input_tokens = result.get("input_tokens", 0)
                    output_tokens = result.get("output_tokens", 0)
                    total_requests += num_requests
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
                    model = result.get("model", "unknown")
                    if model not in usage_by_model:
                        usage_by_model[model] = {
                            "requests": 0,
                            "input_tokens": 0,
                            "output_tokens": 0,
                        }
                    usage_by_model[model]["requests"] += num_requests
                    usage_by_model[model]["input_tokens"] += input_tokens
                    usage_by_model[model]["output_tokens"] += output_tokens
        else:
            logger.warning(
                "Failed to fetch completions usage for normalized metrics: %s",
                usage_response,
            )

        # Process cost data
        total_cost_usd: Optional[float] = None
        if not isinstance(cost_response, Exception):
            cost_data = cost_response.json()
            total_cost_cents = 0.0
            for bucket in cost_data.get("data", []):
                for result in bucket.get("results", []):
                    total_cost_cents += result.get("amount", {}).get("value", 0.0)
            # OpenAI returns costs in cents; convert to dollars.
            total_cost_usd = round(total_cost_cents / 100.0, 4)
        else:
            logger.warning(
                "Failed to fetch costs for normalized metrics: %s",
                cost_response,
            )

        # Fields unavailable from the OpenAI Admin API
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
            "daily_active_users",
            "cost_per_user_usd",
            "cost_per_accepted_suggestion_usd",
            "usage_by_language",
            "usage_by_editor",
        ]

        period = f"{start_time}/{end_time}"

        metrics = CodingToolMetrics(
            tool_name="openai_codex",
            period=period,
            total_chat_interactions=total_requests if total_requests > 0 else None,
            total_cost_usd=total_cost_usd,
            usage_by_model=usage_by_model if usage_by_model else None,
            metadata={
                "unavailable_fields": unavailable_fields,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_requests": total_requests,
            },
        )

        return json.dumps(metrics.to_dict(), indent=2)
