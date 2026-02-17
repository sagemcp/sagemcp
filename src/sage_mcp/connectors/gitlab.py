"""GitLab connector implementation.

Supports GitLab REST API v4 for both gitlab.com and self-hosted instances.
Self-hosted URL is read from connector.configuration["gitlab_url"].

23 tools covering projects, merge requests, issues, pipelines, branches,
commits, groups, milestones, labels, repository operations, and user search.
"""

import base64
import json
import urllib.parse
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


def _encode_project(project_id: str) -> str:
    """URL-encode a project ID for use in GitLab API paths.

    GitLab accepts both numeric IDs and URL-encoded namespace/project paths
    (e.g. "group%2Fproject"). Numeric strings are passed through unchanged;
    anything containing a "/" is URL-encoded with safe=''.
    """
    if str(project_id).isdigit():
        return str(project_id)
    return urllib.parse.quote(str(project_id), safe="")


@register_connector(ConnectorType.GITLAB)
class GitLabConnector(BaseConnector):
    """GitLab connector for accessing GitLab REST API v4.

    Supports both gitlab.com and self-hosted GitLab instances.
    The base URL defaults to https://gitlab.com but can be overridden via
    connector.configuration["gitlab_url"].
    """

    @property
    def display_name(self) -> str:
        return "GitLab"

    @property
    def description(self) -> str:
        return "Access GitLab projects, merge requests, issues, pipelines, and more"

    @property
    def requires_oauth(self) -> bool:
        return True

    def _base_url(self, connector: Connector) -> str:
        """Return the API v4 base URL for the configured GitLab instance."""
        gitlab_url = (connector.configuration or {}).get(
            "gitlab_url", "https://gitlab.com"
        )
        return f"{gitlab_url.rstrip('/')}/api/v4"

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    async def get_tools(
        self,
        connector: Connector,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> List[types.Tool]:
        """Return the 23 GitLab tools.

        All tool names are prefixed with ``gitlab_``.  The prefix is stripped
        before dispatching in ``execute_tool``.
        """
        tools = [
            # 1. list_projects
            types.Tool(
                name="gitlab_list_projects",
                description="List projects accessible to the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "membership": {
                            "type": "boolean",
                            "default": True,
                            "description": "Limit to projects the user is a member of",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number",
                        },
                        "search": {
                            "type": "string",
                            "description": "Search projects by name",
                        },
                        "order_by": {
                            "type": "string",
                            "enum": [
                                "id",
                                "name",
                                "path",
                                "created_at",
                                "updated_at",
                                "last_activity_at",
                            ],
                            "default": "last_activity_at",
                            "description": "Order projects by field",
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "default": "desc",
                            "description": "Sort direction",
                        },
                    },
                },
            ),
            # 2. get_project
            types.Tool(
                name="gitlab_get_project",
                description="Get detailed information about a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID (numeric) or URL-encoded path (e.g. 'group/project')",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 3. list_merge_requests
            types.Tool(
                name="gitlab_list_merge_requests",
                description="List merge requests for a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["opened", "closed", "merged", "all"],
                            "default": "opened",
                            "description": "Merge request state filter",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 4. get_merge_request
            types.Tool(
                name="gitlab_get_merge_request",
                description="Get details of a specific merge request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "merge_request_iid": {
                            "type": "integer",
                            "description": "Merge request IID (project-scoped)",
                        },
                    },
                    "required": ["project_id", "merge_request_iid"],
                },
            ),
            # 5. create_merge_request
            types.Tool(
                name="gitlab_create_merge_request",
                description="Create a new merge request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "source_branch": {
                            "type": "string",
                            "description": "Source branch name",
                        },
                        "target_branch": {
                            "type": "string",
                            "description": "Target branch name",
                        },
                        "title": {
                            "type": "string",
                            "description": "Merge request title",
                        },
                        "description": {
                            "type": "string",
                            "description": "Merge request description",
                        },
                    },
                    "required": [
                        "project_id",
                        "source_branch",
                        "target_branch",
                        "title",
                    ],
                },
            ),
            # 6. list_issues
            types.Tool(
                name="gitlab_list_issues",
                description="List issues for a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["opened", "closed", "all"],
                            "default": "opened",
                            "description": "Issue state filter",
                        },
                        "labels": {
                            "type": "string",
                            "description": "Comma-separated list of label names",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 7. get_issue
            types.Tool(
                name="gitlab_get_issue",
                description="Get details of a specific issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "issue_iid": {
                            "type": "integer",
                            "description": "Issue IID (project-scoped)",
                        },
                    },
                    "required": ["project_id", "issue_iid"],
                },
            ),
            # 8. create_issue
            types.Tool(
                name="gitlab_create_issue",
                description="Create a new issue in a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "title": {
                            "type": "string",
                            "description": "Issue title",
                        },
                        "description": {
                            "type": "string",
                            "description": "Issue description (Markdown supported)",
                        },
                        "labels": {
                            "type": "string",
                            "description": "Comma-separated list of label names",
                        },
                        "assignee_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Array of user IDs to assign",
                        },
                        "milestone_id": {
                            "type": "integer",
                            "description": "Milestone ID to associate",
                        },
                    },
                    "required": ["project_id", "title"],
                },
            ),
            # 9. update_issue
            types.Tool(
                name="gitlab_update_issue",
                description="Update an existing issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "issue_iid": {
                            "type": "integer",
                            "description": "Issue IID (project-scoped)",
                        },
                        "title": {
                            "type": "string",
                            "description": "New issue title",
                        },
                        "description": {
                            "type": "string",
                            "description": "New issue description",
                        },
                        "state_event": {
                            "type": "string",
                            "enum": ["close", "reopen"],
                            "description": "State transition event",
                        },
                        "labels": {
                            "type": "string",
                            "description": "Comma-separated list of label names (replaces existing)",
                        },
                        "assignee_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Array of user IDs to assign (replaces existing)",
                        },
                        "milestone_id": {
                            "type": "integer",
                            "description": "Milestone ID (0 to remove)",
                        },
                    },
                    "required": ["project_id", "issue_iid"],
                },
            ),
            # 10. list_pipelines
            types.Tool(
                name="gitlab_list_pipelines",
                description="List pipelines for a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "status": {
                            "type": "string",
                            "enum": [
                                "created",
                                "waiting_for_resource",
                                "preparing",
                                "pending",
                                "running",
                                "success",
                                "failed",
                                "canceled",
                                "skipped",
                                "manual",
                                "scheduled",
                            ],
                            "description": "Pipeline status filter",
                        },
                        "ref": {
                            "type": "string",
                            "description": "Branch or tag name filter",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 11. get_pipeline
            types.Tool(
                name="gitlab_get_pipeline",
                description="Get details of a specific pipeline",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "pipeline_id": {
                            "type": "integer",
                            "description": "Pipeline ID",
                        },
                    },
                    "required": ["project_id", "pipeline_id"],
                },
            ),
            # 12. list_branches
            types.Tool(
                name="gitlab_list_branches",
                description="List repository branches",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "search": {
                            "type": "string",
                            "description": "Search branches by name",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 13. get_file
            types.Tool(
                name="gitlab_get_file",
                description="Get the content of a file from a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file in the repository",
                        },
                        "ref": {
                            "type": "string",
                            "default": "main",
                            "description": "Branch, tag, or commit SHA (defaults to main)",
                        },
                    },
                    "required": ["project_id", "file_path"],
                },
            ),
            # 14. list_commits
            types.Tool(
                name="gitlab_list_commits",
                description="List repository commits",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "ref_name": {
                            "type": "string",
                            "description": "Branch or tag name",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 15. list_project_members
            types.Tool(
                name="gitlab_list_project_members",
                description="List members of a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 16. list_groups
            types.Tool(
                name="gitlab_list_groups",
                description="List groups accessible to the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                        "search": {
                            "type": "string",
                            "description": "Search groups by name",
                        },
                    },
                },
            ),
            # 17. list_mr_discussions
            types.Tool(
                name="gitlab_list_mr_discussions",
                description="List discussions (comment threads) on a merge request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "merge_request_iid": {
                            "type": "integer",
                            "description": "Merge request IID (project-scoped)",
                        },
                    },
                    "required": ["project_id", "merge_request_iid"],
                },
            ),
            # 18. add_mr_note
            types.Tool(
                name="gitlab_add_mr_note",
                description="Add a note (comment) to a merge request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "merge_request_iid": {
                            "type": "integer",
                            "description": "Merge request IID (project-scoped)",
                        },
                        "body": {
                            "type": "string",
                            "description": "Note body (Markdown supported)",
                        },
                    },
                    "required": ["project_id", "merge_request_iid", "body"],
                },
            ),
            # 19. list_milestones
            types.Tool(
                name="gitlab_list_milestones",
                description="List milestones for a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["active", "closed"],
                            "description": "Milestone state filter",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 20. list_labels
            types.Tool(
                name="gitlab_list_labels",
                description="List labels for a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 21. get_repository_tree
            types.Tool(
                name="gitlab_get_repository_tree",
                description="Get the repository file/directory tree",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "path": {
                            "type": "string",
                            "description": "Path inside the repository (default: root)",
                        },
                        "ref": {
                            "type": "string",
                            "description": "Branch, tag, or commit SHA",
                        },
                        "recursive": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to list recursively",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["project_id"],
                },
            ),
            # 22. search_users
            types.Tool(
                name="gitlab_search_users",
                description="Search GitLab users by email or username. For non-admin tokens, only matches public emails.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": "string",
                            "description": "Email or username to search for",
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page",
                        },
                    },
                    "required": ["search"],
                },
            ),
            # 23. retry_pipeline
            types.Tool(
                name="gitlab_retry_pipeline",
                description="Retry all failed jobs in a pipeline",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or URL-encoded path",
                        },
                        "pipeline_id": {
                            "type": "integer",
                            "description": "Pipeline ID to retry",
                        },
                    },
                    "required": ["project_id", "pipeline_id"],
                },
            ),
        ]

        return tools

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    async def get_resources(
        self,
        connector: Connector,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> List[types.Resource]:
        """Get available GitLab resources (user's projects)."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        try:
            base = self._base_url(connector)
            response = await self._make_authenticated_request(
                "GET",
                f"{base}/projects",
                oauth_cred,
                params={"membership": True, "per_page": 50},
            )
            projects = response.json()

            resources = []
            for project in projects:
                path_with_ns = project.get("path_with_namespace", "")
                resources.append(
                    types.Resource(
                        uri=f"gitlab://project/{path_with_ns}",
                        name=path_with_ns,
                        description=project.get("description") or "No description",
                    )
                )

            return resources

        except Exception:
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
        """Execute a GitLab tool.

        ``tool_name`` arrives WITHOUT the ``gitlab_`` prefix (stripped by the
        MCP server dispatch layer).
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired GitLab credentials"

        dispatch: Dict[str, Any] = {
            "list_projects": self._list_projects,
            "get_project": self._get_project,
            "list_merge_requests": self._list_merge_requests,
            "get_merge_request": self._get_merge_request,
            "create_merge_request": self._create_merge_request,
            "list_issues": self._list_issues,
            "get_issue": self._get_issue,
            "create_issue": self._create_issue,
            "update_issue": self._update_issue,
            "list_pipelines": self._list_pipelines,
            "get_pipeline": self._get_pipeline,
            "list_branches": self._list_branches,
            "get_file": self._get_file,
            "list_commits": self._list_commits,
            "list_project_members": self._list_project_members,
            "list_groups": self._list_groups,
            "list_mr_discussions": self._list_mr_discussions,
            "add_mr_note": self._add_mr_note,
            "list_milestones": self._list_milestones,
            "list_labels": self._list_labels,
            "get_repository_tree": self._get_repository_tree,
            "retry_pipeline": self._retry_pipeline,
            "search_users": self._search_users,
        }

        handler = dispatch.get(tool_name)
        if handler is None:
            return f"Unknown tool: {tool_name}"

        try:
            return await handler(connector, arguments, oauth_cred)
        except Exception as e:
            return f"Error executing GitLab tool '{tool_name}': {str(e)}"

    # ------------------------------------------------------------------
    # Resource reading
    # ------------------------------------------------------------------

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Read a GitLab resource by URI path."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired GitLab credentials"

        try:
            parts = resource_path.split("/", 2)
            if len(parts) < 2:
                return "Error: Invalid resource path"

            resource_type = parts[0]
            project_path = parts[1] if len(parts) == 2 else "/".join(parts[1:])

            if resource_type == "project":
                base = self._base_url(connector)
                encoded = _encode_project(project_path)
                response = await self._make_authenticated_request(
                    "GET",
                    f"{base}/projects/{encoded}",
                    oauth_cred,
                )
                return json.dumps(response.json(), indent=2)

            return "Error: Unsupported resource type"

        except Exception as e:
            return f"Error reading GitLab resource: {str(e)}"

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _list_projects(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List projects (GET /projects)."""
        base = self._base_url(connector)
        params: Dict[str, Any] = {
            "membership": arguments.get("membership", True),
            "per_page": arguments.get("per_page", 20),
            "page": arguments.get("page", 1),
            "order_by": arguments.get("order_by", "last_activity_at"),
            "sort": arguments.get("sort", "desc"),
        }
        if "search" in arguments:
            params["search"] = arguments["search"]

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects", oauth_cred, params=params
        )
        projects = response.json()

        result = []
        for p in projects:
            result.append({
                "id": p["id"],
                "name": p["name"],
                "path_with_namespace": p["path_with_namespace"],
                "description": p.get("description"),
                "visibility": p.get("visibility"),
                "web_url": p.get("web_url"),
                "default_branch": p.get("default_branch"),
                "last_activity_at": p.get("last_activity_at"),
            })

        return json.dumps(result, indent=2)

    async def _get_project(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Get project details (GET /projects/{id})."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects/{pid}", oauth_cred
        )
        return json.dumps(response.json(), indent=2)

    async def _list_merge_requests(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List merge requests (GET /projects/{id}/merge_requests)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        params: Dict[str, Any] = {
            "state": arguments.get("state", "opened"),
            "per_page": arguments.get("per_page", 20),
        }

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects/{pid}/merge_requests", oauth_cred, params=params
        )
        mrs = response.json()

        result = []
        for mr in mrs:
            result.append({
                "iid": mr["iid"],
                "title": mr["title"],
                "state": mr["state"],
                "author": mr.get("author", {}).get("username"),
                "source_branch": mr["source_branch"],
                "target_branch": mr["target_branch"],
                "created_at": mr["created_at"],
                "web_url": mr["web_url"],
            })

        return json.dumps(result, indent=2)

    async def _get_merge_request(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Get merge request details (GET /projects/{id}/merge_requests/{iid})."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        iid = arguments["merge_request_iid"]

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects/{pid}/merge_requests/{iid}", oauth_cred
        )
        return json.dumps(response.json(), indent=2)

    async def _create_merge_request(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Create merge request (POST /projects/{id}/merge_requests)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])

        body: Dict[str, Any] = {
            "source_branch": arguments["source_branch"],
            "target_branch": arguments["target_branch"],
            "title": arguments["title"],
        }
        if "description" in arguments:
            body["description"] = arguments["description"]

        response = await self._make_authenticated_request(
            "POST",
            f"{base}/projects/{pid}/merge_requests",
            oauth_cred,
            json=body,
        )
        mr = response.json()

        result = {
            "iid": mr["iid"],
            "title": mr["title"],
            "state": mr["state"],
            "web_url": mr["web_url"],
            "source_branch": mr["source_branch"],
            "target_branch": mr["target_branch"],
            "created_at": mr["created_at"],
            "message": "Merge request created successfully",
        }
        return json.dumps(result, indent=2)

    async def _list_issues(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List issues (GET /projects/{id}/issues)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        params: Dict[str, Any] = {
            "state": arguments.get("state", "opened"),
            "per_page": arguments.get("per_page", 20),
        }
        if "labels" in arguments:
            params["labels"] = arguments["labels"]

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects/{pid}/issues", oauth_cred, params=params
        )
        issues = response.json()

        result = []
        for issue in issues:
            result.append({
                "iid": issue["iid"],
                "title": issue["title"],
                "state": issue["state"],
                "author": issue.get("author", {}).get("username"),
                "labels": issue.get("labels", []),
                "created_at": issue["created_at"],
                "web_url": issue["web_url"],
            })

        return json.dumps(result, indent=2)

    async def _get_issue(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Get issue details (GET /projects/{id}/issues/{iid})."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        iid = arguments["issue_iid"]

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects/{pid}/issues/{iid}", oauth_cred
        )
        return json.dumps(response.json(), indent=2)

    async def _create_issue(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Create issue (POST /projects/{id}/issues)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])

        body: Dict[str, Any] = {"title": arguments["title"]}
        if "description" in arguments:
            body["description"] = arguments["description"]
        if "labels" in arguments:
            body["labels"] = arguments["labels"]
        if "assignee_ids" in arguments:
            body["assignee_ids"] = arguments["assignee_ids"]
        if "milestone_id" in arguments:
            body["milestone_id"] = arguments["milestone_id"]

        response = await self._make_authenticated_request(
            "POST", f"{base}/projects/{pid}/issues", oauth_cred, json=body
        )
        issue = response.json()

        result = {
            "iid": issue["iid"],
            "title": issue["title"],
            "state": issue["state"],
            "web_url": issue["web_url"],
            "labels": issue.get("labels", []),
            "created_at": issue["created_at"],
            "message": "Issue created successfully",
        }
        return json.dumps(result, indent=2)

    async def _update_issue(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Update issue (PUT /projects/{id}/issues/{iid})."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        iid = arguments["issue_iid"]

        body: Dict[str, Any] = {}
        if "title" in arguments:
            body["title"] = arguments["title"]
        if "description" in arguments:
            body["description"] = arguments["description"]
        if "state_event" in arguments:
            body["state_event"] = arguments["state_event"]
        if "labels" in arguments:
            body["labels"] = arguments["labels"]
        if "assignee_ids" in arguments:
            body["assignee_ids"] = arguments["assignee_ids"]
        if "milestone_id" in arguments:
            body["milestone_id"] = arguments["milestone_id"]

        response = await self._make_authenticated_request(
            "PUT", f"{base}/projects/{pid}/issues/{iid}", oauth_cred, json=body
        )
        issue = response.json()

        result = {
            "iid": issue["iid"],
            "title": issue["title"],
            "state": issue["state"],
            "web_url": issue["web_url"],
            "updated_at": issue["updated_at"],
            "message": "Issue updated successfully",
        }
        return json.dumps(result, indent=2)

    async def _list_pipelines(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List pipelines (GET /projects/{id}/pipelines)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        params: Dict[str, Any] = {
            "per_page": arguments.get("per_page", 20),
        }
        if "status" in arguments:
            params["status"] = arguments["status"]
        if "ref" in arguments:
            params["ref"] = arguments["ref"]

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects/{pid}/pipelines", oauth_cred, params=params
        )
        pipelines = response.json()

        result = []
        for pipeline in pipelines:
            result.append({
                "id": pipeline["id"],
                "status": pipeline["status"],
                "ref": pipeline["ref"],
                "sha": pipeline["sha"],
                "created_at": pipeline["created_at"],
                "updated_at": pipeline["updated_at"],
                "web_url": pipeline["web_url"],
            })

        return json.dumps(result, indent=2)

    async def _get_pipeline(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Get pipeline details (GET /projects/{id}/pipelines/{pipeline_id})."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        pipeline_id = arguments["pipeline_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{base}/projects/{pid}/pipelines/{pipeline_id}",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_branches(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List branches (GET /projects/{id}/repository/branches)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        params: Dict[str, Any] = {
            "per_page": arguments.get("per_page", 20),
        }
        if "search" in arguments:
            params["search"] = arguments["search"]

        response = await self._make_authenticated_request(
            "GET",
            f"{base}/projects/{pid}/repository/branches",
            oauth_cred,
            params=params,
        )
        branches = response.json()

        result = []
        for branch in branches:
            result.append({
                "name": branch["name"],
                "merged": branch.get("merged", False),
                "protected": branch.get("protected", False),
                "default": branch.get("default", False),
                "commit": {
                    "id": branch["commit"]["id"],
                    "short_id": branch["commit"]["short_id"],
                    "title": branch["commit"]["title"],
                    "created_at": branch["commit"]["created_at"],
                },
                "web_url": branch.get("web_url"),
            })

        return json.dumps(result, indent=2)

    async def _get_file(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Get file content (GET /projects/{id}/repository/files/{file_path}).

        The file_path URL segment must be URL-encoded.  Response includes
        base64-encoded ``content`` which is decoded before returning.
        """
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        file_path = urllib.parse.quote(arguments["file_path"], safe="")
        ref = arguments.get("ref", "main")

        response = await self._make_authenticated_request(
            "GET",
            f"{base}/projects/{pid}/repository/files/{file_path}",
            oauth_cred,
            params={"ref": ref},
        )
        file_data = response.json()

        # Decode base64 content
        content_b64 = file_data.get("content", "")
        encoding = file_data.get("encoding", "base64")

        if encoding == "base64" and content_b64:
            decoded = base64.b64decode(content_b64).decode("utf-8", errors="replace")
        else:
            decoded = content_b64

        result = {
            "file_name": file_data.get("file_name"),
            "file_path": file_data.get("file_path"),
            "size": file_data.get("size"),
            "ref": file_data.get("ref"),
            "last_commit_id": file_data.get("last_commit_id"),
            "content": decoded,
        }
        return json.dumps(result, indent=2)

    async def _list_commits(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List commits (GET /projects/{id}/repository/commits)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        params: Dict[str, Any] = {
            "per_page": arguments.get("per_page", 20),
        }
        if "ref_name" in arguments:
            params["ref_name"] = arguments["ref_name"]

        response = await self._make_authenticated_request(
            "GET",
            f"{base}/projects/{pid}/repository/commits",
            oauth_cred,
            params=params,
        )
        commits = response.json()

        result = []
        for commit in commits:
            result.append({
                "id": commit["id"],
                "short_id": commit["short_id"],
                "title": commit["title"],
                "message": commit["message"],
                "author_name": commit["author_name"],
                "author_email": commit["author_email"],
                "authored_date": commit["authored_date"],
                "created_at": commit["created_at"],
                "web_url": commit.get("web_url"),
            })

        return json.dumps(result, indent=2)

    async def _list_project_members(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List project members (GET /projects/{id}/members)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        params: Dict[str, Any] = {
            "per_page": arguments.get("per_page", 20),
        }

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects/{pid}/members", oauth_cred, params=params
        )
        members = response.json()

        result = []
        for member in members:
            result.append({
                "id": member["id"],
                "username": member["username"],
                "name": member["name"],
                "state": member["state"],
                "access_level": member["access_level"],
                "web_url": member.get("web_url"),
            })

        return json.dumps(result, indent=2)

    async def _list_groups(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List groups (GET /groups)."""
        base = self._base_url(connector)
        params: Dict[str, Any] = {
            "per_page": arguments.get("per_page", 20),
        }
        if "search" in arguments:
            params["search"] = arguments["search"]

        response = await self._make_authenticated_request(
            "GET", f"{base}/groups", oauth_cred, params=params
        )
        groups = response.json()

        result = []
        for group in groups:
            result.append({
                "id": group["id"],
                "name": group["name"],
                "path": group["path"],
                "full_path": group["full_path"],
                "description": group.get("description"),
                "visibility": group.get("visibility"),
                "web_url": group.get("web_url"),
            })

        return json.dumps(result, indent=2)

    async def _list_mr_discussions(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List MR discussions (GET /projects/{id}/merge_requests/{iid}/discussions)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        iid = arguments["merge_request_iid"]

        response = await self._make_authenticated_request(
            "GET",
            f"{base}/projects/{pid}/merge_requests/{iid}/discussions",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    async def _add_mr_note(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Add MR note (POST /projects/{id}/merge_requests/{iid}/notes)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        iid = arguments["merge_request_iid"]

        body = {"body": arguments["body"]}

        response = await self._make_authenticated_request(
            "POST",
            f"{base}/projects/{pid}/merge_requests/{iid}/notes",
            oauth_cred,
            json=body,
        )
        note = response.json()

        result = {
            "id": note["id"],
            "body": note["body"],
            "author": note.get("author", {}).get("username"),
            "created_at": note["created_at"],
            "message": "Note added successfully",
        }
        return json.dumps(result, indent=2)

    async def _list_milestones(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List milestones (GET /projects/{id}/milestones)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        params: Dict[str, Any] = {
            "per_page": arguments.get("per_page", 20),
        }
        if "state" in arguments:
            params["state"] = arguments["state"]

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects/{pid}/milestones", oauth_cred, params=params
        )
        milestones = response.json()

        result = []
        for ms in milestones:
            result.append({
                "id": ms["id"],
                "iid": ms["iid"],
                "title": ms["title"],
                "description": ms.get("description"),
                "state": ms["state"],
                "due_date": ms.get("due_date"),
                "start_date": ms.get("start_date"),
                "created_at": ms["created_at"],
                "updated_at": ms["updated_at"],
                "web_url": ms.get("web_url"),
            })

        return json.dumps(result, indent=2)

    async def _list_labels(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """List labels (GET /projects/{id}/labels)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        params: Dict[str, Any] = {
            "per_page": arguments.get("per_page", 20),
        }

        response = await self._make_authenticated_request(
            "GET", f"{base}/projects/{pid}/labels", oauth_cred, params=params
        )
        labels = response.json()

        result = []
        for label in labels:
            result.append({
                "id": label["id"],
                "name": label["name"],
                "color": label["color"],
                "description": label.get("description"),
                "open_issues_count": label.get("open_issues_count", 0),
                "closed_issues_count": label.get("closed_issues_count", 0),
                "open_merge_requests_count": label.get("open_merge_requests_count", 0),
                "text_color": label.get("text_color"),
            })

        return json.dumps(result, indent=2)

    async def _get_repository_tree(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Get repository tree (GET /projects/{id}/repository/tree)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        params: Dict[str, Any] = {
            "per_page": arguments.get("per_page", 20),
        }
        if "path" in arguments:
            params["path"] = arguments["path"]
        if "ref" in arguments:
            params["ref"] = arguments["ref"]
        if arguments.get("recursive"):
            params["recursive"] = True

        response = await self._make_authenticated_request(
            "GET",
            f"{base}/projects/{pid}/repository/tree",
            oauth_cred,
            params=params,
        )
        tree = response.json()

        result = []
        for item in tree:
            result.append({
                "id": item["id"],
                "name": item["name"],
                "type": item["type"],
                "path": item["path"],
                "mode": item["mode"],
            })

        return json.dumps(result, indent=2)

    async def _retry_pipeline(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Retry pipeline (POST /projects/{id}/pipelines/{pipeline_id}/retry)."""
        base = self._base_url(connector)
        pid = _encode_project(arguments["project_id"])
        pipeline_id = arguments["pipeline_id"]

        response = await self._make_authenticated_request(
            "POST",
            f"{base}/projects/{pid}/pipelines/{pipeline_id}/retry",
            oauth_cred,
        )
        pipeline = response.json()

        result = {
            "id": pipeline["id"],
            "status": pipeline["status"],
            "ref": pipeline["ref"],
            "sha": pipeline["sha"],
            "web_url": pipeline["web_url"],
            "message": "Pipeline retry initiated",
        }
        return json.dumps(result, indent=2)

    async def _search_users(
        self,
        connector: Connector,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential,
    ) -> str:
        """Search users (GET /users?search={query})."""
        base = self._base_url(connector)
        params: Dict[str, Any] = {
            "search": arguments["search"],
            "per_page": arguments.get("per_page", 10),
        }

        response = await self._make_authenticated_request(
            "GET", f"{base}/users", oauth_cred, params=params
        )
        users = response.json()

        result = []
        for user in users:
            result.append({
                "id": user["id"],
                "username": user["username"],
                "name": user["name"],
                "state": user["state"],
                "web_url": user.get("web_url"),
            })

        return json.dumps(result, indent=2)
