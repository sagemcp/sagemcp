# OpenAI Codex Connector

The OpenAI Codex connector provides comprehensive integration with the OpenAI organization administration API, enabling Claude Desktop to manage usage analytics, costs, users, projects, invites, audit logs, and service accounts. It authenticates via an organization-scoped Admin API key using the `Authorization: Bearer` header.

## Features

- **17 comprehensive tools** covering usage analytics, cost reporting, user management, project administration, and governance
- **Bearer token authentication** with OpenAI Admin API keys
- **Granular time-bucketed analytics** with customizable grouping dimensions (by project, user, API key, or model)
- **Cross-tool comparison** via normalized CodingToolMetrics schema

## Auth Setup

### Prerequisites

- An OpenAI organization account with admin access
- An Admin API key for the organization

### Step-by-Step Configuration

1. **Generate an Admin API Key**
   - Log in to the OpenAI Platform at https://platform.openai.com
   - Navigate to Organization Settings -> Admin Keys
   - Click "Create new admin key"
   - Copy the generated key
   - Save the key securely -- it will not be shown again

2. **Configure SageMCP**
   - Open the SageMCP web interface
   - Create or select a tenant
   - Add an OpenAI Codex connector
   - Paste the Admin API key into the API key configuration field

3. **Verify the Connection**
   - Use `codex_list_users` to verify credentials are working
   - The tool should return a list of organization members

### Authentication Details

- **Header**: `Authorization: Bearer <api_key>`
- **API Base**: `https://api.openai.com`

## Available Tools

### Usage & Cost Analytics

#### `codex_get_completions_usage`
Get completions usage data for the organization, broken down by time buckets and optional grouping dimensions.

**Parameters:**
- `start_time` (required): Start time as a Unix timestamp (seconds since epoch)
- `end_time` (optional): End time as a Unix timestamp (defaults to current time)
- `bucket_width` (optional): Width of each time bucket -- `1m`, `1h`, or `1d`
- `project_ids` (optional): Filter by project IDs (array of strings)
- `user_ids` (optional): Filter by user IDs (array of strings)
- `api_key_ids` (optional): Filter by API key IDs (array of strings)
- `models` (optional): Filter by model names, e.g. `gpt-4o`, `o3-mini` (array of strings)
- `group_by` (optional): Dimensions to group results by (array of: `project_id`, `user_id`, `api_key_id`, `model`)

#### `codex_get_cost_breakdown`
Get cost data for the organization, broken down by time buckets and optional grouping dimensions.

**Parameters:**
- `start_time` (required): Start time as a Unix timestamp (seconds since epoch)
- `end_time` (optional): End time as a Unix timestamp
- `bucket_width` (optional): Width of each time bucket -- `1m`, `1h`, or `1d`
- `project_ids` (optional): Filter by project IDs (array of strings)
- `group_by` (optional): Dimensions to group results by (array of: `project_id`, `line_item`)

#### `codex_get_embeddings_usage`
Get embeddings usage data for the organization, broken down by time buckets and optional grouping dimensions.

**Parameters:**
- `start_time` (required): Start time as a Unix timestamp (seconds since epoch)
- `end_time` (optional): End time as a Unix timestamp
- `bucket_width` (optional): Width of each time bucket -- `1m`, `1h`, or `1d`
- `project_ids` (optional): Filter by project IDs (array of strings)
- `user_ids` (optional): Filter by user IDs (array of strings)
- `api_key_ids` (optional): Filter by API key IDs (array of strings)
- `models` (optional): Filter by model names (array of strings)
- `group_by` (optional): Dimensions to group results by (array of: `project_id`, `user_id`, `api_key_id`, `model`)

#### `codex_get_code_interpreter_usage`
Get Code Interpreter session usage data for the organization.

**Parameters:**
- `start_time` (required): Start time as a Unix timestamp (seconds since epoch)
- `end_time` (optional): End time as a Unix timestamp
- `bucket_width` (optional): Width of each time bucket -- `1m`, `1h`, or `1d`
- `project_ids` (optional): Filter by project IDs (array of strings)
- `group_by` (optional): Dimensions to group results by (array of: `project_id`)

### Admin & Access Management

#### `codex_list_users`
List all users in the organization.

**Parameters:**
- `limit` (optional): Maximum number of users to return (default: 20)
- `after` (optional): Cursor for pagination; pass the `after` value from a previous response

#### `codex_modify_user`
Modify a user's role in the organization.

**Parameters:**
- `user_id` (required): The ID of the user to modify
- `role` (required): The new role for the user -- `owner` or `reader`

#### `codex_delete_user`
Remove a user from the organization.

