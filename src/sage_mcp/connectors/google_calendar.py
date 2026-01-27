"""Google Calendar connector implementation.

This connector enables interaction with Google Calendar through OAuth 2.0.
Requires OAuth app with scopes:
- https://www.googleapis.com/auth/calendar.readonly (read calendars and events)
- https://www.googleapis.com/auth/calendar.events (create/update/delete events)

OAuth App Setup:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URIs matching your SageMCP OAuth configuration
4. Enable Google Calendar API
5. Note the Client ID and Client Secret for SageMCP configuration
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


@register_connector(ConnectorType.GOOGLE_CALENDAR)
class GoogleCalendarConnector(BaseConnector):
    """Google Calendar connector for accessing Google Calendar API."""

    @property
    def display_name(self) -> str:
        return "Google Calendar"

    @property
    def description(self) -> str:
        return "Access Google Calendar calendars and events, create, read, update, and delete events"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Google Calendar tools."""
        tools = [
            # Calendar Management
            types.Tool(
                name="google_calendar_list_calendars",
                description="List all calendars accessible to the user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "show_hidden": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to show hidden calendars"
                        }
                    }
                }
            ),
            types.Tool(
                name="google_calendar_get_calendar",
                description="Get detailed information about a specific calendar",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (use 'primary' for user's primary calendar)"
                        }
                    },
                    "required": ["calendar_id"]
                }
            ),

            # Event Management
            types.Tool(
                name="google_calendar_list_events",
                description="List events from a calendar within a time range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID (use 'primary' for user's primary calendar)"
                        },
                        "time_min": {
                            "type": "string",
                            "description": "Start time in RFC3339 format (e.g., '2024-01-01T00:00:00Z'). Defaults to now."
                        },
                        "time_max": {
                            "type": "string",
                            "description": "End time in RFC3339 format. Defaults to 30 days from now."
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 250,
                            "default": 50,
                            "description": "Maximum number of events to return"
                        },
                        "single_events": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to expand recurring events into instances"
                        },
                        "order_by": {
                            "type": "string",
                            "enum": ["startTime", "updated"],
                            "default": "startTime",
                            "description": "Order of events in the result"
                        }
                    }
                }
            ),
            types.Tool(
                name="google_calendar_get_event",
                description="Get detailed information about a specific event",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID"
                        }
                    },
                    "required": ["event_id"]
                }
            ),
            types.Tool(
                name="google_calendar_create_event",
                description="Create a new calendar event",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID"
                        },
                        "summary": {
                            "type": "string",
                            "description": "Event title/summary"
                        },
                        "description": {
                            "type": "string",
                            "description": "Event description"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in RFC3339 format (e.g., '2024-01-01T10:00:00-08:00')"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in RFC3339 format"
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of attendee email addresses"
                        },
                        "send_notifications": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to send event notifications to attendees"
                        },
                        "conference_data": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to create a Google Meet link"
                        }
                    },
                    "required": ["summary", "start_time", "end_time"]
                }
            ),
            types.Tool(
                name="google_calendar_update_event",
                description="Update an existing calendar event",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID to update"
                        },
                        "summary": {
                            "type": "string",
                            "description": "New event title/summary"
                        },
                        "description": {
                            "type": "string",
                            "description": "New event description"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "New start time in RFC3339 format"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "New end time in RFC3339 format"
                        },
                        "location": {
                            "type": "string",
                            "description": "New event location"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New list of attendee email addresses"
                        },
                        "send_notifications": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to send event notifications to attendees"
                        }
                    },
                    "required": ["event_id"]
                }
            ),
            types.Tool(
                name="google_calendar_delete_event",
                description="Delete a calendar event",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID to delete"
                        },
                        "send_notifications": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to send cancellation notifications to attendees"
                        }
                    },
                    "required": ["event_id"]
                }
            ),
            types.Tool(
                name="google_calendar_search_events",
                description="Search for events by keyword across calendars",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID to search"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (searches in summary, description, location, attendee names/emails)"
                        },
                        "time_min": {
                            "type": "string",
                            "description": "Start time in RFC3339 format. Defaults to now."
                        },
                        "time_max": {
                            "type": "string",
                            "description": "End time in RFC3339 format"
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 250,
                            "default": 50,
                            "description": "Maximum number of events to return"
                        }
                    },
                    "required": ["query"]
                }
            ),

            # Availability
            types.Tool(
                name="google_calendar_get_freebusy",
                description="Get free/busy information for specified calendars in a time range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of calendar IDs to check (use ['primary'] for user's calendar)"
                        },
                        "time_min": {
                            "type": "string",
                            "description": "Start time in RFC3339 format"
                        },
                        "time_max": {
                            "type": "string",
                            "description": "End time in RFC3339 format"
                        }
                    },
                    "required": ["calendar_ids", "time_min", "time_max"]
                }
            ),

            # Quick Add
            types.Tool(
                name="google_calendar_quick_add",
                description="Create an event from natural language text (e.g., 'Lunch with John tomorrow at noon')",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID"
                        },
                        "text": {
                            "type": "string",
                            "description": "Natural language description of the event"
                        },
                        "send_notifications": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether to send event notifications"
                        }
                    },
                    "required": ["text"]
                }
            ),

            # Event Instances (for recurring events)
            types.Tool(
                name="google_calendar_list_event_instances",
                description="List all instances of a recurring event",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "default": "primary",
                            "description": "Calendar ID"
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Recurring event ID"
                        },
                        "time_min": {
                            "type": "string",
                            "description": "Start time in RFC3339 format"
                        },
                        "time_max": {
                            "type": "string",
                            "description": "End time in RFC3339 format"
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 250,
                            "default": 50,
                            "description": "Maximum number of instances to return"
                        }
                    },
                    "required": ["event_id"]
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Google Calendar resources."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        try:
            # Get user's calendars
            response = await self._make_authenticated_request(
                "GET",
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                oauth_cred,
                params={"maxResults": 50}
            )
            calendars_data = response.json()

            resources = []

            # Add calendar resources
            for cal in calendars_data.get("items", []):
                calendar_id = cal["id"]
                resources.append(types.Resource(
                    uri=f"google_calendar://calendar/{calendar_id}",
                    name=cal.get("summary", "Unnamed Calendar"),
                    description=f"Calendar: {cal.get('description', 'No description')}"
                ))

            # Get upcoming events from primary calendar
            try:
                now = datetime.utcnow().isoformat() + "Z"
                events_response = await self._make_authenticated_request(
                    "GET",
                    "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                    oauth_cred,
                    params={
                        "timeMin": now,
                        "maxResults": 20,
                        "singleEvents": True,
                        "orderBy": "startTime"
                    }
                )
                events_data = events_response.json()

                # Add event resources
                for event in events_data.get("items", []):
                    event_id = event["id"]
                    summary = event.get("summary", "No title")
                    start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
                    resources.append(types.Resource(
                        uri=f"google_calendar://event/primary/{event_id}",
                        name=f"{summary} ({start})",
                        description="Calendar event"
                    ))
            except Exception as e:
                print(f"DEBUG: Could not fetch events: {e}")

            return resources

        except Exception as e:
            print(f"Error fetching Google Calendar resources: {e}")
            return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Google Calendar tool."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google Calendar credentials"

        try:
            # Route to appropriate handler
            if tool_name == "list_calendars":
                return await self._list_calendars(arguments, oauth_cred)
            elif tool_name == "get_calendar":
                return await self._get_calendar(arguments, oauth_cred)
            elif tool_name == "list_events":
                return await self._list_events(arguments, oauth_cred)
            elif tool_name == "get_event":
                return await self._get_event(arguments, oauth_cred)
            elif tool_name == "create_event":
                return await self._create_event(arguments, oauth_cred)
            elif tool_name == "update_event":
                return await self._update_event(arguments, oauth_cred)
            elif tool_name == "delete_event":
                return await self._delete_event(arguments, oauth_cred)
            elif tool_name == "search_events":
                return await self._search_events(arguments, oauth_cred)
            elif tool_name == "get_freebusy":
                return await self._get_freebusy(arguments, oauth_cred)
            elif tool_name == "quick_add":
                return await self._quick_add(arguments, oauth_cred)
            elif tool_name == "list_event_instances":
                return await self._list_event_instances(arguments, oauth_cred)
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
        """Read a Google Calendar resource."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google Calendar credentials"

        try:
            # Parse resource path: calendar/{id} or event/{calendar_id}/{event_id}
            parts = resource_path.split("/")
            if len(parts) < 2:
                return "Error: Invalid resource path"

            resource_type = parts[0]

            if resource_type == "calendar":
                calendar_id = parts[1]
                response = await self._make_authenticated_request(
                    "GET",
                    f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}",
                    oauth_cred
                )
                return json.dumps(response.json(), indent=2)

            elif resource_type == "event":
                if len(parts) < 3:
                    return "Error: Invalid event resource path"
                calendar_id = parts[1]
                event_id = parts[2]
                response = await self._make_authenticated_request(
                    "GET",
                    f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                    oauth_cred
                )
                return json.dumps(response.json(), indent=2)

            else:
                return "Error: Unsupported resource type"

        except Exception as e:
            return f"Error reading Google Calendar resource: {str(e)}"

    # Private implementation methods

    async def _list_calendars(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List user's calendars."""
        params = {}
        if arguments.get("show_hidden"):
            params["showHidden"] = True

        print("DEBUG: Listing Google Calendars")
        response = await self._make_authenticated_request(
            "GET",
            "https://www.googleapis.com/calendar/v3/users/me/calendarList",
            oauth_cred,
            params=params
        )

        data = response.json()
        calendars = []

        for cal in data.get("items", []):
            calendars.append({
                "id": cal["id"],
                "summary": cal.get("summary"),
                "description": cal.get("description"),
                "timeZone": cal.get("timeZone"),
                "accessRole": cal.get("accessRole"),
                "primary": cal.get("primary", False)
            })

        print(f"DEBUG: Found {len(calendars)} calendars")
        return json.dumps({"calendars": calendars}, indent=2)

    async def _get_calendar(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get calendar details."""
        calendar_id = arguments["calendar_id"]

        print(f"DEBUG: Getting calendar: {calendar_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _list_events(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List calendar events."""
        calendar_id = arguments.get("calendar_id", "primary")
        max_results = arguments.get("max_results", 50)
        single_events = arguments.get("single_events", True)
        order_by = arguments.get("order_by", "startTime")

        # Default to now if not specified
        time_min = arguments.get("time_min")
        if not time_min:
            time_min = datetime.utcnow().isoformat() + "Z"

        # Default to 30 days from now if not specified
        time_max = arguments.get("time_max")
        if not time_max:
            time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"

        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": max_results,
            "singleEvents": single_events,
            "orderBy": order_by
        }

        print(f"DEBUG: Listing events from {time_min} to {time_max}")
        response = await self._make_authenticated_request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            oauth_cred,
            params=params
        )

        data = response.json()
        events = []

        for event in data.get("items", []):
            events.append({
                "id": event["id"],
                "summary": event.get("summary"),
                "description": event.get("description"),
                "location": event.get("location"),
                "start": event.get("start"),
                "end": event.get("end"),
                "attendees": event.get("attendees", []),
                "status": event.get("status"),
                "htmlLink": event.get("htmlLink")
            })

        print(f"DEBUG: Found {len(events)} events")
        return json.dumps({"events": events}, indent=2)

    async def _get_event(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get event details."""
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]

        print(f"DEBUG: Getting event: {event_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _create_event(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new event."""
        calendar_id = arguments.get("calendar_id", "primary")
        send_notifications = arguments.get("send_notifications", True)

        event_data = {
            "summary": arguments["summary"],
            "start": {"dateTime": arguments["start_time"]},
            "end": {"dateTime": arguments["end_time"]}
        }

        if "description" in arguments:
            event_data["description"] = arguments["description"]

        if "location" in arguments:
            event_data["location"] = arguments["location"]

        if "attendees" in arguments:
            event_data["attendees"] = [{"email": email} for email in arguments["attendees"]]

        if arguments.get("conference_data"):
            event_data["conferenceData"] = {
                "createRequest": {
                    "requestId": f"meet-{datetime.utcnow().timestamp()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }

        params = {"sendUpdates": "all" if send_notifications else "none"}
        if arguments.get("conference_data"):
            params["conferenceDataVersion"] = 1

        print(f"DEBUG: Creating event: {arguments['summary']}")
        response = await self._make_authenticated_request(
            "POST",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            oauth_cred,
            json=event_data,
            params=params
        )

        result = response.json()
        print(f"DEBUG: Created event: {result.get('id')}")
        return json.dumps(result, indent=2)

    async def _update_event(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Update an existing event."""
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]
        send_notifications = arguments.get("send_notifications", True)

        # Get current event
        current_response = await self._make_authenticated_request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            oauth_cred
        )
        event_data = current_response.json()

        # Update fields
        if "summary" in arguments:
            event_data["summary"] = arguments["summary"]
        if "description" in arguments:
            event_data["description"] = arguments["description"]
        if "location" in arguments:
            event_data["location"] = arguments["location"]
        if "start_time" in arguments:
            event_data["start"] = {"dateTime": arguments["start_time"]}
        if "end_time" in arguments:
            event_data["end"] = {"dateTime": arguments["end_time"]}
        if "attendees" in arguments:
            event_data["attendees"] = [{"email": email} for email in arguments["attendees"]]

        params = {"sendUpdates": "all" if send_notifications else "none"}

        print(f"DEBUG: Updating event: {event_id}")
        response = await self._make_authenticated_request(
            "PUT",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            oauth_cred,
            json=event_data,
            params=params
        )

        print(f"DEBUG: Event {event_id} updated successfully")
        return json.dumps(response.json(), indent=2)

    async def _delete_event(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Delete an event."""
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]
        send_notifications = arguments.get("send_notifications", True)

        params = {"sendUpdates": "all" if send_notifications else "none"}

        print(f"DEBUG: Deleting event: {event_id}")
        await self._make_authenticated_request(
            "DELETE",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
            oauth_cred,
            params=params
        )

        print(f"DEBUG: Event {event_id} deleted successfully")
        return json.dumps({"message": f"Event {event_id} deleted successfully"}, indent=2)

    async def _search_events(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search for events."""
        calendar_id = arguments.get("calendar_id", "primary")
        query = arguments["query"]
        max_results = arguments.get("max_results", 50)

        params = {
            "q": query,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime"
        }

        if "time_min" in arguments:
            params["timeMin"] = arguments["time_min"]
        else:
            params["timeMin"] = datetime.utcnow().isoformat() + "Z"

        if "time_max" in arguments:
            params["timeMax"] = arguments["time_max"]

        print(f"DEBUG: Searching events with query: {query}")
        response = await self._make_authenticated_request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
            oauth_cred,
            params=params
        )

        data = response.json()
        print(f"DEBUG: Found {len(data.get('items', []))} matching events")
        return json.dumps(data, indent=2)

    async def _get_freebusy(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get free/busy information."""
        calendar_ids = arguments["calendar_ids"]
        time_min = arguments["time_min"]
        time_max = arguments["time_max"]

        request_body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": cal_id} for cal_id in calendar_ids]
        }

        print(f"DEBUG: Getting free/busy for {len(calendar_ids)} calendars")
        response = await self._make_authenticated_request(
            "POST",
            "https://www.googleapis.com/calendar/v3/freeBusy",
            oauth_cred,
            json=request_body
        )

        return json.dumps(response.json(), indent=2)

    async def _quick_add(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Quick add event from text."""
        calendar_id = arguments.get("calendar_id", "primary")
        text = arguments["text"]
        send_notifications = arguments.get("send_notifications", True)

        params = {
            "text": text,
            "sendUpdates": "all" if send_notifications else "none"
        }

        print(f"DEBUG: Quick adding event: {text}")
        response = await self._make_authenticated_request(
            "POST",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/quickAdd",
            oauth_cred,
            params=params
        )

        result = response.json()
        print(f"DEBUG: Created event: {result.get('id')}")
        return json.dumps(result, indent=2)

    async def _list_event_instances(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List instances of a recurring event."""
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]
        max_results = arguments.get("max_results", 50)

        params = {"maxResults": max_results}

        if "time_min" in arguments:
            params["timeMin"] = arguments["time_min"]
        if "time_max" in arguments:
            params["timeMax"] = arguments["time_max"]

        print(f"DEBUG: Listing instances for recurring event: {event_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}/instances",
            oauth_cred,
            params=params
        )

        data = response.json()
        print(f"DEBUG: Found {len(data.get('items', []))} instances")
        return json.dumps(data, indent=2)
