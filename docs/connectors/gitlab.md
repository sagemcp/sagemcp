# GitLab Connector

The GitLab connector provides comprehensive integration with GitLab's REST API v4, enabling Claude Desktop to interact with projects, merge requests, issues, pipelines, branches, commits, and more through OAuth 2.0 authentication. Supports both gitlab.com and self-hosted GitLab instances.

## Features

- **22 comprehensive tools** covering projects, merge requests, issues, pipelines, branches, commits, groups, milestones, labels, and repository operations
- **Full OAuth 2.0 authentication** with configurable scopes
- **Self-hosted GitLab support** via configurable base URL
- **Dynamic resource discovery** of projects and namespaces

## OAuth Setup

### Prerequisites

- A GitLab account (gitlab.com or self-hosted instance)
- Access to create OAuth applications

### Step-by-Step Configuration

1. **Create GitLab OAuth Application**
   - Go to GitLab Settings > Applications (User settings or Admin area)
   - Click "New application"
   - Fill in the details:
     - **Name**: `SageMCP` (or your preferred name)
     - **Redirect URI**: `http://localhost:8000/api/v1/oauth/callback/gitlab`
     - **Confidential**: Yes
     - **Scopes**: Select `api`, `read_user`, `read_repository`
   - Click "Save application"

2. **Get Credentials**
   - Note the **Application ID** (Client ID)
   - Note the **Secret** (Client Secret)
   - Save both credentials securely

3. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     GITLAB_CLIENT_ID=your_application_id_here
     GITLAB_CLIENT_SECRET=your_secret_here
     ```
   - For self-hosted GitLab, also configure the connector with:
     ```json
     {
       "gitlab_url": "https://your-gitlab-instance.com"
     }
     ```

4. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add GitLab connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The GitLab connector requires these scopes:
- `api` - Full API access (read/write)
- `read_user` - Read user information
- `read_repository` - Read repository content

## Available Tools

### Project Management

#### `gitlab_list_projects`
List projects accessible to the authenticated user.

**Parameters:**
- `membership` (optional): Limit to projects the user is a member of (default: `true`)
- `per_page` (optional): Number of results per page (1-100, default: 20)
- `page` (optional): Page number (default: 1)
- `search` (optional): Search projects by name
- `order_by` (optional): Order by field - `id`, `name`, `path`, `created_at`, `updated_at`, `last_activity_at` (default: `last_activity_at`)
- `sort` (optional): Sort direction - `asc`, `desc` (default: `desc`)

#### `gitlab_get_project`
Get detailed information about a project.

**Parameters:**
- `project_id` (required): Project ID (numeric) or URL-encoded path (e.g. `group/project`)

### Merge Requests

#### `gitlab_list_merge_requests`
List merge requests for a project.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `state` (optional): Merge request state filter - `opened`, `closed`, `merged`, `all` (default: `opened`)
- `per_page` (optional): Number of results per page (1-100, default: 20)

#### `gitlab_get_merge_request`
Get details of a specific merge request.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `merge_request_iid` (required): Merge request IID (project-scoped)

#### `gitlab_create_merge_request`
Create a new merge request.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `source_branch` (required): Source branch name
- `target_branch` (required): Target branch name
- `title` (required): Merge request title
- `description` (optional): Merge request description

#### `gitlab_list_mr_discussions`
List discussions (comment threads) on a merge request.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `merge_request_iid` (required): Merge request IID (project-scoped)

#### `gitlab_add_mr_note`
Add a note (comment) to a merge request.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `merge_request_iid` (required): Merge request IID (project-scoped)
- `body` (required): Note body (Markdown supported)

### Issues

#### `gitlab_list_issues`
List issues for a project.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `state` (optional): Issue state filter - `opened`, `closed`, `all` (default: `opened`)
- `labels` (optional): Comma-separated list of label names
- `per_page` (optional): Number of results per page (1-100, default: 20)

#### `gitlab_get_issue`
Get details of a specific issue.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `issue_iid` (required): Issue IID (project-scoped)

#### `gitlab_create_issue`
Create a new issue in a project.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `title` (required): Issue title
- `description` (optional): Issue description (Markdown supported)
- `labels` (optional): Comma-separated list of label names
- `assignee_ids` (optional): Array of user IDs to assign
- `milestone_id` (optional): Milestone ID to associate

#### `gitlab_update_issue`
Update an existing issue.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `issue_iid` (required): Issue IID (project-scoped)
- `title` (optional): New issue title
- `description` (optional): New issue description
- `state_event` (optional): State transition event - `close`, `reopen`
- `labels` (optional): Comma-separated list of label names (replaces existing)
- `assignee_ids` (optional): Array of user IDs to assign (replaces existing)
- `milestone_id` (optional): Milestone ID (0 to remove)

### CI/CD Pipelines

#### `gitlab_list_pipelines`
List pipelines for a project.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `status` (optional): Pipeline status filter - `created`, `waiting_for_resource`, `preparing`, `pending`, `running`, `success`, `failed`, `canceled`, `skipped`, `manual`, `scheduled`
- `ref` (optional): Branch or tag name filter
- `per_page` (optional): Number of results per page (1-100, default: 20)

#### `gitlab_get_pipeline`
Get details of a specific pipeline.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `pipeline_id` (required): Pipeline ID

#### `gitlab_retry_pipeline`
Retry all failed jobs in a pipeline.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `pipeline_id` (required): Pipeline ID to retry

### Branches & Commits

#### `gitlab_list_branches`
List repository branches.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `search` (optional): Search branches by name
- `per_page` (optional): Number of results per page (1-100, default: 20)

#### `gitlab_list_commits`
List repository commits.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `ref_name` (optional): Branch or tag name
- `per_page` (optional): Number of results per page (1-100, default: 20)

### Files & Repository

#### `gitlab_get_file`
Get the content of a file from a repository.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `file_path` (required): Path to the file in the repository
- `ref` (optional): Branch, tag, or commit SHA (default: `main`)

#### `gitlab_get_repository_tree`
Get the repository file/directory tree.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `path` (optional): Path inside the repository (default: root)
- `ref` (optional): Branch, tag, or commit SHA
- `recursive` (optional): Whether to list recursively (default: `false`)
- `per_page` (optional): Number of results per page (1-100, default: 20)

### Groups & Members

#### `gitlab_list_project_members`
List members of a project.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `per_page` (optional): Number of results per page (1-100, default: 20)

#### `gitlab_list_groups`
List groups accessible to the authenticated user.

**Parameters:**
- `per_page` (optional): Number of results per page (1-100, default: 20)
- `search` (optional): Search groups by name

### Milestones & Labels

#### `gitlab_list_milestones`
List milestones for a project.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `state` (optional): Milestone state filter - `active`, `closed`
- `per_page` (optional): Number of results per page (1-100, default: 20)

#### `gitlab_list_labels`
List labels for a project.

**Parameters:**
- `project_id` (required): Project ID or URL-encoded path
- `per_page` (optional): Number of results per page (1-100, default: 20)

## Resource URIs

The connector exposes these resource types:

- **Projects**: `gitlab://project/{namespace/project}`
  - Returns full project information

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired GitLab credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "404 Not Found" on project endpoints
- **Solution**: Ensure the project ID or path is correct. For paths containing `/`, they must be URL-encoded (e.g., `group%2Fproject`)

**Issue**: "403 Forbidden"
- **Solution**: Ensure your OAuth token has the required scopes (`api`, `read_user`, `read_repository`) and that you have permission to access the resource

**Issue**: Self-hosted GitLab not connecting
- **Solution**: Verify the `gitlab_url` in the connector configuration matches your instance URL (e.g., `https://gitlab.example.com`). Do not include the `/api/v4` suffix.

**Issue**: "Rate limit exceeded"
- **Solution**: GitLab rate limits vary by instance. For gitlab.com, authenticated requests get 2,000 requests per minute. Wait or optimize your queries.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making GitLab API request to /projects
DEBUG: GitLab API returned 200
```

## API Reference

- **GitLab REST API Documentation**: https://docs.gitlab.com/ee/api/rest/
- **OAuth 2.0 Provider**: https://docs.gitlab.com/ee/integration/oauth_provider.html
- **Rate Limiting**: https://docs.gitlab.com/ee/security/rate_limits.html

## Source Code

Implementation: `src/sage_mcp/connectors/gitlab.py`
