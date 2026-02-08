# Microsoft Outlook Connector

The Outlook connector provides comprehensive email management through Microsoft Graph API v1.0, enabling Claude Desktop to read, send, search, organize, and manage Outlook email messages, folders, attachments, and drafts via OAuth 2.0 authentication with Azure AD.

## Features

- **15 comprehensive tools** covering messages, folders, attachments, drafts, and Focused Inbox
- **Microsoft OAuth 2.0 (Azure AD)** authentication with delegated permissions
- **OData query support** for filtering, sorting, and field selection
- **Focused Inbox integration** leveraging Outlook's AI-powered email classification

## OAuth Setup

### Prerequisites

- A Microsoft account (personal or Microsoft 365 / work / school)
- Access to the [Azure Portal](https://portal.azure.com/) to register an application

### Step-by-Step Configuration

1. **Register an Azure AD Application**
   - Go to Azure Portal > Azure Active Directory > App registrations
   - Click "New registration"
   - Fill in the details:
     - **Name**: `SageMCP` (or your preferred name)
     - **Supported account types**: "Accounts in any organizational directory and personal Microsoft accounts"
     - **Redirect URI**: Select "Web" and enter `http://localhost:8000/api/v1/oauth/callback/microsoft`
   - Click "Register"

2. **Configure API Permissions**
   - In your app registration, go to "API permissions"
   - Click "Add a permission" > "Microsoft Graph" > "Delegated permissions"
   - Add the following permissions:
     - `Mail.ReadWrite`
     - `Mail.Send`
     - `User.Read`
   - Click "Grant admin consent" if you have admin access (optional but recommended)

3. **Get Credentials**
   - Go to "Certificates & secrets" > "New client secret"
   - Note the **Application (client) ID** from the Overview page
   - Note the **Client Secret** value (copy immediately -- it is only shown once)

4. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     MICROSOFT_CLIENT_ID=your_client_id_here
     MICROSOFT_CLIENT_SECRET=your_client_secret_here
     ```

5. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add Outlook connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The Outlook connector requests these delegated permissions:
- `Mail.ReadWrite` - Read and write access to user mail
- `Mail.Send` - Send mail as the user
- `User.Read` - Sign in and read user profile

## Available Tools

### Messages

#### `outlook_list_messages`
List messages from inbox or a specific mail folder. Supports OData query parameters for filtering, sorting, and field selection.

**Parameters:**
- `folder_id` (optional): Mail folder ID or well-known name -- `inbox`, `drafts`, `sentitems`, `deleteditems`, `junkemail`, `archive` (default: `inbox`)
- `top` (optional): Number of messages to return (1-100, default: 25)
- `filter` (optional): OData $filter expression (e.g., `isRead eq false`, `hasAttachments eq true`)
- `select` (optional): Comma-separated list of fields to return (e.g., `subject,from,receivedDateTime,isRead`)
- `order_by` (optional): OData $orderby expression (default: `receivedDateTime desc`)

#### `outlook_get_message`
Get a specific email message by its ID, including full body content and metadata.

**Parameters:**
- `message_id` (required): The unique ID of the message
- `select` (optional): Comma-separated list of fields to return (e.g., `subject,body,from,toRecipients`)

#### `outlook_send_message`
Send a new email message. Supports HTML and text body content, with CC and BCC recipients.

**Parameters:**
- `subject` (required): Email subject line
- `body` (required): Email body content (HTML or plain text depending on content_type)
- `to_recipients` (required): Array of recipient email addresses
- `cc_recipients` (optional): Array of CC recipient email addresses
- `bcc_recipients` (optional): Array of BCC recipient email addresses
- `content_type` (optional): Body content type -- `HTML` or `Text` (default: `HTML`)

#### `outlook_reply_to_message`
Reply to an email message. Can reply to sender only or reply all.

**Parameters:**
- `message_id` (required): The unique ID of the message to reply to
- `comment` (required): The reply body content
- `reply_all` (optional): Whether to reply to all recipients (default: false)

#### `outlook_forward_message`
Forward an email message to one or more recipients with an optional comment.

**Parameters:**
- `message_id` (required): The unique ID of the message to forward
- `to_recipients` (required): Array of recipient email addresses to forward to
- `comment` (optional): Optional comment to include with the forwarded message

#### `outlook_delete_message`
Delete an email message. Moves to Deleted Items folder.

**Parameters:**
- `message_id` (required): The unique ID of the message to delete

#### `outlook_move_message`
Move an email message to a different mail folder.

**Parameters:**
- `message_id` (required): The unique ID of the message to move
- `destination_folder_id` (required): The ID or well-known name of the destination folder (e.g., `archive`, `deleteditems`)

#### `outlook_search_messages`
Search email messages using Microsoft Graph $search query syntax. Searches across subject, body, and other fields.

**Parameters:**
- `query` (required): Search query string (e.g., `budget report`, `from:user@example.com`)
- `top` (optional): Number of results to return (1-100, default: 25)

#### `outlook_flag_message`
Flag, unflag, or mark a message as complete. Flagged messages appear in the flagged email view.

**Parameters:**
- `message_id` (required): The unique ID of the message
- `flag_status` (required): Flag status to set -- `flagged`, `complete`, `notFlagged`

#### `outlook_list_focused_inbox`
List messages from the Focused Inbox. Returns only messages classified as 'focused' by Outlook's AI filtering.

**Parameters:**
- `top` (optional): Number of messages to return (1-100, default: 25)
- `filter` (optional): Additional OData $filter expression to apply on top of focused inbox filter

### Folders

#### `outlook_list_folders`
List all mail folders in the user's mailbox, including folder IDs, display names, and message counts.

**Parameters:** None

#### `outlook_create_folder`
Create a new mail folder. Can create top-level folders or child folders within an existing folder.

**Parameters:**
- `display_name` (required): Display name for the new folder
- `parent_folder_id` (optional): Optional parent folder ID to create a child folder. Omit for a top-level folder.

### Attachments

#### `outlook_list_attachments`
List all attachments on a specific email message, including file names, sizes, and content types.

**Parameters:**
- `message_id` (required): The unique ID of the message

#### `outlook_get_attachment`
Get metadata and content for a specific attachment on an email message.

**Parameters:**
- `message_id` (required): The unique ID of the message
- `attachment_id` (required): The unique ID of the attachment

### Drafts

#### `outlook_create_draft`
Create a draft email message that can be edited and sent later.

**Parameters:**
- `subject` (required): Email subject line
- `body` (required): Email body content (HTML or plain text depending on content_type)
- `to_recipients` (required): Array of recipient email addresses
- `cc_recipients` (optional): Array of CC recipient email addresses
- `content_type` (optional): Body content type -- `HTML` or `Text` (default: `HTML`)

## Usage Examples

### Example 1: List Unread Messages

```typescript
"Show me my unread Outlook emails"

// This will call outlook_list_messages with:
{
  "folder_id": "inbox",
  "filter": "isRead eq false",
  "top": 25
}
```

### Example 2: Search for Messages

```typescript
"Find emails about the Q4 budget report"

// This will call outlook_search_messages with:
{
  "query": "Q4 budget report",
  "top": 25
}
```

### Example 3: Send an Email

```typescript
"Send an email to the team about the standup"

// This will call outlook_send_message with:
{
  "subject": "Daily Standup Reminder",
  "body": "<p>Hi team, just a reminder about our standup at 10am.</p>",
  "to_recipients": ["team@company.com"],
  "content_type": "HTML"
}
```

### Example 4: Check Focused Inbox

```typescript
"Show me my focused inbox"

// This will call outlook_list_focused_inbox with:
{
  "top": 25
}
```

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Microsoft OAuth credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "Insufficient privileges" or 403 error
- **Solution**: Ensure the app registration has `Mail.ReadWrite` and `Mail.Send` delegated permissions. Admin consent may be required for organizational accounts.

**Issue**: "Resource not found" when accessing folders
- **Solution**: Use well-known folder names (`inbox`, `drafts`, `sentitems`, `deleteditems`, `junkemail`, `archive`) or retrieve folder IDs via `outlook_list_folders` first.

**Issue**: "Request rate limit exceeded" (429)
- **Solution**: Microsoft Graph has throttling limits. Back off and retry. Typical limits are ~10,000 requests per 10 minutes per user.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Outlook API request to /v1.0/me/mailFolders/inbox/messages
DEBUG: Outlook API returned 200
```

## API Reference

- **Microsoft Graph Mail API**: https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview
- **OData Query Parameters**: https://learn.microsoft.com/en-us/graph/query-parameters
- **Microsoft Graph Permissions**: https://learn.microsoft.com/en-us/graph/permissions-reference#mail-permissions
- **Throttling Guidance**: https://learn.microsoft.com/en-us/graph/throttling

## Source Code

Implementation: `src/sage_mcp/connectors/outlook.py`
