"""Jira connector implementation.

This connector enables interaction with Jira Cloud through OAuth 2.0.
Requires OAuth app with scopes: read:jira-work, write:jira-work, read:jira-user, offline_access

OAuth App Setup:
1. Go to https://developer.atlassian.com/console/myapps/
2. Create a new OAuth 2.0 integration
3. Add callback URL matching your SageMCP OAuth configuration
4. Enable required scopes: read:jira-work, write:jira-work, read:jira-user, offline_access
5. Note the Client ID and Client Secret for SageMCP configuration
"""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


@register_connector(ConnectorType.JIRA)
class JiraConnector(BaseConnector):
    """Jira connector for accessing Jira Cloud API."""

    def __init__(self):
        super().__init__()
        self._cloud_id_cache: Dict[str, str] = {}  # Cache cloudId per OAuth token

    @property
    def display_name(self) -> str:
        return "Jira"

    @property
    def description(self) -> str:
        return "Access Jira projects, issues, sprints, boards, and workflows"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def _get_cloud_id(self, oauth_cred: OAuthCredential) -> str:
        """Get Jira Cloud ID for the authenticated user.

        The cloudId is required to construct Jira API endpoints.
        This is cached per OAuth token to minimize API calls.
        """
        # Use access token as cache key
        cache_key = oauth_cred.access_token[:20]  # Use token prefix as key

        if cache_key in self._cloud_id_cache:
            return self._cloud_id_cache[cache_key]

        try:
            print("DEBUG: Fetching Jira accessible resources to get cloudId")
            response = await self._make_authenticated_request(
                "GET",
                "https://api.atlassian.com/oauth/token/accessible-resources",
                oauth_cred
            )

            resources = response.json()
            print(f"DEBUG: Found {len(resources)} accessible Jira resources")

            if not resources:
                raise ValueError("No accessible Jira resources found for this account")

            # Use the first accessible resource
            cloud_id = resources[0]["id"]
            self._cloud_id_cache[cache_key] = cloud_id

            print(f"DEBUG: Using cloudId: {cloud_id} ({resources[0].get('name', 'Unknown')})")
            return cloud_id

        except Exception as e:
            print(f"DEBUG: Error fetching Jira cloudId: {str(e)}")
            raise

    def _get_api_base_url(self, cloud_id: str) -> str:
        """Construct Jira API v3 base URL."""
        return f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3"

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Jira tools."""
        tools = [
            # Issue Management
            types.Tool(
                name="jira_search_issues",
                description="Search for Jira issues using JQL (Jira Query Language)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "jql": {
                            "type": "string",
                            "description": "JQL query string (e.g., 'project = PROJ AND status = Open')"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum number of results to return"
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific fields to include (e.g., ['summary', 'status', 'assignee'])"
                        }
                    },
                    "required": ["jql"]
                }
            ),
            types.Tool(
                name="jira_get_issue",
                description="Get detailed information about a specific Jira issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., 'PROJ-123')"
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific fields to include"
                        }
                    },
                    "required": ["issue_key"]
                }
            ),
            types.Tool(
                name="jira_create_issue",
                description="Create a new Jira issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., 'PROJ')"
                        },
                        "summary": {
                            "type": "string",
                            "description": "Issue summary/title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Issue description (supports Jira markdown)"
                        },
                        "issue_type": {
                            "type": "string",
                            "description": "Issue type (e.g., 'Task', 'Bug', 'Story')"
                        },
                        "assignee_id": {
                            "type": "string",
                            "description": "Assignee account ID (optional)"
                        },
                        "priority_name": {
                            "type": "string",
                            "description": "Priority name (e.g., 'High', 'Medium', 'Low')"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of label strings"
                        }
                    },
                    "required": ["project_key", "summary", "issue_type"]
                }
            ),
            types.Tool(
                name="jira_update_issue",
                description="Update an existing Jira issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., 'PROJ-123')"
                        },
                        "summary": {
                            "type": "string",
                            "description": "New summary/title"
                        },
                        "description": {
                            "type": "string",
                            "description": "New description"
                        },
                        "assignee_id": {
                            "type": "string",
                            "description": "New assignee account ID"
                        },
                        "priority_name": {
                            "type": "string",
                            "description": "New priority name"
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New labels array"
                        }
                    },
                    "required": ["issue_key"]
                }
            ),
            types.Tool(
                name="jira_transition_issue",
                description="Transition an issue through workflow (e.g., move to 'In Progress' or 'Done')",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., 'PROJ-123')"
                        },
                        "transition_id": {
                            "type": "string",
                            "description": "Transition ID (use jira_get_transitions to find valid IDs)"
                        },
                        "comment": {
                            "type": "string",
                            "description": "Optional comment to add during transition"
                        }
                    },
                    "required": ["issue_key", "transition_id"]
                }
            ),
            types.Tool(
                name="jira_get_transitions",
                description="Get available workflow transitions for an issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., 'PROJ-123')"
                        }
                    },
                    "required": ["issue_key"]
                }
            ),
            types.Tool(
                name="jira_assign_issue",
                description="Assign an issue to a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., 'PROJ-123')"
                        },
                        "account_id": {
                            "type": "string",
                            "description": "Account ID of the user to assign (use jira_search_users to find)"
                        }
                    },
                    "required": ["issue_key", "account_id"]
                }
            ),

            # Comments
            types.Tool(
                name="jira_add_comment",
                description="Add a comment to an issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., 'PROJ-123')"
                        },
                        "body": {
                            "type": "string",
                            "description": "Comment text (supports Jira markdown)"
                        }
                    },
                    "required": ["issue_key", "body"]
                }
            ),
            types.Tool(
                name="jira_get_comments",
                description="Get all comments for an issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., 'PROJ-123')"
                        }
                    },
                    "required": ["issue_key"]
                }
            ),

            # Projects
            types.Tool(
                name="jira_list_projects",
                description="List all accessible Jira projects",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum number of results"
                        }
                    }
                }
            ),
            types.Tool(
                name="jira_get_project",
                description="Get detailed information about a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., 'PROJ')"
                        }
                    },
                    "required": ["project_key"]
                }
            ),

            # Boards & Sprints
            types.Tool(
                name="jira_list_boards",
                description="List all Jira boards",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Filter by project key (optional)"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum number of results"
                        }
                    }
                }
            ),
            types.Tool(
                name="jira_get_board",
                description="Get detailed information about a board",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "Board ID"
                        }
                    },
                    "required": ["board_id"]
                }
            ),
            types.Tool(
                name="jira_list_sprints",
                description="List sprints for a board",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "Board ID"
                        },
                        "state": {
                            "type": "string",
                            "enum": ["active", "future", "closed"],
                            "description": "Filter by sprint state (optional)"
                        }
                    },
                    "required": ["board_id"]
                }
            ),
            types.Tool(
                name="jira_get_sprint",
                description="Get detailed information about a sprint",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sprint_id": {
                            "type": "integer",
                            "description": "Sprint ID"
                        }
                    },
                    "required": ["sprint_id"]
                }
            ),
            types.Tool(
                name="jira_get_sprint_issues",
                description="Get all issues in a sprint",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sprint_id": {
                            "type": "integer",
                            "description": "Sprint ID"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum number of results"
                        }
                    },
                    "required": ["sprint_id"]
                }
            ),

            # User Management
            types.Tool(
                name="jira_search_users",
                description="Search for Jira users",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (name or email)"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum number of results"
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="jira_get_current_user",
                description="Get information about the currently authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            ),

            # Versions/Releases
            types.Tool(
                name="jira_list_versions",
                description="List versions/releases for a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., 'PROJ')"
                        }
                    },
                    "required": ["project_key"]
                }
            ),
            types.Tool(
                name="jira_get_version",
                description="Get detailed information about a version/release",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "version_id": {
                            "type": "string",
                            "description": "Version ID"
                        }
                    },
                    "required": ["version_id"]
                }
            )
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Jira resources."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        try:
            cloud_id = await self._get_cloud_id(oauth_cred)
            base_url = self._get_api_base_url(cloud_id)

            # Get user's accessible projects
            response = await self._make_authenticated_request(
                "GET",
                f"{base_url}/project",
                oauth_cred,
                params={"maxResults": 50}
            )
            projects = response.json()

            resources = []

            # Add project resources
            for project in projects:
                project_key = project["key"]
                resources.append(types.Resource(
                    uri=f"jira://project/{project_key}",
                    name=f"{project_key}: {project['name']}",
                    description=f"Jira project: {project.get('description', 'No description')}"
                ))

            # Get recent issues across all projects
            try:
                issue_response = await self._make_authenticated_request(
                    "GET",
                    f"{base_url}/search/jql",
                    oauth_cred,
                    params={
                        "jql": "updated >= -30d ORDER BY updated DESC",
                        "maxResults": 20,
                        "fields": "summary,status"
                    }
                )
                issues = issue_response.json().get("issues", [])

                # Add issue resources
                for issue in issues:
                    issue_key = issue["key"]
                    summary = issue["fields"].get("summary", "No summary")
                    resources.append(types.Resource(
                        uri=f"jira://issue/{issue_key}",
                        name=f"{issue_key}: {summary}",
                        description="Jira issue"
                    ))
            except Exception as e:
                print(f"DEBUG: Could not fetch recent issues: {e}")

            return resources

        except Exception as e:
            print(f"Error fetching Jira resources: {e}")
            return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Jira tool."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Jira credentials"

        try:
            # Get cloud ID for API requests
            cloud_id = await self._get_cloud_id(oauth_cred)

            # Route to appropriate handler
            if tool_name == "search_issues":
                return await self._search_issues(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_issue":
                return await self._get_issue(cloud_id, arguments, oauth_cred)
            elif tool_name == "create_issue":
                return await self._create_issue(cloud_id, arguments, oauth_cred)
            elif tool_name == "update_issue":
                return await self._update_issue(cloud_id, arguments, oauth_cred)
            elif tool_name == "transition_issue":
                return await self._transition_issue(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_transitions":
                return await self._get_transitions(cloud_id, arguments, oauth_cred)
            elif tool_name == "assign_issue":
                return await self._assign_issue(cloud_id, arguments, oauth_cred)
            elif tool_name == "add_comment":
                return await self._add_comment(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_comments":
                return await self._get_comments(cloud_id, arguments, oauth_cred)
            elif tool_name == "list_projects":
                return await self._list_projects(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_project":
                return await self._get_project(cloud_id, arguments, oauth_cred)
            elif tool_name == "list_boards":
                return await self._list_boards(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_board":
                return await self._get_board(cloud_id, arguments, oauth_cred)
            elif tool_name == "list_sprints":
                return await self._list_sprints(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_sprint":
                return await self._get_sprint(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_sprint_issues":
                return await self._get_sprint_issues(cloud_id, arguments, oauth_cred)
            elif tool_name == "search_users":
                return await self._search_users(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_current_user":
                return await self._get_current_user(cloud_id, oauth_cred)
            elif tool_name == "list_versions":
                return await self._list_versions(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_version":
                return await self._get_version(cloud_id, arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Jira tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Jira resource."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Jira credentials"

        try:
            cloud_id = await self._get_cloud_id(oauth_cred)
            base_url = self._get_api_base_url(cloud_id)

            # Parse resource path: project/{key} or issue/{key} or board/{id}
            parts = resource_path.split("/", 1)
            if len(parts) < 2:
                return "Error: Invalid resource path"

            resource_type = parts[0]
            resource_id = parts[1]

            if resource_type == "project":
                response = await self._make_authenticated_request(
                    "GET",
                    f"{base_url}/project/{resource_id}",
                    oauth_cred
                )
                return json.dumps(response.json(), indent=2)

            elif resource_type == "issue":
                response = await self._make_authenticated_request(
                    "GET",
                    f"{base_url}/issue/{resource_id}",
                    oauth_cred
                )
                return json.dumps(response.json(), indent=2)

            elif resource_type == "board":
                # Boards use Agile API
                agile_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/agile/1.0"
                response = await self._make_authenticated_request(
                    "GET",
                    f"{agile_url}/board/{resource_id}",
                    oauth_cred
                )
                return json.dumps(response.json(), indent=2)

            else:
                return "Error: Unsupported resource type"

        except Exception as e:
            return f"Error reading Jira resource: {str(e)}"

    # Private implementation methods

    async def _search_issues(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search issues using JQL."""
        base_url = self._get_api_base_url(cloud_id)
        jql = arguments["jql"]
        max_results = arguments.get("max_results", 50)
        fields = arguments.get("fields", ["summary", "status", "assignee", "priority", "created", "updated"])

        # The new /search/jql endpoint requires bounded queries
        # Add a default time filter if the JQL only contains ORDER BY
        jql_upper = jql.upper().strip()
        if jql_upper.startswith("ORDER BY") and "WHERE" not in jql_upper and "=" not in jql:
            # Add a 90-day time restriction for unbounded ORDER BY queries
            jql = f"updated >= -90d {jql}"
            print(f"DEBUG: Added time restriction to unbounded query: {jql}")

        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": ",".join(fields) if isinstance(fields, list) else fields
        }

        print(f"DEBUG: Searching Jira issues with JQL: {jql}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/search/jql",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = {
            "total": data.get("total", 0),
            "issues": []
        }

        for issue in data.get("issues", []):
            result["issues"].append({
                "key": issue["key"],
                "fields": issue.get("fields", {})
            })

        print(f"DEBUG: Found {result['total']} issues")
        return json.dumps(result, indent=2)

    async def _get_issue(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get issue details."""
        base_url = self._get_api_base_url(cloud_id)
        issue_key = arguments["issue_key"]
        fields = arguments.get("fields")

        params = {}
        if fields:
            params["fields"] = ",".join(fields) if isinstance(fields, list) else fields

        print(f"DEBUG: Fetching Jira issue: {issue_key}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/issue/{issue_key}",
            oauth_cred,
            params=params
        )

        return json.dumps(response.json(), indent=2)

    async def _create_issue(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new issue."""
        base_url = self._get_api_base_url(cloud_id)

        # Build fields object
        fields = {
            "project": {"key": arguments["project_key"]},
            "summary": arguments["summary"],
            "issuetype": {"name": arguments["issue_type"]}
        }

        if "description" in arguments:
            # Jira API v3 uses Atlassian Document Format for description
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": arguments["description"]
                            }
                        ]
                    }
                ]
            }

        if "assignee_id" in arguments:
            fields["assignee"] = {"id": arguments["assignee_id"]}

        if "priority_name" in arguments:
            fields["priority"] = {"name": arguments["priority_name"]}

        if "labels" in arguments:
            fields["labels"] = arguments["labels"]

        payload = {"fields": fields}

        print(f"DEBUG: Creating Jira issue in project {arguments['project_key']}")
        response = await self._make_authenticated_request(
            "POST",
            f"{base_url}/issue",
            oauth_cred,
            json=payload
        )

        result = response.json()
        print(f"DEBUG: Created issue: {result.get('key')}")
        return json.dumps(result, indent=2)

    async def _update_issue(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Update an existing issue."""
        base_url = self._get_api_base_url(cloud_id)
        issue_key = arguments["issue_key"]

        # Build fields to update
        fields = {}

        if "summary" in arguments:
            fields["summary"] = arguments["summary"]

        if "description" in arguments:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": arguments["description"]
                            }
                        ]
                    }
                ]
            }

        if "assignee_id" in arguments:
            fields["assignee"] = {"id": arguments["assignee_id"]}

        if "priority_name" in arguments:
            fields["priority"] = {"name": arguments["priority_name"]}

        if "labels" in arguments:
            fields["labels"] = arguments["labels"]

        payload = {"fields": fields}

        print(f"DEBUG: Updating Jira issue: {issue_key}")
        await self._make_authenticated_request(
            "PUT",
            f"{base_url}/issue/{issue_key}",
            oauth_cred,
            json=payload
        )

        # PUT returns 204 No Content on success
        print(f"DEBUG: Issue {issue_key} updated successfully")
        return json.dumps({"message": f"Issue {issue_key} updated successfully"}, indent=2)

    async def _transition_issue(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Transition an issue through workflow."""
        base_url = self._get_api_base_url(cloud_id)
        issue_key = arguments["issue_key"]
        transition_id = arguments["transition_id"]

        payload = {
            "transition": {"id": transition_id}
        }

        if "comment" in arguments:
            payload["update"] = {
                "comment": [
                    {
                        "add": {
                            "body": {
                                "type": "doc",
                                "version": 1,
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": arguments["comment"]
                                            }
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                ]
            }

        print(f"DEBUG: Transitioning issue {issue_key} with transition {transition_id}")
        await self._make_authenticated_request(
            "POST",
            f"{base_url}/issue/{issue_key}/transitions",
            oauth_cred,
            json=payload
        )

        print(f"DEBUG: Issue {issue_key} transitioned successfully")
        return json.dumps({"message": f"Issue {issue_key} transitioned successfully"}, indent=2)

    async def _get_transitions(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get available transitions for an issue."""
        base_url = self._get_api_base_url(cloud_id)
        issue_key = arguments["issue_key"]

        print(f"DEBUG: Fetching transitions for issue: {issue_key}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/issue/{issue_key}/transitions",
            oauth_cred
        )

        data = response.json()
        result = {
            "issue": issue_key,
            "transitions": []
        }

        for transition in data.get("transitions", []):
            result["transitions"].append({
                "id": transition["id"],
                "name": transition["name"],
                "to": transition.get("to", {}).get("name")
            })

        return json.dumps(result, indent=2)

    async def _assign_issue(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Assign an issue to a user."""
        base_url = self._get_api_base_url(cloud_id)
        issue_key = arguments["issue_key"]
        account_id = arguments["account_id"]

        payload = {"accountId": account_id}

        print(f"DEBUG: Assigning issue {issue_key} to user {account_id}")
        await self._make_authenticated_request(
            "PUT",
            f"{base_url}/issue/{issue_key}/assignee",
            oauth_cred,
            json=payload
        )

        print(f"DEBUG: Issue {issue_key} assigned successfully")
        return json.dumps({"message": f"Issue {issue_key} assigned successfully"}, indent=2)

    async def _add_comment(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Add a comment to an issue."""
        base_url = self._get_api_base_url(cloud_id)
        issue_key = arguments["issue_key"]
        body = arguments["body"]

        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": body
                            }
                        ]
                    }
                ]
            }
        }

        print(f"DEBUG: Adding comment to issue: {issue_key}")
        response = await self._make_authenticated_request(
            "POST",
            f"{base_url}/issue/{issue_key}/comment",
            oauth_cred,
            json=payload
        )

        result = response.json()
        print("DEBUG: Comment added successfully")
        return json.dumps(result, indent=2)

    async def _get_comments(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get all comments for an issue."""
        base_url = self._get_api_base_url(cloud_id)
        issue_key = arguments["issue_key"]

        print(f"DEBUG: Fetching comments for issue: {issue_key}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/issue/{issue_key}/comment",
            oauth_cred
        )

        data = response.json()
        result = {
            "total": data.get("total", 0),
            "comments": []
        }

        for comment in data.get("comments", []):
            result["comments"].append({
                "id": comment["id"],
                "author": comment.get("author", {}).get("displayName"),
                "created": comment.get("created"),
                "updated": comment.get("updated"),
                "body": comment.get("body")
            })

        return json.dumps(result, indent=2)

    async def _list_projects(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List all accessible projects."""
        base_url = self._get_api_base_url(cloud_id)
        max_results = arguments.get("max_results", 50)

        print("DEBUG: Listing Jira projects")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/project",
            oauth_cred,
            params={"maxResults": max_results}
        )

        projects = response.json()
        result = []

        for project in projects:
            result.append({
                "id": project["id"],
                "key": project["key"],
                "name": project["name"],
                "projectTypeKey": project.get("projectTypeKey"),
                "description": project.get("description"),
                "lead": project.get("lead", {}).get("displayName")
            })

        print(f"DEBUG: Found {len(result)} projects")
        return json.dumps(result, indent=2)

    async def _get_project(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get project details."""
        base_url = self._get_api_base_url(cloud_id)
        project_key = arguments["project_key"]

        print(f"DEBUG: Fetching project: {project_key}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/project/{project_key}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _list_boards(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List all boards."""
        # Boards use Agile API (v1.0)
        agile_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/agile/1.0"

        params = {
            "maxResults": arguments.get("max_results", 50)
        }

        if "project_key" in arguments:
            params["projectKeyOrId"] = arguments["project_key"]

        print("DEBUG: Listing Jira boards")
        response = await self._make_authenticated_request(
            "GET",
            f"{agile_url}/board",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []

        for board in data.get("values", []):
            result.append({
                "id": board["id"],
                "name": board["name"],
                "type": board["type"],
                "location": board.get("location", {})
            })

        print(f"DEBUG: Found {len(result)} boards")
        return json.dumps(result, indent=2)

    async def _get_board(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get board details."""
        agile_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/agile/1.0"
        board_id = arguments["board_id"]

        print(f"DEBUG: Fetching board: {board_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{agile_url}/board/{board_id}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _list_sprints(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List sprints for a board."""
        agile_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/agile/1.0"
        board_id = arguments["board_id"]

        params = {}
        if "state" in arguments:
            params["state"] = arguments["state"]

        print(f"DEBUG: Listing sprints for board: {board_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{agile_url}/board/{board_id}/sprint",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []

        for sprint in data.get("values", []):
            result.append({
                "id": sprint["id"],
                "name": sprint["name"],
                "state": sprint["state"],
                "startDate": sprint.get("startDate"),
                "endDate": sprint.get("endDate"),
                "completeDate": sprint.get("completeDate"),
                "goal": sprint.get("goal")
            })

        print(f"DEBUG: Found {len(result)} sprints")
        return json.dumps(result, indent=2)

    async def _get_sprint(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get sprint details."""
        agile_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/agile/1.0"
        sprint_id = arguments["sprint_id"]

        print(f"DEBUG: Fetching sprint: {sprint_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{agile_url}/sprint/{sprint_id}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _get_sprint_issues(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get issues in a sprint."""
        agile_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/agile/1.0"
        sprint_id = arguments["sprint_id"]
        max_results = arguments.get("max_results", 50)

        print(f"DEBUG: Fetching issues for sprint: {sprint_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{agile_url}/sprint/{sprint_id}/issue",
            oauth_cred,
            params={"maxResults": max_results}
        )

        data = response.json()
        result = {
            "total": data.get("total", 0),
            "issues": []
        }

        for issue in data.get("issues", []):
            result["issues"].append({
                "key": issue["key"],
                "summary": issue["fields"].get("summary"),
                "status": issue["fields"].get("status", {}).get("name"),
                "assignee": issue["fields"].get("assignee", {}).get("displayName") if issue["fields"].get("assignee") else None
            })

        print(f"DEBUG: Found {result['total']} issues in sprint")
        return json.dumps(result, indent=2)

    async def _search_users(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search for users."""
        base_url = self._get_api_base_url(cloud_id)
        query = arguments["query"]
        max_results = arguments.get("max_results", 50)

        print(f"DEBUG: Searching for users: {query}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/user/search",
            oauth_cred,
            params={
                "query": query,
                "maxResults": max_results
            }
        )

        users = response.json()
        result = []

        for user in users:
            result.append({
                "accountId": user["accountId"],
                "displayName": user.get("displayName"),
                "emailAddress": user.get("emailAddress"),
                "active": user.get("active")
            })

        print(f"DEBUG: Found {len(result)} users")
        return json.dumps(result, indent=2)

    async def _get_current_user(self, cloud_id: str, oauth_cred: OAuthCredential) -> str:
        """Get current user information."""
        base_url = self._get_api_base_url(cloud_id)

        print("DEBUG: Fetching current user")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/myself",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _list_versions(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List versions for a project."""
        base_url = self._get_api_base_url(cloud_id)
        project_key = arguments["project_key"]

        print(f"DEBUG: Listing versions for project: {project_key}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/project/{project_key}/versions",
            oauth_cred
        )

        versions = response.json()
        result = []

        for version in versions:
            result.append({
                "id": version["id"],
                "name": version["name"],
                "description": version.get("description"),
                "archived": version.get("archived"),
                "released": version.get("released"),
                "releaseDate": version.get("releaseDate")
            })

        print(f"DEBUG: Found {len(result)} versions")
        return json.dumps(result, indent=2)

    async def _get_version(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get version details."""
        base_url = self._get_api_base_url(cloud_id)
        version_id = arguments["version_id"]

        print(f"DEBUG: Fetching version: {version_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/version/{version_id}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)
