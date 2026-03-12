"""Zoom connector implementation for accessing Zoom API."""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx
from mcp import types
from mcp.types import ToolAnnotations

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


@register_connector(ConnectorType.ZOOM)
class ZoomConnector(BaseConnector):
    """Zoom connector for accessing meetings, webinars, and recordings."""

    ZOOM_API_BASE = "https://api.zoom.us/v2"

    @property
    def display_name(self) -> str:
        """Return display name for the connector."""
        return "Zoom"

    @property
    def description(self) -> str:
        """Return description of the connector."""
        return "Access and manage Zoom meetings, webinars, users, and recordings"

    @property
    def requires_oauth(self) -> bool:
        """Return whether this connector requires OAuth."""
        return True

    async def _make_authenticated_request(
        self,
        method: str,
        url: str,
        oauth_cred: OAuthCredential,
        **kwargs
    ) -> httpx.Response:
        """Make an authenticated request to Zoom API.

        Uses shared HTTP client with connection pooling for better performance.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            url: Full URL to request
            oauth_cred: OAuth credential with access token
            **kwargs: Additional arguments to pass to httpx request

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPStatusError: If request fails
        """
        from .http_client import get_http_client

        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {oauth_cred.access_token}"
        headers["Content-Type"] = "application/json"
        kwargs["headers"] = headers

        # Use shared client with connection pooling
        client = get_http_client()
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    async def get_tools(
        self,
        connector: Connector,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Tool]:
        """Get available Zoom tools.

        Args:
            connector: The connector configuration
            oauth_cred: OAuth credential (optional)

        Returns:
            List of available tools
        """
        tools = [
            types.Tool(
                name="zoom_list_meetings",
                description="List all scheduled meetings for the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Meeting type filter",
                            "enum": ["scheduled", "live", "upcoming"],
                            "default": "upcoming"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of meetings to return (max 300)",
                            "minimum": 1,
                            "maximum": 300,
                            "default": 30
                        }
                    }
                },
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, riskLevel="low"),
            ),
            types.Tool(
                name="zoom_get_meeting",
                description="Get details of a specific meeting by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "The meeting ID or UUID"
                        }
                    },
                    "required": ["meeting_id"]
                },
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, riskLevel="low"),
            ),
            types.Tool(
                name="zoom_create_meeting",
                description="Create a new scheduled meeting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Meeting topic/title"
                        },
                        "type": {
                            "type": "integer",
                            "description": "Meeting type: 1=Instant, 2=Scheduled, 3=Recurring with no fixed time, 8=Recurring with fixed time",
                            "enum": [1, 2, 3, 8],
                            "default": 2
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Meeting start time in ISO 8601 format (YYYY-MM-DDTHH:mm:ss)"
                        },
                        "duration": {
                            "type": "integer",
                            "description": "Meeting duration in minutes",
                            "default": 60
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone (e.g., America/New_York)",
                            "default": "UTC"
                        },
                        "agenda": {
                            "type": "string",
                            "description": "Meeting agenda/description"
                        }
                    },
                    "required": ["topic"]
                },
                annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True, riskLevel="medium"),
            ),
            types.Tool(
                name="zoom_update_meeting",
                description="Update an existing meeting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "The meeting ID to update"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Updated meeting topic/title"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Updated start time in ISO 8601 format"
                        },
                        "duration": {
                            "type": "integer",
                            "description": "Updated duration in minutes"
                        },
                        "agenda": {
                            "type": "string",
                            "description": "Updated meeting agenda"
                        }
                    },
                    "required": ["meeting_id"]
                },
                annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True, riskLevel="high"),
            ),
            types.Tool(
                name="zoom_delete_meeting",
                description="Delete a scheduled meeting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "The meeting ID to delete"
                        }
                    },
                    "required": ["meeting_id"]
                },
                annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True, riskLevel="critical"),
            ),
            types.Tool(
                name="zoom_get_user",
                description="Get user profile information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID or email address (use 'me' for authenticated user)",
                            "default": "me"
                        }
                    }
                },
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, riskLevel="low"),
            ),
            types.Tool(
                name="zoom_list_recordings",
                description="List cloud recordings for the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "from_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format (default: 30 days ago)"
                        },
                        "to_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format (default: today)"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of recordings to return (max 300)",
                            "minimum": 1,
                            "maximum": 300,
                            "default": 30
                        }
                    }
                },
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, riskLevel="low"),
            ),
            types.Tool(
                name="zoom_get_meeting_recordings",
                description="Get all recordings for a specific meeting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "The meeting ID or UUID"
                        }
                    },
                    "required": ["meeting_id"]
                },
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, riskLevel="low"),
            ),
            types.Tool(
                name="zoom_list_webinars",
                description="List all webinars for the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {
                            "type": "integer",
                            "description": "Number of webinars to return (max 300)",
                            "minimum": 1,
                            "maximum": 300,
                            "default": 30
                        }
                    }
                },
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, riskLevel="low"),
            ),
            types.Tool(
                name="zoom_get_webinar",
                description="Get details of a specific webinar by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "webinar_id": {
                            "type": "string",
                            "description": "The webinar ID"
                        }
                    },
                    "required": ["webinar_id"]
                },
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, riskLevel="low"),
            ),
            types.Tool(
                name="zoom_list_meeting_participants",
                description="Get participants for a past meeting instance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "The meeting ID or UUID"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of participants to return (max 300)",
                            "minimum": 1,
                            "maximum": 300,
                            "default": 30
                        }
                    },
                    "required": ["meeting_id"]
                },
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, riskLevel="low"),
            ),
            types.Tool(
                name="zoom_get_meeting_invitation",
                description="Get the meeting invitation text/HTML",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "The meeting ID"
                        }
                    },
                    "required": ["meeting_id"]
                },
                annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, riskLevel="low"),
            )
        ]
        return tools

    async def get_resources(
        self,
        connector: Connector,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Resource]:
        """Get available Zoom resources.

        Args:
            connector: The connector configuration
            oauth_cred: OAuth credential (optional)

        Returns:
            List of available resources
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        try:
            # List upcoming meetings
            response = await self._make_authenticated_request(
                "GET",
                f"{self.ZOOM_API_BASE}/users/me/meetings",
                oauth_cred,
                params={"type": "upcoming", "page_size": 50}
            )
            meetings = response.json().get("meetings", [])

            resources = []
            for meeting in meetings:
                resources.append(types.Resource(
                    uri=f"zoom://meeting/{meeting['id']}",
                    name=meeting.get("topic", "Untitled Meeting"),
                    description=f"Zoom Meeting - {meeting.get('start_time', 'No start time')}",
                    mimeType="application/vnd.zoom.meeting"
                ))

            return resources
        except Exception:
            return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Zoom tool.

        Args:
            connector: The connector configuration
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            oauth_cred: OAuth credential (optional)

        Returns:
            JSON string result
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return json.dumps({"error": "Invalid or expired OAuth credentials"})

        try:
            if tool_name == "list_meetings":
                return await self._list_meetings(arguments, oauth_cred)
            elif tool_name == "get_meeting":
                return await self._get_meeting(arguments, oauth_cred)
            elif tool_name == "create_meeting":
                return await self._create_meeting(arguments, oauth_cred)
            elif tool_name == "update_meeting":
                return await self._update_meeting(arguments, oauth_cred)
            elif tool_name == "delete_meeting":
                return await self._delete_meeting(arguments, oauth_cred)
            elif tool_name == "get_user":
                return await self._get_user(arguments, oauth_cred)
            elif tool_name == "list_recordings":
                return await self._list_recordings(arguments, oauth_cred)
            elif tool_name == "get_meeting_recordings":
                return await self._get_meeting_recordings(arguments, oauth_cred)
            elif tool_name == "list_webinars":
                return await self._list_webinars(arguments, oauth_cred)
            elif tool_name == "get_webinar":
                return await self._get_webinar(arguments, oauth_cred)
            elif tool_name == "list_meeting_participants":
                return await self._list_meeting_participants(arguments, oauth_cred)
            elif tool_name == "get_meeting_invitation":
                return await self._get_meeting_invitation(arguments, oauth_cred)
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})

        except httpx.HTTPStatusError as e:
            return json.dumps({
                "error": f"HTTP error: {e.response.status_code}",
                "message": e.response.text
            })
        except Exception as e:
            return json.dumps({"error": f"Error executing tool '{tool_name}': {str(e)}"})

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Zoom resource.

        Args:
            connector: The connector configuration
            resource_path: Resource path (format: {type}/{id})
            oauth_cred: OAuth credential (optional)

        Returns:
            Resource content as string
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired OAuth credentials"

        try:
            parts = resource_path.split("/", 1)
            if len(parts) != 2:
                return "Error: Invalid resource path format. Expected: {type}/{id}"

            resource_type, resource_id = parts

            if resource_type == "meeting":
                response = await self._make_authenticated_request(
                    "GET",
                    f"{self.ZOOM_API_BASE}/meetings/{resource_id}",
                    oauth_cred
                )
                meeting_data = response.json()

                return f"""Meeting: {meeting_data.get('topic', 'Untitled')}
