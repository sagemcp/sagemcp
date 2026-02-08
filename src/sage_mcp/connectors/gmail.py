"""Gmail connector implementation."""

import base64
import json
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


@register_connector(ConnectorType.GMAIL)
class GmailConnector(BaseConnector):
    """Gmail connector for sending, reading, and managing Gmail messages and threads."""

    @property
    def display_name(self) -> str:
        return "Gmail"

    @property
    def description(self) -> str:
        return "Send, read, and manage Gmail messages and threads"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Gmail tools."""
        tools = [
            types.Tool(
                name="gmail_list_messages",
                description="List messages in the user's mailbox. Supports Gmail search query syntax for filtering.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "q": {
                            "type": "string",
                            "description": "Gmail search query (e.g., 'from:user@example.com', 'is:unread', 'subject:hello')"
                        },
                        "maxResults": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 500,
                            "default": 20,
                            "description": "Maximum number of messages to return"
                        },
                        "pageToken": {
                            "type": "string",
                            "description": "Page token for retrieving the next page of results"
                        },
                        "labelIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Only return messages with labels matching all of the specified label IDs"
                        }
                    }
                }
            ),
            types.Tool(
                name="gmail_get_message",
                description="Get a specific message by ID with full content including headers and body",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the message to retrieve"
                        }
                    },
                    "required": ["id"]
                }
            ),
            types.Tool(
                name="gmail_search_messages",
                description="Search messages using Gmail search syntax (e.g., 'from:user@example.com after:2024/01/01 has:attachment')",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Gmail search query string"
                        },
                        "maxResults": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 500,
                            "default": 20,
                            "description": "Maximum number of results to return"
                        },
                        "pageToken": {
                            "type": "string",
                            "description": "Page token for retrieving the next page of results"
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="gmail_send_message",
                description="Send a new email message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body content (plain text)"
                        },
                        "cc": {
                            "type": "string",
                            "description": "CC recipient email addresses (comma-separated)"
                        },
                        "bcc": {
                            "type": "string",
                            "description": "BCC recipient email addresses (comma-separated)"
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            ),
            types.Tool(
                name="gmail_reply_to_message",
                description="Reply to an existing email message, preserving the thread",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The ID of the message to reply to"
                        },
                        "body": {
                            "type": "string",
                            "description": "Reply body content (plain text)"
                        },
                        "reply_all": {
                            "type": "boolean",
                            "default": False,
                            "description": "If true, reply to all recipients"
                        }
                    },
                    "required": ["message_id", "body"]
                }
            ),
            types.Tool(
                name="gmail_forward_message",
                description="Forward an existing email message to a new recipient",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The ID of the message to forward"
                        },
                        "to": {
                            "type": "string",
                            "description": "Recipient email address to forward to"
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional additional message to include above the forwarded content",
                            "default": ""
                        }
                    },
                    "required": ["message_id", "to"]
                }
            ),
            types.Tool(
                name="gmail_list_threads",
                description="List email threads in the user's mailbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "q": {
                            "type": "string",
                            "description": "Gmail search query to filter threads"
                        },
                        "maxResults": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 500,
                            "default": 20,
                            "description": "Maximum number of threads to return"
                        },
                        "pageToken": {
                            "type": "string",
                            "description": "Page token for retrieving the next page of results"
                        },
                        "labelIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Only return threads with labels matching all of the specified label IDs"
                        }
                    }
                }
            ),
            types.Tool(
                name="gmail_get_thread",
                description="Get a specific email thread by ID with all messages",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the thread to retrieve"
                        }
                    },
                    "required": ["id"]
                }
            ),
            types.Tool(
                name="gmail_list_labels",
                description="List all labels in the user's mailbox (including system labels like INBOX, SENT, TRASH)",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="gmail_create_label",
                description="Create a new label in the user's mailbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The display name of the label"
                        },
                        "labelListVisibility": {
                            "type": "string",
                            "enum": ["labelShow", "labelShowIfUnread", "labelHide"],
                            "default": "labelShow",
                            "description": "Visibility of the label in the label list"
                        },
                        "messageListVisibility": {
                            "type": "string",
                            "enum": ["show", "hide"],
                            "default": "show",
                            "description": "Visibility of messages with this label in the message list"
                        }
                    },
                    "required": ["name"]
                }
            ),
            types.Tool(
                name="gmail_modify_labels",
                description="Add or remove labels from a specific message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the message to modify"
                        },
                        "addLabelIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of label IDs to add to the message"
                        },
                        "removeLabelIds": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of label IDs to remove from the message"
                        }
                    },
                    "required": ["id"]
                }
            ),
            types.Tool(
                name="gmail_trash_message",
                description="Move a message to the trash",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the message to trash"
                        }
                    },
                    "required": ["id"]
                }
            ),
            types.Tool(
                name="gmail_untrash_message",
                description="Remove a message from the trash",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the message to untrash"
                        }
                    },
                    "required": ["id"]
                }
            ),
            types.Tool(
                name="gmail_create_draft",
                description="Create a draft email message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body content (plain text)"
                        },
                        "cc": {
                            "type": "string",
                            "description": "CC recipient email addresses (comma-separated)"
                        },
                        "bcc": {
                            "type": "string",
                            "description": "BCC recipient email addresses (comma-separated)"
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            ),
            types.Tool(
                name="gmail_list_drafts",
                description="List draft messages in the user's mailbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "maxResults": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 500,
                            "default": 20,
                            "description": "Maximum number of drafts to return"
                        },
                        "pageToken": {
                            "type": "string",
                            "description": "Page token for retrieving the next page of results"
                        }
                    }
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Gmail resources."""
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Gmail tool.

        Tool names arrive WITHOUT the 'gmail_' prefix (stripped by the dispatch layer).
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            if tool_name == "list_messages":
                return await self._list_messages(arguments, oauth_cred)
            elif tool_name == "get_message":
                return await self._get_message(arguments, oauth_cred)
            elif tool_name == "search_messages":
                return await self._search_messages(arguments, oauth_cred)
            elif tool_name == "send_message":
                return await self._send_message(arguments, oauth_cred)
            elif tool_name == "reply_to_message":
                return await self._reply_to_message(arguments, oauth_cred)
            elif tool_name == "forward_message":
                return await self._forward_message(arguments, oauth_cred)
            elif tool_name == "list_threads":
                return await self._list_threads(arguments, oauth_cred)
            elif tool_name == "get_thread":
                return await self._get_thread(arguments, oauth_cred)
            elif tool_name == "list_labels":
                return await self._list_labels(oauth_cred)
            elif tool_name == "create_label":
                return await self._create_label(arguments, oauth_cred)
            elif tool_name == "modify_labels":
                return await self._modify_labels(arguments, oauth_cred)
            elif tool_name == "trash_message":
                return await self._trash_message(arguments, oauth_cred)
            elif tool_name == "untrash_message":
                return await self._untrash_message(arguments, oauth_cred)
            elif tool_name == "create_draft":
                return await self._create_draft(arguments, oauth_cred)
            elif tool_name == "list_drafts":
                return await self._list_drafts(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Gmail tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Gmail resource.

        Supported path formats:
            message/{id} - Read a specific message
            thread/{id}  - Read a specific thread
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            parts = resource_path.split("/", 1)
            if len(parts) != 2:
                return "Error: Invalid resource path. Expected format: message/{id} or thread/{id}"

            resource_type, resource_id = parts

            if resource_type == "message":
                response = await self._make_authenticated_request(
                    "GET",
                    f"{GMAIL_API_BASE}/messages/{resource_id}",
                    oauth_cred,
                    params={"format": "full"}
                )
                data = response.json()
                parsed = self._parse_message(data)
                return json.dumps(parsed, indent=2)

            elif resource_type == "thread":
                response = await self._make_authenticated_request(
                    "GET",
                    f"{GMAIL_API_BASE}/threads/{resource_id}",
                    oauth_cred,
                    params={"format": "full"}
                )
                data = response.json()
                messages = [self._parse_message(msg) for msg in data.get("messages", [])]
                result = {
                    "id": data.get("id"),
                    "historyId": data.get("historyId"),
                    "messages": messages
                }
                return json.dumps(result, indent=2)

            else:
                return "Error: Invalid resource type. Expected 'message' or 'thread'"

        except Exception as e:
            return f"Error reading Gmail resource: {str(e)}"

    # ------------------------------------------------------------------ #
    # Helper: build MIME message
    # ------------------------------------------------------------------ #

    def _build_mime_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        thread_id: Optional[str] = None,
        references: Optional[str] = None,
        in_reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a base64url-encoded RFC 2822 MIME message for the Gmail API.

        Returns a dict suitable for POSTing to messages/send or drafts.
        """
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        if cc:
            message["cc"] = cc
        if bcc:
            message["bcc"] = bcc
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        if references:
            message["References"] = references

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        payload: Dict[str, Any] = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id

        return payload

    # ------------------------------------------------------------------ #
    # Helper: parse message payload
    # ------------------------------------------------------------------ #

    def _parse_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Gmail API message response into a clean dict.

        Extracts Subject, From, To, Date from headers and decodes the body
        from base64url payload parts.
        """
        headers = data.get("payload", {}).get("headers", [])
        header_map: Dict[str, str] = {}
        for h in headers:
            name_lower = h.get("name", "").lower()
            if name_lower in ("subject", "from", "to", "date", "cc", "bcc", "message-id", "in-reply-to", "references"):
                header_map[name_lower] = h.get("value", "")

        body_text = self._extract_body(data.get("payload", {}))

        return {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "labelIds": data.get("labelIds", []),
            "snippet": data.get("snippet", ""),
            "subject": header_map.get("subject", ""),
            "from": header_map.get("from", ""),
            "to": header_map.get("to", ""),
            "cc": header_map.get("cc", ""),
            "date": header_map.get("date", ""),
            "message_id": header_map.get("message-id", ""),
            "in_reply_to": header_map.get("in-reply-to", ""),
            "references": header_map.get("references", ""),
            "body": body_text,
        }

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Recursively extract plain-text body from a message payload.

        Handles both single-part and multipart MIME structures.
        Falls back to the first available part if text/plain is not found.
        """
        # Single-part message
        body_data = payload.get("body", {}).get("data")
        if body_data and payload.get("mimeType", "").startswith("text/plain"):
            return base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")

        # Multipart message -- prefer text/plain, fall back to text/html
        parts = payload.get("parts", [])
        plain_text = ""
        html_text = ""
        for part in parts:
            mime = part.get("mimeType", "")
            part_data = part.get("body", {}).get("data")
            if part_data:
                decoded = base64.urlsafe_b64decode(part_data + "==").decode("utf-8", errors="replace")
                if mime == "text/plain":
                    plain_text = decoded
                elif mime == "text/html" and not html_text:
                    html_text = decoded
            # Recurse into nested multipart
            if part.get("parts"):
                nested = self._extract_body(part)
                if nested and not plain_text:
                    plain_text = nested

        return plain_text or html_text or ""

    # ------------------------------------------------------------------ #
    # Tool implementations
    # ------------------------------------------------------------------ #

    async def _list_messages(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List messages in the user's mailbox."""
        params: Dict[str, Any] = {}
        if "q" in arguments:
            params["q"] = arguments["q"]
        if "maxResults" in arguments:
            params["maxResults"] = arguments["maxResults"]
        else:
            params["maxResults"] = 20
        if "pageToken" in arguments:
            params["pageToken"] = arguments["pageToken"]
        if "labelIds" in arguments:
            params["labelIds"] = arguments["labelIds"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GMAIL_API_BASE}/messages",
            oauth_cred,
            params=params,
        )
        data = response.json()

        messages = data.get("messages", [])
        result = {
            "messages": messages,
            "resultSizeEstimate": data.get("resultSizeEstimate", 0),
            "nextPageToken": data.get("nextPageToken"),
        }
        return json.dumps(result, indent=2)

    async def _get_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get a specific message with full content."""
        message_id = arguments["id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GMAIL_API_BASE}/messages/{message_id}",
            oauth_cred,
            params={"format": "full"},
        )
        data = response.json()
        parsed = self._parse_message(data)
        return json.dumps(parsed, indent=2)

    async def _search_messages(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search messages using Gmail query syntax."""
        params: Dict[str, Any] = {"q": arguments["query"]}
        if "maxResults" in arguments:
            params["maxResults"] = arguments["maxResults"]
        else:
            params["maxResults"] = 20
        if "pageToken" in arguments:
            params["pageToken"] = arguments["pageToken"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GMAIL_API_BASE}/messages",
            oauth_cred,
            params=params,
        )
        data = response.json()

        messages = data.get("messages", [])
        result = {
            "messages": messages,
            "resultSizeEstimate": data.get("resultSizeEstimate", 0),
            "nextPageToken": data.get("nextPageToken"),
        }
        return json.dumps(result, indent=2)

    async def _send_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Send a new email message."""
        payload = self._build_mime_message(
            to=arguments["to"],
            subject=arguments["subject"],
            body=arguments["body"],
            cc=arguments.get("cc"),
            bcc=arguments.get("bcc"),
        )

        response = await self._make_authenticated_request(
            "POST",
            f"{GMAIL_API_BASE}/messages/send",
            oauth_cred,
            json=payload,
        )
        data = response.json()

        result = {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "labelIds": data.get("labelIds", []),
        }
        return json.dumps(result, indent=2)

    async def _reply_to_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Reply to an existing message, preserving the thread."""
        message_id = arguments["message_id"]
        reply_body = arguments["body"]
        reply_all = arguments.get("reply_all", False)

        # Fetch the original message to get headers and thread info
        original_response = await self._make_authenticated_request(
            "GET",
            f"{GMAIL_API_BASE}/messages/{message_id}",
            oauth_cred,
            params={"format": "full"},
        )
        original = original_response.json()
        original_parsed = self._parse_message(original)

        # Build reply headers
        subject = original_parsed.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        to = original_parsed.get("from", "")
        cc = None
        if reply_all:
            # Include original To and CC (excluding the sender)
            original_to = original_parsed.get("to", "")
            original_cc = original_parsed.get("cc", "")
            cc_parts = [p.strip() for p in f"{original_to},{original_cc}".split(",") if p.strip()]
            if cc_parts:
                cc = ", ".join(cc_parts)

        orig_message_id = original_parsed.get("message_id", "")
        orig_references = original_parsed.get("references", "")
        references = f"{orig_references} {orig_message_id}".strip() if orig_references else orig_message_id

        thread_id = original.get("threadId")

        payload = self._build_mime_message(
            to=to,
            subject=subject,
            body=reply_body,
            cc=cc,
            thread_id=thread_id,
            references=references,
            in_reply_to=orig_message_id,
        )

        response = await self._make_authenticated_request(
            "POST",
            f"{GMAIL_API_BASE}/messages/send",
            oauth_cred,
            json=payload,
        )
        data = response.json()

        result = {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "labelIds": data.get("labelIds", []),
        }
        return json.dumps(result, indent=2)

    async def _forward_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Forward an existing message to a new recipient."""
        message_id = arguments["message_id"]
        forward_to = arguments["to"]
        additional_body = arguments.get("body", "")

        # Fetch the original message
        original_response = await self._make_authenticated_request(
            "GET",
            f"{GMAIL_API_BASE}/messages/{message_id}",
            oauth_cred,
            params={"format": "full"},
        )
        original = original_response.json()
        original_parsed = self._parse_message(original)

        # Build forwarded message
        subject = original_parsed.get("subject", "")
        if not subject.lower().startswith("fwd:"):
            subject = f"Fwd: {subject}"

        # Compose the forwarded body
        forward_header = (
            f"\n\n---------- Forwarded message ----------\n"
            f"From: {original_parsed.get('from', '')}\n"
            f"Date: {original_parsed.get('date', '')}\n"
            f"Subject: {original_parsed.get('subject', '')}\n"
            f"To: {original_parsed.get('to', '')}\n\n"
        )
        original_body = original_parsed.get("body", "")
        body = f"{additional_body}{forward_header}{original_body}"

        thread_id = original.get("threadId")

        payload = self._build_mime_message(
            to=forward_to,
            subject=subject,
            body=body,
            thread_id=thread_id,
        )

        response = await self._make_authenticated_request(
            "POST",
            f"{GMAIL_API_BASE}/messages/send",
            oauth_cred,
            json=payload,
        )
        data = response.json()

        result = {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "labelIds": data.get("labelIds", []),
        }
        return json.dumps(result, indent=2)

    async def _list_threads(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List email threads."""
        params: Dict[str, Any] = {}
        if "q" in arguments:
            params["q"] = arguments["q"]
        if "maxResults" in arguments:
            params["maxResults"] = arguments["maxResults"]
        else:
            params["maxResults"] = 20
        if "pageToken" in arguments:
            params["pageToken"] = arguments["pageToken"]
        if "labelIds" in arguments:
            params["labelIds"] = arguments["labelIds"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GMAIL_API_BASE}/threads",
            oauth_cred,
            params=params,
        )
        data = response.json()

        result = {
            "threads": data.get("threads", []),
            "resultSizeEstimate": data.get("resultSizeEstimate", 0),
            "nextPageToken": data.get("nextPageToken"),
        }
        return json.dumps(result, indent=2)

    async def _get_thread(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get a specific thread with all messages."""
        thread_id = arguments["id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GMAIL_API_BASE}/threads/{thread_id}",
            oauth_cred,
            params={"format": "full"},
        )
        data = response.json()

        messages = [self._parse_message(msg) for msg in data.get("messages", [])]
        result = {
            "id": data.get("id"),
            "historyId": data.get("historyId"),
            "messages": messages,
        }
        return json.dumps(result, indent=2)

    async def _list_labels(self, oauth_cred: OAuthCredential) -> str:
        """List all labels."""
        response = await self._make_authenticated_request(
            "GET",
            f"{GMAIL_API_BASE}/labels",
            oauth_cred,
        )
        data = response.json()

        labels = data.get("labels", [])
        result = {
            "labels": labels,
            "count": len(labels),
        }
        return json.dumps(result, indent=2)

    async def _create_label(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new label."""
        payload = {
            "name": arguments["name"],
            "labelListVisibility": arguments.get("labelListVisibility", "labelShow"),
            "messageListVisibility": arguments.get("messageListVisibility", "show"),
        }

        response = await self._make_authenticated_request(
            "POST",
            f"{GMAIL_API_BASE}/labels",
            oauth_cred,
            json=payload,
        )
        data = response.json()

        result = {
            "id": data.get("id"),
            "name": data.get("name"),
            "type": data.get("type"),
            "labelListVisibility": data.get("labelListVisibility"),
            "messageListVisibility": data.get("messageListVisibility"),
        }
        return json.dumps(result, indent=2)

    async def _modify_labels(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Add or remove labels from a message."""
        message_id = arguments["id"]
        payload: Dict[str, Any] = {}

        if "addLabelIds" in arguments:
            payload["addLabelIds"] = arguments["addLabelIds"]
        if "removeLabelIds" in arguments:
            payload["removeLabelIds"] = arguments["removeLabelIds"]

        response = await self._make_authenticated_request(
            "POST",
            f"{GMAIL_API_BASE}/messages/{message_id}/modify",
            oauth_cred,
            json=payload,
        )
        data = response.json()

        result = {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "labelIds": data.get("labelIds", []),
        }
        return json.dumps(result, indent=2)

    async def _trash_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Move a message to the trash."""
        message_id = arguments["id"]

        response = await self._make_authenticated_request(
            "POST",
            f"{GMAIL_API_BASE}/messages/{message_id}/trash",
            oauth_cred,
        )
        data = response.json()

        result = {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "labelIds": data.get("labelIds", []),
        }
        return json.dumps(result, indent=2)

    async def _untrash_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Remove a message from the trash."""
        message_id = arguments["id"]

        response = await self._make_authenticated_request(
            "POST",
            f"{GMAIL_API_BASE}/messages/{message_id}/untrash",
            oauth_cred,
        )
        data = response.json()

        result = {
            "id": data.get("id"),
            "threadId": data.get("threadId"),
            "labelIds": data.get("labelIds", []),
        }
        return json.dumps(result, indent=2)

    async def _create_draft(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a draft email message."""
        message_payload = self._build_mime_message(
            to=arguments["to"],
            subject=arguments["subject"],
            body=arguments["body"],
            cc=arguments.get("cc"),
            bcc=arguments.get("bcc"),
        )

        response = await self._make_authenticated_request(
            "POST",
            f"{GMAIL_API_BASE}/drafts",
            oauth_cred,
            json={"message": message_payload},
        )
        data = response.json()

        result = {
            "id": data.get("id"),
            "message": {
                "id": data.get("message", {}).get("id"),
                "threadId": data.get("message", {}).get("threadId"),
                "labelIds": data.get("message", {}).get("labelIds", []),
            },
        }
        return json.dumps(result, indent=2)

    async def _list_drafts(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List draft messages."""
        params: Dict[str, Any] = {}
        if "maxResults" in arguments:
            params["maxResults"] = arguments["maxResults"]
        else:
            params["maxResults"] = 20
        if "pageToken" in arguments:
            params["pageToken"] = arguments["pageToken"]

        response = await self._make_authenticated_request(
            "GET",
            f"{GMAIL_API_BASE}/drafts",
            oauth_cred,
            params=params,
        )
        data = response.json()

        result = {
            "drafts": data.get("drafts", []),
            "resultSizeEstimate": data.get("resultSizeEstimate", 0),
            "nextPageToken": data.get("nextPageToken"),
        }
        return json.dumps(result, indent=2)
