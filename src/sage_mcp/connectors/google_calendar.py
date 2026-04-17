"""Google Calendar connector implementation."""

import json
from typing import Any, Dict, List, Optional

from mcp import types
from mcp.types import ToolAnnotations

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


@register_connector(ConnectorType.GOOGLE_CALENDAR)
class GoogleCalendarConnector(BaseConnector):
    """Google Calendar connector for managing calendar events."""

    @property
    def display_name(self) -> str:
        return "Google Calendar"

    @property
    def description(self) -> str:
        return "Access Google Calendar events, schedules, and free/busy information"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Google Calendar tools."""
        tools = [
            types.Tool(
                name="google_calendar_list_calendars",
                description="List all calendars in the user's calendar list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "maxResults": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 250,
                            "description": "Maximum number of calendars to return"
                        },
                        "pageToken": {
                            "type": "string",
                            "description": "Page token for retrieving the next page of results"
                        }
                    }
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                    riskLevel="low",
                ),
            ),
            types.Tool(
                name="google_calendar_get_calendar",
                description="Get metadata for a specific calendar",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar identifier (use 'primary' for the user's primary calendar)"
                        }
                    },
                    "required": ["calendar_id"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                    riskLevel="low",
                ),
            ),
            types.Tool(
                name="google_calendar_list_events",
                description="List events on a specified calendar. Supports filtering by time range and ordering.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar identifier (default: 'primary')"
                        },
                        "timeMin": {
                            "type": "string",
                            "description": "Lower bound (inclusive) for event start time as RFC3339 timestamp (e.g., '2025-01-01T00:00:00Z')"
                        },
                        "timeMax": {
                            "type": "string",
                            "description": "Upper bound (exclusive) for event end time as RFC3339 timestamp"
                        },
                        "maxResults": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 2500,
                            "default": 25,
                            "description": "Maximum number of events to return"
                        },
                        "pageToken": {
                            "type": "string",
                            "description": "Page token for retrieving the next page of results"
                        },
                        "singleEvents": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to expand recurring events into individual instances"
                        },
                        "orderBy": {
                            "type": "string",
                            "enum": ["startTime", "updated"],
                            "description": "Sort order (requires singleEvents=true for 'startTime')"
                        }
                    }
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                    riskLevel="low",
                ),
            ),
            types.Tool(
                name="google_calendar_get_event",
                description="Get details of a specific event",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar identifier (default: 'primary')"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event identifier"
                        }
                    },
                    "required": ["event_id"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                    riskLevel="low",
                ),
            ),
            types.Tool(
                name="google_calendar_search_events",
                description="Free-text search for events across event fields (summary, description, location, attendees, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Free-text search query"
                        },
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar identifier (default: 'primary')"
                        },
                        "timeMin": {
                            "type": "string",
                            "description": "Lower bound for event start time as RFC3339 timestamp"
                        },
                        "timeMax": {
                            "type": "string",
                            "description": "Upper bound for event end time as RFC3339 timestamp"
                        },
                        "maxResults": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 2500,
                            "default": 25,
                            "description": "Maximum number of events to return"
                        }
                    },
                    "required": ["query"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                    riskLevel="low",
                ),
            ),
            types.Tool(
                name="google_calendar_get_freebusy",
                description="Query free/busy information for one or more calendars within a time range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "time_min": {
                            "type": "string",
                            "description": "Start of the time range as RFC3339 timestamp"
                        },
                        "time_max": {
                            "type": "string",
                            "description": "End of the time range as RFC3339 timestamp"
                        },
                        "calendar_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": ["primary"],
                            "description": "List of calendar identifiers to query (default: ['primary'])"
                        }
                    },
                    "required": ["time_min", "time_max"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                    riskLevel="low",
                ),
            ),
            types.Tool(
                name="google_calendar_create_event",
                description="Create a new calendar event. Use start_datetime/end_datetime for timed events, or start_date/end_date for all-day events.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Title of the event"
                        },
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar identifier (default: 'primary')"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description or notes for the event"
                        },
                        "location": {
                            "type": "string",
                            "description": "Geographic location of the event"
                        },
                        "start_datetime": {
                            "type": "string",
                            "description": "Start date-time in RFC3339 format (e.g., '2025-06-15T09:00:00-07:00'). Use for timed events."
                        },
                        "end_datetime": {
                            "type": "string",
                            "description": "End date-time in RFC3339 format. Use for timed events."
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format. Use for all-day events."
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format (exclusive). Use for all-day events."
                        },
                        "timezone": {
                            "type": "string",
                            "description": "IANA timezone (e.g., 'America/New_York'). Used with start_datetime/end_datetime."
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of attendee email addresses"
                        },
                        "recurrence": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of RRULE, EXRULE, RDATE, or EXDATE lines (e.g., ['RRULE:FREQ=WEEKLY;COUNT=10'])"
                        },
                        "reminders": {
                            "type": "object",
                            "properties": {
                                "useDefault": {
                                    "type": "boolean",
                                    "description": "Whether to use the calendar's default reminders"
                                },
                                "overrides": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "method": {
                                                "type": "string",
                                                "enum": ["email", "popup"]
                                            },
                                            "minutes": {
                                                "type": "integer"
                                            }
                                        }
                                    },
                                    "description": "Custom reminder overrides"
                                }
                            },
                            "description": "Reminder settings for the event"
                        }
                    },
                    "required": ["summary"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=False,
                    riskLevel="medium",
                ),
            ),
            types.Tool(
                name="google_calendar_update_event",
                description="Update an existing calendar event. Only provided fields are changed; other fields remain unchanged.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar identifier (default: 'primary')"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event identifier"
                        },
                        "summary": {
                            "type": "string",
                            "description": "New title for the event"
                        },
                        "description": {
                            "type": "string",
                            "description": "New description for the event"
                        },
                        "location": {
                            "type": "string",
                            "description": "New location for the event"
                        },
                        "start_datetime": {
                            "type": "string",
                            "description": "New start date-time in RFC3339 format"
                        },
                        "end_datetime": {
                            "type": "string",
                            "description": "New end date-time in RFC3339 format"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New list of attendee email addresses (replaces existing attendees)"
                        }
                    },
                    "required": ["event_id"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=True,
                    idempotentHint=True,
                    openWorldHint=False,
                    riskLevel="high",
                ),
            ),
            types.Tool(
                name="google_calendar_delete_event",
                description="Delete a calendar event. Optionally notify attendees about the cancellation.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar identifier (default: 'primary')"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event identifier"
                        },
                        "sendUpdates": {
                            "type": "string",
                            "enum": ["all", "externalOnly", "none"],
                            "default": "none",
                            "description": "Whether to send cancellation notifications ('all', 'externalOnly', 'none')"
                        }
                    },
                    "required": ["event_id"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=True,
                    idempotentHint=True,
                    openWorldHint=False,
                    riskLevel="critical",
                ),
            ),
            types.Tool(
                name="google_calendar_rsvp_event",
                description="Respond to a calendar event invitation (accept, decline, or tentatively accept)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar identifier (default: 'primary')"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event identifier"
                        },
                        "response_status": {
                            "type": "string",
                            "enum": ["accepted", "declined", "tentative"],
                            "description": "RSVP response status"
                        }
                    },
                    "required": ["event_id", "response_status"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                    riskLevel="medium",
                ),
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Google Calendar resources."""
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Google Calendar tool.

        Tool names arrive WITHOUT the 'google_calendar_' prefix (stripped by the dispatch layer).
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            if tool_name == "list_calendars":
                return await self._list_calendars(arguments, oauth_cred)
            elif tool_name == "get_calendar":
                return await self._get_calendar(arguments, oauth_cred)
            elif tool_name == "list_events":
                return await self._list_events(arguments, oauth_cred)
            elif tool_name == "get_event":
                return await self._get_event(arguments, oauth_cred)
            elif tool_name == "search_events":
                return await self._search_events(arguments, oauth_cred)
            elif tool_name == "get_freebusy":
                return await self._get_freebusy(arguments, oauth_cred)
            elif tool_name == "create_event":
                return await self._create_event(arguments, oauth_cred)
            elif tool_name == "update_event":
                return await self._update_event(arguments, oauth_cred)
            elif tool_name == "delete_event":
                return await self._delete_event(arguments, oauth_cred)
            elif tool_name == "rsvp_event":
                return await self._rsvp_event(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Google Calendar tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Google Calendar resource.

        Supported path formats:
            event/{calendarId}/{eventId} - Read a specific event
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            parts = resource_path.split("/", 2)
            if len(parts) < 2:
                return "Error: Invalid resource path. Expected format: event/{calendarId}/{eventId}"

            resource_type = parts[0]

            if resource_type == "event" and len(parts) == 3:
                calendar_id, event_id = parts[1], parts[2]
                response = await self._make_authenticated_request(
                    "GET",
                    f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
                    oauth_cred,
                )
                return json.dumps(response.json(), indent=2)
            else:
                return "Error: Invalid resource path. Expected format: event/{calendarId}/{eventId}"

        except Exception as e:
            return f"Error reading Google Calendar resource: {str(e)}"

    # ------------------------------------------------------------------ #
    # Tool implementations
    # ------------------------------------------------------------------ #

    async def _list_calendars(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List all calendars in the user's calendar list."""
        params: Dict[str, Any] = {}
        if "maxResults" in arguments:
            params["maxResults"] = arguments["maxResults"]
        if "pageToken" in arguments:
            params["pageToken"] = arguments["pageToken"]

        response = await self._make_authenticated_request(
            "GET",
            f"{CALENDAR_API_BASE}/users/me/calendarList",
            oauth_cred,
            params=params,
        )
        data = response.json()

        items = data.get("items", [])
        result = {
            "calendars": [
                {
                    "id": cal.get("id"),
                    "summary": cal.get("summary"),
                    "description": cal.get("description"),
                    "primary": cal.get("primary", False),
                    "accessRole": cal.get("accessRole"),
                    "timeZone": cal.get("timeZone"),
                    "backgroundColor": cal.get("backgroundColor"),
                }
                for cal in items
            ],
            "nextPageToken": data.get("nextPageToken"),
        }
        return json.dumps(result, indent=2)

    async def _get_calendar(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get metadata for a specific calendar."""
        calendar_id = arguments["calendar_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}",
            oauth_cred,
        )
        data = response.json()

        result = {
            "id": data.get("id"),
            "summary": data.get("summary"),
            "description": data.get("description"),
            "timeZone": data.get("timeZone"),
            "location": data.get("location"),
        }
        return json.dumps(result, indent=2)

    async def _list_events(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List events on a calendar."""
        calendar_id = arguments.get("calendar_id", "primary")
        params: Dict[str, Any] = {}

        if "timeMin" in arguments:
            params["timeMin"] = arguments["timeMin"]
        if "timeMax" in arguments:
            params["timeMax"] = arguments["timeMax"]
        if "maxResults" in arguments:
            params["maxResults"] = arguments["maxResults"]
        else:
            params["maxResults"] = 25
        if "pageToken" in arguments:
            params["pageToken"] = arguments["pageToken"]
        if "singleEvents" in arguments:
            params["singleEvents"] = str(arguments["singleEvents"]).lower()
        else:
            params["singleEvents"] = "true"
        if "orderBy" in arguments:
            params["orderBy"] = arguments["orderBy"]

        response = await self._make_authenticated_request(
            "GET",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            oauth_cred,
            params=params,
        )
        data = response.json()

        result = {
            "events": [self._format_event(e) for e in data.get("items", [])],
            "nextPageToken": data.get("nextPageToken"),
        }
        return json.dumps(result, indent=2)

    async def _get_event(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get details of a specific event."""
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            oauth_cred,
        )
        return json.dumps(self._format_event(response.json()), indent=2)

    async def _search_events(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Free-text search for events."""
        calendar_id = arguments.get("calendar_id", "primary")
        params: Dict[str, Any] = {
            "q": arguments["query"],
            "singleEvents": "true",
        }
        if "timeMin" in arguments:
            params["timeMin"] = arguments["timeMin"]
        if "timeMax" in arguments:
            params["timeMax"] = arguments["timeMax"]
        if "maxResults" in arguments:
            params["maxResults"] = arguments["maxResults"]
        else:
            params["maxResults"] = 25

        response = await self._make_authenticated_request(
            "GET",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            oauth_cred,
            params=params,
        )
        data = response.json()

        result = {
            "events": [self._format_event(e) for e in data.get("items", [])],
            "nextPageToken": data.get("nextPageToken"),
        }
        return json.dumps(result, indent=2)

    async def _get_freebusy(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Query free/busy information."""
        calendar_ids = arguments.get("calendar_ids", ["primary"])
        payload = {
            "timeMin": arguments["time_min"],
            "timeMax": arguments["time_max"],
            "items": [{"id": cid} for cid in calendar_ids],
        }

        response = await self._make_authenticated_request(
            "POST",
            f"{CALENDAR_API_BASE}/freeBusy",
            oauth_cred,
            json=payload,
        )
        data = response.json()

        calendars = data.get("calendars", {})
        result: Dict[str, Any] = {
            "timeMin": data.get("timeMin"),
            "timeMax": data.get("timeMax"),
            "calendars": {},
        }
        for cal_id, cal_data in calendars.items():
            result["calendars"][cal_id] = {
                "busy": cal_data.get("busy", []),
                "errors": cal_data.get("errors", []),
            }
        return json.dumps(result, indent=2)

    async def _create_event(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new calendar event."""
        calendar_id = arguments.get("calendar_id", "primary")

        event_body: Dict[str, Any] = {
            "summary": arguments["summary"],
        }

        if "description" in arguments:
            event_body["description"] = arguments["description"]
        if "location" in arguments:
            event_body["location"] = arguments["location"]

        # Timed event
        if "start_datetime" in arguments:
            start: Dict[str, str] = {"dateTime": arguments["start_datetime"]}
            if "timezone" in arguments:
                start["timeZone"] = arguments["timezone"]
            event_body["start"] = start

            if "end_datetime" in arguments:
                end: Dict[str, str] = {"dateTime": arguments["end_datetime"]}
                if "timezone" in arguments:
                    end["timeZone"] = arguments["timezone"]
                event_body["end"] = end
        # All-day event
        elif "start_date" in arguments:
            event_body["start"] = {"date": arguments["start_date"]}
            if "end_date" in arguments:
                event_body["end"] = {"date": arguments["end_date"]}

        if "attendees" in arguments:
            event_body["attendees"] = [{"email": email} for email in arguments["attendees"]]

        if "recurrence" in arguments:
            event_body["recurrence"] = arguments["recurrence"]

        if "reminders" in arguments:
            event_body["reminders"] = arguments["reminders"]

        response = await self._make_authenticated_request(
            "POST",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events",
            oauth_cred,
            json=event_body,
        )
        return json.dumps(self._format_event(response.json()), indent=2)

    async def _update_event(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Update an existing calendar event (read-modify-write)."""
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]

        # GET the current event
        get_response = await self._make_authenticated_request(
            "GET",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            oauth_cred,
        )
        event_body = get_response.json()

        # Merge changes
        if "summary" in arguments:
            event_body["summary"] = arguments["summary"]
        if "description" in arguments:
            event_body["description"] = arguments["description"]
        if "location" in arguments:
            event_body["location"] = arguments["location"]
        if "start_datetime" in arguments:
            event_body["start"] = {"dateTime": arguments["start_datetime"]}
            if event_body.get("start", {}).get("timeZone"):
                event_body["start"]["timeZone"] = event_body["start"]["timeZone"]
        if "end_datetime" in arguments:
            event_body["end"] = {"dateTime": arguments["end_datetime"]}
            if event_body.get("end", {}).get("timeZone"):
                event_body["end"]["timeZone"] = event_body["end"]["timeZone"]
        if "attendees" in arguments:
            event_body["attendees"] = [{"email": email} for email in arguments["attendees"]]

        # PUT the updated event
        response = await self._make_authenticated_request(
            "PUT",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            oauth_cred,
            json=event_body,
        )
        return json.dumps(self._format_event(response.json()), indent=2)

    async def _delete_event(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Delete a calendar event."""
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]
        params: Dict[str, Any] = {}

        if "sendUpdates" in arguments:
            params["sendUpdates"] = arguments["sendUpdates"]

        await self._make_authenticated_request(
            "DELETE",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            oauth_cred,
            params=params,
        )
        return json.dumps({"deleted": True, "eventId": event_id}, indent=2)

    async def _rsvp_event(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Respond to an event invitation."""
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]
        response_status = arguments["response_status"]

        # GET the current event to find the user's attendee entry
        get_response = await self._make_authenticated_request(
            "GET",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            oauth_cred,
        )
        event_body = get_response.json()

        # Find current user in attendees and update responseStatus.
        # If no attendees list or user not found, add self marker.
        attendees = event_body.get("attendees", [])
        user_found = False
        for attendee in attendees:
            if attendee.get("self"):
                attendee["responseStatus"] = response_status
                user_found = True
                break

        if not user_found:
            # Fallback: add a self-referencing attendee entry
            attendees.append({"self": True, "responseStatus": response_status})
            event_body["attendees"] = attendees

        # PATCH the event with updated attendees
        response = await self._make_authenticated_request(
            "PATCH",
            f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}",
            oauth_cred,
            json={"attendees": event_body["attendees"]},
        )
        return json.dumps(self._format_event(response.json()), indent=2)

    # ------------------------------------------------------------------ #
    # Helper: format event for output
    # ------------------------------------------------------------------ #

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format a Calendar API event response into a clean dict."""
        start = event.get("start", {})
        end = event.get("end", {})
        return {
            "id": event.get("id"),
            "summary": event.get("summary"),
            "description": event.get("description"),
            "location": event.get("location"),
            "status": event.get("status"),
            "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"),
            "timeZone": start.get("timeZone"),
            "htmlLink": event.get("htmlLink"),
            "creator": event.get("creator"),
            "organizer": event.get("organizer"),
            "attendees": [
                {
                    "email": a.get("email"),
                    "displayName": a.get("displayName"),
                    "responseStatus": a.get("responseStatus"),
                    "self": a.get("self", False),
                }
                for a in event.get("attendees", [])
            ],
            "recurrence": event.get("recurrence"),
            "recurringEventId": event.get("recurringEventId"),
        }