ID: {meeting_data.get('id')}
Start Time: {meeting_data.get('start_time', 'Not scheduled')}
Duration: {meeting_data.get('duration', 'N/A')} minutes
Join URL: {meeting_data.get('join_url', 'N/A')}
Agenda: {meeting_data.get('agenda', 'No agenda')}
"""
            else:
                return f"Error: Unknown resource type: {resource_type}"

        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error reading resource: {str(e)}"

    # Tool implementation methods

    async def _list_meetings(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """List meetings for the authenticated user."""
        meeting_type = arguments.get("type", "upcoming")
        page_size = arguments.get("page_size", 30)

        response = await self._make_authenticated_request(
            "GET",
            f"{self.ZOOM_API_BASE}/users/me/meetings",
            oauth_cred,
            params={"type": meeting_type, "page_size": page_size}
        )

        data = response.json()
        meetings = data.get("meetings", [])

        result = []
        for meeting in meetings:
            result.append({
                "id": meeting.get("id"),
                "topic": meeting.get("topic"),
                "type": meeting.get("type"),
                "start_time": meeting.get("start_time"),
                "duration": meeting.get("duration"),
                "timezone": meeting.get("timezone"),
                "join_url": meeting.get("join_url"),
                "agenda": meeting.get("agenda")
            })

        return json.dumps({
            "meetings": result,
            "count": len(result),
            "total_records": data.get("total_records", len(result))
        }, indent=2)

    async def _get_meeting(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Get a specific meeting by ID."""
        meeting_id = arguments["meeting_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{self.ZOOM_API_BASE}/meetings/{meeting_id}",
            oauth_cred
        )

        meeting_data = response.json()

        return json.dumps({
            "id": meeting_data.get("id"),
            "uuid": meeting_data.get("uuid"),
            "host_id": meeting_data.get("host_id"),
            "topic": meeting_data.get("topic"),
            "type": meeting_data.get("type"),
            "status": meeting_data.get("status"),
            "start_time": meeting_data.get("start_time"),
            "duration": meeting_data.get("duration"),
            "timezone": meeting_data.get("timezone"),
            "agenda": meeting_data.get("agenda"),
            "created_at": meeting_data.get("created_at"),
            "join_url": meeting_data.get("join_url"),
            "password": meeting_data.get("password"),
            "settings": meeting_data.get("settings", {})
        }, indent=2)

    async def _create_meeting(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Create a new meeting."""
        meeting_data: Dict[str, Any] = {
            "topic": arguments["topic"],
            "type": arguments.get("type", 2),
            "duration": arguments.get("duration", 60),
            "timezone": arguments.get("timezone", "UTC")
        }

        if "start_time" in arguments:
            meeting_data["start_time"] = arguments["start_time"]

        if "agenda" in arguments:
            meeting_data["agenda"] = arguments["agenda"]

        response = await self._make_authenticated_request(
            "POST",
            f"{self.ZOOM_API_BASE}/users/me/meetings",
            oauth_cred,
            json=meeting_data
        )

        result = response.json()

        return json.dumps({
            "id": result.get("id"),
            "uuid": result.get("uuid"),
            "host_id": result.get("host_id"),
            "topic": result.get("topic"),
            "type": result.get("type"),
            "start_time": result.get("start_time"),
            "duration": result.get("duration"),
            "timezone": result.get("timezone"),
            "join_url": result.get("join_url"),
            "password": result.get("password"),
            "created_at": result.get("created_at")
        }, indent=2)

    async def _update_meeting(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Update an existing meeting."""
        meeting_id = arguments["meeting_id"]

        update_data: Dict[str, Any] = {}
        if "topic" in arguments:
            update_data["topic"] = arguments["topic"]
        if "start_time" in arguments:
            update_data["start_time"] = arguments["start_time"]
        if "duration" in arguments:
            update_data["duration"] = arguments["duration"]
        if "agenda" in arguments:
            update_data["agenda"] = arguments["agenda"]

        await self._make_authenticated_request(
            "PATCH",
            f"{self.ZOOM_API_BASE}/meetings/{meeting_id}",
            oauth_cred,
            json=update_data
        )

        return json.dumps({
            "status": "success",
            "message": f"Meeting {meeting_id} updated successfully"
        }, indent=2)

    async def _delete_meeting(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Delete a meeting."""
        meeting_id = arguments["meeting_id"]

        await self._make_authenticated_request(
            "DELETE",
            f"{self.ZOOM_API_BASE}/meetings/{meeting_id}",
            oauth_cred
        )

        return json.dumps({
            "status": "success",
            "message": f"Meeting {meeting_id} deleted successfully"
        }, indent=2)

    async def _get_user(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Get user information."""
        user_id = arguments.get("user_id", "me")

        response = await self._make_authenticated_request(
            "GET",
            f"{self.ZOOM_API_BASE}/users/{user_id}",
            oauth_cred
        )

        user_data = response.json()

        return json.dumps({
            "id": user_data.get("id"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "email": user_data.get("email"),
            "type": user_data.get("type"),
            "pmi": user_data.get("pmi"),
            "timezone": user_data.get("timezone"),
            "verified": user_data.get("verified"),
            "created_at": user_data.get("created_at"),
            "last_login_time": user_data.get("last_login_time"),
            "pic_url": user_data.get("pic_url"),
            "account_id": user_data.get("account_id")
        }, indent=2)

    async def _list_recordings(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """List cloud recordings."""
        # Default to last 30 days if not specified
        to_date = arguments.get("to_date", datetime.now().strftime("%Y-%m-%d"))
        from_date = arguments.get(
            "from_date",
            (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        )
        page_size = arguments.get("page_size", 30)

        response = await self._make_authenticated_request(
            "GET",
            f"{self.ZOOM_API_BASE}/users/me/recordings",
            oauth_cred,
            params={
                "from": from_date,
                "to": to_date,
                "page_size": page_size
            }
        )

        data = response.json()
        meetings = data.get("meetings", [])

        result = []
        for meeting in meetings:
            recording_files = meeting.get("recording_files", [])
            result.append({
                "meeting_id": meeting.get("id"),
                "uuid": meeting.get("uuid"),
                "topic": meeting.get("topic"),
                "start_time": meeting.get("start_time"),
                "duration": meeting.get("duration"),
                "total_size": meeting.get("total_size"),
                "recording_count": meeting.get("recording_count"),
                "recording_files": [
                    {
                        "id": f.get("id"),
                        "file_type": f.get("file_type"),
                        "file_size": f.get("file_size"),
                        "download_url": f.get("download_url"),
                        "play_url": f.get("play_url")
                    }
                    for f in recording_files
                ]
            })

        return json.dumps({
            "recordings": result,
            "count": len(result),
            "from": from_date,
            "to": to_date
        }, indent=2)

    async def _get_meeting_recordings(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Get recordings for a specific meeting."""
        meeting_id = arguments["meeting_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{self.ZOOM_API_BASE}/meetings/{meeting_id}/recordings",
            oauth_cred
        )

        data = response.json()

        recording_files = data.get("recording_files", [])
        result = {
            "uuid": data.get("uuid"),
            "id": data.get("id"),
            "account_id": data.get("account_id"),
            "host_id": data.get("host_id"),
            "topic": data.get("topic"),
            "start_time": data.get("start_time"),
            "duration": data.get("duration"),
            "total_size": data.get("total_size"),
            "recording_count": data.get("recording_count"),
            "recording_files": [
                {
                    "id": f.get("id"),
                    "meeting_id": f.get("meeting_id"),
                    "recording_start": f.get("recording_start"),
                    "recording_end": f.get("recording_end"),
                    "file_type": f.get("file_type"),
                    "file_size": f.get("file_size"),
                    "download_url": f.get("download_url"),
                    "play_url": f.get("play_url"),
                    "status": f.get("status")
                }
                for f in recording_files
            ]
        }

        return json.dumps(result, indent=2)

    async def _list_webinars(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """List webinars for the authenticated user."""
        page_size = arguments.get("page_size", 30)

        response = await self._make_authenticated_request(
            "GET",
            f"{self.ZOOM_API_BASE}/users/me/webinars",
            oauth_cred,
            params={"page_size": page_size}
        )

        data = response.json()
        webinars = data.get("webinars", [])

        result = []
        for webinar in webinars:
            result.append({
                "id": webinar.get("id"),
                "uuid": webinar.get("uuid"),
                "topic": webinar.get("topic"),
                "type": webinar.get("type"),
                "start_time": webinar.get("start_time"),
                "duration": webinar.get("duration"),
                "timezone": webinar.get("timezone"),
                "join_url": webinar.get("join_url"),
                "agenda": webinar.get("agenda")
            })

        return json.dumps({
            "webinars": result,
            "count": len(result),
            "total_records": data.get("total_records", len(result))
        }, indent=2)

    async def _get_webinar(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Get a specific webinar by ID."""
        webinar_id = arguments["webinar_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{self.ZOOM_API_BASE}/webinars/{webinar_id}",
            oauth_cred
        )

        webinar_data = response.json()

        return json.dumps({
            "id": webinar_data.get("id"),
            "uuid": webinar_data.get("uuid"),
            "host_id": webinar_data.get("host_id"),
            "topic": webinar_data.get("topic"),
            "type": webinar_data.get("type"),
            "start_time": webinar_data.get("start_time"),
            "duration": webinar_data.get("duration"),
            "timezone": webinar_data.get("timezone"),
            "agenda": webinar_data.get("agenda"),
            "created_at": webinar_data.get("created_at"),
            "join_url": webinar_data.get("join_url"),
            "settings": webinar_data.get("settings", {})
        }, indent=2)

    async def _list_meeting_participants(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """List participants for a past meeting."""
        meeting_id = arguments["meeting_id"]
        page_size = arguments.get("page_size", 30)

        response = await self._make_authenticated_request(
            "GET",
            f"{self.ZOOM_API_BASE}/past_meetings/{meeting_id}/participants",
            oauth_cred,
            params={"page_size": page_size}
        )

        data = response.json()
        participants = data.get("participants", [])

        result = []
        for participant in participants:
            result.append({
                "id": participant.get("id"),
                "user_id": participant.get("user_id"),
                "name": participant.get("name"),
                "user_email": participant.get("user_email"),
                "join_time": participant.get("join_time"),
                "leave_time": participant.get("leave_time"),
                "duration": participant.get("duration"),
                "status": participant.get("status")
            })

        return json.dumps({
            "participants": result,
            "count": len(result),
            "total_records": data.get("total_records", len(result))
        }, indent=2)

    async def _get_meeting_invitation(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Get meeting invitation text."""
        meeting_id = arguments["meeting_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{self.ZOOM_API_BASE}/meetings/{meeting_id}/invitation",
            oauth_cred
        )

        data = response.json()

        return json.dumps({
            "invitation": data.get("invitation", "")
        }, indent=2)
