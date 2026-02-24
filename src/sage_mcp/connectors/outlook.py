"""Microsoft Outlook connector implementation using Microsoft Graph API v1.0."""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0/me"


@register_connector(ConnectorType.OUTLOOK)
class OutlookConnector(BaseConnector):
    """Microsoft Outlook connector for managing email via Microsoft Graph API."""

    @property
    def display_name(self) -> str:
        return "Microsoft Outlook"

    @property
    def description(self) -> str:
        return "Read, send, and manage emails via Microsoft Outlook"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Outlook tools."""
        tools = [
            types.Tool(
                name="outlook_list_messages",
                description="List messages from inbox or a specific mail folder. Supports OData query parameters for filtering, sorting, and field selection.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_id": {
                            "type": "string",
                            "default": "inbox",
                            "description": "Mail folder ID or well-known name (inbox, drafts, sentitems, deleteditems, junkemail, archive)"
                        },
                        "top": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of messages to return"
                        },
                        "filter": {
                            "type": "string",
                            "description": "OData $filter expression (e.g., \"isRead eq false\", \"hasAttachments eq true\")"
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of fields to return (e.g., \"subject,from,receivedDateTime,isRead\")"
                        },
                        "order_by": {
                            "type": "string",
                            "default": "receivedDateTime desc",
                            "description": "OData $orderby expression (e.g., \"receivedDateTime desc\", \"subject asc\")"
                        }
                    }
                }
            ),
            types.Tool(
                name="outlook_get_message",
                description="Get a specific email message by its ID, including full body content and metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The unique ID of the message"
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of fields to return (e.g., \"subject,body,from,toRecipients\")"
                        }
                    },
                    "required": ["message_id"]
                }
            ),
            types.Tool(
                name="outlook_send_message",
                description="Send a new email message. Supports HTML and text body content, with CC and BCC recipients.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Email subject line"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body content (HTML or plain text depending on content_type)"
                        },
                        "to_recipients": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of recipient email addresses"
                        },
                        "cc_recipients": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of CC recipient email addresses"
                        },
                        "bcc_recipients": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of BCC recipient email addresses"
                        },
                        "content_type": {
                            "type": "string",
                            "enum": ["HTML", "Text"],
                            "default": "HTML",
                            "description": "Body content type"
                        }
                    },
                    "required": ["subject", "body", "to_recipients"]
                }
            ),
            types.Tool(
                name="outlook_reply_to_message",
                description="Reply to an email message. Can reply to sender only or reply all.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The unique ID of the message to reply to"
                        },
                        "comment": {
                            "type": "string",
                            "description": "The reply body content"
                        },
                        "reply_all": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to reply to all recipients"
                        }
                    },
                    "required": ["message_id", "comment"]
                }
            ),
            types.Tool(
                name="outlook_forward_message",
                description="Forward an email message to one or more recipients with an optional comment.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The unique ID of the message to forward"
                        },
                        "to_recipients": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of recipient email addresses to forward to"
                        },
                        "comment": {
                            "type": "string",
                            "description": "Optional comment to include with the forwarded message"
                        }
                    },
                    "required": ["message_id", "to_recipients"]
                }
            ),
            types.Tool(
                name="outlook_delete_message",
                description="Delete an email message. Moves to Deleted Items folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The unique ID of the message to delete"
                        }
                    },
                    "required": ["message_id"]
                }
            ),
            types.Tool(
                name="outlook_move_message",
                description="Move an email message to a different mail folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The unique ID of the message to move"
                        },
                        "destination_folder_id": {
                            "type": "string",
                            "description": "The ID or well-known name of the destination folder (e.g., \"archive\", \"deleteditems\")"
                        }
                    },
                    "required": ["message_id", "destination_folder_id"]
                }
            ),
            types.Tool(
                name="outlook_list_folders",
                description="List all mail folders in the user's mailbox, including folder IDs, display names, and message counts.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="outlook_create_folder",
                description="Create a new mail folder. Can create top-level folders or child folders within an existing folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "display_name": {
                            "type": "string",
                            "description": "Display name for the new folder"
                        },
                        "parent_folder_id": {
                            "type": "string",
                            "description": "Optional parent folder ID to create a child folder. Omit for a top-level folder."
                        }
                    },
                    "required": ["display_name"]
                }
            ),
            types.Tool(
                name="outlook_list_attachments",
                description="List all attachments on a specific email message, including file names, sizes, and content types.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The unique ID of the message"
                        }
                    },
                    "required": ["message_id"]
                }
            ),
            types.Tool(
                name="outlook_get_attachment",
                description="Get metadata and content for a specific attachment on an email message.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The unique ID of the message"
                        },
                        "attachment_id": {
                            "type": "string",
                            "description": "The unique ID of the attachment"
                        }
                    },
                    "required": ["message_id", "attachment_id"]
                }
            ),
            types.Tool(
                name="outlook_create_draft",
                description="Create a draft email message that can be edited and sent later.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Email subject line"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body content (HTML or plain text depending on content_type)"
                        },
                        "to_recipients": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of recipient email addresses"
                        },
                        "cc_recipients": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of CC recipient email addresses"
                        },
                        "content_type": {
                            "type": "string",
                            "enum": ["HTML", "Text"],
                            "default": "HTML",
                            "description": "Body content type"
                        }
                    },
                    "required": ["subject", "body", "to_recipients"]
                }
            ),
            types.Tool(
                name="outlook_search_messages",
                description="Search email messages using Microsoft Graph $search query syntax. Searches across subject, body, and other fields.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string (e.g., \"budget report\", \"from:user@example.com\")"
                        },
                        "top": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of results to return"
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="outlook_flag_message",
                description="Flag, unflag, or mark a message as complete. Flagged messages appear in the flagged email view.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The unique ID of the message"
                        },
                        "flag_status": {
                            "type": "string",
                            "enum": ["flagged", "complete", "notFlagged"],
                            "description": "Flag status to set on the message"
                        }
                    },
                    "required": ["message_id", "flag_status"]
                }
            ),
            types.Tool(
                name="outlook_list_focused_inbox",
                description="List messages from the Focused Inbox. Returns only messages classified as 'focused' by Outlook's AI filtering.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "top": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Number of messages to return"
                        },
                        "filter": {
                            "type": "string",
                            "description": "Additional OData $filter expression to apply on top of focused inbox filter"
                        }
                    }
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Outlook resources.

        Returns an empty list; Outlook resources are accessed dynamically via tools.
        """
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute an Outlook tool.

        Args:
            connector: The connector configuration.
            tool_name: Tool name WITHOUT the 'outlook_' prefix.
            arguments: Tool arguments from the client.
            oauth_cred: OAuth credential for Microsoft Graph API authentication.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Microsoft OAuth credentials"

        try:
            if tool_name == "list_messages":
                return await self._list_messages(arguments, oauth_cred)
            elif tool_name == "get_message":
                return await self._get_message(arguments, oauth_cred)
            elif tool_name == "send_message":
                return await self._send_message(arguments, oauth_cred)
            elif tool_name == "reply_to_message":
                return await self._reply_to_message(arguments, oauth_cred)
            elif tool_name == "forward_message":
                return await self._forward_message(arguments, oauth_cred)
            elif tool_name == "delete_message":
                return await self._delete_message(arguments, oauth_cred)
            elif tool_name == "move_message":
                return await self._move_message(arguments, oauth_cred)
            elif tool_name == "list_folders":
                return await self._list_folders(arguments, oauth_cred)
            elif tool_name == "create_folder":
                return await self._create_folder(arguments, oauth_cred)
            elif tool_name == "list_attachments":
                return await self._list_attachments(arguments, oauth_cred)
            elif tool_name == "get_attachment":
                return await self._get_attachment(arguments, oauth_cred)
            elif tool_name == "create_draft":
                return await self._create_draft(arguments, oauth_cred)
            elif tool_name == "search_messages":
                return await self._search_messages(arguments, oauth_cred)
            elif tool_name == "flag_message":
                return await self._flag_message(arguments, oauth_cred)
            elif tool_name == "list_focused_inbox":
                return await self._list_focused_inbox(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Outlook tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read an Outlook resource.

        Supports path format: message/{message_id}
        Returns message subject and snippet.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Microsoft OAuth credentials"

        try:
            parts = resource_path.split("/", 1)
            if len(parts) != 2 or parts[0] != "message":
                return "Error: Invalid resource path. Expected format: message/{message_id}"

            message_id = parts[1]

            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/messages/{message_id}",
                oauth_cred,
                params={"$select": "subject,from,receivedDateTime,bodyPreview"}
            )
            data = response.json()

            subject = data.get("subject", "(No subject)")
            from_addr = data.get("from", {}).get("emailAddress", {}).get("address", "Unknown")
            received = data.get("receivedDateTime", "")
            preview = data.get("bodyPreview", "")

            return f"Subject: {subject}\nFrom: {from_addr}\nReceived: {received}\n\n{preview}"

        except Exception as e:
            return f"Error reading Outlook resource: {str(e)}"

    # ------------------------------------------------------------------ #
    # Helper methods
    # ------------------------------------------------------------------ #

    @staticmethod
    def _format_recipients(emails: List[str]) -> List[Dict[str, Any]]:
        """Convert a list of email strings to Microsoft Graph recipient format.

        Args:
            emails: List of email address strings.

        Returns:
            List of recipient dicts in the format:
            [{"emailAddress": {"address": "user@example.com"}}, ...]
        """
        return [{"emailAddress": {"address": email}} for email in emails]

    @staticmethod
    def _format_message_summary(message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract a concise summary from a Graph API message object.

        Args:
            message: Raw message dict from Microsoft Graph API.

        Returns:
            Dict with normalized field names for consistent output.
        """
        from_email = message.get("from", {}).get("emailAddress", {})
        to_recipients = [
            r.get("emailAddress", {}).get("address", "")
            for r in message.get("toRecipients", [])
        ]

        return {
            "id": message.get("id"),
            "subject": message.get("subject"),
            "from": from_email.get("address"),
            "from_name": from_email.get("name"),
            "to": to_recipients,
            "received_date_time": message.get("receivedDateTime"),
            "is_read": message.get("isRead"),
            "has_attachments": message.get("hasAttachments"),
            "importance": message.get("importance"),
            "body_preview": message.get("bodyPreview"),
            "flag": message.get("flag", {}).get("flagStatus"),
            "inference_classification": message.get("inferenceClassification"),
        }

    # ------------------------------------------------------------------ #
    # Tool implementation methods
    # ------------------------------------------------------------------ #

    async def _list_messages(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List messages from inbox or a specific mail folder."""
        folder_id = arguments.get("folder_id", "inbox")
        top = arguments.get("top", 25)
        filter_expr = arguments.get("filter")
        select = arguments.get("select")
        order_by = arguments.get("order_by", "receivedDateTime desc")

        try:
            params: Dict[str, Any] = {
                "$top": top,
                "$orderby": order_by,
            }
            if filter_expr:
                params["$filter"] = filter_expr
            if select:
                params["$select"] = select

            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/mailFolders/{folder_id}/messages",
                oauth_cred,
                params=params
            )
            data = response.json()

            messages = [
                self._format_message_summary(msg)
                for msg in data.get("value", [])
            ]

            return json.dumps({"messages": messages, "count": len(messages)}, indent=2)

        except Exception as e:
            return f"Error listing messages: {str(e)}"

    async def _get_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get a specific message by ID."""
        message_id = arguments["message_id"]
        select = arguments.get("select")

        try:
            params: Dict[str, Any] = {}
            if select:
                params["$select"] = select

            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/messages/{message_id}",
                oauth_cred,
                params=params if params else None
            )
            data = response.json()

            from_email = data.get("from", {}).get("emailAddress", {})
            to_recipients = [
                {"address": r.get("emailAddress", {}).get("address"),
                 "name": r.get("emailAddress", {}).get("name")}
                for r in data.get("toRecipients", [])
            ]
            cc_recipients = [
                {"address": r.get("emailAddress", {}).get("address"),
                 "name": r.get("emailAddress", {}).get("name")}
                for r in data.get("ccRecipients", [])
            ]

            result = {
                "id": data.get("id"),
                "subject": data.get("subject"),
                "from": {"address": from_email.get("address"), "name": from_email.get("name")},
                "to_recipients": to_recipients,
                "cc_recipients": cc_recipients,
                "received_date_time": data.get("receivedDateTime"),
                "sent_date_time": data.get("sentDateTime"),
                "is_read": data.get("isRead"),
                "has_attachments": data.get("hasAttachments"),
                "importance": data.get("importance"),
                "body_content_type": data.get("body", {}).get("contentType"),
                "body": data.get("body", {}).get("content"),
                "body_preview": data.get("bodyPreview"),
                "flag": data.get("flag", {}).get("flagStatus"),
                "categories": data.get("categories", []),
                "inference_classification": data.get("inferenceClassification"),
                "web_link": data.get("webLink"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting message: {str(e)}"

    async def _send_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Send a new email message via the sendMail endpoint."""
        subject = arguments["subject"]
        body = arguments["body"]
        to_recipients = arguments["to_recipients"]
        cc_recipients = arguments.get("cc_recipients", [])
        bcc_recipients = arguments.get("bcc_recipients", [])
        content_type = arguments.get("content_type", "HTML")

        try:
            message: Dict[str, Any] = {
                "subject": subject,
                "body": {
                    "contentType": content_type,
                    "content": body
                },
                "toRecipients": self._format_recipients(to_recipients),
            }

            if cc_recipients:
                message["ccRecipients"] = self._format_recipients(cc_recipients)
            if bcc_recipients:
                message["bccRecipients"] = self._format_recipients(bcc_recipients)

            await self._make_authenticated_request(
                "POST",
                f"{GRAPH_API_BASE}/sendMail",
                oauth_cred,
                json={
                    "message": message,
                    "saveToSentItems": True
                }
            )

            return json.dumps({
                "success": True,
                "message": f"Email sent to {', '.join(to_recipients)}",
                "subject": subject
            }, indent=2)

        except Exception as e:
            return f"Error sending message: {str(e)}"

    async def _reply_to_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Reply to an email message."""
        message_id = arguments["message_id"]
        comment = arguments["comment"]
        reply_all = arguments.get("reply_all", False)

        try:
            action = "replyAll" if reply_all else "reply"

            await self._make_authenticated_request(
                "POST",
                f"{GRAPH_API_BASE}/messages/{message_id}/{action}",
                oauth_cred,
                json={"comment": comment}
            )

            return json.dumps({
                "success": True,
                "message": f"{'Reply all' if reply_all else 'Reply'} sent",
                "message_id": message_id
            }, indent=2)

        except Exception as e:
            return f"Error replying to message: {str(e)}"

    async def _forward_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Forward an email message."""
        message_id = arguments["message_id"]
        to_recipients = arguments["to_recipients"]
        comment = arguments.get("comment", "")

        try:
            body: Dict[str, Any] = {
                "toRecipients": self._format_recipients(to_recipients),
            }
            if comment:
                body["comment"] = comment

            await self._make_authenticated_request(
                "POST",
                f"{GRAPH_API_BASE}/messages/{message_id}/forward",
                oauth_cred,
                json=body
            )

            return json.dumps({
                "success": True,
                "message": f"Message forwarded to {', '.join(to_recipients)}",
                "message_id": message_id
            }, indent=2)

        except Exception as e:
            return f"Error forwarding message: {str(e)}"

    async def _delete_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Delete an email message."""
        message_id = arguments["message_id"]

        try:
            await self._make_authenticated_request(
                "DELETE",
                f"{GRAPH_API_BASE}/messages/{message_id}",
                oauth_cred
            )

            return json.dumps({
                "success": True,
                "message": "Message deleted",
                "message_id": message_id
            }, indent=2)

        except Exception as e:
            return f"Error deleting message: {str(e)}"

    async def _move_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Move a message to a different mail folder."""
        message_id = arguments["message_id"]
        destination_folder_id = arguments["destination_folder_id"]

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{GRAPH_API_BASE}/messages/{message_id}/move",
                oauth_cred,
                json={"destinationId": destination_folder_id}
            )
            data = response.json()

            return json.dumps({
                "success": True,
                "message": f"Message moved to folder '{destination_folder_id}'",
                "new_message_id": data.get("id"),
                "parent_folder_id": data.get("parentFolderId")
            }, indent=2)

        except Exception as e:
            return f"Error moving message: {str(e)}"

    async def _list_folders(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List mail folders in the user's mailbox."""
        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/mailFolders",
                oauth_cred,
                params={"$top": 100}
            )
            data = response.json()

            folders = []
            for folder in data.get("value", []):
                folders.append({
                    "id": folder.get("id"),
                    "display_name": folder.get("displayName"),
                    "parent_folder_id": folder.get("parentFolderId"),
                    "child_folder_count": folder.get("childFolderCount"),
                    "total_item_count": folder.get("totalItemCount"),
                    "unread_item_count": folder.get("unreadItemCount"),
                })

            return json.dumps({"folders": folders, "count": len(folders)}, indent=2)

        except Exception as e:
            return f"Error listing folders: {str(e)}"

    async def _create_folder(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new mail folder."""
        display_name = arguments["display_name"]
        parent_folder_id = arguments.get("parent_folder_id")

        try:
            if parent_folder_id:
                url = f"{GRAPH_API_BASE}/mailFolders/{parent_folder_id}/childFolders"
            else:
                url = f"{GRAPH_API_BASE}/mailFolders"

            response = await self._make_authenticated_request(
                "POST",
                url,
                oauth_cred,
                json={"displayName": display_name}
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "display_name": data.get("displayName"),
                "parent_folder_id": data.get("parentFolderId"),
                "child_folder_count": data.get("childFolderCount"),
                "total_item_count": data.get("totalItemCount"),
                "unread_item_count": data.get("unreadItemCount"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error creating folder: {str(e)}"

    async def _list_attachments(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List attachments on a specific message."""
        message_id = arguments["message_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/messages/{message_id}/attachments",
                oauth_cred
            )
            data = response.json()

            attachments = []
            for att in data.get("value", []):
                attachments.append({
                    "id": att.get("id"),
                    "name": att.get("name"),
                    "content_type": att.get("contentType"),
                    "size": att.get("size"),
                    "is_inline": att.get("isInline"),
                    "last_modified_date_time": att.get("lastModifiedDateTime"),
                })

            return json.dumps({"attachments": attachments, "count": len(attachments)}, indent=2)

        except Exception as e:
            return f"Error listing attachments: {str(e)}"

    async def _get_attachment(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get a specific attachment's metadata and content."""
        message_id = arguments["message_id"]
        attachment_id = arguments["attachment_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/messages/{message_id}/attachments/{attachment_id}",
                oauth_cred
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "content_type": data.get("contentType"),
                "size": data.get("size"),
                "is_inline": data.get("isInline"),
                "last_modified_date_time": data.get("lastModifiedDateTime"),
                "content_bytes": data.get("contentBytes"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting attachment: {str(e)}"

    async def _create_draft(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a draft email message."""
        subject = arguments["subject"]
        body = arguments["body"]
        to_recipients = arguments["to_recipients"]
        cc_recipients = arguments.get("cc_recipients", [])
        content_type = arguments.get("content_type", "HTML")

        try:
            draft: Dict[str, Any] = {
                "subject": subject,
                "body": {
                    "contentType": content_type,
                    "content": body
                },
                "toRecipients": self._format_recipients(to_recipients),
            }

            if cc_recipients:
                draft["ccRecipients"] = self._format_recipients(cc_recipients)

            response = await self._make_authenticated_request(
                "POST",
                f"{GRAPH_API_BASE}/messages",
                oauth_cred,
                json=draft
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "subject": data.get("subject"),
                "is_draft": data.get("isDraft"),
                "created_date_time": data.get("createdDateTime"),
                "web_link": data.get("webLink"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error creating draft: {str(e)}"

    async def _search_messages(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search messages using OData $search."""
        query = arguments["query"]
        top = arguments.get("top", 25)

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/messages",
                oauth_cred,
                params={
                    "$search": f'"{query}"',
                    "$top": top,
                }
            )
            data = response.json()

            messages = [
                self._format_message_summary(msg)
                for msg in data.get("value", [])
            ]

            return json.dumps({"messages": messages, "count": len(messages), "query": query}, indent=2)

        except Exception as e:
            return f"Error searching messages: {str(e)}"

    async def _flag_message(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Flag or unflag an email message."""
        message_id = arguments["message_id"]
        flag_status = arguments["flag_status"]

        try:
            response = await self._make_authenticated_request(
                "PATCH",
                f"{GRAPH_API_BASE}/messages/{message_id}",
                oauth_cred,
                json={
                    "flag": {
                        "flagStatus": flag_status
                    }
                }
            )
            data = response.json()

            return json.dumps({
                "success": True,
                "message_id": data.get("id"),
                "flag_status": data.get("flag", {}).get("flagStatus"),
                "subject": data.get("subject"),
            }, indent=2)

        except Exception as e:
            return f"Error flagging message: {str(e)}"

    async def _list_focused_inbox(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List messages from the Focused Inbox."""
        top = arguments.get("top", 25)
        additional_filter = arguments.get("filter")

        try:
            filter_expr = "inferenceClassification eq 'focused'"
            if additional_filter:
                filter_expr = f"{filter_expr} and {additional_filter}"

            response = await self._make_authenticated_request(
                "GET",
                f"{GRAPH_API_BASE}/messages",
                oauth_cred,
                params={
                    "$filter": filter_expr,
                    "$top": top,
                    "$orderby": "receivedDateTime desc",
                }
            )
            data = response.json()

            messages = [
                self._format_message_summary(msg)
                for msg in data.get("value", [])
            ]

            return json.dumps({"messages": messages, "count": len(messages)}, indent=2)

        except Exception as e:
            return f"Error listing focused inbox: {str(e)}"
