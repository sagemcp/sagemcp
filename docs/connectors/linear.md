# Linear Connector

The Linear connector provides comprehensive integration with Linear's GraphQL API, enabling Claude Desktop to interact with issues, projects, teams, cycles, labels, workflow states, and users through OAuth 2.0 authentication. All API calls use GraphQL with Relay-style cursor pagination.

## Features

- **18 comprehensive tools** covering issues, teams, projects, cycles, labels, workflow states, comments, and users
- **Full OAuth 2.0 authentication** with Linear's OAuth provider
- **GraphQL API** with efficient Relay-style cursor pagination
- **Full-text search** across issues
- **Rich issue management** including create, update, archive, and comment

## OAuth Setup

### Prerequisites

- A Linear account with admin or owner access to the workspace
- Access to create OAuth applications

### Step-by-Step Configuration

1. **Create Linear OAuth Application**
   - Go to Linear Settings > API > OAuth Applications
   - Click "New OAuth Application"
   - Fill in the details:
     - **Application name**: `SageMCP` (or your preferred name)
     - **Redirect URI**: `http://localhost:8000/api/v1/oauth/callback/linear`
     - **Description**: Optional description of your integration
   - Click "Create"

2. **Get Credentials**
   - Note the **Client ID**
   - Note the **Client Secret**
   - Save both credentials securely

3. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     LINEAR_CLIENT_ID=your_client_id_here
     LINEAR_CLIENT_SECRET=your_client_secret_here
     ```

4. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add Linear connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The Linear connector requests full API access via the `read` and `write` scopes during OAuth authorization.

## Available Tools

### Issue Management

#### `linear_list_issues`
List Linear issues with optional team, project, and state filters.

**Parameters:**
- `teamId` (optional): Filter by team ID
- `projectId` (optional): Filter by project ID
- `stateId` (optional): Filter by workflow state ID
- `first` (optional): Number of issues to return (1-250, default: 50)

#### `linear_get_issue`
Get a Linear issue by ID.

**Parameters:**
- `id` (required): Issue ID

#### `linear_create_issue`
Create a new Linear issue.

**Parameters:**
- `title` (required): Issue title
- `teamId` (required): Team ID to create the issue in
- `description` (optional): Issue description (Markdown)
- `priority` (optional): Priority level - `0` (None), `1` (Urgent), `2` (High), `3` (Medium), `4` (Low)
- `assigneeId` (optional): User ID to assign
- `labelIds` (optional): Array of label IDs to attach
- `stateId` (optional): Workflow state ID
- `projectId` (optional): Project ID

#### `linear_update_issue`
Update an existing Linear issue.

**Parameters:**
- `id` (required): Issue ID to update
- `title` (optional): New title
- `description` (optional): New description (Markdown)
- `priority` (optional): Priority level - `0` (None), `1` (Urgent), `2` (High), `3` (Medium), `4` (Low)
- `stateId` (optional): New workflow state ID
- `assigneeId` (optional): New assignee user ID

#### `linear_search_issues`
Search Linear issues by text query.

**Parameters:**
- `query` (required): Search text
- `first` (optional): Maximum results to return (1-250, default: 50)

#### `linear_archive_issue`
Archive a Linear issue.

**Parameters:**
- `id` (required): Issue ID to archive

### Teams

#### `linear_list_teams`
List all Linear teams in the organization.

**Parameters:** None

#### `linear_get_team`
Get a Linear team by ID with members.

**Parameters:**
- `id` (required): Team ID

### Projects

#### `linear_list_projects`
List Linear projects, optionally filtered by team.

**Parameters:**
- `teamId` (optional): Team ID to filter projects

#### `linear_get_project`
Get a Linear project by ID.

**Parameters:**
- `id` (required): Project ID

#### `linear_create_project`
Create a new Linear project.

**Parameters:**
- `name` (required): Project name
- `teamIds` (required): Array of team IDs to associate with the project
- `description` (optional): Project description

### Cycles

#### `linear_list_cycles`
List cycles for a Linear team.

**Parameters:**
- `teamId` (required): Team ID

#### `linear_get_cycle`
Get a Linear cycle by ID.

**Parameters:**
- `id` (required): Cycle ID

### Labels & Workflow States

#### `linear_list_labels`
List all issue labels in the Linear organization.

**Parameters:** None

#### `linear_list_workflow_states`
List workflow states for a Linear team.

**Parameters:**
- `teamId` (required): Team ID

### Comments

#### `linear_add_comment`
Add a comment to a Linear issue.

**Parameters:**
- `issueId` (required): Issue ID to comment on
- `body` (required): Comment body (Markdown)

#### `linear_list_comments`
List comments on a Linear issue.

**Parameters:**
- `issueId` (required): Issue ID

### Users

#### `linear_list_users`
List users in the Linear organization.

**Parameters:** None

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Linear credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "You don't have access to this resource"
- **Solution**: Ensure your Linear account has the appropriate permissions within the workspace. Only workspace members can access the API.

**Issue**: Empty results when filtering by team or project
- **Solution**: Verify the team ID or project ID is correct. Use `linear_list_teams` or `linear_list_projects` to find valid IDs.

**Issue**: Priority values seem wrong
- **Solution**: Linear uses an inverted priority scale: `0` = No priority, `1` = Urgent, `2` = High, `3` = Medium, `4` = Low. Lower numbers mean higher priority.

**Issue**: "Rate limit exceeded"
- **Solution**: Linear's API has rate limits. The connector uses pagination to minimize requests. Wait or reduce the `first` parameter in your queries.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Executing Linear GraphQL query: ListIssues
DEBUG: Linear API returned data for 50 issues
```

## API Reference

- **Linear GraphQL API Documentation**: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
- **OAuth 2.0 Authentication**: https://developers.linear.app/docs/oauth/authentication
- **Rate Limiting**: https://developers.linear.app/docs/graphql/rate-limiting

## Source Code

Implementation: `src/sage_mcp/connectors/linear.py`
