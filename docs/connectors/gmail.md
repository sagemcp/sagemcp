# Gmail Connector

The Gmail connector provides comprehensive integration with Google's Gmail API, enabling Claude Desktop to send, read, search, and manage email messages, threads, labels, and drafts through OAuth 2.0 authentication.

## Features

- **15 comprehensive tools** covering messages, threads, labels, and drafts
- **Full OAuth 2.0 authentication** with Google account access
- **Gmail search syntax support** for powerful message filtering
- **Thread-aware replies and forwards** preserving conversation context

## OAuth Setup

### Prerequisites

- A Google account
- Access to the Google Cloud Console to create OAuth credentials

### Step-by-Step Configuration

1. **Create Google OAuth Credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/) > APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Web application" as the application type
   - Fill in the details:
     - **Name**: `SageMCP` (or your preferred name)
     - **Authorized redirect URIs**: `http://localhost:8000/api/v1/oauth/callback/google`
   - Click "Create"

2. **Enable the Gmail API**
   - In the Google Cloud Console, go to APIs & Services > Library
   - Search for "Gmail API"
   - Click "Enable"

3. **Get Credentials**
   - Note the **Client ID**
   - Note the **Client Secret**
   - Save both credentials securely

4. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     GOOGLE_CLIENT_ID=your_client_id_here
     GOOGLE_CLIENT_SECRET=your_client_secret_here
     ```

5. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add Gmail connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The Gmail connector requests the following scope:
- `https://mail.google.com/` - Full access to Gmail (read, send, delete, manage)

## Available Tools

### Messages

#### `gmail_list_messages`
List messages in the user's mailbox. Supports Gmail search query syntax for filtering.

**Parameters:**
- `q` (optional): Gmail search query (e.g., `from:user@example.com`, `is:unread`, `subject:hello`)
- `maxResults` (optional): Maximum number of messages to return (1-500, default: 20)
- `pageToken` (optional): Page token for retrieving the next page of results
- `labelIds` (optional): Array of label IDs -- only return messages matching all specified labels

#### `gmail_get_message`
Get a specific message by ID with full content including headers and body.

**Parameters:**
- `id` (required): The ID of the message to retrieve

#### `gmail_search_messages`
Search messages using Gmail search syntax (e.g., `from:user@example.com after:2024/01/01 has:attachment`).

**Parameters:**
- `query` (required): Gmail search query string
- `maxResults` (optional): Maximum number of results to return (1-500, default: 20)
- `pageToken` (optional): Page token for retrieving the next page of results

#### `gmail_send_message`
Send a new email message.

**Parameters:**
- `to` (required): Recipient email address
- `subject` (required): Email subject line
- `body` (required): Email body content (plain text)
- `cc` (optional): CC recipient email addresses (comma-separated)
- `bcc` (optional): BCC recipient email addresses (comma-separated)

#### `gmail_reply_to_message`
Reply to an existing email message, preserving the thread.

**Parameters:**
- `message_id` (required): The ID of the message to reply to
- `body` (required): Reply body content (plain text)
- `reply_all` (optional): If true, reply to all recipients (default: false)

#### `gmail_forward_message`
Forward an existing email message to a new recipient.

**Parameters:**
- `message_id` (required): The ID of the message to forward
- `to` (required): Recipient email address to forward to
- `body` (optional): Optional additional message to include above the forwarded content (default: "")

#### `gmail_trash_message`
Move a message to the trash.

**Parameters:**
- `id` (required): The ID of the message to trash

#### `gmail_untrash_message`
Remove a message from the trash.

**Parameters:**
- `id` (required): The ID of the message to untrash

### Threads

#### `gmail_list_threads`
List email threads in the user's mailbox.

**Parameters:**
- `q` (optional): Gmail search query to filter threads
- `maxResults` (optional): Maximum number of threads to return (1-500, default: 20)
- `pageToken` (optional): Page token for retrieving the next page of results
- `labelIds` (optional): Array of label IDs -- only return threads matching all specified labels

#### `gmail_get_thread`
Get a specific email thread by ID with all messages.

**Parameters:**
- `id` (required): The ID of the thread to retrieve

### Labels

#### `gmail_list_labels`
List all labels in the user's mailbox (including system labels like INBOX, SENT, TRASH).

**Parameters:** None

#### `gmail_create_label`
Create a new label in the user's mailbox.

**Parameters:**
- `name` (required): The display name of the label
- `labelListVisibility` (optional): Visibility in the label list -- `labelShow`, `labelShowIfUnread`, `labelHide` (default: `labelShow`)
- `messageListVisibility` (optional): Visibility of messages with this label -- `show`, `hide` (default: `show`)

#### `gmail_modify_labels`
Add or remove labels from a specific message.

**Parameters:**
- `id` (required): The ID of the message to modify
- `addLabelIds` (optional): Array of label IDs to add to the message
- `removeLabelIds` (optional): Array of label IDs to remove from the message

### Drafts

#### `gmail_create_draft`
Create a draft email message.

**Parameters:**
- `to` (required): Recipient email address
- `subject` (required): Email subject line
- `body` (required): Email body content (plain text)
- `cc` (optional): CC recipient email addresses (comma-separated)
- `bcc` (optional): BCC recipient email addresses (comma-separated)

#### `gmail_list_drafts`
List draft messages in the user's mailbox.

**Parameters:**
- `maxResults` (optional): Maximum number of drafts to return (1-500, default: 20)
- `pageToken` (optional): Page token for retrieving the next page of results

## Usage Examples

### Example 1: Search Unread Messages

```typescript
"Show me my unread emails from the last week"

// This will call gmail_search_messages with:
{
  "query": "is:unread newer_than:7d"
}
```

### Example 2: Send an Email

```typescript
"Send an email to alice@example.com about the meeting tomorrow"

// This will call gmail_send_message with:
{
  "to": "alice@example.com",
  "subject": "Meeting Tomorrow",
  "body": "Hi Alice, just confirming our meeting tomorrow..."
}
```

### Example 3: Reply to a Thread

```typescript
"Reply to that last message saying I'll be there"

// This will call gmail_reply_to_message with:
{
  "message_id": "18abc123def",
  "body": "I'll be there. Thanks!"
}
```

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Google OAuth credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "Insufficient Permission" or 403 error
- **Solution**: Ensure the Gmail API is enabled in your Google Cloud Console and that the OAuth consent screen includes the `https://mail.google.com/` scope

**Issue**: "Daily sending limit exceeded"
- **Solution**: Gmail has sending limits (500 emails/day for personal accounts, 2,000/day for Workspace). Wait until the limit resets.

**Issue**: "Precondition check failed" on label operations
- **Solution**: Verify the label ID exists by calling `gmail_list_labels` first. System labels (INBOX, SENT, etc.) cannot be deleted.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Gmail API request to /gmail/v1/users/me/messages
DEBUG: Gmail API returned 200
```

## API Reference

- **Gmail REST API Documentation**: https://developers.google.com/gmail/api/reference/rest
- **Gmail Search Operators**: https://support.google.com/mail/answer/7190
- **OAuth Scopes**: https://developers.google.com/gmail/api/auth/scopes
- **Rate Limits**: https://developers.google.com/gmail/api/reference/quota

## Source Code

Implementation: `src/sage_mcp/connectors/gmail.py`
