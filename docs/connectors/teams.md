# Microsoft Teams Connector

The Microsoft Teams connector provides comprehensive integration with Microsoft Graph API, enabling Claude Desktop to manage teams, channels, chats, messages, and members through Microsoft OAuth 2.0 (Azure AD) authentication.

## Features

- **13 comprehensive tools** covering teams, channels, channel messages, chats, chat messages, message replies, search, and membership
- **Full Microsoft OAuth 2.0 authentication** via Azure Active Directory
- **Channel and chat messaging** including send, reply, and search
- **OData query support** for filtering channels and chats
- **Team and channel member management**

## OAuth Setup

### Prerequisites

- A Microsoft 365 account with Teams access
- Access to the Azure Active Directory portal to register applications

### Step-by-Step Configuration

1. **Register Azure AD Application**
   - Go to https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
   - Click "New registration"
   - Fill in the details:
     - **Name**: `SageMCP` (or your preferred name)
     - **Supported account types**: "Accounts in any organizational directory" (for multi-tenant) or "Single tenant" (for your organization only)
     - **Redirect URI**: Select "Web" and enter `http://localhost:8000/api/v1/oauth/callback/teams`
   - Click "Register"

2. **Configure API Permissions**
   - Go to "API permissions"
   - Click "Add a permission" > "Microsoft Graph" > "Delegated permissions"
   - Add the following permissions:
     - `Team.ReadBasic.All` - Read team names and descriptions
     - `Channel.ReadBasic.All` - Read channel names and descriptions
     - `ChannelMessage.Read.All` - Read channel messages
     - `Chat.Read` - Read user chat messages
     - `User.Read` - Read user profile
   - For sending messages, also add:
     - `ChannelMessage.Send` - Send channel messages
     - `Chat.ReadWrite` - Read and send chat messages
   - Click "Grant admin consent" if you have admin access

3. **Get Credentials**
   - Go to "Overview" and note the **Application (client) ID**
   - Go to "Certificates & secrets" > "New client secret"
   - Add a description and set expiry
   - Note the **Value** (Client Secret) -- this is only shown once
   - Save both credentials securely

4. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     TEAMS_CLIENT_ID=your_application_id_here
     TEAMS_CLIENT_SECRET=your_client_secret_here
     ```

5. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add Microsoft Teams connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The Microsoft Teams connector requires these Microsoft Graph delegated permissions:
- `Team.ReadBasic.All` - Read the names and descriptions of teams
- `Channel.ReadBasic.All` - Read channel names and descriptions
- `ChannelMessage.Read.All` - Read messages in team channels
- `Chat.Read` - Read user chat messages
- `User.Read` - Read basic user profile

## Available Tools

### Team Management

#### `teams_list_teams`
List teams the authenticated user is a member of.

**Parameters:**
- `select` (optional): Comma-separated list of properties to select (e.g., `id,displayName,description`)

#### `teams_get_team`
Get details of a specific team.

**Parameters:**
- `team_id` (required): The ID of the team

#### `teams_list_team_members`
List members of a team.

**Parameters:**
- `team_id` (required): The ID of the team

### Channel Management

#### `teams_list_channels`
List channels in a team.

**Parameters:**
- `team_id` (required): The ID of the team
- `filter` (optional): OData $filter expression to filter channels (e.g., `membershipType eq 'standard'`)

#### `teams_get_channel`
Get details of a specific channel in a team.

**Parameters:**
- `team_id` (required): The ID of the team
- `channel_id` (required): The ID of the channel

#### `teams_list_channel_members`
List members of a specific channel in a team.

**Parameters:**
- `team_id` (required): The ID of the team
- `channel_id` (required): The ID of the channel

### Channel Messages

#### `teams_list_channel_messages`
List messages in a channel. Returns the most recent messages.

**Parameters:**
- `team_id` (required): The ID of the team
- `channel_id` (required): The ID of the channel
- `top` (optional): Number of messages to return (1-50, default: 25)

#### `teams_get_channel_message`
Get a specific message in a channel.

**Parameters:**
- `team_id` (required): The ID of the team
- `channel_id` (required): The ID of the channel
- `message_id` (required): The ID of the message

#### `teams_send_channel_message`
Send a message to a channel in a team.

**Parameters:**
- `team_id` (required): The ID of the team
- `channel_id` (required): The ID of the channel
- `content` (required): The message content
- `content_type` (optional): The content type of the message body - `text`, `html` (default: `html`)

#### `teams_reply_to_message`
Reply to a specific message in a channel.

**Parameters:**
- `team_id` (required): The ID of the team
- `channel_id` (required): The ID of the channel
- `message_id` (required): The ID of the message to reply to
- `content` (required): The reply content
- `content_type` (optional): The content type of the reply body - `text`, `html` (default: `html`)

### Chat Management

#### `teams_list_chats`
List chats the authenticated user is part of.

**Parameters:**
- `top` (optional): Number of chats to return (1-50, default: 25)
- `filter` (optional): OData $filter expression to filter chats (e.g., `chatType eq 'oneOnOne'`)

#### `teams_list_chat_messages`
List messages in a chat.

**Parameters:**
- `chat_id` (required): The ID of the chat
- `top` (optional): Number of messages to return (1-50, default: 25)

#### `teams_send_chat_message`
Send a message in a chat.

**Parameters:**
- `chat_id` (required): The ID of the chat
- `content` (required): The message content
- `content_type` (optional): The content type of the message body - `text`, `html` (default: `html`)

### Search

#### `teams_search_messages`
Search across messages in the user's chats. Uses the Microsoft Graph `/me/chats/getAllMessages` endpoint with `$search`.

**Parameters:**
- `query` (required): The search query string
- `top` (optional): Number of results to return (1-50, default: 25)

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Microsoft OAuth credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "Insufficient privileges to complete the operation"
- **Solution**: Ensure the Azure AD app has the required API permissions and that admin consent has been granted. Go to Azure Portal > App registrations > API permissions and click "Grant admin consent."

**Issue**: Cannot read channel messages
- **Solution**: The `ChannelMessage.Read.All` permission requires admin consent. Contact your Microsoft 365 administrator to grant consent for the application.

**Issue**: "Access denied" when sending messages
- **Solution**: Add the `ChannelMessage.Send` and/or `Chat.ReadWrite` permissions to your Azure AD app registration and grant admin consent.

**Issue**: OData $filter not working
- **Solution**: Not all properties support filtering. Refer to the Microsoft Graph API documentation for supported filter properties on each endpoint.

**Issue**: Search returns empty results
- **Solution**: The `$search` parameter on `/me/chats/getAllMessages` may require additional permissions or Microsoft 365 compliance features to be enabled. Consult your tenant administrator.

**Issue**: "Rate limit exceeded"
- **Solution**: Microsoft Graph has throttling limits. The connector follows standard retry patterns. Reduce request frequency or use the `$top` parameter to limit results.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Teams API request to /me/joinedTeams
DEBUG: Teams API returned 200
```

## API Reference

- **Microsoft Teams API Overview**: https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview
- **Microsoft Graph API Reference**: https://learn.microsoft.com/en-us/graph/api/overview
- **Azure AD App Registration**: https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app
- **Microsoft Graph Permissions**: https://learn.microsoft.com/en-us/graph/permissions-reference
- **Throttling Guidance**: https://learn.microsoft.com/en-us/graph/throttling

## Source Code

Implementation: `src/sage_mcp/connectors/teams.py`
