"""Microsoft Teams connector implementation."""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


@register_connector(ConnectorType.TEAMS)
class TeamsConnector(BaseConnector):
    """Microsoft Teams connector for managing teams, channels, chats, and messages."""

    @property
    def display_name(self) -> str:
        return "Microsoft Teams"

    @property
    def description(self) -> str:
        return "Manage Microsoft Teams teams, channels, chats, and messages"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Microsoft Teams tools."""
        tools = [
            types.Tool(
                name="teams_list_teams",
                description="List teams the authenticated user is a member of",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of properties to select (e.g., 'id,displayName,description')"
                        }
                    }
                }
            ),
            types.Tool(
                name="teams_get_team",
                description="Get details of a specific team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team"
                        }
                    },
                    "required": ["team_id"]
                }
            ),
            types.Tool(
                name="teams_list_channels",
                description="List channels in a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team"
                        },
                        "filter": {
                            "type": "string",
                            "description": "OData $filter expression to filter channels (e.g., \"membershipType eq 'standard'\")"
                        }
                    },
                    "required": ["team_id"]
                }
            ),
            types.Tool(
                name="teams_get_channel",
                description="Get details of a specific channel in a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team"
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "The ID of the channel"
                        }
                    },
                    "required": ["team_id", "channel_id"]
                }
            ),
            types.Tool(
                name="teams_list_channel_messages",
                description="List messages in a channel. Returns the most recent messages.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team"
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "The ID of the channel"
                        },
                        "top": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 25,
                            "description": "Number of messages to return"
                        }
                    },
                    "required": ["team_id", "channel_id"]
                }
            ),
            types.Tool(
                name="teams_get_channel_message",
                description="Get a specific message in a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team"
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "The ID of the channel"
                        },
                        "message_id": {
                            "type": "string",
                            "description": "The ID of the message"
                        }
                    },
                    "required": ["team_id", "channel_id", "message_id"]
                }
            ),
            types.Tool(
                name="teams_send_channel_message",
                description="Send a message to a channel in a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team"
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "The ID of the channel"
                        },
                        "content": {
                            "type": "string",
                            "description": "The message content"
                        },
                        "content_type": {
                            "type": "string",
                            "enum": ["text", "html"],
                            "default": "html",
                            "description": "The content type of the message body"
                        }
                    },
                    "required": ["team_id", "channel_id", "content"]
                }
            ),
            types.Tool(
                name="teams_reply_to_message",
                description="Reply to a specific message in a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team"
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "The ID of the channel"
                        },
                        "message_id": {
                            "type": "string",
                            "description": "The ID of the message to reply to"
                        },
                        "content": {
                            "type": "string",
                            "description": "The reply content"
                        },
                        "content_type": {
                            "type": "string",
                            "enum": ["text", "html"],
                            "default": "html",
                            "description": "The content type of the reply body"
                        }
                    },
                    "required": ["team_id", "channel_id", "message_id", "content"]
                }
            ),
            types.Tool(
                name="teams_list_chats",
                description="List chats the authenticated user is part of",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "top": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 25,
                            "description": "Number of chats to return"
                        },
                        "filter": {
                            "type": "string",
                            "description": "OData $filter expression to filter chats (e.g., \"chatType eq 'oneOnOne'\")"
                        }
                    }
                }
            ),
            types.Tool(
                name="teams_list_chat_messages",
                description="List messages in a chat",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_id": {
                            "type": "string",
                            "description": "The ID of the chat"
                        },
                        "top": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 25,
                            "description": "Number of messages to return"
                        }
                    },
                    "required": ["chat_id"]
                }
            ),
            types.Tool(
                name="teams_send_chat_message",
                description="Send a message in a chat",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_id": {
                            "type": "string",
                            "description": "The ID of the chat"
                        },
                        "content": {
                            "type": "string",
                            "description": "The message content"
                        },
                        "content_type": {
                            "type": "string",
                            "enum": ["text", "html"],
                            "default": "html",
                            "description": "The content type of the message body"
                        }
                    },
                    "required": ["chat_id", "content"]
                }
            ),
            types.Tool(
                name="teams_list_team_members",
                description="List members of a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team"
                        }
                    },
                    "required": ["team_id"]
                }
            ),
            types.Tool(
                name="teams_search_messages",
                description="Search across messages in the user's chats. Uses the Microsoft Graph /me/chats/getAllMessages endpoint with $search.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query string"
                        },
                        "top": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 25,
                            "description": "Number of results to return"
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="teams_get_user_by_email",
                description="Look up a Microsoft 365 user by email address using Microsoft Graph",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email address to look up"
                        }
                    },
                    "required": ["email"]
                }
            ),
            types.Tool(
                name="teams_list_channel_members",
                description="List members of a specific channel in a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team"
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "The ID of the channel"
                        }
                    },
                    "required": ["team_id", "channel_id"]
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Microsoft Teams resources.

        Returns an empty list; Teams resources are accessed dynamically via tools.
        """
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Microsoft Teams tool.

        Args:
            connector: The connector configuration.
            tool_name: Tool name WITHOUT the 'teams_' prefix.
            arguments: Tool arguments from the client.
            oauth_cred: OAuth credential for API authentication.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Microsoft OAuth credentials"

        try:
            if tool_name == "list_teams":
                return await self._list_teams(arguments, oauth_cred)
            elif tool_name == "get_team":
                return await self._get_team(arguments, oauth_cred)
            elif tool_name == "list_channels":
                return await self._list_channels(arguments, oauth_cred)
            elif tool_name == "get_channel":
                return await self._get_channel(arguments, oauth_cred)
            elif tool_name == "list_channel_messages":
                return await self._list_channel_messages(arguments, oauth_cred)
            elif tool_name == "get_channel_message":
                return await self._get_channel_message(arguments, oauth_cred)
            elif tool_name == "send_channel_message":
                return await self._send_channel_message(arguments, oauth_cred)
            elif tool_name == "reply_to_message":
                return await self._reply_to_message(arguments, oauth_cred)
            elif tool_name == "list_chats":
                return await self._list_chats(arguments, oauth_cred)
            elif tool_name == "list_chat_messages":
                return await self._list_chat_messages(arguments, oauth_cred)
            elif tool_name == "send_chat_message":
                return await self._send_chat_message(arguments, oauth_cred)
            elif tool_name == "list_team_members":
                return await self._list_team_members(arguments, oauth_cred)
            elif tool_name == "search_messages":
                return await self._search_messages(arguments, oauth_cred)
            elif tool_name == "list_channel_members":
                return await self._list_channel_members(arguments, oauth_cred)
            elif tool_name == "get_user_by_email":
                return await self._get_user_by_email(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Teams tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Microsoft Teams resource.

        Supports path format: team/{team_id}
        Returns team metadata and channel list.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Microsoft OAuth credentials"

        try:
            parts = resource_path.split("/", 1)
            if len(parts) != 2 or parts[0] != "team":
                return "Error: Invalid resource path. Expected format: team/{team_id}"

            team_id = parts[1]

            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/teams/{team_id}",
                oauth_cred
            )
            data = response.json()

            display_name = data.get("displayName", "Unknown")
            description = data.get("description", "")

            return f"Team: {display_name}\nDescription: {description}"

        except Exception as e:
            return f"Error reading Teams resource: {str(e)}"

    # ------------------------------------------------------------------ #
    # Tool implementation methods
    # ------------------------------------------------------------------ #

    async def _list_teams(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List teams the user is a member of via Microsoft Graph."""
        select = arguments.get("select")

        try:
            params: Dict[str, Any] = {}
            if select:
                params["$select"] = select

            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/me/joinedTeams",
                oauth_cred,
                params=params if params else None
            )
            data = response.json()

            teams = []
            for team in data.get("value", []):
                teams.append({
                    "id": team.get("id"),
                    "displayName": team.get("displayName"),
                    "description": team.get("description"),
                    "isArchived": team.get("isArchived"),
                    "visibility": team.get("visibility")
                })

            return json.dumps({"teams": teams, "count": len(teams)}, indent=2)

        except Exception as e:
            return f"Error listing teams: {str(e)}"

    async def _get_team(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get team details via Microsoft Graph."""
        team_id = arguments["team_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/teams/{team_id}",
                oauth_cred
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "displayName": data.get("displayName"),
                "description": data.get("description"),
                "isArchived": data.get("isArchived"),
                "visibility": data.get("visibility"),
                "webUrl": data.get("webUrl"),
                "createdDateTime": data.get("createdDateTime"),
                "memberSettings": data.get("memberSettings"),
                "messagingSettings": data.get("messagingSettings"),
                "funSettings": data.get("funSettings")
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting team: {str(e)}"

    async def _list_channels(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List channels in a team via Microsoft Graph."""
        team_id = arguments["team_id"]
        filter_expr = arguments.get("filter")

        try:
            params: Dict[str, Any] = {}
            if filter_expr:
                params["$filter"] = filter_expr

            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/teams/{team_id}/channels",
                oauth_cred,
                params=params if params else None
            )
            data = response.json()

            channels = []
            for channel in data.get("value", []):
                channels.append({
                    "id": channel.get("id"),
                    "displayName": channel.get("displayName"),
                    "description": channel.get("description"),
                    "membershipType": channel.get("membershipType"),
                    "webUrl": channel.get("webUrl"),
                    "createdDateTime": channel.get("createdDateTime")
                })

            return json.dumps({"channels": channels, "count": len(channels)}, indent=2)

        except Exception as e:
            return f"Error listing channels: {str(e)}"

    async def _get_channel(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get channel details via Microsoft Graph."""
        team_id = arguments["team_id"]
        channel_id = arguments["channel_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/teams/{team_id}/channels/{channel_id}",
                oauth_cred
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "displayName": data.get("displayName"),
                "description": data.get("description"),
                "membershipType": data.get("membershipType"),
                "webUrl": data.get("webUrl"),
                "email": data.get("email"),
                "createdDateTime": data.get("createdDateTime"),
                "isFavoriteByDefault": data.get("isFavoriteByDefault")
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting channel: {str(e)}"

    async def _list_channel_messages(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List messages in a channel via Microsoft Graph."""
        team_id = arguments["team_id"]
        channel_id = arguments["channel_id"]
        top = arguments.get("top", 25)

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/teams/{team_id}/channels/{channel_id}/messages",
                oauth_cred,
                params={"$top": top}
            )
            data = response.json()

            messages = []
            for msg in data.get("value", []):
                messages.append({
                    "id": msg.get("id"),
                    "createdDateTime": msg.get("createdDateTime"),
                    "lastModifiedDateTime": msg.get("lastModifiedDateTime"),
                    "subject": msg.get("subject"),
                    "body": {
                        "contentType": msg.get("body", {}).get("contentType"),
                        "content": msg.get("body", {}).get("content")
                    },
                    "from": {
                        "displayName": msg.get("from", {}).get("user", {}).get("displayName") if msg.get("from") else None
                    },
                    "importance": msg.get("importance"),
                    "messageType": msg.get("messageType")
                })

            return json.dumps({"messages": messages, "count": len(messages)}, indent=2)

        except Exception as e:
            return f"Error listing channel messages: {str(e)}"

    async def _get_channel_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get a specific channel message via Microsoft Graph."""
        team_id = arguments["team_id"]
        channel_id = arguments["channel_id"]
        message_id = arguments["message_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/teams/{team_id}/channels/{channel_id}/messages/{message_id}",
                oauth_cred
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "createdDateTime": data.get("createdDateTime"),
                "lastModifiedDateTime": data.get("lastModifiedDateTime"),
                "subject": data.get("subject"),
                "body": {
                    "contentType": data.get("body", {}).get("contentType"),
                    "content": data.get("body", {}).get("content")
                },
                "from": {
                    "displayName": data.get("from", {}).get("user", {}).get("displayName") if data.get("from") else None
                },
                "importance": data.get("importance"),
                "messageType": data.get("messageType"),
                "attachments": data.get("attachments", []),
                "reactions": data.get("reactions", [])
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting channel message: {str(e)}"

    async def _send_channel_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Send a message to a channel via Microsoft Graph."""
        team_id = arguments["team_id"]
        channel_id = arguments["channel_id"]
        content = arguments["content"]
        content_type = arguments.get("content_type", "html")

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{GRAPH_API_BASE}/teams/{team_id}/channels/{channel_id}/messages",
                oauth_cred,
                json={
                    "body": {
                        "contentType": content_type,
                        "content": content
                    }
                }
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "createdDateTime": data.get("createdDateTime"),
                "body": {
                    "contentType": data.get("body", {}).get("contentType"),
                    "content": data.get("body", {}).get("content")
                },
                "from": {
                    "displayName": data.get("from", {}).get("user", {}).get("displayName") if data.get("from") else None
                }
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error sending channel message: {str(e)}"

    async def _reply_to_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Reply to a channel message via Microsoft Graph."""
        team_id = arguments["team_id"]
        channel_id = arguments["channel_id"]
        message_id = arguments["message_id"]
        content = arguments["content"]
        content_type = arguments.get("content_type", "html")

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{GRAPH_API_BASE}/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies",
                oauth_cred,
                json={
                    "body": {
                        "contentType": content_type,
                        "content": content
                    }
                }
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "createdDateTime": data.get("createdDateTime"),
                "body": {
                    "contentType": data.get("body", {}).get("contentType"),
                    "content": data.get("body", {}).get("content")
                },
                "from": {
                    "displayName": data.get("from", {}).get("user", {}).get("displayName") if data.get("from") else None
                }
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error replying to message: {str(e)}"

    async def _list_chats(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List user's chats via Microsoft Graph."""
        top = arguments.get("top", 25)
        filter_expr = arguments.get("filter")

        try:
            params: Dict[str, Any] = {"$top": top}
            if filter_expr:
                params["$filter"] = filter_expr

            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/me/chats",
                oauth_cred,
                params=params
            )
            data = response.json()

            chats = []
            for chat in data.get("value", []):
                chats.append({
                    "id": chat.get("id"),
                    "topic": chat.get("topic"),
                    "chatType": chat.get("chatType"),
                    "createdDateTime": chat.get("createdDateTime"),
                    "lastUpdatedDateTime": chat.get("lastUpdatedDateTime"),
                    "webUrl": chat.get("webUrl")
                })

            return json.dumps({"chats": chats, "count": len(chats)}, indent=2)

        except Exception as e:
            return f"Error listing chats: {str(e)}"

    async def _list_chat_messages(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List messages in a chat via Microsoft Graph."""
        chat_id = arguments["chat_id"]
        top = arguments.get("top", 25)

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/me/chats/{chat_id}/messages",
                oauth_cred,
                params={"$top": top}
            )
            data = response.json()

            messages = []
            for msg in data.get("value", []):
                messages.append({
                    "id": msg.get("id"),
                    "createdDateTime": msg.get("createdDateTime"),
                    "lastModifiedDateTime": msg.get("lastModifiedDateTime"),
                    "body": {
                        "contentType": msg.get("body", {}).get("contentType"),
                        "content": msg.get("body", {}).get("content")
                    },
                    "from": {
                        "displayName": msg.get("from", {}).get("user", {}).get("displayName") if msg.get("from") else None
                    },
                    "messageType": msg.get("messageType")
                })

            return json.dumps({"messages": messages, "count": len(messages)}, indent=2)

        except Exception as e:
            return f"Error listing chat messages: {str(e)}"

    async def _send_chat_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Send a message in a chat via Microsoft Graph."""
        chat_id = arguments["chat_id"]
        content = arguments["content"]
        content_type = arguments.get("content_type", "html")

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{GRAPH_API_BASE}/me/chats/{chat_id}/messages",
                oauth_cred,
                json={
                    "body": {
                        "contentType": content_type,
                        "content": content
                    }
                }
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "createdDateTime": data.get("createdDateTime"),
                "body": {
                    "contentType": data.get("body", {}).get("contentType"),
                    "content": data.get("body", {}).get("content")
                },
                "from": {
                    "displayName": data.get("from", {}).get("user", {}).get("displayName") if data.get("from") else None
                }
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error sending chat message: {str(e)}"

    async def _list_team_members(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List members of a team via Microsoft Graph."""
        team_id = arguments["team_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/teams/{team_id}/members",
                oauth_cred
            )
            data = response.json()

            members = []
            for member in data.get("value", []):
                members.append({
                    "id": member.get("id"),
                    "displayName": member.get("displayName"),
                    "email": member.get("email"),
                    "roles": member.get("roles", []),
                    "userId": member.get("userId")
                })

            return json.dumps({"members": members, "count": len(members)}, indent=2)

        except Exception as e:
            return f"Error listing team members: {str(e)}"

    async def _search_messages(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search across messages in the user's chats via Microsoft Graph."""
        query = arguments["query"]
        top = arguments.get("top", 25)

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/me/chats/getAllMessages",
                oauth_cred,
                params={
                    "$search": f"\"{query}\"",
                    "$top": top
                }
            )
            data = response.json()

            messages = []
            for msg in data.get("value", []):
                messages.append({
                    "id": msg.get("id"),
                    "createdDateTime": msg.get("createdDateTime"),
                    "chatId": msg.get("chatId"),
                    "body": {
                        "contentType": msg.get("body", {}).get("contentType"),
                        "content": msg.get("body", {}).get("content")
                    },
                    "from": {
                        "displayName": msg.get("from", {}).get("user", {}).get("displayName") if msg.get("from") else None
                    },
                    "messageType": msg.get("messageType")
                })

            return json.dumps({"messages": messages, "count": len(messages)}, indent=2)

        except Exception as e:
            return f"Error searching messages: {str(e)}"

    async def _list_channel_members(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List members of a channel via Microsoft Graph."""
        team_id = arguments["team_id"]
        channel_id = arguments["channel_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/teams/{team_id}/channels/{channel_id}/members",
                oauth_cred
            )
            data = response.json()

            members = []
            for member in data.get("value", []):
                members.append({
                    "id": member.get("id"),
                    "displayName": member.get("displayName"),
                    "email": member.get("email"),
                    "roles": member.get("roles", []),
                    "userId": member.get("userId")
                })

            return json.dumps({"members": members, "count": len(members)}, indent=2)

        except Exception as e:
            return f"Error listing channel members: {str(e)}"

    async def _get_user_by_email(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Look up a Microsoft 365 user by email address via Microsoft Graph."""
        email = arguments["email"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/users",
                oauth_cred,
                params={
                    "$filter": f"mail eq '{email}' or userPrincipalName eq '{email}'",
                    "$select": "id,displayName,mail,userPrincipalName,jobTitle,department"
                }
            )
            data = response.json()

            users = []
            for user in data.get("value", []):
                users.append({
                    "id": user.get("id"),
                    "displayName": user.get("displayName"),
                    "mail": user.get("mail"),
                    "userPrincipalName": user.get("userPrincipalName"),
                    "jobTitle": user.get("jobTitle"),
                    "department": user.get("department")
                })

            return json.dumps({"users": users, "count": len(users)}, indent=2)

        except Exception as e:
            return f"Error looking up user by email: {str(e)}"
