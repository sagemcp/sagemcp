"""Bitbucket Cloud connector implementation.

Provides 19 tools for interacting with Bitbucket Cloud API v2.
Workspace model: workspace > project > repository.
API base: https://api.bitbucket.org/2.0/

Bitbucket uses its own OAuth provider, separate from Atlassian Cloud (Jira/Confluence).
"""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

BASE_URL = "https://api.bitbucket.org/2.0"


@register_connector(ConnectorType.BITBUCKET)
class BitbucketConnector(BaseConnector):
    """Bitbucket Cloud connector for accessing repositories, pull requests, pipelines, and more."""

    @property
    def display_name(self) -> str:
        return "Bitbucket"

    @property
    def description(self) -> str:
        return "Access Bitbucket Cloud repositories, pull requests, pipelines, and workspaces"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Bitbucket tools.

        Returns 19 tools covering repositories, pull requests, issues,
        pipelines, branches, commits, workspaces, and file content.
        Tool names are prefixed with 'bitbucket_' for namespace isolation.
        """
        tools = [
            types.Tool(
                name="bitbucket_list_repositories",
                description="List repositories in a Bitbucket workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "pagelen": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of results per page (max 100)"
                        },
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number"
                        },
                        "q": {
                            "type": "string",
                            "description": "Query filter (e.g. 'name ~ \"myrepo\"')"
                        },
                        "sort": {
                            "type": "string",
                            "description": "Sort field (e.g. '-updated_on' for newest first)"
                        }
                    },
                    "required": ["workspace"]
                }
            ),
            types.Tool(
                name="bitbucket_get_repository",
                description="Get detailed information about a Bitbucket repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        }
                    },
                    "required": ["workspace", "repo_slug"]
                }
            ),
            types.Tool(
                name="bitbucket_list_pull_requests",
                description="List pull requests for a Bitbucket repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "state": {
                            "type": "string",
                            "enum": ["OPEN", "MERGED", "DECLINED", "SUPERSEDED"],
                            "default": "OPEN",
                            "description": "Pull request state filter"
                        },
                        "pagelen": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["workspace", "repo_slug"]
                }
            ),
            types.Tool(
                name="bitbucket_get_pull_request",
                description="Get details of a specific pull request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "pull_request_id": {
                            "type": "integer",
                            "description": "Pull request ID"
                        }
                    },
                    "required": ["workspace", "repo_slug", "pull_request_id"]
                }
            ),
            types.Tool(
                name="bitbucket_create_pull_request",
                description="Create a new pull request in a Bitbucket repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "title": {
                            "type": "string",
                            "description": "Pull request title"
                        },
                        "source_branch": {
                            "type": "string",
                            "description": "Source branch name"
                        },
                        "destination_branch": {
                            "type": "string",
                            "description": "Destination branch name (defaults to repo main branch)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Pull request description"
                        },
                        "close_source_branch": {
                            "type": "boolean",
                            "default": False,
                            "description": "Close source branch after merge"
                        }
                    },
                    "required": ["workspace", "repo_slug", "title", "source_branch"]
                }
            ),
            types.Tool(
                name="bitbucket_list_pr_comments",
                description="List comments on a pull request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "pull_request_id": {
                            "type": "integer",
                            "description": "Pull request ID"
                        }
                    },
                    "required": ["workspace", "repo_slug", "pull_request_id"]
                }
            ),
            types.Tool(
                name="bitbucket_add_pr_comment",
                description="Add a comment to a pull request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "pull_request_id": {
                            "type": "integer",
                            "description": "Pull request ID"
                        },
                        "body": {
                            "type": "string",
                            "description": "Comment body (Markdown supported)"
                        }
                    },
                    "required": ["workspace", "repo_slug", "pull_request_id", "body"]
                }
            ),
            types.Tool(
                name="bitbucket_list_issues",
                description="List issues for a Bitbucket repository (requires issue tracker to be enabled)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "q": {
                            "type": "string",
                            "description": "Query filter (e.g. 'state = \"open\"')"
                        },
                        "pagelen": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["workspace", "repo_slug"]
                }
            ),
            types.Tool(
                name="bitbucket_get_issue",
                description="Get details of a specific issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "issue_id": {
                            "type": "integer",
                            "description": "Issue ID"
                        }
                    },
                    "required": ["workspace", "repo_slug", "issue_id"]
                }
            ),
            types.Tool(
                name="bitbucket_create_issue",
                description="Create a new issue in a Bitbucket repository (requires issue tracker to be enabled)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "title": {
                            "type": "string",
                            "description": "Issue title"
                        },
                        "content": {
                            "type": "string",
                            "description": "Issue body/description (Markdown supported)"
                        },
                        "kind": {
                            "type": "string",
                            "enum": ["bug", "enhancement", "proposal", "task"],
                            "default": "bug",
                            "description": "Issue kind"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["trivial", "minor", "major", "critical", "blocker"],
                            "default": "major",
                            "description": "Issue priority"
                        }
                    },
                    "required": ["workspace", "repo_slug", "title"]
                }
            ),
            types.Tool(
                name="bitbucket_list_pipelines",
                description="List pipelines for a Bitbucket repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "pagelen": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of results per page"
                        },
                        "sort": {
                            "type": "string",
                            "description": "Sort field (e.g. '-created_on')"
                        }
                    },
                    "required": ["workspace", "repo_slug"]
                }
            ),
            types.Tool(
                name="bitbucket_get_pipeline",
                description="Get details of a specific pipeline run",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "pipeline_uuid": {
                            "type": "string",
                            "description": "Pipeline UUID (with or without curly braces)"
                        }
                    },
                    "required": ["workspace", "repo_slug", "pipeline_uuid"]
                }
            ),
            types.Tool(
                name="bitbucket_trigger_pipeline",
                description="Trigger a new pipeline run for a branch or commit",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch name to run the pipeline on"
                        },
                        "commit": {
                            "type": "string",
                            "description": "Specific commit hash (optional, defaults to branch HEAD)"
                        }
                    },
                    "required": ["workspace", "repo_slug", "branch"]
                }
            ),
            types.Tool(
                name="bitbucket_list_branches",
                description="List branches for a Bitbucket repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "pagelen": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of results per page"
                        },
                        "q": {
                            "type": "string",
                            "description": "Query filter (e.g. 'name ~ \"feature\"')"
                        }
                    },
                    "required": ["workspace", "repo_slug"]
                }
            ),
            types.Tool(
                name="bitbucket_list_commits",
                description="List commits for a Bitbucket repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "pagelen": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["workspace", "repo_slug"]
                }
            ),
            types.Tool(
                name="bitbucket_get_file",
                description="Get the content of a file from a Bitbucket repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "commit": {
                            "type": "string",
                            "description": "Commit hash or branch name (e.g. 'main', 'HEAD', or a SHA)"
                        },
                        "path": {
                            "type": "string",
                            "description": "File path within the repository"
                        }
                    },
                    "required": ["workspace", "repo_slug", "commit", "path"]
                }
            ),
            types.Tool(
                name="bitbucket_list_workspaces",
                description="List workspaces the authenticated user belongs to",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pagelen": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of results per page"
                        }
                    }
                }
            ),
            types.Tool(
                name="bitbucket_list_workspace_members",
                description="List members of a Bitbucket workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "pagelen": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["workspace"]
                }
            ),
            types.Tool(
                name="bitbucket_get_diff",
                description="Get the diff of a pull request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "Workspace slug or UUID"
                        },
                        "repo_slug": {
                            "type": "string",
                            "description": "Repository slug"
                        },
                        "pull_request_id": {
                            "type": "integer",
                            "description": "Pull request ID"
                        }
                    },
                    "required": ["workspace", "repo_slug", "pull_request_id"]
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Bitbucket resources."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{BASE_URL}/repositories",
                oauth_cred,
                params={"role": "member", "pagelen": 50}
            )
            data = response.json()

            resources = []
            for repo in data.get("values", []):
                full_name = repo.get("full_name", "")

                resources.append(types.Resource(
                    uri=f"bitbucket://repo/{full_name}",
                    name=full_name,
                    description=f"Bitbucket repository: {repo.get('description') or 'No description'}"
                ))

            return resources

        except Exception:
            return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Bitbucket tool.

        Tool names arrive WITHOUT the 'bitbucket_' prefix (stripped by the dispatch layer).
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Bitbucket credentials"

        try:
            if tool_name == "list_repositories":
                return await self._list_repositories(arguments, oauth_cred)
            elif tool_name == "get_repository":
                return await self._get_repository(arguments, oauth_cred)
            elif tool_name == "list_pull_requests":
                return await self._list_pull_requests(arguments, oauth_cred)
            elif tool_name == "get_pull_request":
                return await self._get_pull_request(arguments, oauth_cred)
            elif tool_name == "create_pull_request":
                return await self._create_pull_request(arguments, oauth_cred)
            elif tool_name == "list_pr_comments":
                return await self._list_pr_comments(arguments, oauth_cred)
            elif tool_name == "add_pr_comment":
                return await self._add_pr_comment(arguments, oauth_cred)
            elif tool_name == "list_issues":
                return await self._list_issues(arguments, oauth_cred)
            elif tool_name == "get_issue":
                return await self._get_issue(arguments, oauth_cred)
            elif tool_name == "create_issue":
                return await self._create_issue(arguments, oauth_cred)
            elif tool_name == "list_pipelines":
                return await self._list_pipelines(arguments, oauth_cred)
            elif tool_name == "get_pipeline":
                return await self._get_pipeline(arguments, oauth_cred)
            elif tool_name == "trigger_pipeline":
                return await self._trigger_pipeline(arguments, oauth_cred)
            elif tool_name == "list_branches":
                return await self._list_branches(arguments, oauth_cred)
            elif tool_name == "list_commits":
                return await self._list_commits(arguments, oauth_cred)
            elif tool_name == "get_file":
                return await self._get_file(arguments, oauth_cred)
            elif tool_name == "list_workspaces":
                return await self._list_workspaces(arguments, oauth_cred)
            elif tool_name == "list_workspace_members":
                return await self._list_workspace_members(arguments, oauth_cred)
            elif tool_name == "get_diff":
                return await self._get_diff(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Bitbucket tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Bitbucket resource."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Bitbucket credentials"

        try:
            parts = resource_path.split("/", 2)
            if len(parts) < 2:
                return "Error: Invalid resource path"

            resource_type = parts[0]

            if resource_type == "repo" and len(parts) == 3:
                workspace, repo_slug = parts[1], parts[2]
                response = await self._make_authenticated_request(
                    "GET",
                    f"{BASE_URL}/repositories/{workspace}/{repo_slug}",
                    oauth_cred
                )
                return json.dumps(response.json(), indent=2)

            return "Error: Unsupported resource type"

        except Exception as e:
            return f"Error reading Bitbucket resource: {str(e)}"

    # ── Repository tools ─────────────────────────────────────────────

    async def _list_repositories(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List repositories in a workspace."""
        workspace = arguments["workspace"]
        params: Dict[str, Any] = {}

        if "pagelen" in arguments:
            params["pagelen"] = arguments["pagelen"]
        if "page" in arguments:
            params["page"] = arguments["page"]
        if "q" in arguments:
            params["q"] = arguments["q"]
        if "sort" in arguments:
            params["sort"] = arguments["sort"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = {
            "size": data.get("size"),
            "page": data.get("page"),
            "pagelen": data.get("pagelen"),
            "repositories": []
        }

        for repo in data.get("values", []):
            result["repositories"].append({
                "slug": repo.get("slug"),
                "full_name": repo.get("full_name"),
                "name": repo.get("name"),
                "description": repo.get("description"),
                "is_private": repo.get("is_private"),
                "scm": repo.get("scm"),
                "updated_on": repo.get("updated_on"),
                "language": repo.get("language"),
                "mainbranch": repo.get("mainbranch", {}).get("name") if repo.get("mainbranch") else None,
            })

        return json.dumps(result, indent=2)

    async def _get_repository(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get repository details."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    # ── Pull request tools ───────────────────────────────────────────

    async def _list_pull_requests(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List pull requests for a repository."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        params: Dict[str, Any] = {}

        if "state" in arguments:
            params["state"] = arguments["state"]
        if "pagelen" in arguments:
            params["pagelen"] = arguments["pagelen"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []
        for pr in data.get("values", []):
            result.append({
                "id": pr.get("id"),
                "title": pr.get("title"),
                "state": pr.get("state"),
                "author": pr.get("author", {}).get("display_name"),
                "source_branch": pr.get("source", {}).get("branch", {}).get("name"),
                "destination_branch": pr.get("destination", {}).get("branch", {}).get("name"),
                "created_on": pr.get("created_on"),
                "updated_on": pr.get("updated_on"),
                "comment_count": pr.get("comment_count"),
                "task_count": pr.get("task_count"),
            })

        return json.dumps(result, indent=2)

    async def _get_pull_request(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get details of a specific pull request."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        pr_id = arguments["pull_request_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _create_pull_request(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new pull request."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]

        body: Dict[str, Any] = {
            "title": arguments["title"],
            "source": {
                "branch": {
                    "name": arguments["source_branch"]
                }
            }
        }

        if "destination_branch" in arguments:
            body["destination"] = {
                "branch": {
                    "name": arguments["destination_branch"]
                }
            }

        if "description" in arguments:
            body["description"] = arguments["description"]

        if "close_source_branch" in arguments:
            body["close_source_branch"] = arguments["close_source_branch"]

        response = await self._make_authenticated_request(
            "POST",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests",
            oauth_cred,
            json=body
        )

        pr = response.json()
        result = {
            "id": pr.get("id"),
            "title": pr.get("title"),
            "state": pr.get("state"),
            "source_branch": pr.get("source", {}).get("branch", {}).get("name"),
            "destination_branch": pr.get("destination", {}).get("branch", {}).get("name"),
            "author": pr.get("author", {}).get("display_name"),
            "created_on": pr.get("created_on"),
            "links": {
                "html": pr.get("links", {}).get("html", {}).get("href")
            },
            "message": "Pull request created successfully"
        }

        return json.dumps(result, indent=2)

    async def _list_pr_comments(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List comments on a pull request."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        pr_id = arguments["pull_request_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/comments",
            oauth_cred
        )

        data = response.json()
        result = []
        for comment in data.get("values", []):
            result.append({
                "id": comment.get("id"),
                "content": comment.get("content", {}).get("raw"),
                "user": comment.get("user", {}).get("display_name"),
                "created_on": comment.get("created_on"),
                "updated_on": comment.get("updated_on"),
                "inline": comment.get("inline"),
            })

        return json.dumps(result, indent=2)

    async def _add_pr_comment(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Add a comment to a pull request."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        pr_id = arguments["pull_request_id"]

        body = {
            "content": {
                "raw": arguments["body"]
            }
        }

        response = await self._make_authenticated_request(
            "POST",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/comments",
            oauth_cred,
            json=body
        )

        comment = response.json()
        result = {
            "id": comment.get("id"),
            "content": comment.get("content", {}).get("raw"),
            "user": comment.get("user", {}).get("display_name"),
            "created_on": comment.get("created_on"),
            "message": "Comment added successfully"
        }

        return json.dumps(result, indent=2)

    # ── Issue tools ──────────────────────────────────────────────────

    async def _list_issues(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List issues for a repository.

        Note: Issues may return 404 if the issue tracker is disabled on the repository.
        """
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        params: Dict[str, Any] = {}

        if "q" in arguments:
            params["q"] = arguments["q"]
        if "pagelen" in arguments:
            params["pagelen"] = arguments["pagelen"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/issues",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []
        for issue in data.get("values", []):
            result.append({
                "id": issue.get("id"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "priority": issue.get("priority"),
                "kind": issue.get("kind"),
                "reporter": issue.get("reporter", {}).get("display_name"),
                "assignee": issue.get("assignee", {}).get("display_name") if issue.get("assignee") else None,
                "created_on": issue.get("created_on"),
                "updated_on": issue.get("updated_on"),
            })

        return json.dumps(result, indent=2)

    async def _get_issue(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get details of a specific issue."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        issue_id = arguments["issue_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/issues/{issue_id}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _create_issue(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new issue.

        Note: Issues may return 404 if the issue tracker is disabled on the repository.
        """
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]

        body: Dict[str, Any] = {
            "title": arguments["title"]
        }

        if "content" in arguments:
            body["content"] = {"raw": arguments["content"]}

        if "kind" in arguments:
            body["kind"] = arguments["kind"]

        if "priority" in arguments:
            body["priority"] = arguments["priority"]

        response = await self._make_authenticated_request(
            "POST",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/issues",
            oauth_cred,
            json=body
        )

        issue = response.json()
        result = {
            "id": issue.get("id"),
            "title": issue.get("title"),
            "state": issue.get("state"),
            "kind": issue.get("kind"),
            "priority": issue.get("priority"),
            "reporter": issue.get("reporter", {}).get("display_name"),
            "created_on": issue.get("created_on"),
            "links": {
                "html": issue.get("links", {}).get("html", {}).get("href")
            },
            "message": "Issue created successfully"
        }

        return json.dumps(result, indent=2)

    # ── Pipeline tools ───────────────────────────────────────────────

    async def _list_pipelines(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List pipelines for a repository."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        params: Dict[str, Any] = {}

        if "pagelen" in arguments:
            params["pagelen"] = arguments["pagelen"]
        if "sort" in arguments:
            params["sort"] = arguments["sort"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pipelines",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []
        for pipeline in data.get("values", []):
            target = pipeline.get("target", {})
            result.append({
                "uuid": pipeline.get("uuid"),
                "build_number": pipeline.get("build_number"),
                "state": pipeline.get("state", {}).get("name"),
                "state_result": pipeline.get("state", {}).get("result", {}).get("name") if pipeline.get("state", {}).get("result") else None,
                "target_branch": target.get("ref_name") or target.get("source"),
                "target_type": target.get("ref_type") or target.get("type"),
                "created_on": pipeline.get("created_on"),
                "completed_on": pipeline.get("completed_on"),
                "duration_in_seconds": pipeline.get("duration_in_seconds"),
            })

        return json.dumps(result, indent=2)

    async def _get_pipeline(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get details of a specific pipeline run."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        pipeline_uuid = arguments["pipeline_uuid"]

        # Normalize UUID: ensure it has curly braces
        if not pipeline_uuid.startswith("{"):
            pipeline_uuid = f"{{{pipeline_uuid}}}"

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pipelines/{pipeline_uuid}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _trigger_pipeline(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Trigger a new pipeline run.

        Uses the Bitbucket Pipelines API target format:
        {"target": {"ref_type": "branch", "type": "pipeline_ref_target", "ref_name": "<branch>"}}
        """
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]

        body: Dict[str, Any] = {
            "target": {
                "ref_type": "branch",
                "type": "pipeline_ref_target",
                "ref_name": arguments["branch"]
            }
        }

        if "commit" in arguments:
            body["target"]["commit"] = {"hash": arguments["commit"], "type": "commit"}

        response = await self._make_authenticated_request(
            "POST",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pipelines",
            oauth_cred,
            json=body
        )

        pipeline = response.json()
        result = {
            "uuid": pipeline.get("uuid"),
            "build_number": pipeline.get("build_number"),
            "state": pipeline.get("state", {}).get("name"),
            "target_branch": pipeline.get("target", {}).get("ref_name"),
            "created_on": pipeline.get("created_on"),
            "message": "Pipeline triggered successfully"
        }

        return json.dumps(result, indent=2)

    # ── Branch and commit tools ──────────────────────────────────────

    async def _list_branches(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List branches for a repository."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        params: Dict[str, Any] = {}

        if "pagelen" in arguments:
            params["pagelen"] = arguments["pagelen"]
        if "q" in arguments:
            params["q"] = arguments["q"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/refs/branches",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []
        for branch in data.get("values", []):
            target = branch.get("target", {})
            result.append({
                "name": branch.get("name"),
                "default_merge_strategy": branch.get("default_merge_strategy"),
                "target": {
                    "hash": target.get("hash"),
                    "date": target.get("date"),
                    "message": target.get("message"),
                    "author": target.get("author", {}).get("raw") if target.get("author") else None,
                }
            })

        return json.dumps(result, indent=2)

    async def _list_commits(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List commits for a repository."""
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        params: Dict[str, Any] = {}

        if "pagelen" in arguments:
            params["pagelen"] = arguments["pagelen"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/commits",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []
        for commit in data.get("values", []):
            result.append({
                "hash": commit.get("hash"),
                "message": commit.get("message"),
                "date": commit.get("date"),
                "author": commit.get("author", {}).get("raw"),
                "parents": [p.get("hash") for p in commit.get("parents", [])],
            })

        return json.dumps(result, indent=2)

    # ── File content tool ────────────────────────────────────────────

    async def _get_file(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get file content from a repository.

        Uses the /src/{commit}/{path} endpoint. The commit parameter can be
        a branch name, tag, or commit hash.
        """
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        commit = arguments["commit"]
        path = arguments["path"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/src/{commit}/{path}",
            oauth_cred
        )

        # The src endpoint may return raw file content (not JSON) for files,
        # or JSON for directory listings.
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return json.dumps(response.json(), indent=2)

        return response.text

    # ── Workspace tools ──────────────────────────────────────────────

    async def _list_workspaces(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List workspaces the authenticated user belongs to."""
        params: Dict[str, Any] = {}

        if "pagelen" in arguments:
            params["pagelen"] = arguments["pagelen"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/workspaces",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []
        for ws in data.get("values", []):
            result.append({
                "uuid": ws.get("uuid"),
                "slug": ws.get("slug"),
                "name": ws.get("name"),
                "is_private": ws.get("is_private"),
                "created_on": ws.get("created_on"),
            })

        return json.dumps(result, indent=2)

    async def _list_workspace_members(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List members of a workspace."""
        workspace = arguments["workspace"]
        params: Dict[str, Any] = {}

        if "pagelen" in arguments:
            params["pagelen"] = arguments["pagelen"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/workspaces/{workspace}/members",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []
        for member in data.get("values", []):
            user = member.get("user", {})
            result.append({
                "display_name": user.get("display_name"),
                "uuid": user.get("uuid"),
                "nickname": user.get("nickname"),
                "account_id": user.get("account_id"),
            })

        return json.dumps(result, indent=2)

    # ── Diff tool ────────────────────────────────────────────────────

    async def _get_diff(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get the diff of a pull request.

        The diff endpoint returns plain text (not JSON), so we return
        the raw response body directly.
        """
        workspace = arguments["workspace"]
        repo_slug = arguments["repo_slug"]
        pr_id = arguments["pull_request_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{BASE_URL}/repositories/{workspace}/{repo_slug}/pullrequests/{pr_id}/diff",
            oauth_cred
        )

        return response.text
