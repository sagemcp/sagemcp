"""GitHub connector implementation."""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


@register_connector(ConnectorType.GITHUB)
class GitHubConnector(BaseConnector):
    """GitHub connector for accessing GitHub API."""

    @property
    def display_name(self) -> str:
        return "GitHub"

    @property
    def description(self) -> str:
        return "Access GitHub repositories, issues, pull requests, and more"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available GitHub tools."""
        tools = [
            types.Tool(
                name="github_list_repositories",
                description="List repositories for the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["all", "owner", "public", "private", "member"],
                            "default": "all",
                            "description": "Type of repositories to list"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["created", "updated", "pushed", "full_name"],
                            "default": "updated",
                            "description": "Sort order"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    }
                }
            ),
            types.Tool(
                name="github_get_repository",
                description="Get detailed information about a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_list_issues",
                description="List issues for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "default": "open",
                            "description": "Issue state"
                        },
                        "labels": {
                            "type": "string",
                            "description": "Comma-separated list of labels"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_get_issue",
                description="Get details of a specific issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "issue_number": {
                            "type": "integer",
                            "description": "Issue number"
                        }
                    },
                    "required": ["owner", "repo", "issue_number"]
                }
            ),
            types.Tool(
                name="github_create_issue",
                description="Create a new issue in a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "title": {
                            "type": "string",
                            "description": "Issue title"
                        },
                        "body": {
                            "type": "string",
                            "description": "Issue body/description"
                        },
                        "labels": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Array of label names to assign"
                        },
                        "assignees": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Array of usernames to assign"
                        },
                        "milestone": {
                            "type": "integer",
                            "description": "Milestone number to associate"
                        }
                    },
                    "required": ["owner", "repo", "title"]
                }
            ),
            types.Tool(
                name="github_update_issue",
                description="Update an existing issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "issue_number": {
                            "type": "integer",
                            "description": "Issue number to update"
                        },
                        "title": {
                            "type": "string",
                            "description": "New issue title"
                        },
                        "body": {
                            "type": "string",
                            "description": "New issue body/description"
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed"],
                            "description": "Issue state"
                        },
                        "labels": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Array of label names (replaces existing labels)"
                        },
                        "assignees": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Array of usernames to assign (replaces existing assignees)"
                        },
                        "milestone": {
                            "type": "integer",
                            "description": "Milestone number to associate (or null to remove)"
                        }
                    },
                    "required": ["owner", "repo", "issue_number"]
                }
            ),
            types.Tool(
                name="github_get_file_content",
                description="Get the content of a file from a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "path": {
                            "type": "string",
                            "description": "File path"
                        },
                        "ref": {
                            "type": "string",
                            "description": "Git reference (branch, tag, or commit SHA)"
                        }
                    },
                    "required": ["owner", "repo", "path"]
                }
            ),
            types.Tool(
                name="github_list_pull_requests",
                description="List pull requests for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "default": "open",
                            "description": "Pull request state"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_search_repositories",
                description="Search for repositories",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "q": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["stars", "forks", "help-wanted-issues", "updated"],
                            "description": "Sort field"
                        },
                        "order": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "default": "desc",
                            "description": "Sort order"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["q"]
                }
            ),
            types.Tool(
                name="github_check_token_scopes",
                description="Check the current OAuth token's scopes and user information",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="github_list_organizations",
                description="List organizations the user belongs to",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="github_get_user_info",
                description="Get information about a specific GitHub user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "GitHub username to look up"
                        }
                    },
                    "required": ["username"]
                }
            ),
            types.Tool(
                name="github_search_users_by_email",
                description="Search for GitHub users by email address. Only matches users who have set their email as public on GitHub.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email address to search for"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 30,
                            "default": 5,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["email"]
                }
            ),
            types.Tool(
                name="github_list_commits",
                description="List commits for a repository or branch",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "sha": {
                            "type": "string",
                            "description": "SHA or branch to start listing commits from"
                        },
                        "path": {
                            "type": "string",
                            "description": "Only commits containing this file path"
                        },
                        "author": {
                            "type": "string",
                            "description": "GitHub username or email of the author"
                        },
                        "since": {
                            "type": "string",
                            "description": "Only commits after this date (ISO 8601)"
                        },
                        "until": {
                            "type": "string",
                            "description": "Only commits before this date (ISO 8601)"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_get_commit",
                description="Get details of a specific commit including files changed, stats, and diff",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "sha": {
                            "type": "string",
                            "description": "Commit SHA"
                        }
                    },
                    "required": ["owner", "repo", "sha"]
                }
            ),
            types.Tool(
                name="github_compare_commits",
                description="Compare two commits or branches to see differences",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "base": {
                            "type": "string",
                            "description": "Base branch or commit SHA"
                        },
                        "head": {
                            "type": "string",
                            "description": "Head branch or commit SHA"
                        }
                    },
                    "required": ["owner", "repo", "base", "head"]
                }
            ),
            types.Tool(
                name="github_list_branches",
                description="List branches for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "protected": {
                            "type": "boolean",
                            "description": "Filter by protected branches"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_get_branch",
                description="Get detailed information about a specific branch",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch name"
                        }
                    },
                    "required": ["owner", "repo", "branch"]
                }
            ),
            types.Tool(
                name="github_get_user_activity",
                description="Get user's recent activity including commits, PRs, issues, and reviews",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "GitHub username"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of events per page"
                        }
                    },
                    "required": ["username"]
                }
            ),
            types.Tool(
                name="github_get_user_stats",
                description="Get statistics about a user's contributions, repos, followers, etc.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "GitHub username"
                        }
                    },
                    "required": ["username"]
                }
            ),
            types.Tool(
                name="github_list_contributors",
                description="List contributors to a repository with contribution stats",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_get_repo_stats",
                description="Get detailed statistics about a repository (languages, activity, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_list_workflows",
                description="List GitHub Actions workflows for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_list_workflow_runs",
                description="List workflow runs for a repository or specific workflow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "workflow_id": {
                            "type": "string",
                            "description": "Optional: Workflow ID or filename to filter"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["completed", "action_required", "cancelled", "failure", "neutral", "skipped", "stale", "success", "timed_out", "in_progress", "queued", "requested", "waiting"],
                            "description": "Filter by status"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_get_workflow_run",
                description="Get details of a specific workflow run",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "run_id": {
                            "type": "integer",
                            "description": "Workflow run ID"
                        }
                    },
                    "required": ["owner", "repo", "run_id"]
                }
            ),
            types.Tool(
                name="github_list_releases",
                description="List releases for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "per_page": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 10,
                            "description": "Number of results per page"
                        }
                    },
                    "required": ["owner", "repo"]
                }
            ),
            types.Tool(
                name="github_get_release",
                description="Get details of a specific release",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner"
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name"
                        },
                        "release_id": {
                            "type": "string",
                            "description": "Release ID or tag name (e.g., 'v1.0.0' or 'latest')"
                        }
                    },
                    "required": ["owner", "repo", "release_id"]
                }
            )
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available GitHub resources."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        # Get user's repositories to create resource URIs
        try:
            response = await self._make_authenticated_request(
                "GET",
                "https://api.github.com/user/repos",
                oauth_cred,
                params={"type": "all", "per_page": 50}
            )
            repos = response.json()

            resources = []
            for repo in repos:
                owner = repo["owner"]["login"]
                name = repo["name"]

                # Add repository resource
                resources.append(types.Resource(
                    uri=f"github://repo/{owner}/{name}",
                    name=f"{owner}/{name}",
                    description=f"GitHub repository: {repo.get('description', 'No description')}"
                ))

                # Add common files as resources
                common_files = ["README.md", "package.json", "pyproject.toml", "Dockerfile", ".github/workflows"]
                for file_path in common_files:
                    resources.append(types.Resource(
                        uri=f"github://file/{owner}/{name}/{file_path}",
                        name=f"{owner}/{name}:{file_path}",
                        description=f"File in {owner}/{name}"
                    ))

            return resources

        except Exception as e:
            print(f"Error fetching GitHub resources: {e}")
            return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a GitHub tool."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired GitHub credentials"

        try:
            if tool_name == "list_repositories":
                return await self._list_repositories(arguments, oauth_cred)
            elif tool_name == "get_repository":
                return await self._get_repository(arguments, oauth_cred)
            elif tool_name == "list_issues":
                return await self._list_issues(arguments, oauth_cred)
            elif tool_name == "get_issue":
                return await self._get_issue(arguments, oauth_cred)
            elif tool_name == "create_issue":
                return await self._create_issue(arguments, oauth_cred)
            elif tool_name == "update_issue":
                return await self._update_issue(arguments, oauth_cred)
            elif tool_name == "get_file_content":
                return await self._get_file_content(arguments, oauth_cred)
            elif tool_name == "list_pull_requests":
                return await self._list_pull_requests(arguments, oauth_cred)
            elif tool_name == "search_repositories":
                return await self._search_repositories(arguments, oauth_cred)
            elif tool_name == "check_token_scopes":
                return await self._check_token_scopes(oauth_cred)
            elif tool_name == "list_organizations":
                return await self._list_organizations(oauth_cred)
            elif tool_name == "get_user_info":
                return await self._get_user_info(arguments, oauth_cred)
            elif tool_name == "search_users_by_email":
                return await self._search_users_by_email(arguments, oauth_cred)
            elif tool_name == "list_commits":
                return await self._list_commits(arguments, oauth_cred)
            elif tool_name == "get_commit":
                return await self._get_commit(arguments, oauth_cred)
            elif tool_name == "compare_commits":
                return await self._compare_commits(arguments, oauth_cred)
            elif tool_name == "list_branches":
                return await self._list_branches(arguments, oauth_cred)
            elif tool_name == "get_branch":
                return await self._get_branch(arguments, oauth_cred)
            elif tool_name == "get_user_activity":
                return await self._get_user_activity(arguments, oauth_cred)
            elif tool_name == "get_user_stats":
                return await self._get_user_stats(arguments, oauth_cred)
            elif tool_name == "list_contributors":
                return await self._list_contributors(arguments, oauth_cred)
            elif tool_name == "get_repo_stats":
                return await self._get_repo_stats(arguments, oauth_cred)
            elif tool_name == "list_workflows":
                return await self._list_workflows(arguments, oauth_cred)
            elif tool_name == "list_workflow_runs":
                return await self._list_workflow_runs(arguments, oauth_cred)
            elif tool_name == "get_workflow_run":
                return await self._get_workflow_run(arguments, oauth_cred)
            elif tool_name == "list_releases":
                return await self._list_releases(arguments, oauth_cred)
            elif tool_name == "get_release":
                return await self._get_release(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing GitHub tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a GitHub resource."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired GitHub credentials"

        try:
            # Parse resource path: repo/owner/name or file/owner/name/path
            parts = resource_path.split("/", 3)
            if len(parts) < 3:
                return "Error: Invalid resource path"

            resource_type = parts[0]
            owner = parts[1]
            repo_name = parts[2]

            if resource_type == "repo":
                # Return repository information
                response = await self._make_authenticated_request(
                    "GET",
                    f"https://api.github.com/repos/{owner}/{repo_name}",
                    oauth_cred
                )
                repo_data = response.json()
                return json.dumps(repo_data, indent=2)

            elif resource_type == "file" and len(parts) == 4:
                file_path = parts[3]
                # Return file content
                response = await self._make_authenticated_request(
                    "GET",
                    f"https://api.github.com/repos/{owner}/{repo_name}/contents/{file_path}",
                    oauth_cred
                )
                file_data = response.json()

                if file_data.get("type") == "file":
                    import base64
                    content = base64.b64decode(file_data["content"]).decode("utf-8")
                    return content
                else:
                    return json.dumps(file_data, indent=2)

            else:
                return "Error: Unsupported resource type"

        except Exception as e:
            return f"Error reading GitHub resource: {str(e)}"

    async def _list_repositories(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List user repositories."""
        params = {
            "type": arguments.get("type", "all"),
            "sort": arguments.get("sort", "updated"),
            "per_page": arguments.get("per_page", 10)
        }

        try:
            print(f"DEBUG: Making GitHub API request to /user/repos with params: {params}")
            response = await self._make_authenticated_request(
                "GET",
                "https://api.github.com/user/repos",
                oauth_cred,
                params=params
            )

            repos = response.json()
            print(f"DEBUG: GitHub API returned {len(repos)} repositories")

            result = []
            for repo in repos:
                result.append({
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description"),
                    "private": repo["private"],
                    "html_url": repo["html_url"],
                    "updated_at": repo["updated_at"]
                })

            return json.dumps(result, indent=2)

        except Exception as e:
            print(f"DEBUG: GitHub API error in _list_repositories: {str(e)}")
            print(f"DEBUG: Error type: {type(e)}")
            if hasattr(e, 'response'):
                print(f"DEBUG: HTTP status: {e.response.status_code}")
                print(f"DEBUG: Response text: {e.response.text}")
            raise

    async def _get_repository(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get repository details."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _list_issues(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List repository issues."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        params = {
            "state": arguments.get("state", "open"),
            "per_page": arguments.get("per_page", 10)
        }

        if "labels" in arguments:
            params["labels"] = arguments["labels"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            oauth_cred,
            params=params
        )

        issues = response.json()
        result = []
        for issue in issues:
            # Skip pull requests (they appear in issues API)
            if "pull_request" not in issue:
                result.append({
                    "number": issue["number"],
                    "title": issue["title"],
                    "state": issue["state"],
                    "user": issue["user"]["login"],
                    "created_at": issue["created_at"],
                    "html_url": issue["html_url"]
                })

        return json.dumps(result, indent=2)

    async def _get_issue(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get details of a specific issue."""
        owner = arguments["owner"]
        repo = arguments["repo"]
        issue_number = arguments["issue_number"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}",
            oauth_cred
        )

        issue = response.json()

        result = {
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body"),
            "state": issue["state"],
            "user": {
                "login": issue["user"]["login"],
                "avatar_url": issue["user"]["avatar_url"]
            },
            "labels": [{"name": label["name"], "color": label["color"]} for label in issue.get("labels", [])],
            "assignees": [{"login": assignee["login"]} for assignee in issue.get("assignees", [])],
            "milestone": issue.get("milestone", {}).get("title") if issue.get("milestone") else None,
            "comments": issue.get("comments", 0),
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "closed_at": issue.get("closed_at"),
            "html_url": issue["html_url"]
        }

        return json.dumps(result, indent=2)

    async def _create_issue(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new issue in a repository."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        # Build request body
        body = {
            "title": arguments["title"]
        }

        if "body" in arguments:
            body["body"] = arguments["body"]

        if "labels" in arguments:
            body["labels"] = arguments["labels"]

        if "assignees" in arguments:
            body["assignees"] = arguments["assignees"]

        if "milestone" in arguments:
            body["milestone"] = arguments["milestone"]

        response = await self._make_authenticated_request(
            "POST",
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            oauth_cred,
            json=body
        )

        issue = response.json()

        result = {
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body"),
            "state": issue["state"],
            "user": issue["user"]["login"],
            "labels": [label["name"] for label in issue.get("labels", [])],
            "assignees": [assignee["login"] for assignee in issue.get("assignees", [])],
            "created_at": issue["created_at"],
            "html_url": issue["html_url"],
            "message": "Issue created successfully"
        }

        return json.dumps(result, indent=2)

    async def _update_issue(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Update an existing issue."""
        owner = arguments["owner"]
        repo = arguments["repo"]
        issue_number = arguments["issue_number"]

        # Build request body with only provided fields
        body = {}

        if "title" in arguments:
            body["title"] = arguments["title"]

        if "body" in arguments:
            body["body"] = arguments["body"]

        if "state" in arguments:
            body["state"] = arguments["state"]

        if "labels" in arguments:
            body["labels"] = arguments["labels"]

        if "assignees" in arguments:
            body["assignees"] = arguments["assignees"]

        if "milestone" in arguments:
            body["milestone"] = arguments["milestone"]

        response = await self._make_authenticated_request(
            "PATCH",
            f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}",
            oauth_cred,
            json=body
        )

        issue = response.json()

        result = {
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body"),
            "state": issue["state"],
            "user": issue["user"]["login"],
            "labels": [label["name"] for label in issue.get("labels", [])],
            "assignees": [assignee["login"] for assignee in issue.get("assignees", [])],
            "updated_at": issue["updated_at"],
            "html_url": issue["html_url"],
            "message": "Issue updated successfully"
        }

        return json.dumps(result, indent=2)

    async def _get_file_content(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get file content from repository."""
        owner = arguments["owner"]
        repo = arguments["repo"]
        path = arguments["path"]
        ref = arguments.get("ref")

        params = {}
        if ref:
            params["ref"] = ref

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            oauth_cred,
            params=params
        )

        file_data = response.json()
        if file_data.get("type") == "file":
            import base64
            content = base64.b64decode(file_data["content"]).decode("utf-8")
            return f"File: {path}\n\n{content}"
        else:
            return json.dumps(file_data, indent=2)

    async def _list_pull_requests(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List repository pull requests."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        params = {
            "state": arguments.get("state", "open"),
            "per_page": arguments.get("per_page", 10)
        }

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            oauth_cred,
            params=params
        )

        pulls = response.json()
        result = []
        for pr in pulls:
            result.append({
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "user": pr["user"]["login"],
                "created_at": pr["created_at"],
                "html_url": pr["html_url"],
                "base": pr["base"]["ref"],
                "head": pr["head"]["ref"]
            })

        return json.dumps(result, indent=2)

    async def _search_repositories(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search for repositories."""
        params = {
            "q": arguments["q"],
            "per_page": arguments.get("per_page", 10)
        }

        if "sort" in arguments:
            params["sort"] = arguments["sort"]
        if "order" in arguments:
            params["order"] = arguments["order"]

        response = await self._make_authenticated_request(
            "GET",
            "https://api.github.com/search/repositories",
            oauth_cred,
            params=params
        )

        search_results = response.json()
        result = {
            "total_count": search_results["total_count"],
            "repositories": []
        }

        for repo in search_results["items"]:
            result["repositories"].append({
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description"),
                "html_url": repo["html_url"],
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "language": repo.get("language")
            })

        return json.dumps(result, indent=2)

    async def _check_token_scopes(self, oauth_cred: OAuthCredential) -> str:
        """Check the current OAuth token's scopes and user information."""
        try:
            # Get current user information
            user_response = await self._make_authenticated_request(
                "GET",
                "https://api.github.com/user",
                oauth_cred
            )
            user_data = user_response.json()

            # Get the token's scopes from the response headers
            token_scopes = user_response.headers.get("X-OAuth-Scopes", "")
            accepted_scopes = user_response.headers.get("X-Accepted-OAuth-Scopes", "")

            # Also check what the stored credential says
            stored_scopes = oauth_cred.scopes if oauth_cred.scopes else "No scopes stored"

            result = {
                "user": {
                    "login": user_data.get("login"),
                    "id": user_data.get("id"),
                    "type": user_data.get("type"),
                    "name": user_data.get("name"),
                    "email": user_data.get("email"),
                    "company": user_data.get("company"),
                    "public_repos": user_data.get("public_repos"),
                    "private_repos": user_data.get("total_private_repos")
                },
                "token_info": {
                    "current_scopes": token_scopes.split(", ") if token_scopes else [],
                    "accepted_scopes": accepted_scopes.split(", ") if accepted_scopes else [],
                    "stored_scopes": stored_scopes,
                    "expires_at": str(oauth_cred.expires_at) if oauth_cred.expires_at else "No expiration"
                }
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error checking token information: {str(e)}"

    async def _list_organizations(self, oauth_cred: OAuthCredential) -> str:
        """List organizations the user belongs to."""
        try:
            # Get user's organizations
            org_response = await self._make_authenticated_request(
                "GET",
                "https://api.github.com/user/orgs",
                oauth_cred
            )
            orgs_data = org_response.json()

            result = {
                "organizations": [],
                "total_count": len(orgs_data)
            }

            for org in orgs_data:
                result["organizations"].append({
                    "login": org.get("login"),
                    "id": org.get("id"),
                    "description": org.get("description"),
                    "url": org.get("url"),
                    "html_url": org.get("html_url")
                })

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error listing organizations: {str(e)}"

    async def _get_user_info(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get information about a specific GitHub user."""
        username = arguments["username"]

        try:
            # Get user information
            user_response = await self._make_authenticated_request(
                "GET",
                f"https://api.github.com/users/{username}",
                oauth_cred
            )
            user_data = user_response.json()

            # Also try to get their repositories
            repos_response = await self._make_authenticated_request(
                "GET",
                f"https://api.github.com/users/{username}/repos",
                oauth_cred,
                params={"per_page": 20}
            )
            repos_data = repos_response.json()

            result = {
                "user": {
                    "login": user_data.get("login"),
                    "id": user_data.get("id"),
                    "type": user_data.get("type"),
                    "name": user_data.get("name"),
                    "company": user_data.get("company"),
                    "blog": user_data.get("blog"),
                    "location": user_data.get("location"),
                    "email": user_data.get("email"),
                    "bio": user_data.get("bio"),
                    "public_repos": user_data.get("public_repos"),
                    "public_gists": user_data.get("public_gists"),
                    "followers": user_data.get("followers"),
                    "following": user_data.get("following"),
                    "created_at": user_data.get("created_at"),
                    "updated_at": user_data.get("updated_at")
                },
                "repositories": []
            }

            for repo in repos_data:
                result["repositories"].append({
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "private": repo["private"],
                    "description": repo.get("description"),
                    "html_url": repo["html_url"],
                    "language": repo.get("language"),
                    "stargazers_count": repo["stargazers_count"],
                    "updated_at": repo["updated_at"]
                })

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting user info for {username}: {str(e)}"

    async def _search_users_by_email(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search for GitHub users by email address."""
        email = arguments["email"]
        per_page = arguments.get("per_page", 5)

        response = await self._make_authenticated_request(
            "GET",
            "https://api.github.com/search/users",
            oauth_cred,
            params={"q": f"{email} in:email", "per_page": per_page}
        )

        search_results = response.json()
        result = {
            "total_count": search_results.get("total_count", 0),
            "users": []
        }

        for user in search_results.get("items", []):
            result["users"].append({
                "login": user["login"],
                "id": user["id"],
                "html_url": user["html_url"],
                "type": user["type"]
            })

        return json.dumps(result, indent=2)

    async def _list_commits(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List commits for a repository."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        params = {
            "per_page": arguments.get("per_page", 10)
        }

        # Add optional filters
        if "sha" in arguments:
            params["sha"] = arguments["sha"]
        if "path" in arguments:
            params["path"] = arguments["path"]
        if "author" in arguments:
            params["author"] = arguments["author"]
        if "since" in arguments:
            params["since"] = arguments["since"]
        if "until" in arguments:
            params["until"] = arguments["until"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/commits",
            oauth_cred,
            params=params
        )

        commits = response.json()
        result = []
        for commit in commits:
            result.append({
                "sha": commit["sha"],
                "message": commit["commit"]["message"],
                "author": {
                    "name": commit["commit"]["author"]["name"],
                    "email": commit["commit"]["author"]["email"],
                    "date": commit["commit"]["author"]["date"]
                },
                "committer": {
                    "name": commit["commit"]["committer"]["name"],
                    "date": commit["commit"]["committer"]["date"]
                },
                "html_url": commit["html_url"],
                "comment_count": commit["commit"]["comment_count"]
            })

        return json.dumps(result, indent=2)

    async def _get_commit(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get detailed information about a specific commit."""
        owner = arguments["owner"]
        repo = arguments["repo"]
        sha = arguments["sha"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
            oauth_cred
        )

        commit = response.json()

        result = {
            "sha": commit["sha"],
            "message": commit["commit"]["message"],
            "author": commit["commit"]["author"],
            "committer": commit["commit"]["committer"],
            "html_url": commit["html_url"],
            "stats": commit.get("stats", {}),
            "files": []
        }

        # Add file changes
        for file in commit.get("files", []):
            result["files"].append({
                "filename": file["filename"],
                "status": file["status"],
                "additions": file["additions"],
                "deletions": file["deletions"],
                "changes": file["changes"],
                "patch": file.get("patch", "")
            })

        return json.dumps(result, indent=2)

    async def _compare_commits(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Compare two commits or branches."""
        owner = arguments["owner"]
        repo = arguments["repo"]
        base = arguments["base"]
        head = arguments["head"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/compare/{base}...{head}",
            oauth_cred
        )

        comparison = response.json()

        result = {
            "status": comparison["status"],
            "ahead_by": comparison["ahead_by"],
            "behind_by": comparison["behind_by"],
            "total_commits": comparison["total_commits"],
            "commits": [],
            "files": []
        }

        # Add commits
        for commit in comparison.get("commits", []):
            result["commits"].append({
                "sha": commit["sha"],
                "message": commit["commit"]["message"],
                "author": commit["commit"]["author"]["name"],
                "date": commit["commit"]["author"]["date"]
            })

        # Add file changes
        for file in comparison.get("files", []):
            result["files"].append({
                "filename": file["filename"],
                "status": file["status"],
                "additions": file["additions"],
                "deletions": file["deletions"],
                "changes": file["changes"]
            })

        return json.dumps(result, indent=2)

    async def _list_branches(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List branches for a repository."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        params = {
            "per_page": arguments.get("per_page", 10)
        }

        if "protected" in arguments:
            params["protected"] = arguments["protected"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/branches",
            oauth_cred,
            params=params
        )

        branches = response.json()
        result = []
        for branch in branches:
            result.append({
                "name": branch["name"],
                "protected": branch["protected"],
                "commit": {
                    "sha": branch["commit"]["sha"],
                    "url": branch["commit"]["url"]
                }
            })

        return json.dumps(result, indent=2)

    async def _get_branch(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get detailed information about a branch."""
        owner = arguments["owner"]
        repo = arguments["repo"]
        branch = arguments["branch"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}",
            oauth_cred
        )

        branch_data = response.json()

        result = {
            "name": branch_data["name"],
            "protected": branch_data["protected"],
            "commit": branch_data["commit"],
            "protection": branch_data.get("protection", {})
        }

        return json.dumps(result, indent=2)

    async def _get_user_activity(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get user's recent activity events."""
        username = arguments["username"]
        per_page = arguments.get("per_page", 10)

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/users/{username}/events",
            oauth_cred,
            params={"per_page": per_page}
        )

        events = response.json()
        result = {
            "username": username,
            "total_events": len(events),
            "events": []
        }

        for event in events:
            event_data = {
                "type": event["type"],
                "created_at": event["created_at"],
                "repo": event["repo"]["name"]
            }

            # Add type-specific details
            if event["type"] == "PushEvent":
                event_data["commits"] = len(event["payload"].get("commits", []))
                event_data["ref"] = event["payload"].get("ref", "")
            elif event["type"] == "PullRequestEvent":
                event_data["action"] = event["payload"].get("action")
                pr = event["payload"].get("pull_request", {})
                event_data["pr_number"] = pr.get("number")
                event_data["pr_title"] = pr.get("title", "")
            elif event["type"] == "PullRequestReviewEvent":
                event_data["action"] = event["payload"].get("action")
                pr = event["payload"].get("pull_request", {})
                event_data["pr_number"] = pr.get("number")
                event_data["pr_title"] = pr.get("title", "")
            elif event["type"] == "PullRequestReviewCommentEvent":
                event_data["action"] = event["payload"].get("action")
                pr = event["payload"].get("pull_request", {})
                event_data["pr_number"] = pr.get("number")
                event_data["pr_title"] = pr.get("title", "")
            elif event["type"] == "IssuesEvent":
                event_data["action"] = event["payload"].get("action")
                issue = event["payload"].get("issue", {})
                event_data["issue_number"] = issue.get("number")
                event_data["issue_title"] = issue.get("title", "")
            elif event["type"] == "IssueCommentEvent":
                event_data["action"] = event["payload"].get("action")
                issue = event["payload"].get("issue", {})
                event_data["issue_number"] = issue.get("number")
            elif event["type"] == "CreateEvent":
                event_data["ref_type"] = event["payload"]["ref_type"]
                event_data["ref"] = event["payload"].get("ref")
            elif event["type"] == "WatchEvent":
                event_data["action"] = event["payload"]["action"]

            result["events"].append(event_data)

        return json.dumps(result, indent=2)

    async def _get_user_stats(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get comprehensive statistics about a user."""
        username = arguments["username"]

        # Get user info
        user_response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/users/{username}",
            oauth_cred
        )
        user_data = user_response.json()

        # Get user's repositories
        repos_response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/users/{username}/repos",
            oauth_cred,
            params={"per_page": 100, "sort": "updated"}
        )
        repos = repos_response.json()

        # Calculate statistics
        total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
        total_forks = sum(repo.get("forks_count", 0) for repo in repos)
        languages = {}
        for repo in repos:
            lang = repo.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        result = {
            "user": {
                "login": user_data["login"],
                "name": user_data.get("name"),
                "bio": user_data.get("bio"),
                "company": user_data.get("company"),
                "location": user_data.get("location"),
                "blog": user_data.get("blog"),
                "twitter": user_data.get("twitter_username"),
                "email": user_data.get("email")
            },
            "statistics": {
                "public_repos": user_data["public_repos"],
                "public_gists": user_data.get("public_gists", 0),
                "followers": user_data["followers"],
                "following": user_data["following"],
                "total_stars_received": total_stars,
                "total_forks_received": total_forks,
                "account_created": user_data["created_at"],
                "last_updated": user_data["updated_at"]
            },
            "languages": languages,
            "top_repositories": []
        }

        # Add top repositories by stars
        top_repos = sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:5]
        for repo in top_repos:
            result["top_repositories"].append({
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description"),
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "language": repo.get("language"),
                "html_url": repo["html_url"]
            })

        return json.dumps(result, indent=2)

    async def _list_contributors(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List contributors to a repository."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/contributors",
            oauth_cred,
            params={"per_page": arguments.get("per_page", 10)}
        )

        contributors = response.json()
        result = []
        for contributor in contributors:
            result.append({
                "login": contributor["login"],
                "contributions": contributor["contributions"],
                "avatar_url": contributor["avatar_url"],
                "html_url": contributor["html_url"],
                "type": contributor["type"]
            })

        return json.dumps(result, indent=2)

    async def _get_repo_stats(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get detailed statistics about a repository."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        # Get repository info
        repo_response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}",
            oauth_cred
        )
        repo_data = repo_response.json()

        # Get languages
        languages_response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/languages",
            oauth_cred
        )
        languages = languages_response.json()

        # Calculate language percentages
        total_bytes = sum(languages.values())
        language_percentages = {
            lang: round((bytes_count / total_bytes) * 100, 2)
            for lang, bytes_count in languages.items()
        } if total_bytes > 0 else {}

        result = {
            "repository": {
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "description": repo_data.get("description"),
                "homepage": repo_data.get("homepage"),
                "created_at": repo_data["created_at"],
                "updated_at": repo_data["updated_at"],
                "pushed_at": repo_data["pushed_at"]
            },
            "statistics": {
                "stars": repo_data["stargazers_count"],
                "watchers": repo_data["watchers_count"],
                "forks": repo_data["forks_count"],
                "open_issues": repo_data["open_issues_count"],
                "size_kb": repo_data["size"],
                "default_branch": repo_data["default_branch"],
                "network_count": repo_data.get("network_count", 0),
                "subscribers_count": repo_data.get("subscribers_count", 0)
            },
            "languages": language_percentages,
            "topics": repo_data.get("topics", []),
            "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
            "visibility": "private" if repo_data["private"] else "public",
            "features": {
                "has_issues": repo_data["has_issues"],
                "has_projects": repo_data["has_projects"],
                "has_wiki": repo_data["has_wiki"],
                "has_pages": repo_data["has_pages"],
                "has_downloads": repo_data["has_downloads"],
                "has_discussions": repo_data.get("has_discussions", False)
            }
        }

        return json.dumps(result, indent=2)

    async def _list_workflows(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List GitHub Actions workflows."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/actions/workflows",
            oauth_cred,
            params={"per_page": arguments.get("per_page", 10)}
        )

        data = response.json()
        result = []
        for workflow in data.get("workflows", []):
            result.append({
                "id": workflow["id"],
                "name": workflow["name"],
                "path": workflow["path"],
                "state": workflow["state"],
                "created_at": workflow["created_at"],
                "updated_at": workflow["updated_at"],
                "html_url": workflow["html_url"]
            })

        return json.dumps(result, indent=2)

    async def _list_workflow_runs(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List workflow runs."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        params = {"per_page": arguments.get("per_page", 10)}

        if "status" in arguments:
            params["status"] = arguments["status"]

        # Determine endpoint based on workflow_id
        if "workflow_id" in arguments:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{arguments['workflow_id']}/runs"
        else:
            url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"

        response = await self._make_authenticated_request(
            "GET",
            url,
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []
        for run in data.get("workflow_runs", []):
            result.append({
                "id": run["id"],
                "name": run["name"],
                "head_branch": run["head_branch"],
                "head_sha": run["head_sha"],
                "status": run["status"],
                "conclusion": run.get("conclusion"),
                "workflow_id": run["workflow_id"],
                "created_at": run["created_at"],
                "updated_at": run["updated_at"],
                "html_url": run["html_url"],
                "event": run["event"]
            })

        return json.dumps(result, indent=2)

    async def _get_workflow_run(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get details of a specific workflow run."""
        owner = arguments["owner"]
        repo = arguments["repo"]
        run_id = arguments["run_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}",
            oauth_cred
        )

        run = response.json()

        result = {
            "id": run["id"],
            "name": run["name"],
            "head_branch": run["head_branch"],
            "head_sha": run["head_sha"],
            "status": run["status"],
            "conclusion": run.get("conclusion"),
            "workflow_id": run["workflow_id"],
            "workflow_name": run.get("workflow_name"),
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
            "run_started_at": run.get("run_started_at"),
            "html_url": run["html_url"],
            "event": run["event"],
            "actor": run["actor"]["login"],
            "run_number": run["run_number"],
            "run_attempt": run["run_attempt"]
        }

        return json.dumps(result, indent=2)

    async def _list_releases(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List releases for a repository."""
        owner = arguments["owner"]
        repo = arguments["repo"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/releases",
            oauth_cred,
            params={"per_page": arguments.get("per_page", 10)}
        )

        releases = response.json()
        result = []
        for release in releases:
            result.append({
                "id": release["id"],
                "tag_name": release["tag_name"],
                "name": release["name"],
                "draft": release["draft"],
                "prerelease": release["prerelease"],
                "created_at": release["created_at"],
                "published_at": release["published_at"],
                "author": release["author"]["login"],
                "html_url": release["html_url"],
                "assets_count": len(release.get("assets", []))
            })

        return json.dumps(result, indent=2)

    async def _get_release(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get details of a specific release."""
        owner = arguments["owner"]
        repo = arguments["repo"]
        release_id = arguments["release_id"]

        # Handle "latest" as special case
        if release_id.lower() == "latest":
            url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        else:
            # Try as tag name first
            url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{release_id}"

        response = await self._make_authenticated_request(
            "GET",
            url,
            oauth_cred
        )

        release = response.json()

        result = {
            "id": release["id"],
            "tag_name": release["tag_name"],
            "target_commitish": release["target_commitish"],
            "name": release["name"],
            "body": release.get("body"),
            "draft": release["draft"],
            "prerelease": release["prerelease"],
            "created_at": release["created_at"],
            "published_at": release["published_at"],
            "author": {
                "login": release["author"]["login"],
                "avatar_url": release["author"]["avatar_url"]
            },
            "html_url": release["html_url"],
            "assets": []
        }

        # Add release assets
        for asset in release.get("assets", []):
            result["assets"].append({
                "name": asset["name"],
                "size": asset["size"],
                "download_count": asset["download_count"],
                "content_type": asset["content_type"],
                "browser_download_url": asset["browser_download_url"],
                "created_at": asset["created_at"],
                "updated_at": asset["updated_at"]
            })

        return json.dumps(result, indent=2)