**Parameters:**
- `user_id` (required): The ID of the user to remove

#### `codex_list_invites`
List pending invitations in the organization.

**Parameters:**
- `limit` (optional): Maximum number of invites to return
- `after` (optional): Cursor for pagination

#### `codex_create_invite`
Invite a new user to the organization by email.

**Parameters:**
- `email` (required): The email address of the person to invite
- `role` (required): The role to assign to the invited user -- `owner` or `reader`

#### `codex_list_projects`
List all projects in the organization.

**Parameters:**
- `limit` (optional): Maximum number of projects to return
- `after` (optional): Cursor for pagination
- `include_archived` (optional): Whether to include archived projects (boolean)

#### `codex_get_project`
Get details of a specific project.

**Parameters:**
- `project_id` (required): The ID of the project to retrieve

#### `codex_create_project`
Create a new project in the organization.

**Parameters:**
- `name` (required): The name of the project to create

#### `codex_list_project_api_keys`
List API keys associated with a project.

**Parameters:**
- `project_id` (required): The ID of the project
- `limit` (optional): Maximum number of API keys to return
- `after` (optional): Cursor for pagination

### Governance

#### `codex_list_audit_events`
List audit log events for the organization, with optional filters.

**Parameters:**
- `effective_at_start` (optional): Return events on or after this Unix timestamp
- `effective_at_end` (optional): Return events before this Unix timestamp
- `project_ids` (optional): Filter by project IDs (array of strings)
- `event_types` (optional): Filter by event types, e.g. `api_key.created` (array of strings)
- `actor_ids` (optional): Filter by actor (user) IDs (array of strings)
- `actor_emails` (optional): Filter by actor email addresses (array of strings)
- `limit` (optional): Maximum number of events to return
- `after` (optional): Cursor for pagination

#### `codex_list_service_accounts`
List service accounts for a project.

**Parameters:**
- `project_id` (required): The ID of the project
- `limit` (optional): Maximum number of service accounts to return
- `after` (optional): Cursor for pagination

### Normalized Metrics

#### `codex_get_normalized_metrics`
Get normalized CodingToolMetrics for cross-tool comparison. Combines completions usage and cost data into a standard schema.

**Parameters:**
- `start_time` (required): Start time as a Unix timestamp (seconds since epoch)
- `end_time` (optional): End time as a Unix timestamp (defaults to current time)

## Usage Examples

### Example 1: Get Daily Cost Breakdown by Project

```typescript
"Show me daily costs grouped by project for the last 7 days"

// This will call codex_get_cost_breakdown with:
{
  "start_time": 1704067200,
  "bucket_width": "1d",
  "group_by": ["project_id"]
}
```

### Example 2: Monitor Model Usage

```typescript
"How much are we using gpt-4o vs o3-mini this month?"

// This will call codex_get_completions_usage with:
{
  "start_time": 1704067200,
  "bucket_width": "1d",
  "models": ["gpt-4o", "o3-mini"],
  "group_by": ["model"]
}
```

### Example 3: Audit Recent API Key Activity

```typescript
"Show me all API key creation events from the past week"

// This will call codex_list_audit_events with:
{
  "effective_at_start": 1703462400,
  "event_types": ["api_key.created"]
}
```

## Troubleshooting

### Common Issues

**Issue**: "Unauthorized" or 401 errors
- **Solution**: Verify you are using an Admin API key, not a standard project API key. Admin keys are created from Organization Settings, not project-level settings.

**Issue**: "Forbidden" or 403 errors on usage endpoints
- **Solution**: Ensure the API key has organization-level admin access. Standard API keys do not have access to the `/v1/organization/` endpoints.

**Issue**: Empty data in usage/cost responses
- **Solution**: Usage and cost data may be delayed by up to a few hours. Ensure your `start_time` covers a period with completed billing cycles. Also check that `bucket_width` is appropriate for your time range (e.g. `1d` for multi-day queries, `1h` for same-day queries).

**Issue**: Pagination cursor not working
- **Solution**: The `after` parameter must be the exact cursor string from a previous response's pagination metadata. Do not construct cursor values manually.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making OpenAI API request to /v1/organization/usage/completions
DEBUG: OpenAI API returned 200
```

## API Reference

- **OpenAI Administration API Documentation**: https://platform.openai.com/docs/api-reference/administration
- **Usage API**: https://platform.openai.com/docs/api-reference/usage
- **Audit Logs API**: https://platform.openai.com/docs/api-reference/audit-logs
- **Organization Management**: https://platform.openai.com/docs/api-reference/organization

## Source Code

Implementation: `src/sage_mcp/connectors/codex.py`
