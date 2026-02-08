"""GitHub Copilot connector implementation.

Provides 19 tools for managing GitHub Copilot seats, usage analytics,
and organizational policies. Reuses GitHub OAuth credentials -- the
token must have the `manage_billing:copilot` and `read:org` scopes.

API reference: https://docs.github.com/en/rest/copilot
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .coding_tool_metrics import CodingToolMetrics
from .registry import register_connector

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


@register_connector(ConnectorType.COPILOT)
class CopilotConnector(BaseConnector):
    """GitHub Copilot connector for seat management, usage analytics, and policy governance."""

    @property
    def display_name(self) -> str:
        return "GitHub Copilot"

    @property
    def description(self) -> str:
        return "Manage GitHub Copilot seats, usage analytics, and org policies"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(
        self,
        connector: Connector,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> List[types.Tool]:
        """Return the 19 Copilot tools with full JSON Schema input definitions."""
        return [
            # ----------------------------------------------------------------
            # Org Stats & Analytics (9 tools)
            # ----------------------------------------------------------------
            types.Tool(
                name="copilot_get_org_usage",
                description="Get daily Copilot usage metrics for an organization (1-day granularity)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "since": {
                            "type": "string",
                            "description": "Start date (ISO 8601, e.g. 2024-01-01)"
                        },
                        "until": {
                            "type": "string",
                            "description": "End date (ISO 8601, e.g. 2024-01-31)"
                        },
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number for pagination"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 28,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_usage_trends",
                description="Get 28-day rolling usage trends for an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "since": {
                            "type": "string",
                            "description": "Start date (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "End date (ISO 8601)"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_user_usage",
                description="Get per-user daily Copilot usage metrics for an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "since": {
                            "type": "string",
                            "description": "Start date (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "End date (ISO 8601)"
                        },
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number for pagination"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 28,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_acceptance_rate",
                description="Compute the suggestion acceptance rate from daily org usage data",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "since": {
                            "type": "string",
                            "description": "Start date (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "End date (ISO 8601)"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_usage_by_language",
                description="Break down Copilot usage by programming language",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "since": {
                            "type": "string",
                            "description": "Start date (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "End date (ISO 8601)"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_usage_by_editor",
                description="Break down Copilot usage by editor/IDE",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "since": {
                            "type": "string",
                            "description": "Start date (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "End date (ISO 8601)"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_chat_usage",
                description="Get Copilot Chat usage metrics for an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "since": {
                            "type": "string",
                            "description": "Start date (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "End date (ISO 8601)"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_pr_summary_usage",
                description="Get Copilot pull request summary usage metrics",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "since": {
                            "type": "string",
                            "description": "Start date (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "End date (ISO 8601)"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_legacy_metrics",
                description="Get legacy Copilot metrics (deprecated endpoint, use org usage for new integrations)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        }
                    },
                    "required": ["org"]
                },
            ),
            # ----------------------------------------------------------------
            # Seat Management (6 tools)
            # ----------------------------------------------------------------
            types.Tool(
                name="copilot_get_billing_info",
                description="Get Copilot billing information and seat summary for an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_list_seat_assignments",
                description="List all Copilot seat assignments for an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number for pagination"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 50,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_seat_details",
                description="Get Copilot seat details for a specific organization member",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "username": {
                            "type": "string",
                            "description": "GitHub username"
                        }
                    },
                    "required": ["org", "username"]
                },
            ),
            types.Tool(
                name="copilot_add_seats",
                description="Add Copilot seats for specified users in an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "selected_usernames": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of GitHub usernames to assign Copilot seats"
                        }
                    },
                    "required": ["org", "selected_usernames"]
                },
            ),
            types.Tool(
                name="copilot_remove_seats",
                description="Remove Copilot seats for specified users in an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "selected_usernames": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of GitHub usernames to remove Copilot seats from"
                        }
                    },
                    "required": ["org", "selected_usernames"]
                },
            ),
            types.Tool(
                name="copilot_list_inactive_seats",
                description="List Copilot seats inactive for a given number of days",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "days_inactive": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 30,
                            "description": "Number of days of inactivity threshold"
                        }
                    },
                    "required": ["org"]
                },
            ),
            # ----------------------------------------------------------------
            # Policy & Governance (3 tools)
            # ----------------------------------------------------------------
            types.Tool(
                name="copilot_get_org_config",
                description="Get Copilot feature policies and configuration for an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_get_content_exclusions",
                description="Get Copilot content exclusion rules for an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        }
                    },
                    "required": ["org"]
                },
            ),
            types.Tool(
                name="copilot_list_audit_events",
                description="List Copilot-related audit log events for an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "phrase": {
                            "type": "string",
                            "default": "action:copilot",
                            "description": "Audit log search phrase"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 30,
                            "description": "Number of results per page"
                        },
                        "after": {
                            "type": "string",
                            "description": "Cursor for pagination (from previous response)"
                        }
                    },
                    "required": ["org"]
                },
            ),
            # ----------------------------------------------------------------
            # Normalized metrics (1 tool)
            # ----------------------------------------------------------------
            types.Tool(
                name="copilot_get_normalized_metrics",
                description="Get normalized CodingToolMetrics for cross-tool comparison",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org": {
                            "type": "string",
                            "description": "GitHub organization login"
                        },
                        "since": {
                            "type": "string",
                            "description": "Start date (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "End date (ISO 8601)"
                        }
                    },
                    "required": ["org"]
                },
            ),
        ]

    async def get_resources(
        self,
        connector: Connector,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> List[types.Resource]:
        """Copilot connector does not expose resources."""
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Dispatch a Copilot tool call to the appropriate handler.

        ``tool_name`` arrives with the ``copilot_`` prefix already stripped
        (e.g. ``"get_org_usage"``).
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired GitHub credentials"

        try:
            # Org Stats & Analytics
            if tool_name == "get_org_usage":
                return await self._get_org_usage(arguments, oauth_cred)
            elif tool_name == "get_usage_trends":
                return await self._get_usage_trends(arguments, oauth_cred)
            elif tool_name == "get_user_usage":
                return await self._get_user_usage(arguments, oauth_cred)
            elif tool_name == "get_acceptance_rate":
                return await self._get_acceptance_rate(arguments, oauth_cred)
            elif tool_name == "get_usage_by_language":
                return await self._get_usage_by_language(arguments, oauth_cred)
            elif tool_name == "get_usage_by_editor":
                return await self._get_usage_by_editor(arguments, oauth_cred)
            elif tool_name == "get_chat_usage":
                return await self._get_chat_usage(arguments, oauth_cred)
            elif tool_name == "get_pr_summary_usage":
                return await self._get_pr_summary_usage(arguments, oauth_cred)
            elif tool_name == "get_legacy_metrics":
                return await self._get_legacy_metrics(arguments, oauth_cred)
            # Seat Management
            elif tool_name == "get_billing_info":
                return await self._get_billing_info(arguments, oauth_cred)
            elif tool_name == "list_seat_assignments":
                return await self._list_seat_assignments(arguments, oauth_cred)
            elif tool_name == "get_seat_details":
                return await self._get_seat_details(arguments, oauth_cred)
            elif tool_name == "add_seats":
                return await self._add_seats(arguments, oauth_cred)
            elif tool_name == "remove_seats":
                return await self._remove_seats(arguments, oauth_cred)
            elif tool_name == "list_inactive_seats":
                return await self._list_inactive_seats(arguments, oauth_cred)
            # Policy & Governance
            elif tool_name == "get_org_config":
                return await self._get_org_config(arguments, oauth_cred)
            elif tool_name == "get_content_exclusions":
                return await self._get_content_exclusions(arguments, oauth_cred)
            elif tool_name == "list_audit_events":
                return await self._list_audit_events(arguments, oauth_cred)
            # Normalized metrics
            elif tool_name == "get_normalized_metrics":
                return await self._get_normalized_metrics(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Copilot tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Copilot connector does not support resources."""
        return "Copilot connector does not support resources"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_org_usage_raw(
        self,
        org: str,
        oauth_cred: OAuthCredential,
        since: Optional[str] = None,
        until: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Any:
        """Fetch raw 1-day org usage data. Reused by derived tools."""
        params: Dict[str, Any] = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/copilot/metrics/reports/organization-1-day",
            oauth_cred,
            params=params,
        )
        return response.json()

    # ------------------------------------------------------------------
    # Org Stats & Analytics
    # ------------------------------------------------------------------

    async def _get_org_usage(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /orgs/{org}/copilot/metrics/reports/organization-1-day"""
        org = arguments["org"]
        data = await self._fetch_org_usage_raw(
            org,
            oauth_cred,
            since=arguments.get("since"),
            until=arguments.get("until"),
            page=arguments.get("page"),
            per_page=arguments.get("per_page"),
        )
        return json.dumps(data, indent=2)

    async def _get_usage_trends(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /orgs/{org}/copilot/metrics/reports/organization-28-day"""
        org = arguments["org"]
        params: Dict[str, Any] = {}
        if arguments.get("since"):
            params["since"] = arguments["since"]
        if arguments.get("until"):
            params["until"] = arguments["until"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/copilot/metrics/reports/organization-28-day",
            oauth_cred,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_user_usage(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /orgs/{org}/copilot/metrics/reports/users-1-day"""
        org = arguments["org"]
        params: Dict[str, Any] = {}
        if arguments.get("since"):
            params["since"] = arguments["since"]
        if arguments.get("until"):
            params["until"] = arguments["until"]
        if arguments.get("page"):
            params["page"] = arguments["page"]
        if arguments.get("per_page"):
            params["per_page"] = arguments["per_page"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/copilot/metrics/reports/users-1-day",
            oauth_cred,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_acceptance_rate(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Derive acceptance rate from 1-day org usage data.

        Iterates over daily reports, sums total_suggestions_count and
        total_acceptances_count across all copilot_ide_code_completions
        entries, and computes the ratio.
        """
        org = arguments["org"]
        data = await self._fetch_org_usage_raw(
            org,
            oauth_cred,
            since=arguments.get("since"),
            until=arguments.get("until"),
        )

        total_suggestions = 0
        total_acceptances = 0

        reports = data if isinstance(data, list) else [data]
        for day in reports:
            for ide_entry in day.get("copilot_ide_code_completions", {}).get("editors", []):
                for model in ide_entry.get("models", []):
                    for lang in model.get("languages", []):
                        total_suggestions += lang.get("total_code_suggestions", 0)
                        total_acceptances += lang.get("total_code_acceptances", 0)

        rate = (total_acceptances / total_suggestions * 100) if total_suggestions > 0 else 0.0

        result = {
            "org": org,
            "since": arguments.get("since"),
            "until": arguments.get("until"),
            "total_suggestions": total_suggestions,
            "total_acceptances": total_acceptances,
            "acceptance_rate_pct": round(rate, 2),
        }
        return json.dumps(result, indent=2)

    async def _get_usage_by_language(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Derive per-language usage breakdown from 1-day org usage data."""
        org = arguments["org"]
        data = await self._fetch_org_usage_raw(
            org,
            oauth_cred,
            since=arguments.get("since"),
            until=arguments.get("until"),
        )

        language_stats: Dict[str, Dict[str, int]] = {}

        reports = data if isinstance(data, list) else [data]
        for day in reports:
            for ide_entry in day.get("copilot_ide_code_completions", {}).get("editors", []):
                for model in ide_entry.get("models", []):
                    for lang in model.get("languages", []):
                        name = lang.get("name", "unknown")
                        if name not in language_stats:
                            language_stats[name] = {
                                "total_code_suggestions": 0,
                                "total_code_acceptances": 0,
                                "total_code_lines_suggested": 0,
                                "total_code_lines_accepted": 0,
                            }
                        language_stats[name]["total_code_suggestions"] += lang.get("total_code_suggestions", 0)
                        language_stats[name]["total_code_acceptances"] += lang.get("total_code_acceptances", 0)
                        language_stats[name]["total_code_lines_suggested"] += lang.get("total_code_lines_suggested", 0)
                        language_stats[name]["total_code_lines_accepted"] += lang.get("total_code_lines_accepted", 0)

        # Add acceptance rate per language
        for stats in language_stats.values():
            suggestions = stats["total_code_suggestions"]
            acceptances = stats["total_code_acceptances"]
            stats["acceptance_rate_pct"] = round(
                (acceptances / suggestions * 100) if suggestions > 0 else 0.0, 2
            )

        result = {
            "org": org,
            "since": arguments.get("since"),
            "until": arguments.get("until"),
            "languages": language_stats,
        }
        return json.dumps(result, indent=2)

    async def _get_usage_by_editor(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Derive per-editor usage breakdown from 1-day org usage data."""
        org = arguments["org"]
        data = await self._fetch_org_usage_raw(
            org,
            oauth_cred,
            since=arguments.get("since"),
            until=arguments.get("until"),
        )

        editor_stats: Dict[str, Dict[str, int]] = {}

        reports = data if isinstance(data, list) else [data]
        for day in reports:
            for ide_entry in day.get("copilot_ide_code_completions", {}).get("editors", []):
                editor_name = ide_entry.get("name", "unknown")
                if editor_name not in editor_stats:
                    editor_stats[editor_name] = {
                        "total_code_suggestions": 0,
                        "total_code_acceptances": 0,
                        "total_code_lines_suggested": 0,
                        "total_code_lines_accepted": 0,
                    }
                for model in ide_entry.get("models", []):
                    for lang in model.get("languages", []):
                        editor_stats[editor_name]["total_code_suggestions"] += lang.get("total_code_suggestions", 0)
                        editor_stats[editor_name]["total_code_acceptances"] += lang.get("total_code_acceptances", 0)
                        editor_stats[editor_name]["total_code_lines_suggested"] += lang.get("total_code_lines_suggested", 0)
                        editor_stats[editor_name]["total_code_lines_accepted"] += lang.get("total_code_lines_accepted", 0)

        for stats in editor_stats.values():
            suggestions = stats["total_code_suggestions"]
            acceptances = stats["total_code_acceptances"]
            stats["acceptance_rate_pct"] = round(
                (acceptances / suggestions * 100) if suggestions > 0 else 0.0, 2
            )

        result = {
            "org": org,
            "since": arguments.get("since"),
            "until": arguments.get("until"),
            "editors": editor_stats,
        }
        return json.dumps(result, indent=2)

    async def _get_chat_usage(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Derive Copilot Chat usage from 1-day org usage data."""
        org = arguments["org"]
        data = await self._fetch_org_usage_raw(
            org,
            oauth_cred,
            since=arguments.get("since"),
            until=arguments.get("until"),
        )

        total_chats = 0
        total_insertion_events = 0
        total_copy_events = 0
        daily_chat: List[Dict[str, Any]] = []

        reports = data if isinstance(data, list) else [data]
        for day in reports:
            day_chats = 0
            day_insertions = 0
            day_copies = 0

            for ide_entry in day.get("copilot_ide_chat", {}).get("editors", []):
                for model in ide_entry.get("models", []):
                    day_chats += model.get("total_chats", 0)
                    day_insertions += model.get("total_chat_insertion_events", 0)
                    day_copies += model.get("total_chat_copy_events", 0)

            total_chats += day_chats
            total_insertion_events += day_insertions
            total_copy_events += day_copies

            if day.get("date"):
                daily_chat.append({
                    "date": day["date"],
                    "total_chats": day_chats,
                    "total_insertion_events": day_insertions,
                    "total_copy_events": day_copies,
                })

        result = {
            "org": org,
            "since": arguments.get("since"),
            "until": arguments.get("until"),
            "total_chats": total_chats,
            "total_insertion_events": total_insertion_events,
            "total_copy_events": total_copy_events,
            "daily": daily_chat,
        }
        return json.dumps(result, indent=2)

    async def _get_pr_summary_usage(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Derive Copilot PR summary usage from 1-day org usage data."""
        org = arguments["org"]
        data = await self._fetch_org_usage_raw(
            org,
            oauth_cred,
            since=arguments.get("since"),
            until=arguments.get("until"),
        )

        total_pr_summaries = 0
        daily_pr: List[Dict[str, Any]] = []

        reports = data if isinstance(data, list) else [data]
        for day in reports:
            day_summaries = 0

            for model in day.get("copilot_dotcom_pull_requests", {}).get("models", []):
                day_summaries += model.get("total_pr_summaries_created", 0)

            total_pr_summaries += day_summaries

            if day.get("date"):
                daily_pr.append({
                    "date": day["date"],
                    "total_pr_summaries": day_summaries,
                })

        result = {
            "org": org,
            "since": arguments.get("since"),
            "until": arguments.get("until"),
            "total_pr_summaries": total_pr_summaries,
            "daily": daily_pr,
        }
        return json.dumps(result, indent=2)

    async def _get_legacy_metrics(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /orgs/{org}/copilot/metrics (legacy/deprecated endpoint)."""
        org = arguments["org"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/copilot/metrics",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Seat Management
    # ------------------------------------------------------------------

    async def _get_billing_info(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /orgs/{org}/copilot/billing"""
        org = arguments["org"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/copilot/billing",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_seat_assignments(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /orgs/{org}/copilot/billing/seats"""
        org = arguments["org"]
        params: Dict[str, Any] = {}
        if arguments.get("page"):
            params["page"] = arguments["page"]
        if arguments.get("per_page"):
            params["per_page"] = arguments["per_page"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/copilot/billing/seats",
            oauth_cred,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_seat_details(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /orgs/{org}/members/{username}/copilot"""
        org = arguments["org"]
        username = arguments["username"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/members/{username}/copilot",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    async def _add_seats(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """POST /orgs/{org}/copilot/billing/selected_users"""
        org = arguments["org"]
        selected_usernames = arguments["selected_usernames"]

        response = await self._make_authenticated_request(
            "POST",
            f"{GITHUB_API}/orgs/{org}/copilot/billing/selected_users",
            oauth_cred,
            json={"selected_usernames": selected_usernames},
        )
        result = response.json()
        result["message"] = "Copilot seats added successfully"
        return json.dumps(result, indent=2)

    async def _remove_seats(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """DELETE /orgs/{org}/copilot/billing/selected_users"""
        org = arguments["org"]
        selected_usernames = arguments["selected_usernames"]

        response = await self._make_authenticated_request(
            "DELETE",
            f"{GITHUB_API}/orgs/{org}/copilot/billing/selected_users",
            oauth_cred,
            json={"selected_usernames": selected_usernames},
        )
        result = response.json()
        result["message"] = "Copilot seats removed successfully"
        return json.dumps(result, indent=2)

    async def _list_inactive_seats(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Derived: list seats inactive for N days.

        Fetches all seat assignments (paginated), filters by
        last_activity_at older than the threshold.
        """
        org = arguments["org"]
        days_inactive = arguments.get("days_inactive", 30)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_inactive)

        # Paginate through all seats
        all_seats: List[Dict[str, Any]] = []
        page = 1
        per_page = 100
        while True:
            response = await self._make_authenticated_request(
                "GET",
                f"{GITHUB_API}/orgs/{org}/copilot/billing/seats",
                oauth_cred,
                params={"page": page, "per_page": per_page},
            )
            data = response.json()
            seats = data.get("seats", [])
            if not seats:
                break
            all_seats.extend(seats)
            total_seats = data.get("total_seats", 0)
            if len(all_seats) >= total_seats:
                break
            page += 1

        inactive: List[Dict[str, Any]] = []
        for seat in all_seats:
            last_activity = seat.get("last_activity_at")
            if last_activity is None:
                # Never used -- definitely inactive
                inactive.append({
                    "login": seat.get("assignee", {}).get("login", "unknown"),
                    "last_activity_at": None,
                    "created_at": seat.get("created_at"),
                    "plan_type": seat.get("plan_type"),
                })
            else:
                try:
                    activity_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
                    if activity_dt < cutoff:
                        inactive.append({
                            "login": seat.get("assignee", {}).get("login", "unknown"),
                            "last_activity_at": last_activity,
                            "created_at": seat.get("created_at"),
                            "plan_type": seat.get("plan_type"),
                            "days_since_active": (datetime.now(timezone.utc) - activity_dt).days,
                        })
                except (ValueError, TypeError):
                    # Unparseable date -- include as inactive for safety
                    inactive.append({
                        "login": seat.get("assignee", {}).get("login", "unknown"),
                        "last_activity_at": last_activity,
                        "created_at": seat.get("created_at"),
                        "plan_type": seat.get("plan_type"),
                    })

        result = {
            "org": org,
            "days_inactive_threshold": days_inactive,
            "total_seats": len(all_seats),
            "inactive_count": len(inactive),
            "inactive_seats": inactive,
        }
        return json.dumps(result, indent=2)

    # ------------------------------------------------------------------
    # Policy & Governance
    # ------------------------------------------------------------------

    async def _get_org_config(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Derived: extract Copilot feature policies from billing response.

        The billing endpoint returns seat_management_setting,
        public_code_suggestions, and other policy fields.
        """
        org = arguments["org"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/copilot/billing",
            oauth_cred,
        )
        billing = response.json()

        config = {
            "org": org,
            "seat_management_setting": billing.get("seat_management_setting"),
            "public_code_suggestions": billing.get("public_code_suggestions"),
            "ide_chat": billing.get("ide_chat"),
            "platform_chat": billing.get("platform_chat"),
            "cli": billing.get("cli"),
            "seat_breakdown": billing.get("seat_breakdown"),
            "plan_type": billing.get("plan_type"),
        }
        return json.dumps(config, indent=2)

    async def _get_content_exclusions(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /orgs/{org}/copilot/content_exclusions"""
        org = arguments["org"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/copilot/content_exclusions",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_audit_events(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /orgs/{org}/audit-log with Copilot phrase filter."""
        org = arguments["org"]
        params: Dict[str, Any] = {
            "phrase": arguments.get("phrase", "action:copilot"),
            "per_page": arguments.get("per_page", 30),
        }
        if arguments.get("after"):
            params["after"] = arguments["after"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/audit-log",
            oauth_cred,
            params=params,
        )
        return json.dumps(response.json(), indent=2)

    # ------------------------------------------------------------------
    # Normalized metrics
    # ------------------------------------------------------------------

    async def _get_normalized_metrics(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Build a CodingToolMetrics object from billing + usage endpoints.

        Calls both /copilot/billing and /copilot/metrics/reports/organization-1-day,
        then maps into the standardized schema for cross-tool comparison.
        """
        org = arguments["org"]
        since = arguments.get("since")
        until = arguments.get("until")
        period = f"{since or 'start'}/{until or 'now'}"

        unavailable_fields: List[str] = []

        # Fetch billing info for seat counts
        billing_response = await self._make_authenticated_request(
            "GET",
            f"{GITHUB_API}/orgs/{org}/copilot/billing",
            oauth_cred,
        )
        billing = billing_response.json()

        # Fetch usage data
        usage_data = await self._fetch_org_usage_raw(
            org, oauth_cred, since=since, until=until
        )

        # -- Seat metrics --
        seat_breakdown = billing.get("seat_breakdown", {})
        total_seats = billing.get("total_seats")
        active_seats = seat_breakdown.get("active_this_cycle")
        inactive_seats = seat_breakdown.get("inactive_this_cycle")

        seat_utilization_pct = None
        if total_seats and total_seats > 0 and active_seats is not None:
            seat_utilization_pct = round(active_seats / total_seats * 100, 2)

        # -- Usage metrics from org-1-day reports --
        total_suggestions = 0
        total_acceptances = 0
        total_lines_suggested = 0
        total_lines_accepted = 0
        total_chats = 0
        language_breakdown: Dict[str, Any] = {}
        editor_breakdown: Dict[str, Any] = {}

        reports = usage_data if isinstance(usage_data, list) else [usage_data]
        for day in reports:
            for ide_entry in day.get("copilot_ide_code_completions", {}).get("editors", []):
                editor_name = ide_entry.get("name", "unknown")
                if editor_name not in editor_breakdown:
                    editor_breakdown[editor_name] = {"suggestions": 0, "acceptances": 0}
                for model in ide_entry.get("models", []):
                    for lang in model.get("languages", []):
                        lang_name = lang.get("name", "unknown")
                        suggestions = lang.get("total_code_suggestions", 0)
                        acceptances = lang.get("total_code_acceptances", 0)
                        lines_suggested = lang.get("total_code_lines_suggested", 0)
                        lines_accepted = lang.get("total_code_lines_accepted", 0)

                        total_suggestions += suggestions
                        total_acceptances += acceptances
                        total_lines_suggested += lines_suggested
                        total_lines_accepted += lines_accepted

                        if lang_name not in language_breakdown:
                            language_breakdown[lang_name] = {"suggestions": 0, "acceptances": 0}
                        language_breakdown[lang_name]["suggestions"] += suggestions
                        language_breakdown[lang_name]["acceptances"] += acceptances

                        editor_breakdown[editor_name]["suggestions"] += suggestions
                        editor_breakdown[editor_name]["acceptances"] += acceptances

            for chat_editor in day.get("copilot_ide_chat", {}).get("editors", []):
                for model in chat_editor.get("models", []):
                    total_chats += model.get("total_chats", 0)

        acceptance_rate_pct = (
            round(total_acceptances / total_suggestions * 100, 2)
            if total_suggestions > 0
            else None
        )

        # Fields not available from the Copilot API
        unavailable_fields.extend([
            "daily_active_users",
            "total_cost_usd",
            "cost_per_user_usd",
            "cost_per_accepted_suggestion_usd",
            "usage_by_model",
        ])

        metrics = CodingToolMetrics(
            tool_name="github_copilot",
            period=period,
            total_seats=total_seats,
            active_seats=active_seats,
            seat_utilization_pct=seat_utilization_pct,
            inactive_seats=inactive_seats,
            total_suggestions=total_suggestions,
            total_acceptances=total_acceptances,
            acceptance_rate_pct=acceptance_rate_pct,
            total_lines_suggested=total_lines_suggested,
            total_lines_accepted=total_lines_accepted,
            total_chat_interactions=total_chats,
            daily_active_users=None,
            total_cost_usd=None,
            cost_per_user_usd=None,
            cost_per_accepted_suggestion_usd=None,
            usage_by_language=language_breakdown if language_breakdown else None,
            usage_by_editor=editor_breakdown if editor_breakdown else None,
            usage_by_model=None,
            metadata={"unavailable_fields": unavailable_fields},
        )

        return json.dumps(metrics.to_dict(), indent=2)
