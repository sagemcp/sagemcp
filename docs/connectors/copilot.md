# GitHub Copilot Connector

The GitHub Copilot connector provides comprehensive integration with GitHub's Copilot API, enabling Claude Desktop to manage Copilot seats, track usage analytics, enforce organizational policies, and generate normalized cross-tool metrics. It reuses GitHub OAuth credentials and requires the `manage_billing:copilot` and `read:org` scopes.

## Features

- **19 comprehensive tools** covering usage analytics, seat management, policy governance, and normalized metrics
- **Reuses GitHub OAuth 2.0** authentication -- no separate credentials needed
- **Derived analytics** including acceptance rates, language/editor breakdowns, and inactive seat detection
- **Cross-tool comparison** via normalized CodingToolMetrics schema

## OAuth Setup

### Prerequisites

- A GitHub account with organization owner or billing manager access
- An existing GitHub OAuth app configured in SageMCP (see the GitHub connector setup)
- The Copilot Business or Enterprise plan enabled for your organization

### Step-by-Step Configuration

1. **Ensure GitHub OAuth App Has Required Scopes**
   - The GitHub Copilot connector reuses your existing GitHub OAuth credentials
   - Your OAuth app must request the additional scopes listed below
   - If you already have a GitHub connector configured, re-authorize to pick up the new scopes

2. **Re-authorize if Needed**
   - Open the SageMCP web interface
   - Navigate to your tenant's connector list
   - Add a GitHub Copilot connector
   - Complete the OAuth authorization flow (this will request the Copilot-specific scopes)

3. **Configure SageMCP**
   - The Copilot connector uses the same `.env` variables as GitHub:
     ```env
     GITHUB_CLIENT_ID=your_client_id_here
     GITHUB_CLIENT_SECRET=your_client_secret_here
     ```

### Required OAuth Scopes

The Copilot connector requires these scopes in addition to standard GitHub scopes:
- `manage_billing:copilot` - Access Copilot billing and seat management
- `read:org` - Read organization membership and settings

## Available Tools

### Org Stats & Analytics

#### `copilot_get_org_usage`
Get daily Copilot usage metrics for an organization (1-day granularity).

**Parameters:**
- `org` (required): GitHub organization login
- `since` (optional): Start date (ISO 8601, e.g. `2024-01-01`)
- `until` (optional): End date (ISO 8601, e.g. `2024-01-31`)
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of results per page (1-100, default: 28)

#### `copilot_get_usage_trends`
Get 28-day rolling usage trends for an organization.

**Parameters:**
- `org` (required): GitHub organization login
- `since` (optional): Start date (ISO 8601)
- `until` (optional): End date (ISO 8601)

#### `copilot_get_user_usage`
Get per-user daily Copilot usage metrics for an organization.

**Parameters:**
- `org` (required): GitHub organization login
- `since` (optional): Start date (ISO 8601)
- `until` (optional): End date (ISO 8601)
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of results per page (1-100, default: 28)

#### `copilot_get_acceptance_rate`
Compute the suggestion acceptance rate from daily org usage data.

**Parameters:**
- `org` (required): GitHub organization login
- `since` (optional): Start date (ISO 8601)
- `until` (optional): End date (ISO 8601)

#### `copilot_get_usage_by_language`
Break down Copilot usage by programming language.

**Parameters:**
- `org` (required): GitHub organization login
- `since` (optional): Start date (ISO 8601)
- `until` (optional): End date (ISO 8601)

#### `copilot_get_usage_by_editor`
Break down Copilot usage by editor/IDE.

**Parameters:**
- `org` (required): GitHub organization login
- `since` (optional): Start date (ISO 8601)
- `until` (optional): End date (ISO 8601)

#### `copilot_get_chat_usage`
Get Copilot Chat usage metrics for an organization.

**Parameters:**
- `org` (required): GitHub organization login
- `since` (optional): Start date (ISO 8601)
- `until` (optional): End date (ISO 8601)

#### `copilot_get_pr_summary_usage`
Get Copilot pull request summary usage metrics.

**Parameters:**
- `org` (required): GitHub organization login
- `since` (optional): Start date (ISO 8601)
- `until` (optional): End date (ISO 8601)

#### `copilot_get_legacy_metrics`
Get legacy Copilot metrics (deprecated endpoint, use org usage for new integrations).

