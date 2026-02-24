# Discord Connector

The Discord connector provides comprehensive integration with Discord's REST API v10, enabling Claude Desktop to manage guilds (servers), channels, messages, threads, reactions, roles, and members through OAuth 2.0 authentication. All Discord IDs are snowflake strings (large integers represented as strings).

## Features

- **15 comprehensive tools** covering guilds, channels, messages, threads, reactions, roles, and members
- **Full OAuth 2.0 authentication** with Discord's OAuth provider
- **Message management** including send, edit, delete, and search
- **Thread support** for creating and listing threads
- **Dynamic resource discovery** of guilds and channels

## OAuth Setup

### Prerequisites

- A Discord account
- Access to the Discord Developer Portal to create applications

### Step-by-Step Configuration

1. **Create Discord Application**
   - Go to https://discord.com/developers/applications
   - Click "New Application"
   - Enter a name: `SageMCP` (or your preferred name)
   - Click "Create"

2. **Configure OAuth2**
   - Go to "OAuth2" in the left sidebar
   - Note the **Client ID**
   - Click "Reset Secret" to generate a **Client Secret**
   - Add redirect URL: `http://localhost:8000/api/v1/oauth/callback/discord`
   - Under "OAuth2 URL Generator", select scopes:
     - `guilds` - Access to list guilds
     - `messages.read` - Read messages
     - `bot` - Bot access for sending messages and managing content

3. **Configure Bot (if needed)**
   - Go to "Bot" in the left sidebar
   - Enable "Message Content Intent" under Privileged Gateway Intents
   - This is required for reading message content

4. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     DISCORD_CLIENT_ID=your_client_id_here
     DISCORD_CLIENT_SECRET=your_client_secret_here
     ```

5. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add Discord connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The Discord connector requires these scopes:
- `guilds` - Access to the user's guild list
- `messages.read` - Read message content in guilds
- `bot` - Bot functionality for sending messages and managing content

## Available Tools

### Guilds (Servers)

#### `discord_list_guilds`
List guilds (servers) the bot/user is a member of.

**Parameters:** None

#### `discord_get_guild`
Get detailed information about a specific guild (server) by ID.

**Parameters:**
- `guild_id` (required): The guild (server) snowflake ID

### Channels

#### `discord_list_channels`
List all channels in a guild.

**Parameters:**
- `guild_id` (required): The guild (server) snowflake ID

#### `discord_get_channel`
Get detailed information about a specific channel.

**Parameters:**
- `channel_id` (required): The channel snowflake ID

### Messages

#### `discord_list_messages`
List recent messages in a channel.

**Parameters:**
- `channel_id` (required): The channel snowflake ID
- `limit` (optional): Number of messages to return (1-100, default: 50)

#### `discord_send_message`
Send a message to a channel.

**Parameters:**
- `channel_id` (required): The channel snowflake ID
- `content` (required): The message content text (max 2000 characters)

#### `discord_edit_message`
Edit an existing message in a channel.

**Parameters:**
- `channel_id` (required): The channel snowflake ID
- `message_id` (required): The message snowflake ID
- `content` (required): The new message content text

#### `discord_delete_message`
Delete a message from a channel.

**Parameters:**
- `channel_id` (required): The channel snowflake ID
- `message_id` (required): The message snowflake ID

#### `discord_search_messages`
Search messages in a guild by content.

**Parameters:**
- `guild_id` (required): The guild (server) snowflake ID
- `query` (required): Search query string

### Threads

#### `discord_list_threads`
List all active threads in a guild.

**Parameters:**
- `guild_id` (required): The guild (server) snowflake ID

#### `discord_create_thread`
Create a new thread from an existing message.

**Parameters:**
- `channel_id` (required): The channel snowflake ID containing the message
- `message_id` (required): The message snowflake ID to create a thread from
- `name` (required): Name of the thread (1-100 characters)
- `auto_archive_duration` (optional): Duration in minutes to auto-archive the thread - `60`, `1440`, `4320`, `10080` (default: `1440`)

### Reactions

#### `discord_add_reaction`
Add a reaction emoji to a message.

**Parameters:**
- `channel_id` (required): The channel snowflake ID
- `message_id` (required): The message snowflake ID
- `emoji` (required): The emoji to react with. Use Unicode emoji (URL-encoded) or custom emoji in the format `name:id`

### Roles & Members

#### `discord_list_guild_members`
List members of a guild.

**Parameters:**
- `guild_id` (required): The guild (server) snowflake ID
- `limit` (optional): Number of members to return (1-1000, default: 100)

#### `discord_list_roles`
List all roles in a guild.

**Parameters:**
- `guild_id` (required): The guild (server) snowflake ID

### Users

#### `discord_get_user`
Get information about the current authenticated user.

**Parameters:** None

## Resource URIs

The connector exposes these resource types:

- **Guilds**: `discord://{guild_id}`
  - Returns guild metadata including member and channel counts

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Discord credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "Missing Access" or "Missing Permissions"
- **Solution**: Ensure the bot has been invited to the guild with appropriate permissions. Check that the bot role has access to the channels you are trying to read or write.

**Issue**: "Message content is empty"
- **Solution**: Enable "Message Content Intent" in the Discord Developer Portal under Bot settings. Without this privileged intent, message content will be empty for bots.

**Issue**: Cannot send messages
- **Solution**: Verify the bot has "Send Messages" permission in the target channel. Channel-level permission overrides may restrict the bot even if the guild-level permission is granted.

**Issue**: "Unknown Emoji" when adding reactions
- **Solution**: Unicode emoji must be URL-encoded. Custom emoji must be in the format `name:id` (e.g., `custom_emoji:123456789`).

**Issue**: "Rate limit exceeded"
- **Solution**: Discord has strict rate limits per endpoint. The connector handles basic rate limiting, but excessive requests may still be throttled. Wait for the rate limit to reset.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Discord API request to /guilds/123456789/channels
DEBUG: Discord API returned 200
```

## API Reference

- **Discord Developer Documentation**: https://discord.com/developers/docs/reference
- **OAuth2 Guide**: https://discord.com/developers/docs/topics/oauth2
- **Rate Limits**: https://discord.com/developers/docs/topics/rate-limits
- **Gateway Intents**: https://discord.com/developers/docs/topics/gateway#gateway-intents

## Source Code

Implementation: `src/sage_mcp/connectors/discord.py`
