"""Linear connector implementation.

All Linear API calls go through GraphQL at https://api.linear.app/graphql.
Uses the shared GraphQLClient for single queries and Relay-style pagination.

Linear priority values: 0=No priority, 1=Urgent, 2=High, 3=Medium, 4=Low.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GraphQL endpoint
# ---------------------------------------------------------------------------
LINEAR_API = "https://api.linear.app/graphql"

# ---------------------------------------------------------------------------
# Query / mutation fragments (kept together so they are easy to audit)
# ---------------------------------------------------------------------------

# -- Issues ----------------------------------------------------------------

_LIST_ISSUES_QUERY = """
query ListIssues($first: Int!, $after: String, $teamId: String, $projectId: String, $stateId: String) {
  issues(
    first: $first
    after: $after
    filter: {
      team: { id: { eq: $teamId } }
      project: { id: { eq: $projectId } }
      state: { id: { eq: $stateId } }
    }
  ) {
    nodes {
      id
      identifier
      title
      description
      priority
      priorityLabel
      url
      createdAt
      updatedAt
      state { id name color }
      assignee { id name email }
      team { id name key }
      project { id name }
      labels { nodes { id name color } }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

_GET_ISSUE_QUERY = """
query GetIssue($id: String!) {
  issue(id: $id) {
    id
    identifier
    title
    description
    priority
    priorityLabel
    estimate
    url
    createdAt
    updatedAt
    completedAt
    canceledAt
    dueDate
    state { id name color }
    assignee { id name email }
    creator { id name email }
    team { id name key }
    project { id name }
    cycle { id name number }
    parent { id identifier title }
    labels { nodes { id name color } }
  }
}
"""

_CREATE_ISSUE_MUTATION = """
mutation CreateIssue($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue {
      id
      identifier
      title
      url
      priority
      priorityLabel
      state { id name }
      assignee { id name }
      team { id name key }
      project { id name }
      labels { nodes { id name } }
      createdAt
    }
  }
}
"""

_UPDATE_ISSUE_MUTATION = """
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue {
      id
      identifier
      title
      url
      priority
      priorityLabel
      state { id name }
      assignee { id name }
      updatedAt
    }
  }
}
"""

_SEARCH_ISSUES_QUERY = """
query SearchIssues($query: String!, $first: Int!, $after: String) {
  issueSearch(query: $query, first: $first, after: $after) {
    nodes {
      id
      identifier
      title
      description
      priority
      priorityLabel
      url
      createdAt
      updatedAt
      state { id name color }
      assignee { id name email }
      team { id name key }
      project { id name }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

_ARCHIVE_ISSUE_MUTATION = """
mutation ArchiveIssue($id: String!) {
  issueArchive(id: $id) {
    success
  }
}
"""

# -- Teams -----------------------------------------------------------------

_LIST_TEAMS_QUERY = """
query ListTeams($first: Int!, $after: String) {
  teams(first: $first, after: $after) {
    nodes {
      id
      name
      key
      description
      color
      icon
      createdAt
      updatedAt
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

_GET_TEAM_QUERY = """
query GetTeam($id: String!) {
  team(id: $id) {
    id
    name
    key
    description
    color
    icon
    createdAt
    updatedAt
    members { nodes { id name email } }
  }
}
"""

# -- Projects --------------------------------------------------------------

_LIST_PROJECTS_QUERY = """
query ListProjects($first: Int!, $after: String) {
  projects(first: $first, after: $after) {
    nodes {
      id
      name
      description
      icon
      color
      state
      progress
      startDate
      targetDate
      url
      createdAt
      updatedAt
      teams { nodes { id name key } }
      lead { id name email }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

_LIST_PROJECTS_BY_TEAM_QUERY = """
query ListProjectsByTeam($teamId: String!, $first: Int!, $after: String) {
  team(id: $teamId) {
    projects(first: $first, after: $after) {
      nodes {
        id
        name
        description
        icon
        color
        state
        progress
        startDate
        targetDate
        url
        createdAt
        updatedAt
        lead { id name email }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

_GET_PROJECT_QUERY = """
query GetProject($id: String!) {
  project(id: $id) {
    id
    name
    description
    icon
    color
    state
    progress
    startDate
    targetDate
    url
    createdAt
    updatedAt
    teams { nodes { id name key } }
    lead { id name email }
    members { nodes { id name email } }
  }
}
"""

_CREATE_PROJECT_MUTATION = """
mutation CreateProject($input: ProjectCreateInput!) {
  projectCreate(input: $input) {
    success
    project {
      id
      name
      description
      url
      state
      createdAt
      teams { nodes { id name key } }
    }
  }
}
"""

# -- Cycles ----------------------------------------------------------------

_LIST_CYCLES_QUERY = """
query ListCycles($teamId: String!, $first: Int!, $after: String) {
  team(id: $teamId) {
    cycles(first: $first, after: $after) {
      nodes {
        id
        name
        number
        startsAt
        endsAt
        completedAt
        progress
        scopeId: id
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

_GET_CYCLE_QUERY = """
query GetCycle($id: String!) {
  cycle(id: $id) {
    id
    name
    number
    startsAt
    endsAt
    completedAt
    progress
    issues { nodes { id identifier title state { name } } }
  }
}
"""

# -- Labels ----------------------------------------------------------------

_LIST_LABELS_QUERY = """
query ListLabels($first: Int!, $after: String) {
  issueLabels(first: $first, after: $after) {
    nodes {
      id
      name
      color
      description
      createdAt
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

# -- Workflow states -------------------------------------------------------

_LIST_WORKFLOW_STATES_QUERY = """
query ListWorkflowStates($teamId: String!, $first: Int!, $after: String) {
  team(id: $teamId) {
    states(first: $first, after: $after) {
      nodes {
        id
        name
        color
        type
        position
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

# -- Comments --------------------------------------------------------------

_ADD_COMMENT_MUTATION = """
mutation AddComment($input: CommentCreateInput!) {
  commentCreate(input: $input) {
    success
    comment {
      id
      body
      url
      createdAt
      user { id name email }
    }
  }
}
"""

_LIST_COMMENTS_QUERY = """
query ListComments($issueId: String!, $first: Int!, $after: String) {
  issue(id: $issueId) {
    comments(first: $first, after: $after) {
      nodes {
        id
        body
        url
        createdAt
        updatedAt
        user { id name email }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

# -- Users -----------------------------------------------------------------

_LIST_USERS_QUERY = """
query ListUsers($first: Int!, $after: String) {
  users(first: $first, after: $after) {
    nodes {
      id
      name
      displayName
      email
      active
      admin
      avatarUrl
      createdAt
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

_GET_USER_BY_EMAIL_QUERY = """
query GetUserByEmail($email: String!) {
  users(filter: { email: { eq: $email } }) {
    nodes {
      id
      name
      displayName
      email
      active
      admin
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


# ---------------------------------------------------------------------------
# Connector implementation
# ---------------------------------------------------------------------------

@register_connector(ConnectorType.LINEAR)
class LinearConnector(BaseConnector):
    """Linear connector for accessing issues, projects, teams, and cycles.

    All API calls use the shared GraphQLClient pointed at Linear's single
    GraphQL endpoint.  Paginated queries use Relay-style cursor pagination
    via ``collect_connection``.
    """

    @property
    def display_name(self) -> str:
        return "Linear"

    @property
    def description(self) -> str:
        return "Access Linear issues, projects, teams, and cycles"

    @property
    def requires_oauth(self) -> bool:
        return True

    # -- helpers -----------------------------------------------------------

    def _get_client(self, oauth_cred: OAuthCredential):
        """Create a GraphQL client for Linear API.

        A new lightweight client is created per call; the underlying HTTP
        connection pool is shared via ``get_http_client()``.
        """
        from .graphql import GraphQLClient

        return GraphQLClient(
            endpoint=LINEAR_API,
            auth_header="Authorization",
            auth_value=f"Bearer {oauth_cred.access_token}",
        )

    # -- BaseConnector interface -------------------------------------------

    async def get_tools(
        self,
        connector: Connector,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> List[types.Tool]:
        """Return the 18 Linear tools with their JSON Schema input definitions."""
        return [
            # 1. list_issues
            types.Tool(
                name="linear_list_issues",
                description="List Linear issues with optional team, project, and state filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "teamId": {
                            "type": "string",
                            "description": "Filter by team ID",
                        },
                        "projectId": {
                            "type": "string",
                            "description": "Filter by project ID",
                        },
                        "stateId": {
                            "type": "string",
                            "description": "Filter by workflow state ID",
                        },
                        "first": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 250,
                            "default": 50,
                            "description": "Number of issues to return",
                        },
                    },
                },
            ),
            # 2. get_issue
            types.Tool(
                name="linear_get_issue",
                description="Get a Linear issue by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Issue ID",
                        },
                    },
                    "required": ["id"],
                },
            ),
            # 3. create_issue
            types.Tool(
                name="linear_create_issue",
                description="Create a new Linear issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Issue title",
                        },
                        "description": {
                            "type": "string",
                            "description": "Issue description (Markdown)",
                        },
                        "teamId": {
                            "type": "string",
                            "description": "Team ID to create the issue in",
                        },
                        "priority": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 4,
                            "description": "Priority: 0=None, 1=Urgent, 2=High, 3=Medium, 4=Low",
                        },
                        "assigneeId": {
                            "type": "string",
                            "description": "User ID to assign",
                        },
                        "labelIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Label IDs to attach",
                        },
                        "stateId": {
                            "type": "string",
                            "description": "Workflow state ID",
                        },
                        "projectId": {
                            "type": "string",
                            "description": "Project ID",
                        },
                    },
                    "required": ["title", "teamId"],
                },
            ),
            # 4. update_issue
            types.Tool(
                name="linear_update_issue",
                description="Update an existing Linear issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Issue ID to update",
                        },
                        "title": {
                            "type": "string",
                            "description": "New title",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description (Markdown)",
                        },
                        "priority": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 4,
                            "description": "Priority: 0=None, 1=Urgent, 2=High, 3=Medium, 4=Low",
                        },
                        "stateId": {
                            "type": "string",
                            "description": "New workflow state ID",
                        },
                        "assigneeId": {
                            "type": "string",
                            "description": "New assignee user ID",
                        },
                    },
                    "required": ["id"],
                },
            ),
            # 5. search_issues
            types.Tool(
                name="linear_search_issues",
                description="Search Linear issues by text query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search text",
                        },
                        "first": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 250,
                            "default": 50,
                            "description": "Maximum results to return",
                        },
                    },
                    "required": ["query"],
                },
            ),
            # 6. archive_issue
            types.Tool(
                name="linear_archive_issue",
                description="Archive a Linear issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Issue ID to archive",
                        },
                    },
                    "required": ["id"],
                },
            ),
            # 7. list_teams
            types.Tool(
                name="linear_list_teams",
                description="List all Linear teams in the organization",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            # 8. get_team
            types.Tool(
                name="linear_get_team",
                description="Get a Linear team by ID with members",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Team ID",
                        },
                    },
                    "required": ["id"],
                },
            ),
            # 9. list_projects
            types.Tool(
                name="linear_list_projects",
                description="List Linear projects, optionally filtered by team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "teamId": {
                            "type": "string",
                            "description": "Optional team ID to filter projects",
                        },
                    },
                },
            ),
            # 10. get_project
            types.Tool(
                name="linear_get_project",
                description="Get a Linear project by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Project ID",
                        },
                    },
                    "required": ["id"],
                },
            ),
            # 11. create_project
            types.Tool(
                name="linear_create_project",
                description="Create a new Linear project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Project name",
                        },
                        "description": {
                            "type": "string",
                            "description": "Project description",
                        },
                        "teamIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Team IDs to associate with the project",
                        },
                    },
                    "required": ["name", "teamIds"],
                },
            ),
            # 12. list_cycles
            types.Tool(
                name="linear_list_cycles",
                description="List cycles for a Linear team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "teamId": {
                            "type": "string",
                            "description": "Team ID",
                        },
                    },
                    "required": ["teamId"],
                },
            ),
            # 13. get_cycle
            types.Tool(
                name="linear_get_cycle",
                description="Get a Linear cycle by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Cycle ID",
                        },
                    },
                    "required": ["id"],
                },
            ),
            # 14. list_labels
            types.Tool(
                name="linear_list_labels",
                description="List all issue labels in the Linear organization",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            # 15. list_workflow_states
            types.Tool(
                name="linear_list_workflow_states",
                description="List workflow states for a Linear team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "teamId": {
                            "type": "string",
                            "description": "Team ID",
                        },
                    },
                    "required": ["teamId"],
                },
            ),
            # 16. add_comment
            types.Tool(
                name="linear_add_comment",
                description="Add a comment to a Linear issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issueId": {
                            "type": "string",
                            "description": "Issue ID to comment on",
                        },
                        "body": {
                            "type": "string",
                            "description": "Comment body (Markdown)",
                        },
                    },
                    "required": ["issueId", "body"],
                },
            ),
            # 17. list_comments
            types.Tool(
                name="linear_list_comments",
                description="List comments on a Linear issue",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issueId": {
                            "type": "string",
                            "description": "Issue ID",
                        },
                    },
                    "required": ["issueId"],
                },
            ),
            # 18. list_users
            types.Tool(
                name="linear_list_users",
                description="List users in the Linear organization",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            # 19. get_user_by_email
            types.Tool(
                name="linear_get_user_by_email",
                description="Look up a Linear organization member by their email address",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email address to look up",
                        },
                    },
                    "required": ["email"],
                },
            ),
        ]

    async def get_resources(
        self,
        connector: Connector,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> List[types.Resource]:
        """Linear does not expose MCP resources."""
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Dispatch a tool call to the appropriate private method.

        ``tool_name`` arrives WITHOUT the ``linear_`` prefix -- the MCP
        server strips the connector prefix before calling us.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Linear credentials"

        try:
            if tool_name == "list_issues":
                return await self._list_issues(arguments, oauth_cred)
            elif tool_name == "get_issue":
                return await self._get_issue(arguments, oauth_cred)
            elif tool_name == "create_issue":
                return await self._create_issue(arguments, oauth_cred)
            elif tool_name == "update_issue":
                return await self._update_issue(arguments, oauth_cred)
            elif tool_name == "search_issues":
                return await self._search_issues(arguments, oauth_cred)
            elif tool_name == "archive_issue":
                return await self._archive_issue(arguments, oauth_cred)
            elif tool_name == "list_teams":
                return await self._list_teams(arguments, oauth_cred)
            elif tool_name == "get_team":
                return await self._get_team(arguments, oauth_cred)
            elif tool_name == "list_projects":
                return await self._list_projects(arguments, oauth_cred)
            elif tool_name == "get_project":
                return await self._get_project(arguments, oauth_cred)
            elif tool_name == "create_project":
                return await self._create_project(arguments, oauth_cred)
            elif tool_name == "list_cycles":
                return await self._list_cycles(arguments, oauth_cred)
            elif tool_name == "get_cycle":
                return await self._get_cycle(arguments, oauth_cred)
            elif tool_name == "list_labels":
                return await self._list_labels(arguments, oauth_cred)
            elif tool_name == "list_workflow_states":
                return await self._list_workflow_states(arguments, oauth_cred)
            elif tool_name == "add_comment":
                return await self._add_comment(arguments, oauth_cred)
            elif tool_name == "list_comments":
                return await self._list_comments(arguments, oauth_cred)
            elif tool_name == "list_users":
                return await self._list_users(arguments, oauth_cred)
            elif tool_name == "get_user_by_email":
                return await self._get_user_by_email(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            logger.exception("Error executing Linear tool '%s'", tool_name)
            return f"Error executing Linear tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Linear does not expose MCP resources."""
        return "Error: Linear connector does not support resource reading"

    # -- Tool implementations ----------------------------------------------

    async def _list_issues(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """List issues with optional team/project/state filters."""
        client = self._get_client(oauth_cred)
        variables: Dict[str, Any] = {}
        if arguments.get("teamId"):
            variables["teamId"] = arguments["teamId"]
        if arguments.get("projectId"):
            variables["projectId"] = arguments["projectId"]
        if arguments.get("stateId"):
            variables["stateId"] = arguments["stateId"]

        max_items = arguments.get("first", 50)
        issues = await client.collect_connection(
            _LIST_ISSUES_QUERY,
            variables,
            connection_path="issues",
            page_size=min(max_items, 50),
            max_items=max_items,
        )
        return json.dumps(issues, indent=2)

    async def _get_issue(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Get a single issue by ID."""
        client = self._get_client(oauth_cred)
        data = await client.execute(_GET_ISSUE_QUERY, {"id": arguments["id"]})
        return json.dumps(data.get("issue", {}), indent=2)

    async def _create_issue(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Create a new issue."""
        client = self._get_client(oauth_cred)
        input_data: Dict[str, Any] = {
            "title": arguments["title"],
            "teamId": arguments["teamId"],
        }
        for key in ("description", "priority", "assigneeId", "labelIds", "stateId", "projectId"):
            if key in arguments:
                input_data[key] = arguments[key]

        data = await client.execute(_CREATE_ISSUE_MUTATION, {"input": input_data})
        payload = data.get("issueCreate", {})
        result = payload.get("issue", {})
        result["success"] = payload.get("success", False)
        return json.dumps(result, indent=2)

    async def _update_issue(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Update an existing issue."""
        client = self._get_client(oauth_cred)
        issue_id = arguments["id"]
        input_data: Dict[str, Any] = {}
        for key in ("title", "description", "priority", "stateId", "assigneeId"):
            if key in arguments:
                input_data[key] = arguments[key]

        data = await client.execute(
            _UPDATE_ISSUE_MUTATION, {"id": issue_id, "input": input_data}
        )
        payload = data.get("issueUpdate", {})
        result = payload.get("issue", {})
        result["success"] = payload.get("success", False)
        return json.dumps(result, indent=2)

    async def _search_issues(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Full-text search for issues."""
        client = self._get_client(oauth_cred)
        max_items = arguments.get("first", 50)
        issues = await client.collect_connection(
            _SEARCH_ISSUES_QUERY,
            {"query": arguments["query"]},
            connection_path="issueSearch",
            page_size=min(max_items, 50),
            max_items=max_items,
        )
        return json.dumps(issues, indent=2)

    async def _archive_issue(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Archive an issue by ID."""
        client = self._get_client(oauth_cred)
        data = await client.execute(_ARCHIVE_ISSUE_MUTATION, {"id": arguments["id"]})
        payload = data.get("issueArchive", {})
        return json.dumps(
            {
                "id": arguments["id"],
                "archived": payload.get("success", False),
            },
            indent=2,
        )

    # -- Teams -------------------------------------------------------------

    async def _list_teams(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """List all teams."""
        client = self._get_client(oauth_cred)
        teams = await client.collect_connection(
            _LIST_TEAMS_QUERY, connection_path="teams"
        )
        return json.dumps(teams, indent=2)

    async def _get_team(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Get a team by ID with its members."""
        client = self._get_client(oauth_cred)
        data = await client.execute(_GET_TEAM_QUERY, {"id": arguments["id"]})
        team = data.get("team", {})
        # Flatten members from nested connection
        if "members" in team:
            team["members"] = team["members"].get("nodes", [])
        return json.dumps(team, indent=2)

    # -- Projects ----------------------------------------------------------

    async def _list_projects(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """List projects, optionally filtered by team."""
        client = self._get_client(oauth_cred)
        team_id = arguments.get("teamId")
        if team_id:
            projects = await client.collect_connection(
                _LIST_PROJECTS_BY_TEAM_QUERY,
                {"teamId": team_id},
                connection_path="team.projects",
            )
        else:
            projects = await client.collect_connection(
                _LIST_PROJECTS_QUERY, connection_path="projects"
            )
        # Flatten nested team connections
        for project in projects:
            if "teams" in project:
                project["teams"] = project["teams"].get("nodes", [])
        return json.dumps(projects, indent=2)

    async def _get_project(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Get a project by ID."""
        client = self._get_client(oauth_cred)
        data = await client.execute(_GET_PROJECT_QUERY, {"id": arguments["id"]})
        project = data.get("project", {})
        # Flatten nested connections
        for key in ("teams", "members"):
            if key in project:
                project[key] = project[key].get("nodes", [])
        return json.dumps(project, indent=2)

    async def _create_project(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Create a new project."""
        client = self._get_client(oauth_cred)
        input_data: Dict[str, Any] = {
            "name": arguments["name"],
            "teamIds": arguments["teamIds"],
        }
        if "description" in arguments:
            input_data["description"] = arguments["description"]

        data = await client.execute(_CREATE_PROJECT_MUTATION, {"input": input_data})
        payload = data.get("projectCreate", {})
        result = payload.get("project", {})
        result["success"] = payload.get("success", False)
        # Flatten teams
        if "teams" in result:
            result["teams"] = result["teams"].get("nodes", [])
        return json.dumps(result, indent=2)

    # -- Cycles ------------------------------------------------------------

    async def _list_cycles(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """List cycles for a team."""
        client = self._get_client(oauth_cred)
        cycles = await client.collect_connection(
            _LIST_CYCLES_QUERY,
            {"teamId": arguments["teamId"]},
            connection_path="team.cycles",
        )
        return json.dumps(cycles, indent=2)

    async def _get_cycle(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Get a cycle by ID."""
        client = self._get_client(oauth_cred)
        data = await client.execute(_GET_CYCLE_QUERY, {"id": arguments["id"]})
        cycle = data.get("cycle", {})
        # Flatten issues connection
        if "issues" in cycle:
            cycle["issues"] = cycle["issues"].get("nodes", [])
        return json.dumps(cycle, indent=2)

    # -- Labels ------------------------------------------------------------

    async def _list_labels(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """List all issue labels."""
        client = self._get_client(oauth_cred)
        labels = await client.collect_connection(
            _LIST_LABELS_QUERY, connection_path="issueLabels"
        )
        return json.dumps(labels, indent=2)

    # -- Workflow states ----------------------------------------------------

    async def _list_workflow_states(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """List workflow states for a team."""
        client = self._get_client(oauth_cred)
        states = await client.collect_connection(
            _LIST_WORKFLOW_STATES_QUERY,
            {"teamId": arguments["teamId"]},
            connection_path="team.states",
        )
        return json.dumps(states, indent=2)

    # -- Comments ----------------------------------------------------------

    async def _add_comment(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Add a comment to an issue."""
        client = self._get_client(oauth_cred)
        input_data = {
            "issueId": arguments["issueId"],
            "body": arguments["body"],
        }
        data = await client.execute(_ADD_COMMENT_MUTATION, {"input": input_data})
        payload = data.get("commentCreate", {})
        result = payload.get("comment", {})
        result["success"] = payload.get("success", False)
        return json.dumps(result, indent=2)

    async def _list_comments(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """List comments on an issue."""
        client = self._get_client(oauth_cred)
        comments = await client.collect_connection(
            _LIST_COMMENTS_QUERY,
            {"issueId": arguments["issueId"]},
            connection_path="issue.comments",
        )
        return json.dumps(comments, indent=2)

    # -- Users -------------------------------------------------------------

    async def _list_users(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """List organization users."""
        client = self._get_client(oauth_cred)
        users = await client.collect_connection(
            _LIST_USERS_QUERY, connection_path="users"
        )
        return json.dumps(users, indent=2)

    async def _get_user_by_email(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """Look up a user by email address."""
        client = self._get_client(oauth_cred)
        data = await client.execute(
            _GET_USER_BY_EMAIL_QUERY, {"email": arguments["email"]}
        )
        users = data.get("users", {}).get("nodes", [])
        return json.dumps(users, indent=2)
