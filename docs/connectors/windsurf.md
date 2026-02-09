# Windsurf Connector

The Windsurf connector provides integration with the Codeium/Windsurf server API, enabling Claude Desktop to manage team analytics, usage configuration, credit balance, and Cascade (AI agent) usage. It uses a non-standard authentication model where the API key (`service_key`) is injected directly into the JSON request body rather than passed via HTTP headers. All endpoints are POST-only.

## Features

- **11 tools** including 6 confirmed API endpoints, 4 stub tools with workaround guidance, and 1 normalized metrics tool
- **Service key authentication** injected into JSON request body (no HTTP auth headers)
- **Cascade analytics** for tracking AI agent usage alongside code completion metrics
- **Cross-tool comparison** via normalized CodingToolMetrics schema

> **Note**: Windsurf/Codeium has limited public API documentation. Four tools are stubs that return structured error responses with workaround suggestions for accessing the data through alternative means (e.g., the Codeium dashboard).

## Auth Setup

### Prerequisites

- A Windsurf/Codeium team or enterprise account
- A service API key for the team

### Step-by-Step Configuration

1. **Obtain a Service API Key**
   - Log in to the Codeium dashboard at https://codeium.com/team
   - Navigate to Team Settings -> API
   - Generate or copy your team service key
   - Save the key securely

2. **Configure SageMCP**
   - Open the SageMCP web interface
   - Create or select a tenant
   - Add a Windsurf connector
   - Paste the service API key into the API key configuration field

3. **Verify the Connection**
   - Use `windsurf_get_usage_config` to verify credentials are working
   - The tool should return your current team usage configuration

### Authentication Details

- **Method**: Service key injected into JSON request body as `service_key` field
- **All endpoints are POST-only** (no GET requests)
- **Content-Type**: `application/json` (automatically set)
- **API Base**: `https://server.codeium.com/api/v1`

## Available Tools

### Confirmed API Endpoints

#### `windsurf_get_analytics`
Get team-wide analytics for Windsurf/Codeium usage over a date range.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format
- `metrics` (required): List of metric names to retrieve (array of strings, e.g. `["completions", "active_users", "acceptance_rate"]`)

#### `windsurf_get_user_analytics`
Get per-user analytics for a specific team member over a date range.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format
- `user_id` (required): The Codeium user ID to get analytics for

#### `windsurf_get_cascade_analytics`
Get Cascade (AI agent) usage analytics over a date range.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

#### `windsurf_get_usage_config`
Get the current Windsurf/Codeium usage configuration for the team.

**Parameters:** None

#### `windsurf_set_usage_config`
Update Windsurf/Codeium usage configuration settings for the team.

**Parameters:**
- `config` (required): Configuration settings to update (object with key-value pairs)

#### `windsurf_get_credit_balance`
Get the team's current Windsurf/Codeium credit balance.

**Parameters:** None

### Stub Tools

These tools are included for API completeness but return structured error responses because the underlying Codeium APIs are not publicly documented. Each stub response includes a `workaround` field with instructions for accessing the data through alternative means.

#### `windsurf_list_members`
List team members (stub -- API not publicly available).

**Parameters:** None

**Returns:** Structured error with workaround: Export member list from the Windsurf team settings dashboard at https://codeium.com/team.

#### `windsurf_list_audit_events`
List audit events (stub -- API not publicly available).

**Parameters:** None

**Returns:** Structured error with workaround: Contact Codeium enterprise support for audit log exports.

#### `windsurf_get_spending_breakdown`
Get detailed spending breakdown (stub -- API not publicly available).

**Parameters:** None

**Returns:** Structured error with workaround: Use `windsurf_get_credit_balance` for aggregate credit data, or check billing in the Codeium dashboard.

#### `windsurf_get_seat_info`
Get team seat allocation info (stub -- API not publicly available).

**Parameters:** None

**Returns:** Structured error with workaround: Check team seat information in the Windsurf dashboard at https://codeium.com/team/settings.

### Normalized Metrics

#### `windsurf_get_normalized_metrics`
Get normalized CodingToolMetrics for cross-tool comparison. Aggregates analytics and credit data into a standard schema. Many fields will be unavailable due to Windsurf API limitations.

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

## Usage Examples

### Example 1: Get Team Analytics

```typescript
"Show me Windsurf completions and active user metrics for January 2024"

// This will call windsurf_get_analytics with:
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "metrics": ["completions", "active_users", "acceptance_rate"]
}
```

### Example 2: Check Credit Balance

```typescript
"What is our current Windsurf credit balance?"

// This will call windsurf_get_credit_balance with:
{}
// (service_key is injected automatically into the request body)
```

### Example 3: Track Cascade Agent Usage

```typescript
"How much is our team using Windsurf's Cascade agent this quarter?"

// This will call windsurf_get_cascade_analytics with:
{
  "start_date": "2024-04-01",
  "end_date": "2024-06-30"
}
```

## Troubleshooting

### Common Issues

**Issue**: "API key not configured" or authentication errors
- **Solution**: Verify the service key is correctly entered in the connector configuration. Windsurf uses a non-standard auth model -- the key is injected into the JSON body, not HTTP headers. Ensure the key has not been revoked in the Codeium dashboard.

**Issue**: "ConnectorAuthError" on every request
- **Solution**: The service key may be expired or invalid. Generate a new service key from https://codeium.com/team settings and update the connector configuration.

**Issue**: Stub tools returning "API not available"
- **Solution**: This is expected behavior. Four tools (list_members, list_audit_events, get_spending_breakdown, get_seat_info) are stubs because Codeium has not publicly documented these endpoints. Check the `workaround` field in the response for alternative ways to access the data.

**Issue**: Timeout or connection errors
- **Solution**: The Windsurf API is hosted at `server.codeium.com`. Verify that your network allows outbound HTTPS connections to this domain. The connector includes automatic retry with exponential backoff for transient failures (429 rate limits, 5xx server errors, connection drops).

**Issue**: Empty or unexpected data in analytics responses
- **Solution**: Ensure the `metrics` array in `windsurf_get_analytics` contains valid metric names. Available metrics include `completions`, `active_users`, and `acceptance_rate`. Analytics data may have a processing delay.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Windsurf API request to /api/v1/Analytics
DEBUG: Windsurf API returned 200
```

## API Reference

- **Codeium API** (limited public docs): https://codeium.com/api
- **Codeium Team Dashboard**: https://codeium.com/team
- **Codeium Enterprise Support**: https://codeium.com/enterprise

## Source Code

Implementation: `src/sage_mcp/connectors/windsurf.py`
