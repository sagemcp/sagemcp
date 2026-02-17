"""Slack connector implementation."""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


@register_connector(ConnectorType.SLACK)
class SlackConnector(BaseConnector):
    """Slack connector for accessing Slack API."""

    @property
    def display_name(self) -> str:
        return "Slack"

    @property
    def description(self) -> str:
        return "Access Slack channels, messages, users, and more"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Slack tools."""
        tools = [
            types.Tool(
                name="slack_conversations_history",
                description="Get messages from a channel or direct message by channel_id",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel ID to fetch history from"
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                            "default": 20,
                            "description": "Number of messages to return"
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor for next page of results"
                        },
                        "oldest": {
                            "type": "string",
                            "description": "Start of time range (Unix timestamp)"
                        },
                        "latest": {
                            "type": "string",
                            "description": "End of time range (Unix timestamp)"
                        },
                        "include_all_metadata": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include all metadata in messages"
                        }
                    },
                    "required": ["channel_id"]
                }
            ),
            types.Tool(
                name="slack_conversations_replies",
                description="Get a thread of messages posted to a conversation by channel_id and thread_ts",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel ID containing the thread"
                        },
                        "thread_ts": {
                            "type": "string",
                            "description": "Timestamp of the parent message"
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                            "default": 20,
                            "description": "Number of messages to return"
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor for next page of results"
                        },
                        "oldest": {
                            "type": "string",
                            "description": "Start of time range (Unix timestamp)"
                        },
                        "latest": {
                            "type": "string",
                            "description": "End of time range (Unix timestamp)"
                        }
                    },
                    "required": ["channel_id", "thread_ts"]
                }
            ),
            types.Tool(
                name="slack_conversations_add_message",
                description="Post a message to a channel, private channel, or direct message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel ID to post message to"
                        },
                        "text": {
                            "type": "string",
                            "description": "Message text content"
                        },
                        "thread_ts": {
                            "type": "string",
                            "description": "Thread timestamp to reply to"
                        },
                        "blocks": {
                            "type": "array",
                            "description": "Structured blocks for rich formatting",
                            "items": {
                                "type": "object"
                            }
                        },
                        "attachments": {
                            "type": "array",
                            "description": "Message attachments",
                            "items": {
                                "type": "object"
                            }
                        }
                    },
                    "required": ["channel_id", "text"]
                }
            ),
            types.Tool(
                name="slack_conversations_search_messages",
                description="Search messages in channels, threads, and DMs using various filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string"
                        },
                        "count": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results to return per page"
                        },
                        "page": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1,
                            "description": "Page number of results"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["score", "timestamp"],
                            "default": "score",
                            "description": "Sort order"
                        },
                        "sort_dir": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "default": "desc",
                            "description": "Sort direction"
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="slack_conversations_list",
                description="List channels available in the workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "types": {
                            "type": "string",
                            "default": "public_channel",
                            "description": "Comma-separated list of channel types: public_channel, private_channel, mpim, im"
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                            "default": 20,
                            "description": "Number of channels to return"
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor for next page of results"
                        },
                        "exclude_archived": {
                            "type": "boolean",
                            "default": False,
                            "description": "Exclude archived channels"
                        }
                    }
                }
            ),
            types.Tool(
                name="slack_conversations_info",
                description="Get information about a specific channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel ID to get information about"
                        },
                        "include_locale": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include locale information"
                        },
                        "include_num_members": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include number of members"
                        }
                    },
                    "required": ["channel_id"]
                }
            ),
            types.Tool(
                name="slack_users_list",
                description="List all users in the workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000,
                            "default": 20,
                            "description": "Number of users to return"
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor for next page of results"
                        },
                        "include_locale": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include locale information"
                        }
                    }
                }
            ),
            types.Tool(
                name="slack_users_info",
                description="Get information about a specific user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID to get information about"
                        },
                        "include_locale": {
                            "type": "boolean",
                            "default": False,
                            "description": "Include locale information"
                        }
                    },
                    "required": ["user_id"]
                }
            ),
            types.Tool(
                name="slack_users_lookup_by_email",
                description="Look up a Slack user by their email address. Requires the users:read.email scope.",
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
                name="slack_reactions_add",
                description="Add an emoji reaction to a message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel ID containing the message"
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Message timestamp"
                        },
                        "name": {
                            "type": "string",
                            "description": "Emoji name (without colons)"
                        }
                    },
                    "required": ["channel_id", "timestamp", "name"]
                }
            ),
            types.Tool(
                name="slack_reactions_remove",
                description="Remove an emoji reaction from a message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Channel ID containing the message"
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Message timestamp"
                        },
                        "name": {
                            "type": "string",
                            "description": "Emoji name (without colons)"
                        }
                    },
                    "required": ["channel_id", "timestamp", "name"]
                }
            ),
            types.Tool(
                name="slack_auth_test",
                description="Check authentication and get workspace/user information",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            )
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Slack resources."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        # Get workspace info and channels to create resource URIs
        try:
            # Get workspace info
            auth_response = await self._make_authenticated_request(
                "POST",
                "https://slack.com/api/auth.test",
                oauth_cred
            )
            auth_data = auth_response.json()

            if not auth_data.get("ok"):
                print(f"Error getting Slack auth info: {auth_data.get('error')}")
                return []

            workspace_id = auth_data.get("team_id")
            workspace_name = auth_data.get("team")

            # Get channels
            channels_response = await self._make_authenticated_request(
                "POST",
                "https://slack.com/api/conversations.list",
                oauth_cred,
                json={"limit": 100, "types": "public_channel,private_channel"}
            )
            channels_data = channels_response.json()

            resources = []

            # Add workspace resource
            resources.append(types.Resource(
                uri=f"slack://{workspace_id}",
                name=f"Slack Workspace: {workspace_name}",
                description=f"Slack workspace {workspace_name}"
            ))

            # Add channel resources
            if channels_data.get("ok") and channels_data.get("channels"):
                for channel in channels_data["channels"]:
                    channel_id = channel["id"]
                    channel_name = channel["name"]
                    is_private = channel.get("is_private", False)
                    channel_type = "private" if is_private else "public"

                    resources.append(types.Resource(
                        uri=f"slack://{workspace_id}/channel/{channel_id}",
                        name=f"#{channel_name}",
                        description=f"{channel_type.capitalize()} channel: {channel.get('purpose', {}).get('value', 'No description')}"
                    ))

            return resources

        except Exception as e:
            print(f"Error fetching Slack resources: {e}")
            return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Slack tool."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Slack credentials"

        try:
            if tool_name == "conversations_history":
                return await self._conversations_history(arguments, oauth_cred)
            elif tool_name == "conversations_replies":
                return await self._conversations_replies(arguments, oauth_cred)
            elif tool_name == "conversations_add_message":
                return await self._conversations_add_message(arguments, oauth_cred)
            elif tool_name == "conversations_search_messages":
                return await self._conversations_search_messages(arguments, oauth_cred)
            elif tool_name == "conversations_list":
                return await self._conversations_list(arguments, oauth_cred)
            elif tool_name == "conversations_info":
                return await self._conversations_info(arguments, oauth_cred)
            elif tool_name == "users_list":
                return await self._users_list(arguments, oauth_cred)
            elif tool_name == "users_info":
                return await self._users_info(arguments, oauth_cred)
            elif tool_name == "users_lookup_by_email":
                return await self._users_lookup_by_email(arguments, oauth_cred)
            elif tool_name == "reactions_add":
                return await self._reactions_add(arguments, oauth_cred)
            elif tool_name == "reactions_remove":
                return await self._reactions_remove(arguments, oauth_cred)
            elif tool_name == "auth_test":
                return await self._auth_test(oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Slack tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Slack resource."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Slack credentials"

        try:
            # Parse resource path: workspace_id or workspace_id/channel/channel_id
            parts = resource_path.split("/")

            if len(parts) == 1:
                # Workspace info
                workspace_id = parts[0]
                response = await self._make_authenticated_request(
                    "POST",
                    "https://slack.com/api/team.info",
                    oauth_cred,
                    json={"team": workspace_id}
                )
                data = response.json()
                if data.get("ok"):
                    return json.dumps(data["team"], indent=2)
                else:
                    return f"Error: {data.get('error')}"

            elif len(parts) == 3 and parts[1] == "channel":
                # Channel messages
                channel_id = parts[2]
                response = await self._make_authenticated_request(
                    "POST",
                    "https://slack.com/api/conversations.history",
                    oauth_cred,
                    json={"channel": channel_id, "limit": 50}
                )
                data = response.json()
                if data.get("ok"):
                    messages = data.get("messages", [])
                    result = {
                        "channel_id": channel_id,
                        "message_count": len(messages),
                        "messages": messages
                    }
                    return json.dumps(result, indent=2)
                else:
                    return f"Error: {data.get('error')}"
            else:
                return "Error: Invalid resource path"

        except Exception as e:
            return f"Error reading Slack resource: {str(e)}"

    async def _conversations_history(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get conversation history."""
        payload = {
            "channel": arguments["channel_id"],
            "limit": arguments.get("limit", 20)
        }

        if "cursor" in arguments:
            payload["cursor"] = arguments["cursor"]
        if "oldest" in arguments:
            payload["oldest"] = arguments["oldest"]
        if "latest" in arguments:
            payload["latest"] = arguments["latest"]
        if arguments.get("include_all_metadata"):
            payload["include_all_metadata"] = True

        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/conversations.history",
            oauth_cred,
            json=payload
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps({
                "messages": data.get("messages", []),
                "has_more": data.get("has_more", False),
                "response_metadata": data.get("response_metadata", {})
            }, indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _conversations_replies(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get conversation thread replies."""
        payload = {
            "channel": arguments["channel_id"],
            "ts": arguments["thread_ts"],
            "limit": arguments.get("limit", 20)
        }

        if "cursor" in arguments:
            payload["cursor"] = arguments["cursor"]
        if "oldest" in arguments:
            payload["oldest"] = arguments["oldest"]
        if "latest" in arguments:
            payload["latest"] = arguments["latest"]

        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/conversations.replies",
            oauth_cred,
            json=payload
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps({
                "messages": data.get("messages", []),
                "has_more": data.get("has_more", False),
                "response_metadata": data.get("response_metadata", {})
            }, indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _conversations_add_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Post a message to a channel."""
        payload = {
            "channel": arguments["channel_id"],
            "text": arguments["text"]
        }

        if "thread_ts" in arguments:
            payload["thread_ts"] = arguments["thread_ts"]
        if "blocks" in arguments:
            payload["blocks"] = arguments["blocks"]
        if "attachments" in arguments:
            payload["attachments"] = arguments["attachments"]

        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/chat.postMessage",
            oauth_cred,
            json=payload
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps({
                "ts": data.get("ts"),
                "channel": data.get("channel"),
                "message": data.get("message", {})
            }, indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _conversations_search_messages(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search messages."""
        params = {
            "query": arguments["query"],
            "count": arguments.get("count", 20),
            "page": arguments.get("page", 1),
            "sort": arguments.get("sort", "score"),
            "sort_dir": arguments.get("sort_dir", "desc")
        }

        response = await self._make_authenticated_request(
            "GET",
            "https://slack.com/api/search.messages",
            oauth_cred,
            params=params
        )

        data = response.json()
        if data.get("ok"):
            messages = data.get("messages", {})
            return json.dumps({
                "total": messages.get("total", 0),
                "matches": messages.get("matches", []),
                "paging": messages.get("paging", {})
            }, indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _conversations_list(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List conversations."""
        payload = {
            "limit": arguments.get("limit", 20),
            "types": arguments.get("types", "public_channel"),
            "exclude_archived": arguments.get("exclude_archived", False)
        }

        if "cursor" in arguments:
            payload["cursor"] = arguments["cursor"]

        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/conversations.list",
            oauth_cred,
            json=payload
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps({
                "channels": data.get("channels", []),
                "response_metadata": data.get("response_metadata", {})
            }, indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _conversations_info(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get conversation info."""
        payload = {
            "channel": arguments["channel_id"],
            "include_locale": arguments.get("include_locale", False),
            "include_num_members": arguments.get("include_num_members", False)
        }

        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/conversations.info",
            oauth_cred,
            json=payload
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps(data.get("channel", {}), indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _users_list(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List users."""
        payload = {
            "limit": arguments.get("limit", 20),
            "include_locale": arguments.get("include_locale", False)
        }

        if "cursor" in arguments:
            payload["cursor"] = arguments["cursor"]

        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/users.list",
            oauth_cred,
            json=payload
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps({
                "members": data.get("members", []),
                "response_metadata": data.get("response_metadata", {})
            }, indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _users_info(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get user info."""
        payload = {
            "user": arguments["user_id"],
            "include_locale": arguments.get("include_locale", False)
        }

        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/users.info",
            oauth_cred,
            json=payload
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps(data.get("user", {}), indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _users_lookup_by_email(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Look up a user by email address."""
        email = arguments["email"]

        response = await self._make_authenticated_request(
            "GET",
            "https://slack.com/api/users.lookupByEmail",
            oauth_cred,
            params={"email": email}
        )

        data = response.json()
        if data.get("ok"):
            user = data.get("user", {})
            profile = user.get("profile", {})
            return json.dumps({
                "id": user.get("id"),
                "name": user.get("name"),
                "real_name": user.get("real_name"),
                "display_name": profile.get("display_name"),
                "email": profile.get("email"),
                "title": profile.get("title")
            }, indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _reactions_add(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Add a reaction to a message."""
        payload = {
            "channel": arguments["channel_id"],
            "timestamp": arguments["timestamp"],
            "name": arguments["name"]
        }

        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/reactions.add",
            oauth_cred,
            json=payload
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps({"success": True, "message": "Reaction added"}, indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _reactions_remove(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Remove a reaction from a message."""
        payload = {
            "channel": arguments["channel_id"],
            "timestamp": arguments["timestamp"],
            "name": arguments["name"]
        }

        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/reactions.remove",
            oauth_cred,
            json=payload
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps({"success": True, "message": "Reaction removed"}, indent=2)
        else:
            return f"Error: {data.get('error')}"

    async def _auth_test(self, oauth_cred: OAuthCredential) -> str:
        """Test authentication and get workspace info."""
        response = await self._make_authenticated_request(
            "POST",
            "https://slack.com/api/auth.test",
            oauth_cred
        )

        data = response.json()
        if data.get("ok"):
            return json.dumps({
                "url": data.get("url"),
                "team": data.get("team"),
                "user": data.get("user"),
                "team_id": data.get("team_id"),
                "user_id": data.get("user_id"),
                "bot_id": data.get("bot_id")
            }, indent=2)
        else:
            return f"Error: {data.get('error')}"
