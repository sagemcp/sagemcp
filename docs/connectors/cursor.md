# Cursor Connector

The Cursor connector provides comprehensive integration with the Cursor Business API, enabling Claude Desktop to manage team analytics, members, spending, audit logs, and governance settings. It authenticates via HTTP Basic Auth with the API key as the username and an empty password (colon-terminated, base64-encoded).

## Features

- **18 comprehensive tools** covering team analytics, member management, spending controls, audit logs, and governance
- **Basic Auth authentication** with Cursor Business API keys
- **Rich analytics** including agent edits, tab usage, DAU, model usage, file extensions, MCP adoption, and leaderboards
- **Cross-tool comparison** via normalized CodingToolMetrics schema

## Auth Setup

### Prerequisites

- A Cursor Business or Enterprise plan
- Team admin access to generate an API key

### Step-by-Step Configuration

1. **Generate a Cursor API Key**
   - Log in to the Cursor dashboard at https://cursor.com
   - Navigate to Team Settings -> API
   - Generate a new API key
   - Copy the generated key
   - Save the key securely

2. **Configure SageMCP**
   - Open the SageMCP web interface
   - Create or select a tenant
   - Add a Cursor connector
   - Paste the API key into the API key configuration field

3. **Verify the Connection**
   - Use `cursor_list_members` to verify credentials are working
   - The tool should return a list of team members

### Authentication Details

- **Method**: HTTP Basic Auth
- **Username**: The API key
- **Password**: Empty (the key is followed by a colon, then base64-encoded)
- **Header**: `Authorization: Basic <base64(api_key:)>`
- **API Base**: `https://api2.cursor.sh`

## Available Tools

### Analytics

#### `cursor_get_agent_edits`
Get team agent edit analytics for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format (e.g. `2024-01-01`)
- `end_date` (required): End date in ISO 8601 format (e.g. `2024-01-31`)

#### `cursor_get_tab_usage`
Get team tab/autocomplete usage analytics for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

#### `cursor_get_daily_active_users`
Get daily active user counts for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

#### `cursor_get_model_usage`
Get model usage breakdown for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

#### `cursor_get_top_file_extensions`
Get top file extensions used by the team for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

#### `cursor_get_mcp_adoption`
Get MCP (Model Context Protocol) adoption analytics for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

#### `cursor_get_commands_adoption`
Get commands adoption analytics for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

#### `cursor_get_leaderboard`
Get team usage leaderboard for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

#### `cursor_get_daily_usage_data`
Get detailed daily usage data for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

#### `cursor_get_usage_events`
Get filtered usage events for specific users and event types.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format
- `user_ids` (optional): List of user IDs to filter events for (array of strings)
- `event_types` (optional): List of event types to filter, e.g. `agent_edit`, `tab_accept` (array of strings)

#### `cursor_get_client_versions`
Get client version distribution for the team over a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

### Admin & Billing

#### `cursor_list_members`
List all members of the Cursor team.

**Parameters:** None

#### `cursor_remove_member`
Remove a member from the Cursor team by user ID.

**Parameters:**
- `user_id` (required): The user ID of the member to remove

#### `cursor_get_spending`
Get team spending breakdown for a date range.

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

#### `cursor_set_user_spend_limit`
Set a spending limit in USD for a specific team member.

**Parameters:**
- `user_id` (required): The user ID to set the spending limit for
- `limit_usd` (required): The spending limit in USD (number)

### Governance

#### `cursor_list_audit_events`
List audit log events with optional pagination.

**Parameters:**
- `start_date` (optional): Start date in ISO 8601 format
- `end_date` (optional): End date in ISO 8601 format
- `per_page` (optional): Number of results per page (default determined by API)
- `cursor` (optional): Pagination cursor from a previous response

#### `cursor_get_repo_blocklists`
Get the list of blocked repositories for the team.

**Parameters:** None

### Normalized Metrics

#### `cursor_get_normalized_metrics`
Get normalized CodingToolMetrics for cross-tool comparison (DAU, spending, members).

**Parameters:**
- `start_date` (required): Start date in ISO 8601 format
- `end_date` (required): End date in ISO 8601 format

## Usage Examples

### Example 1: Review Team Leaderboard

```typescript
"Show me the team usage leaderboard for January 2024"

// This will call cursor_get_leaderboard with:
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31"
}
```

### Example 2: Set a Spending Limit

```typescript
"Set a $50 spending limit for user abc123"

// This will call cursor_set_user_spend_limit with:
{
  "user_id": "abc123",
  "limit_usd": 50.0
}
```

### Example 3: Check MCP Adoption

```typescript
"How is MCP adoption trending on our team this quarter?"

// This will call cursor_get_mcp_adoption with:
{
  "start_date": "2024-04-01",
  "end_date": "2024-06-30"
}
```

## Troubleshooting

### Common Issues

**Issue**: "Unauthorized" or 401 errors
- **Solution**: Verify the API key is correct and has not been revoked. Ensure the key is being sent as Basic Auth (the connector handles this automatically). Check that you have a Cursor Business or Enterprise plan -- the API is not available on individual plans.

**Issue**: "Forbidden" or 403 errors on analytics endpoints
- **Solution**: Ensure the API key was generated by a team admin. Non-admin API keys may not have access to team-level analytics endpoints.

**Issue**: Empty analytics data
- **Solution**: Analytics data may have a processing delay. Ensure your date range covers completed days. Verify that your team has active Cursor usage during the requested period.

**Issue**: "Connection refused" or timeout errors
- **Solution**: The Cursor API is hosted at `api2.cursor.sh`. Verify that your network allows outbound HTTPS connections to this domain. The connector includes automatic retry with exponential backoff for transient failures.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Cursor API request to /analytics/team/agent-edits
DEBUG: Cursor API returned 200
```

## API Reference

- **Cursor Business API Documentation**: https://docs.cursor.com/account/teams/api
- **Cursor Team Settings**: https://cursor.com/settings
- **Cursor Business Plan**: https://cursor.com/business

## Source Code

Implementation: `src/sage_mcp/connectors/cursor.py`