**Parameters:**
- `org` (required): GitHub organization login

### Seat Management

#### `copilot_get_billing_info`
Get Copilot billing information and seat summary for an organization.

**Parameters:**
- `org` (required): GitHub organization login

#### `copilot_list_seat_assignments`
List all Copilot seat assignments for an organization.

**Parameters:**
- `org` (required): GitHub organization login
- `page` (optional): Page number for pagination (default: 1)
- `per_page` (optional): Number of results per page (1-100, default: 50)

#### `copilot_get_seat_details`
Get Copilot seat details for a specific organization member.

**Parameters:**
- `org` (required): GitHub organization login
- `username` (required): GitHub username

#### `copilot_add_seats`
Add Copilot seats for specified users in an organization.

**Parameters:**
- `org` (required): GitHub organization login
- `selected_usernames` (required): List of GitHub usernames to assign Copilot seats (array of strings)

#### `copilot_remove_seats`
Remove Copilot seats for specified users in an organization.

**Parameters:**
- `org` (required): GitHub organization login
- `selected_usernames` (required): List of GitHub usernames to remove Copilot seats from (array of strings)

#### `copilot_list_inactive_seats`
List Copilot seats inactive for a given number of days.

**Parameters:**
- `org` (required): GitHub organization login
- `days_inactive` (optional): Number of days of inactivity threshold (default: 30)

### Policy & Governance

#### `copilot_get_org_config`
Get Copilot feature policies and configuration for an organization.

**Parameters:**
- `org` (required): GitHub organization login

#### `copilot_get_content_exclusions`
Get Copilot content exclusion rules for an organization.

**Parameters:**
- `org` (required): GitHub organization login

#### `copilot_list_audit_events`
List Copilot-related audit log events for an organization.

**Parameters:**
- `org` (required): GitHub organization login
- `phrase` (optional): Audit log search phrase (default: `action:copilot`)
- `per_page` (optional): Number of results per page (1-100, default: 30)
- `after` (optional): Cursor for pagination (from previous response)

### Normalized Metrics

#### `copilot_get_normalized_metrics`
Get normalized CodingToolMetrics for cross-tool comparison.

**Parameters:**
- `org` (required): GitHub organization login
- `since` (optional): Start date (ISO 8601)
- `until` (optional): End date (ISO 8601)

## Usage Examples

### Example 1: Check Acceptance Rate

```typescript
"What is my organization's Copilot acceptance rate for January 2024?"

// This will call copilot_get_acceptance_rate with:
{
  "org": "my-org",
  "since": "2024-01-01",
  "until": "2024-01-31"
}
```

### Example 2: Find Inactive Seats

```typescript
"Show me Copilot seats that have been inactive for over 60 days"

// This will call copilot_list_inactive_seats with:
{
  "org": "my-org",
  "days_inactive": 60
}
```

### Example 3: Compare Usage Across Editors

```typescript
"Break down our Copilot usage by editor for the last month"

// This will call copilot_get_usage_by_editor with:
{
  "org": "my-org",
  "since": "2024-06-01",
  "until": "2024-06-30"
}
```

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired GitHub credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface. The Copilot connector shares credentials with the GitHub connector.

**Issue**: "Resource not accessible by integration" or 403 errors
- **Solution**: Ensure your GitHub token has the `manage_billing:copilot` scope. Re-authorize the OAuth flow to pick up the required scope. You must be an organization owner or billing manager.

**Issue**: "Not Found" (404) on usage endpoints
- **Solution**: Verify that your organization has a Copilot Business or Enterprise plan. The metrics API is not available on individual Copilot plans.

**Issue**: Empty usage data returned
- **Solution**: Usage data has a 24-48 hour reporting delay. Ensure your date range covers past completed days, not the current day.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making GitHub API request to /orgs/my-org/copilot/metrics/reports/organization-1-day
DEBUG: GitHub API returned 200
```

## API Reference

- **GitHub Copilot REST API Documentation**: https://docs.github.com/en/rest/copilot
- **Copilot Metrics API**: https://docs.github.com/en/rest/copilot/copilot-metrics
- **Copilot Billing API**: https://docs.github.com/en/rest/copilot/copilot-business
- **OAuth Scopes**: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps

## Source Code

Implementation: `src/sage_mcp/connectors/copilot.py`
