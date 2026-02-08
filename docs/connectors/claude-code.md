# Claude Code Connector

The Claude Code connector provides comprehensive integration with the Anthropic Admin API, enabling Claude Desktop to manage organization usage, costs, users, workspaces, and API keys. It authenticates using an organization-level Admin API key (`sk-ant-admin...`) passed via the `x-api-key` header, with the `anthropic-version` header included on every request.

## Features

- **19 comprehensive tools** covering usage analytics, cost reporting, user management, and workspace administration
- **API key authentication** with Anthropic Admin API keys (no OAuth flow required)
- **Organization-level visibility** into usage reports, cost breakdowns, and code analytics
- **Cross-tool comparison** via normalized CodingToolMetrics schema

## Auth Setup

### Prerequisites

- An Anthropic organization account with admin access
- An Admin API key (starts with `sk-ant-admin...`)

### Step-by-Step Configuration

1. **Generate an Admin API Key**
   - Log in to the Anthropic Console at https://console.anthropic.com
   - Navigate to Organization Settings -> API Keys
   - Click "Create Key" and select the Admin key type
   - Copy the generated key (it starts with `sk-ant-admin...`)
   - Save the key securely -- it will not be shown again

2. **Configure SageMCP**
   - Open the SageMCP web interface
   - Create or select a tenant
   - Add a Claude Code connector
   - Paste the Admin API key into the API key configuration field

3. **Verify the Connection**
   - Use `claude_code_get_org_info` to verify credentials are working
   - The tool should return your organization name and details

### Authentication Details

- **Header**: `x-api-key` (no prefix, raw key value)
- **Required Header**: `anthropic-version: 2023-06-01` (automatically included)
- **API Base**: `https://api.anthropic.com`

## Available Tools

### Org Stats & Analytics

#### `claude_code_get_usage`
Get message usage data for the Anthropic organization.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of results per page (1-100, default: 30)

#### `claude_code_get_cost_breakdown`
Get cost breakdown data for the Anthropic organization.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

#### `claude_code_get_code_analytics`
Get Claude Code specific analytics for the organization.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

#### `claude_code_get_org_info`
Get information about the current Anthropic organization.

**Parameters:** None

### Admin & Access Management

#### `claude_code_list_users`
List users in the Anthropic organization.

**Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of results per page (1-100, default: 30)

#### `claude_code_update_user_role`
Update a user's role in the organization.

**Parameters:**
- `user_id` (required): The user ID to update
- `role` (required): New role for the user (e.g. `admin`, `member`)

#### `claude_code_remove_user`
Remove a user from the organization.

**Parameters:**
- `user_id` (required): The user ID to remove

#### `claude_code_list_invites`
List pending invitations for the organization.

**Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of results per page (1-100, default: 30)

#### `claude_code_create_invite`
Invite a user to the organization.

**Parameters:**
- `email` (required): Email address of the user to invite
- `role` (required): Role to assign (e.g. `admin`, `member`)

#### `claude_code_delete_invite`
Delete a pending invitation.

**Parameters:**
- `invite_id` (required): The invitation ID to delete

#### `claude_code_list_workspaces`
List workspaces in the organization.

**Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of results per page (1-100, default: 30)

#### `claude_code_get_workspace`
Get details of a specific workspace.

**Parameters:**
- `workspace_id` (required): The workspace ID to retrieve

#### `claude_code_list_api_keys`
List API keys for the organization.

**Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of results per page (1-100, default: 30)

#### `claude_code_update_api_key`
Update an API key's name or status.

**Parameters:**
- `api_key_id` (required): The API key ID to update
- `name` (optional): New display name for the API key
- `status` (optional): New status (e.g. `active`, `disabled`)

### Workspace Management

#### `claude_code_create_workspace`
Create a new workspace in the organization.

**Parameters:**
- `name` (required): Name of the workspace
- `description` (optional): Optional description of the workspace

#### `claude_code_list_workspace_members`
List members of a specific workspace.

**Parameters:**
- `workspace_id` (required): The workspace ID
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of results per page (1-100, default: 30)

#### `claude_code_add_workspace_member`
Add a member to a workspace.

**Parameters:**
- `workspace_id` (required): The workspace ID
- `user_id` (required): The user ID to add
- `role` (optional): Role within the workspace (e.g. `admin`, `member`)

### Normalized Metrics

#### `claude_code_get_normalized_metrics`
Get normalized CodingToolMetrics by aggregating usage, cost, and code analytics data for cross-tool comparison.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

## Usage Examples

### Example 1: Get Organization Cost Breakdown

```typescript
"Show me the cost breakdown for my Anthropic organization in January 2024"

// This will call claude_code_get_cost_breakdown with:
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

### Example 2: Invite a New Team Member

```typescript
"Invite jane@company.com to our Anthropic organization as a member"

// This will call claude_code_create_invite with:
{
  "email": "jane@company.com",
  "role": "member"
}
```

### Example 3: Review API Key Inventory

```typescript
"List all API keys in our organization"

// This will call claude_code_list_api_keys with:
{
  "page": 1,
  "per_page": 100
}
```

## Troubleshooting

### Common Issues

**Issue**: "Unauthorized" or 401 errors
- **Solution**: Verify you are using an Admin API key (starts with `sk-ant-admin...`), not a regular API key (`sk-ant-api...`). Admin keys are generated from Organization Settings, not personal API settings.

**Issue**: "Forbidden" or 403 errors
- **Solution**: Ensure the Admin API key has not been revoked and that the key's organization matches your target organization. Admin keys are scoped to a single organization.

**Issue**: "anthropic-version header is required"
- **Solution**: This should not occur when using the connector (the header is injected automatically). If you see this error, verify the connector is up to date.

**Issue**: Empty or missing data in usage reports
- **Solution**: Usage data may have a reporting delay of up to 24 hours. Ensure your date range covers completed days. Also verify the organization has active API usage during the requested period.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Claude Code API request to /v1/organizations/usage_report/messages
DEBUG: Anthropic API returned 200
```

## API Reference

- **Anthropic Admin API Documentation**: https://docs.anthropic.com/en/docs/administration
- **API Key Management**: https://console.anthropic.com/settings/admin-keys
- **Organization Management**: https://docs.anthropic.com/en/api/admin-api

## Source Code

Implementation: `src/sage_mcp/connectors/claude_code.py`
