# Bitbucket Connector

The Bitbucket connector provides comprehensive integration with Bitbucket Cloud's REST API v2.0, enabling Claude Desktop to interact with repositories, pull requests, issues, pipelines, branches, commits, and workspaces through OAuth 2.0 authentication.

## Features

- **19 comprehensive tools** covering repositories, pull requests, issues, pipelines, branches, commits, workspaces, and file content
- **Full OAuth 2.0 authentication** via Bitbucket OAuth consumers
- **Workspace-centric model** reflecting Bitbucket's workspace > project > repository hierarchy
- **Dynamic resource discovery** of repositories and workspaces

## OAuth Setup

### Prerequisites

- A Bitbucket Cloud account
- Access to create OAuth consumers in a workspace

### Step-by-Step Configuration

1. **Create Bitbucket OAuth Consumer**
   - Go to Bitbucket workspace Settings > OAuth consumers
   - Click "Add consumer"
   - Fill in the details:
     - **Name**: `SageMCP` (or your preferred name)
     - **Callback URL**: `http://localhost:8000/api/v1/oauth/callback/bitbucket`
     - **Permissions**: Select the required permissions:
       - Account: Read
       - Repositories: Read, Write
       - Pull requests: Read, Write
       - Issues: Read, Write
       - Pipelines: Read, Write
   - Click "Save"

2. **Get Credentials**
   - Note the **Key** (Client ID)
   - Note the **Secret** (Client Secret)
   - Save both credentials securely

3. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     BITBUCKET_CLIENT_ID=your_key_here
     BITBUCKET_CLIENT_SECRET=your_secret_here
     ```

4. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add Bitbucket connector
   - Complete OAuth authorization flow

### Required OAuth Permissions

The Bitbucket connector requires these permissions:
- **Account**: Read
- **Repositories**: Read, Write
- **Pull requests**: Read, Write
- **Issues**: Read, Write (for repositories with issue tracker enabled)
- **Pipelines**: Read, Write

## Available Tools

### Repository Management

#### `bitbucket_list_repositories`
List repositories in a Bitbucket workspace.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `pagelen` (optional): Number of results per page (1-100, default: 25)
- `page` (optional): Page number (default: 1)
- `q` (optional): Query filter (e.g. `name ~ "myrepo"`)
- `sort` (optional): Sort field (e.g. `-updated_on` for newest first)

#### `bitbucket_get_repository`
Get detailed information about a Bitbucket repository.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug

### Pull Requests

#### `bitbucket_list_pull_requests`
List pull requests for a Bitbucket repository.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `state` (optional): Pull request state filter - `OPEN`, `MERGED`, `DECLINED`, `SUPERSEDED` (default: `OPEN`)
- `pagelen` (optional): Number of results per page (1-100, default: 25)

#### `bitbucket_get_pull_request`
Get details of a specific pull request.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `pull_request_id` (required): Pull request ID

#### `bitbucket_create_pull_request`
Create a new pull request in a Bitbucket repository.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `title` (required): Pull request title
- `source_branch` (required): Source branch name
- `destination_branch` (optional): Destination branch name (defaults to repo main branch)
- `description` (optional): Pull request description
- `close_source_branch` (optional): Close source branch after merge (default: `false`)

#### `bitbucket_list_pr_comments`
List comments on a pull request.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `pull_request_id` (required): Pull request ID

#### `bitbucket_add_pr_comment`
Add a comment to a pull request.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `pull_request_id` (required): Pull request ID
- `body` (required): Comment body (Markdown supported)

#### `bitbucket_get_diff`
Get the diff of a pull request.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `pull_request_id` (required): Pull request ID

### Issues

#### `bitbucket_list_issues`
List issues for a Bitbucket repository (requires issue tracker to be enabled).

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `q` (optional): Query filter (e.g. `state = "open"`)
- `pagelen` (optional): Number of results per page (1-100, default: 25)

#### `bitbucket_get_issue`
Get details of a specific issue.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `issue_id` (required): Issue ID

#### `bitbucket_create_issue`
Create a new issue in a Bitbucket repository (requires issue tracker to be enabled).

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `title` (required): Issue title
- `content` (optional): Issue body/description (Markdown supported)
- `kind` (optional): Issue kind - `bug`, `enhancement`, `proposal`, `task` (default: `bug`)
- `priority` (optional): Issue priority - `trivial`, `minor`, `major`, `critical`, `blocker` (default: `major`)

### Pipelines

#### `bitbucket_list_pipelines`
List pipelines for a Bitbucket repository.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `pagelen` (optional): Number of results per page (1-100, default: 25)
- `sort` (optional): Sort field (e.g. `-created_on`)

#### `bitbucket_get_pipeline`
Get details of a specific pipeline run.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `pipeline_uuid` (required): Pipeline UUID (with or without curly braces)

#### `bitbucket_trigger_pipeline`
Trigger a new pipeline run for a branch or commit.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `branch` (required): Branch name to run the pipeline on
- `commit` (optional): Specific commit hash (defaults to branch HEAD)

### Branches & Commits

#### `bitbucket_list_branches`
List branches for a Bitbucket repository.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `pagelen` (optional): Number of results per page (1-100, default: 25)
- `q` (optional): Query filter (e.g. `name ~ "feature"`)

#### `bitbucket_list_commits`
List commits for a Bitbucket repository.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `pagelen` (optional): Number of results per page (1-100, default: 25)

### Files & Content

#### `bitbucket_get_file`
Get the content of a file from a Bitbucket repository.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `repo_slug` (required): Repository slug
- `commit` (required): Commit hash or branch name (e.g. `main`, `HEAD`, or a SHA)
- `path` (required): File path within the repository

### Workspaces

#### `bitbucket_list_workspaces`
List workspaces the authenticated user belongs to.

**Parameters:**
- `pagelen` (optional): Number of results per page (1-100, default: 25)

#### `bitbucket_list_workspace_members`
List members of a Bitbucket workspace.

**Parameters:**
- `workspace` (required): Workspace slug or UUID
- `pagelen` (optional): Number of results per page (1-100, default: 25)

## Resource URIs

The connector exposes these resource types:

- **Repositories**: `bitbucket://repo/{workspace}/{repo_slug}`
  - Returns full repository information

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Bitbucket credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "404 Not Found" on issue endpoints
- **Solution**: Bitbucket's issue tracker must be explicitly enabled on a repository. Go to Repository Settings > Features > Issue tracker and enable it.

**Issue**: "403 Forbidden"
- **Solution**: Ensure your OAuth consumer has the required permissions and that you have access to the workspace/repository

**Issue**: Pipeline trigger fails
- **Solution**: Ensure Pipelines is enabled for the repository and that your `bitbucket-pipelines.yml` file exists in the repository

**Issue**: "Rate limit exceeded"
- **Solution**: Bitbucket Cloud has API rate limits of 1,000 requests per hour per user. Wait or optimize your queries.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Bitbucket API request to /repositories/workspace/repo
DEBUG: Bitbucket API returned 200
```

## API Reference

- **Bitbucket Cloud REST API Documentation**: https://developer.atlassian.com/cloud/bitbucket/rest/
- **OAuth Consumers**: https://support.atlassian.com/bitbucket-cloud/docs/use-oauth-on-bitbucket-cloud/
- **Rate Limiting**: https://support.atlassian.com/bitbucket-cloud/docs/api-request-limits/

## Source Code

Implementation: `src/sage_mcp/connectors/bitbucket.py`
