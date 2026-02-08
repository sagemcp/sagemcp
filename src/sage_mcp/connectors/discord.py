"""Discord connector implementation.

Provides 15 tools for managing Discord guilds (servers), channels, messages,
threads, reactions, roles, and members via Discord REST API v10.

All IDs in Discord are snowflake strings (large integers represented as strings).
API reference: https://discord.com/developers/docs/reference
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"


@register_connector(ConnectorType.DISCORD)
class DiscordConnector(BaseConnector):
    """Discord connector for managing servers, channels, and messages.

    Uses Discord REST API v10 with OAuth2 Bearer token authentication.
    All authenticated requests go through BaseConnector._make_authenticated_request()
    which handles retry, connection pooling, and token injection.
    """

    @property
    def display_name(self) -> str:
        return "Discord"

    @property
    def description(self) -> str:
        return "Manage Discord servers, channels, and messages"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Tool]:
        """Return the 15 Discord tools with JSON Schema input definitions.

        Tool names follow the convention: discord_{tool_name}.
        Cold path -- called once per tools/list request, result is cached by ServerPool.
        """
        tools = [
            types.Tool(
                name="discord_list_guilds",
                description="List guilds (servers) the bot/user is a member of",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            types.Tool(
                name="discord_get_guild",
                description="Get detailed information about a specific guild (server) by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "The guild (server) snowflake ID",
                        }
                    },
                    "required": ["guild_id"],
                },
            ),
            types.Tool(
                name="discord_list_channels",
                description="List all channels in a guild",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "The guild (server) snowflake ID",
                        }
                    },
                    "required": ["guild_id"],
                },
            ),
            types.Tool(
                name="discord_get_channel",
                description="Get detailed information about a specific channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel snowflake ID",
                        }
                    },
                    "required": ["channel_id"],
                },
            ),
            types.Tool(
                name="discord_list_messages",
                description="List recent messages in a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel snowflake ID",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 50,
                            "description": "Number of messages to return (1-100, default 50)",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            types.Tool(
                name="discord_send_message",
                description="Send a message to a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel snowflake ID",
                        },
                        "content": {
                            "type": "string",
                            "description": "The message content text (max 2000 characters)",
                        },
                    },
                    "required": ["channel_id", "content"],
                },
            ),
            types.Tool(
                name="discord_edit_message",
                description="Edit an existing message in a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel snowflake ID",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "The message snowflake ID",
                        },
                        "content": {
                            "type": "string",
                            "description": "The new message content text",
                        },
                    },
                    "required": ["channel_id", "message_id", "content"],
                },
            ),
            types.Tool(
                name="discord_delete_message",
                description="Delete a message from a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel snowflake ID",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "The message snowflake ID",
                        },
                    },
                    "required": ["channel_id", "message_id"],
                },
            ),
            types.Tool(
                name="discord_list_guild_members",
                description="List members of a guild",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "The guild (server) snowflake ID",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                            "default": 100,
                            "description": "Number of members to return (1-1000, default 100)",
                        },
                    },
                    "required": ["guild_id"],
                },
            ),
            types.Tool(
                name="discord_search_messages",
                description="Search messages in a guild by content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "The guild (server) snowflake ID",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query string",
                        },
                    },
                    "required": ["guild_id", "query"],
                },
            ),
            types.Tool(
                name="discord_list_threads",
                description="List all active threads in a guild",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "The guild (server) snowflake ID",
                        }
                    },
                    "required": ["guild_id"],
                },
            ),
            types.Tool(
                name="discord_create_thread",
                description="Create a new thread from an existing message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel snowflake ID containing the message",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "The message snowflake ID to create a thread from",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the thread (1-100 characters)",
                        },
                        "auto_archive_duration": {
                            "type": "integer",
                            "enum": [60, 1440, 4320, 10080],
                            "default": 1440,
                            "description": "Duration in minutes to auto-archive the thread (60, 1440, 4320, or 10080)",
                        },
                    },
                    "required": ["channel_id", "message_id", "name"],
                },
            ),
            types.Tool(
                name="discord_add_reaction",
                description="Add a reaction emoji to a message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "The channel snowflake ID",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "The message snowflake ID",
                        },
                        "emoji": {
                            "type": "string",
                            "description": "The emoji to react with. Use Unicode emoji (e.g. a URL-encoded unicode character) or custom emoji in the format name:id",
                        },
                    },
                    "required": ["channel_id", "message_id", "emoji"],
                },
            ),
            types.Tool(
                name="discord_list_roles",
                description="List all roles in a guild",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "The guild (server) snowflake ID",
                        }
                    },
                    "required": ["guild_id"],
                },
            ),
            types.Tool(
                name="discord_get_user",
                description="Get information about the current authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
        ]
        return tools

    async def get_resources(
        self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Resource]:
        """Return Discord resources (guilds and their channels).

        Cold path -- only called on resources/list requests.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        try:
            response = await self._make_authenticated_request(
                "GET", f"{DISCORD_API_BASE}/users/@me/guilds", oauth_cred
            )
            guilds = response.json()

            resources = []
            for guild in guilds:
                guild_id = guild["id"]
                guild_name = guild.get("name", "Unknown")
                resources.append(
                    types.Resource(
                        uri=f"discord://{guild_id}",
                        name=f"Discord Server: {guild_name}",
                        description=f"Discord server {guild_name}",
                    )
                )
            return resources

        except Exception as e:
            logger.warning("Failed to fetch Discord resources: %s", e)
            return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Dispatch a tool call to the appropriate handler.

        Hot path -- tool_name arrives WITHOUT the 'discord_' prefix.
        All handlers return json.dumps(result, indent=2) strings.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Discord credentials"

        # Dispatch table -- avoids elif chain for cleaner profiling
        dispatch = {
            "list_guilds": self._list_guilds,
            "get_guild": self._get_guild,
            "list_channels": self._list_channels,
            "get_channel": self._get_channel,
            "list_messages": self._list_messages,
            "send_message": self._send_message,
            "edit_message": self._edit_message,
            "delete_message": self._delete_message,
            "list_guild_members": self._list_guild_members,
            "search_messages": self._search_messages,
            "list_threads": self._list_threads,
            "create_thread": self._create_thread,
            "add_reaction": self._add_reaction,
            "list_roles": self._list_roles,
            "get_user": self._get_user,
        }

        handler = dispatch.get(tool_name)
        if handler is None:
            return f"Unknown tool: {tool_name}"

        try:
            return await handler(arguments, oauth_cred)
        except Exception as e:
            logger.error(
                "Discord tool '%s' failed: %s", tool_name, e, exc_info=True
            )
            return f"Error executing Discord tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None,
    ) -> str:
        """Read a Discord resource by path.

        Supports guild-level resource paths (guild_id).
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Discord credentials"

        try:
            # resource_path is the guild_id
            guild_id = resource_path.strip("/")
            response = await self._make_authenticated_request(
                "GET",
                f"{DISCORD_API_BASE}/guilds/{guild_id}",
                oauth_cred,
                params={"with_counts": "true"},
            )
            return json.dumps(response.json(), indent=2)
        except Exception as e:
            return f"Error reading Discord resource: {str(e)}"

    # ------------------------------------------------------------------
    # Tool handler implementations
    # ------------------------------------------------------------------

    async def _list_guilds(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /users/@me/guilds -- list guilds the user/bot is in."""
        response = await self._make_authenticated_request(
            "GET", f"{DISCORD_API_BASE}/users/@me/guilds", oauth_cred
        )
        return json.dumps(response.json(), indent=2)

    async def _get_guild(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /guilds/{guild_id}?with_counts=true -- get guild details."""
        guild_id = arguments["guild_id"]
        response = await self._make_authenticated_request(
            "GET",
            f"{DISCORD_API_BASE}/guilds/{guild_id}",
            oauth_cred,
            params={"with_counts": "true"},
        )
        return json.dumps(response.json(), indent=2)

    async def _list_channels(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /guilds/{guild_id}/channels -- list guild channels."""
        guild_id = arguments["guild_id"]
        response = await self._make_authenticated_request(
            "GET",
            f"{DISCORD_API_BASE}/guilds/{guild_id}/channels",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_channel(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /channels/{channel_id} -- get channel details."""
        channel_id = arguments["channel_id"]
        response = await self._make_authenticated_request(
            "GET",
            f"{DISCORD_API_BASE}/channels/{channel_id}",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    async def _list_messages(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /channels/{channel_id}/messages?limit=N -- list channel messages."""
        channel_id = arguments["channel_id"]
        limit = arguments.get("limit", 50)
        # Clamp to Discord's maximum
        limit = min(max(limit, 1), 100)

        response = await self._make_authenticated_request(
            "GET",
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
            oauth_cred,
            params={"limit": limit},
        )
        return json.dumps(response.json(), indent=2)

    async def _send_message(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """POST /channels/{channel_id}/messages -- send a message."""
        channel_id = arguments["channel_id"]
        content = arguments["content"]

        response = await self._make_authenticated_request(
            "POST",
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages",
            oauth_cred,
            json={"content": content},
        )
        return json.dumps(response.json(), indent=2)

    async def _edit_message(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """PATCH /channels/{channel_id}/messages/{message_id} -- edit a message."""
        channel_id = arguments["channel_id"]
        message_id = arguments["message_id"]
        content = arguments["content"]

        response = await self._make_authenticated_request(
            "PATCH",
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}",
            oauth_cred,
            json={"content": content},
        )
        return json.dumps(response.json(), indent=2)

    async def _delete_message(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """DELETE /channels/{channel_id}/messages/{message_id} -- delete a message.

        Returns 204 No Content on success -- no response body to parse.
        """
        channel_id = arguments["channel_id"]
        message_id = arguments["message_id"]

        await self._make_authenticated_request(
            "DELETE",
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}",
            oauth_cred,
        )
        return json.dumps(
            {"success": True, "message": "Message deleted successfully"}, indent=2
        )

    async def _list_guild_members(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /guilds/{guild_id}/members?limit=N -- list guild members."""
        guild_id = arguments["guild_id"]
        limit = arguments.get("limit", 100)
        # Clamp to Discord's maximum
        limit = min(max(limit, 1), 1000)

        response = await self._make_authenticated_request(
            "GET",
            f"{DISCORD_API_BASE}/guilds/{guild_id}/members",
            oauth_cred,
            params={"limit": limit},
        )
        return json.dumps(response.json(), indent=2)

    async def _search_messages(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /guilds/{guild_id}/messages/search?content=query -- search messages."""
        guild_id = arguments["guild_id"]
        query = arguments["query"]

        response = await self._make_authenticated_request(
            "GET",
            f"{DISCORD_API_BASE}/guilds/{guild_id}/messages/search",
            oauth_cred,
            params={"content": query},
        )
        return json.dumps(response.json(), indent=2)

    async def _list_threads(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /guilds/{guild_id}/threads/active -- list active threads."""
        guild_id = arguments["guild_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{DISCORD_API_BASE}/guilds/{guild_id}/threads/active",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    async def _create_thread(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """POST /channels/{channel_id}/messages/{message_id}/threads -- create thread."""
        channel_id = arguments["channel_id"]
        message_id = arguments["message_id"]
        name = arguments["name"]
        auto_archive_duration = arguments.get("auto_archive_duration", 1440)

        response = await self._make_authenticated_request(
            "POST",
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}/threads",
            oauth_cred,
            json={
                "name": name,
                "auto_archive_duration": auto_archive_duration,
            },
        )
        return json.dumps(response.json(), indent=2)

    async def _add_reaction(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """PUT /channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me

        Returns 204 No Content on success -- no response body to parse.
        The emoji parameter must be URL-encoded if it contains special characters.
        """
        channel_id = arguments["channel_id"]
        message_id = arguments["message_id"]
        emoji = arguments["emoji"]

        await self._make_authenticated_request(
            "PUT",
            f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me",
            oauth_cred,
        )
        return json.dumps(
            {"success": True, "message": "Reaction added successfully"}, indent=2
        )

    async def _list_roles(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /guilds/{guild_id}/roles -- list guild roles."""
        guild_id = arguments["guild_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{DISCORD_API_BASE}/guilds/{guild_id}/roles",
            oauth_cred,
        )
        return json.dumps(response.json(), indent=2)

    async def _get_user(
        self, arguments: Dict[str, Any], oauth_cred: OAuthCredential
    ) -> str:
        """GET /users/@me -- get current authenticated user info."""
        response = await self._make_authenticated_request(
            "GET", f"{DISCORD_API_BASE}/users/@me", oauth_cred
        )
        return json.dumps(response.json(), indent=2)
