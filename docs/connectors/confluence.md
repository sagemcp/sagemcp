# Confluence Connector

The Confluence connector provides comprehensive integration with Confluence Cloud's REST API, enabling Claude Desktop to interact with spaces, pages, comments, labels, search, and content management through Atlassian OAuth 2.0 authentication. Uses the v2 REST API for most operations and v1 for CQL search.

## Features

- **16 comprehensive tools** covering spaces, pages, comments, labels, search, page history, and attachments
- **Full Atlassian OAuth 2.0 authentication** (shared OAuth app with Jira)
- **CQL search support** via Confluence Query Language
- **Page lifecycle management** including create, update, and delete
- **Content in Atlassian Storage Format** (XHTML) for page bodies

## OAuth Setup

### Prerequisites

- An Atlassian Cloud account with Confluence access
- Access to create OAuth 2.0 integrations in the Atlassian Developer Console

### Step-by-Step Configuration

1. **Create Atlassian OAuth 2.0 Integration**
   - Go to https://developer.atlassian.com/console/myapps/
   - Click "Create" > "OAuth 2.0 integration"
   - Fill in the details:
     - **Name**: `SageMCP` (or your preferred name)
   - Click "Create"

2. **Configure Permissions**
   - In the app settings, go to "Permissions"
   - Add the Confluence API permissions:
     - `read:confluence-content.all` - Read all Confluence content
     - `write:confluence-content` - Write Confluence content
     - `read:confluence-space.summary` - Read space summaries
   - Also add `offline_access` for refresh tokens

3. **Configure Authorization**
   - Go to "Authorization" > "OAuth 2.0 (3LO)"
   - Add callback URL: `http://localhost:8000/api/v1/oauth/callback/confluence`
   - Click "Save changes"

4. **Get Credentials**
   - Go to "Settings"
   - Note the **Client ID**
   - Note the **Secret** (Client Secret)
   - Save both credentials securely

5. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     CONFLUENCE_CLIENT_ID=your_client_id_here
     CONFLUENCE_CLIENT_SECRET=your_client_secret_here
     ```
   - Note: If using the same Atlassian OAuth app as Jira, the Client ID and Secret will be the same.

6. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add Confluence connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The Confluence connector requires these scopes:
- `read:confluence-content.all` - Read all Confluence content
- `write:confluence-content` - Create and update Confluence content
- `read:confluence-space.summary` - Read space summary information
- `offline_access` - Required for refresh token support

## Available Tools

### Space Management

#### `confluence_list_spaces`
List Confluence spaces.

**Parameters:**
- `limit` (optional): Maximum number of spaces to return (1-250, default: 25)
- `type` (optional): Filter by space type - `global`, `personal`
- `status` (optional): Filter by space status - `current`, `archived`

#### `confluence_get_space`
Get detailed information about a Confluence space by its ID.

**Parameters:**
- `space_id` (required): The numeric ID of the space

### Page Management

#### `confluence_list_pages`
List pages in Confluence, optionally filtered by space.

**Parameters:**
- `space_id` (optional): Filter by space ID
- `limit` (optional): Maximum number of pages to return (1-250, default: 25)
- `sort` (optional): Sort order - `id`, `-id`, `title`, `-title`, `created-date`, `-created-date`, `modified-date`, `-modified-date` (prefix with `-` for descending)
- `status` (optional): Filter by page status - `current`, `archived`, `deleted`, `trashed`

#### `confluence_get_page`
Get a Confluence page by ID, including its body content in storage format.

**Parameters:**
- `page_id` (required): The numeric ID of the page

#### `confluence_create_page`
Create a new page in a Confluence space. Body must be in Atlassian Storage Format (XHTML).

**Parameters:**
- `space_id` (required): The numeric ID of the space to create the page in
- `title` (required): Page title
- `body` (required): Page body in Atlassian Storage Format (XHTML). Example: `<p>Hello world</p>`
- `parent_id` (optional): Parent page ID to nest under

#### `confluence_update_page`
Update an existing Confluence page. Requires current version number (will be auto-incremented).

**Parameters:**
- `page_id` (required): The numeric ID of the page to update
- `title` (required): New page title
- `body` (required): New page body in Atlassian Storage Format (XHTML)
- `version_number` (required): Current version number of the page (will be incremented by 1 for the update)
- `status` (optional): Page status after update - `current`, `draft` (default: `current`)

#### `confluence_delete_page`
Delete a Confluence page by ID.

**Parameters:**
- `page_id` (required): The numeric ID of the page to delete

### Search

#### `confluence_search_content`
Search Confluence content using CQL (Confluence Query Language). Example: `type=page AND space.key=DEV AND text~'architecture'`

**Parameters:**
- `cql` (required): CQL query string (e.g., `type=page AND space.key=DEV`)
- `limit` (optional): Maximum number of results to return (1-100, default: 25)

### Page Hierarchy

#### `confluence_get_page_children`
Get child pages of a Confluence page.

**Parameters:**
- `page_id` (required): The numeric ID of the parent page
- `limit` (optional): Maximum number of child pages to return (1-250, default: 25)

### Comments

#### `confluence_list_page_comments`
Get footer comments on a Confluence page.

**Parameters:**
- `page_id` (required): The numeric ID of the page
- `limit` (optional): Maximum number of comments to return (1-250, default: 25)

#### `confluence_add_comment`
Add a footer comment to a Confluence page. Body must be in Atlassian Storage Format.

**Parameters:**
- `page_id` (required): The numeric ID of the page to comment on
- `body` (required): Comment body in Atlassian Storage Format (XHTML). Example: `<p>Great work!</p>`

### Labels

#### `confluence_get_page_labels`
Get labels on a Confluence page.

**Parameters:**
- `page_id` (required): The numeric ID of the page

#### `confluence_add_label`
Add a label to a Confluence page.

**Parameters:**
- `page_id` (required): The numeric ID of the page
- `label` (required): Label name to add

### History & Attachments

#### `confluence_get_page_history`
Get version history of a Confluence page.

**Parameters:**
- `page_id` (required): The numeric ID of the page
- `limit` (optional): Maximum number of versions to return (1-250, default: 25)

#### `confluence_list_page_attachments`
List attachments on a Confluence page.

**Parameters:**
- `page_id` (required): The numeric ID of the page
- `limit` (optional): Maximum number of attachments to return (1-250, default: 25)

## Resource URIs

The connector exposes these resource types:

- **Spaces**: `confluence://space/{space_id}`
  - Returns space metadata and properties

- **Pages**: `confluence://page/{page_id}`
  - Returns page content in storage format

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Confluence credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "No accessible Confluence resources found"
- **Solution**: Ensure the OAuth token has Confluence access. If using a shared Atlassian OAuth app, verify Confluence permissions are enabled alongside Jira permissions.

**Issue**: Page update fails with version conflict
- **Solution**: The `version_number` parameter must match the current version of the page. Use `confluence_get_page` to retrieve the current version number before updating.

**Issue**: CQL search returns unexpected results
- **Solution**: Verify your CQL syntax. Common CQL operators: `AND`, `OR`, `NOT`, `=`, `~` (contains), `IN`. Refer to the Confluence CQL documentation for full syntax.

**Issue**: Page body not rendering correctly
- **Solution**: Page bodies must be in Atlassian Storage Format (XHTML), not plain text or Markdown. Example: `<p>Paragraph text</p>`, `<h1>Heading</h1>`, `<ul><li>List item</li></ul>`

**Issue**: "Rate limit exceeded"
- **Solution**: Atlassian Cloud has API rate limits. Wait or optimize your queries by using specific filters.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Listing Confluence spaces
DEBUG: Found 12 spaces
DEBUG: Fetching Confluence page: 12345
```

## API Reference

- **Confluence REST API v2 Documentation**: https://developer.atlassian.com/cloud/confluence/rest/v2/
- **Confluence REST API v1 (CQL Search)**: https://developer.atlassian.com/cloud/confluence/rest/v1/
- **Atlassian OAuth 2.0**: https://developer.atlassian.com/cloud/confluence/oauth-2-3lo-apps/
- **CQL Syntax Reference**: https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/

## Source Code

Implementation: `src/sage_mcp/connectors/confluence.py`
