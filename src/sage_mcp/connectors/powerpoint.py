"""Microsoft PowerPoint connector implementation.

Uses Microsoft Graph API v1.0 for OneDrive file operations on PowerPoint
presentations (.pptx). Provides file management (list, create, copy, move,
delete, export) and content inspection via thumbnails and preview endpoints.

OAuth provider: "microsoft" (Azure AD / Microsoft Entra ID).
"""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
DRIVE_API_BASE = f"{GRAPH_API_BASE}/me/drive"
PPTX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


@register_connector(ConnectorType.POWERPOINT)
class PowerPointConnector(BaseConnector):
    """Microsoft PowerPoint connector for managing presentations via OneDrive."""

    @property
    def display_name(self) -> str:
        return "Microsoft PowerPoint"

    @property
    def description(self) -> str:
        return "Manage Microsoft PowerPoint presentations on OneDrive via Microsoft Graph API"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available PowerPoint tools."""
        tools = [
            types.Tool(
                name="powerpoint_list_presentations",
                description="List PowerPoint (.pptx) files from the user's OneDrive. Optionally filter by search query.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Optional search term to filter presentations by name"
                        },
                        "top": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Maximum number of results to return"
                        }
                    }
                }
            ),
            types.Tool(
                name="powerpoint_get_presentation",
                description="Get metadata for a specific PowerPoint presentation (file size, created/modified dates, download URL, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the presentation"
                        }
                    },
                    "required": ["item_id"]
                }
            ),
            types.Tool(
                name="powerpoint_get_slide_content",
                description="Get a preview/embed URL for a PowerPoint presentation. Useful for inspecting slide content without downloading the binary file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the presentation"
                        }
                    },
                    "required": ["item_id"]
                }
            ),
            types.Tool(
                name="powerpoint_create_presentation",
                description="Create a new empty PowerPoint presentation on OneDrive. The filename should end with .pptx.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the new file (should end with .pptx, e.g., 'My Presentation.pptx')"
                        }
                    },
                    "required": ["filename"]
                }
            ),
            types.Tool(
                name="powerpoint_export_pdf",
                description="Export a PowerPoint presentation as a PDF. Returns the PDF download URL or content metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the presentation to export"
                        }
                    },
                    "required": ["item_id"]
                }
            ),
            types.Tool(
                name="powerpoint_upload_presentation",
                description="Get the upload URL for updating an existing PowerPoint file. Binary file upload is not practical via MCP tool calls; this returns the endpoint and instructions for direct Graph API upload.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the presentation to update"
                        }
                    },
                    "required": ["item_id"]
                }
            ),
            types.Tool(
                name="powerpoint_list_slides",
                description="List slide thumbnails for a PowerPoint presentation. Returns thumbnail URLs and dimensions for each slide.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the presentation"
                        }
                    },
                    "required": ["item_id"]
                }
            ),
            types.Tool(
                name="powerpoint_copy_presentation",
                description="Copy a PowerPoint presentation to a new file, optionally in a different folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the presentation to copy"
                        },
                        "new_name": {
                            "type": "string",
                            "description": "Name for the copied file (e.g., 'Copy of Presentation.pptx')"
                        },
                        "parent_folder_id": {
                            "type": "string",
                            "description": "Optional OneDrive folder ID to copy into. Omit to copy in the same folder."
                        }
                    },
                    "required": ["item_id", "new_name"]
                }
            ),
            types.Tool(
                name="powerpoint_move_presentation",
                description="Move a PowerPoint presentation to a different OneDrive folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the presentation to move"
                        },
                        "destination_folder_id": {
                            "type": "string",
                            "description": "The OneDrive folder ID to move the presentation into"
                        }
                    },
                    "required": ["item_id", "destination_folder_id"]
                }
            ),
            types.Tool(
                name="powerpoint_delete_presentation",
                description="Delete a PowerPoint presentation from OneDrive. This moves the file to the recycle bin.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the presentation to delete"
                        }
                    },
                    "required": ["item_id"]
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available PowerPoint resources.

        Returns an empty list; presentation resources are accessed via tools.
        """
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a PowerPoint tool.

        Args:
            connector: The connector configuration.
            tool_name: Tool name WITHOUT the 'powerpoint_' prefix.
            arguments: Tool arguments from the client.
            oauth_cred: OAuth credential for Microsoft Graph API authentication.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Microsoft OAuth credentials"

        try:
            if tool_name == "list_presentations":
                return await self._list_presentations(arguments, oauth_cred)
            elif tool_name == "get_presentation":
                return await self._get_presentation(arguments, oauth_cred)
            elif tool_name == "get_slide_content":
                return await self._get_slide_content(arguments, oauth_cred)
            elif tool_name == "create_presentation":
                return await self._create_presentation(arguments, oauth_cred)
            elif tool_name == "export_pdf":
                return await self._export_pdf(arguments, oauth_cred)
            elif tool_name == "upload_presentation":
                return await self._upload_presentation(arguments, oauth_cred)
            elif tool_name == "list_slides":
                return await self._list_slides(arguments, oauth_cred)
            elif tool_name == "copy_presentation":
                return await self._copy_presentation(arguments, oauth_cred)
            elif tool_name == "move_presentation":
                return await self._move_presentation(arguments, oauth_cred)
            elif tool_name == "delete_presentation":
                return await self._delete_presentation(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing PowerPoint tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a PowerPoint resource.

        Supports path format: presentation/{item_id}
        Returns presentation file metadata.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Microsoft OAuth credentials"

        try:
            parts = resource_path.split("/", 1)
            if len(parts) != 2 or parts[0] != "presentation":
                return "Error: Invalid resource path. Expected format: presentation/{item_id}"

            item_id = parts[1]

            response = await self._make_authenticated_request(
                "GET",
                f"{DRIVE_API_BASE}/items/{item_id}",
                oauth_cred,
                params={"$select": "id,name,size,createdDateTime,lastModifiedDateTime,webUrl"}
            )
            data = response.json()

            name = data.get("name", "Unknown")
            url = data.get("webUrl", "")
            size = data.get("size", 0)

            return f"Presentation: {name}\nURL: {url}\nSize: {size} bytes"

        except Exception as e:
            return f"Error reading PowerPoint resource: {str(e)}"

    # ------------------------------------------------------------------ #
    # Tool implementation methods
    # ------------------------------------------------------------------ #

    async def _list_presentations(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List PowerPoint files from OneDrive via search."""
        search_query = arguments.get("search_query", ".pptx")
        top = arguments.get("top", 25)

        try:
            # Use the search endpoint to find .pptx files
            if search_query and search_query != ".pptx":
                # Search with user query, filter to pptx
                url = f"{DRIVE_API_BASE}/root/search(q='{search_query}')"
            else:
                # Default: search for all pptx files
                url = f"{DRIVE_API_BASE}/root/search(q='.pptx')"

            response = await self._make_authenticated_request(
                "GET",
                url,
                oauth_cred,
                params={
                    "$top": top,
                    "$select": "id,name,size,createdDateTime,lastModifiedDateTime,webUrl,parentReference"
                }
            )

            items = response.json().get("value", [])

            # Filter to only .pptx files
            presentations = []
            for item in items:
                name = item.get("name", "")
                if name.lower().endswith(".pptx"):
                    presentations.append({
                        "id": item.get("id"),
                        "name": name,
                        "size": item.get("size"),
                        "created_time": item.get("createdDateTime"),
                        "modified_time": item.get("lastModifiedDateTime"),
                        "web_url": item.get("webUrl"),
                        "parent_path": item.get("parentReference", {}).get("path")
                    })

            return json.dumps({"presentations": presentations, "count": len(presentations)}, indent=2)

        except Exception as e:
            return f"Error listing presentations: {str(e)}"

    async def _get_presentation(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get presentation metadata from OneDrive."""
        item_id = arguments["item_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{DRIVE_API_BASE}/items/{item_id}",
                oauth_cred,
                params={
                    "$select": "id,name,size,createdDateTime,lastModifiedDateTime,"
                               "webUrl,createdBy,lastModifiedBy,parentReference,file"
                }
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "size": data.get("size"),
                "mime_type": data.get("file", {}).get("mimeType"),
                "created_time": data.get("createdDateTime"),
                "modified_time": data.get("lastModifiedDateTime"),
                "web_url": data.get("webUrl"),
                "created_by": data.get("createdBy", {}).get("user", {}).get("displayName"),
                "modified_by": data.get("lastModifiedBy", {}).get("user", {}).get("displayName"),
                "parent_path": data.get("parentReference", {}).get("path")
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting presentation: {str(e)}"

    async def _get_slide_content(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get a preview/embed URL for inspecting presentation content.

        Uses the Graph API preview endpoint to get an embeddable URL.
        Full binary parsing of .pptx files is not performed to avoid
        heavyweight dependencies.
        """
        item_id = arguments["item_id"]

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{DRIVE_API_BASE}/items/{item_id}/preview",
                oauth_cred,
                json={}
            )
            data = response.json()

            result = {
                "item_id": item_id,
                "embed_url": data.get("getUrl"),
                "post_url": data.get("postUrl"),
                "post_parameters": data.get("postParameters"),
                "note": "Use the embed_url to view the presentation in a browser. "
                        "For programmatic slide text extraction, download the file "
                        "via the Graph API and parse the .pptx XML content."
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting slide content: {str(e)}"

    async def _create_presentation(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new empty PowerPoint presentation on OneDrive."""
        filename = arguments["filename"]

        # Ensure the filename ends with .pptx
        if not filename.lower().endswith(".pptx"):
            filename += ".pptx"

        try:
            # Create an empty file with the correct MIME type.
            # An empty byte payload with the PPTX content type tells OneDrive
            # to create a blank PowerPoint file.
            response = await self._make_authenticated_request(
                "PUT",
                f"{DRIVE_API_BASE}/root:/{filename}:/content",
                oauth_cred,
                content=b"",
                headers={"Content-Type": PPTX_MIME_TYPE}
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "size": data.get("size"),
                "web_url": data.get("webUrl"),
                "created_time": data.get("createdDateTime"),
                "note": "An empty PowerPoint file has been created. Open it via "
                        "the web_url to add slides and content."
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error creating presentation: {str(e)}"

    async def _export_pdf(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Export a presentation as PDF via the Graph API content endpoint."""
        item_id = arguments["item_id"]

        try:
            # The Graph API supports format conversion via the content endpoint.
            # With format=pdf, it returns the converted PDF content.
            # We request it but don't download the full binary; instead we
            # capture the redirect URL or response metadata.
            # First, get the file metadata for context
            meta_response = await self._make_authenticated_request(
                "GET",
                f"{DRIVE_API_BASE}/items/{item_id}",
                oauth_cred,
                params={"$select": "id,name,size,webUrl"}
            )
            meta = meta_response.json()

            result = {
                "item_id": item_id,
                "source_name": meta.get("name"),
                "export_url": f"{DRIVE_API_BASE}/items/{item_id}/content?format=pdf",
                "method": "GET",
                "auth": "Bearer token required in Authorization header",
                "note": "Use the export_url with a GET request and your OAuth token "
                        "to download the PDF. The Graph API will convert the "
                        "presentation and return the PDF binary content."
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error exporting presentation to PDF: {str(e)}"

    async def _upload_presentation(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Provide upload URL and instructions for updating a presentation file.

        Binary file upload is not practical via MCP tool calls. This tool returns
        the upload endpoint and instructions for using the Graph API directly.
        """
        item_id = arguments["item_id"]

        try:
            # Get current file metadata for context
            response = await self._make_authenticated_request(
                "GET",
                f"{DRIVE_API_BASE}/items/{item_id}",
                oauth_cred,
                params={"$select": "id,name,size,webUrl"}
            )
            data = response.json()

            result = {
                "item_id": item_id,
                "current_name": data.get("name"),
                "current_size": data.get("size"),
                "web_url": data.get("webUrl"),
                "upload_url": f"{DRIVE_API_BASE}/items/{item_id}/content",
                "upload_method": "PUT",
                "content_type": PPTX_MIME_TYPE,
                "auth": "Bearer token required in Authorization header",
                "note": "To upload/update the file, send a PUT request to the "
                        "upload_url with the .pptx binary content in the request "
                        "body. For files larger than 4MB, use the resumable upload "
                        "session endpoint: POST /me/drive/items/{item_id}/createUploadSession"
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting upload info: {str(e)}"

    async def _list_slides(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List slide thumbnails for a presentation.

        Uses the Graph API thumbnails endpoint to retrieve thumbnail
        images for each slide/page in the presentation.
        """
        item_id = arguments["item_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{DRIVE_API_BASE}/items/{item_id}/thumbnails",
                oauth_cred
            )
            data = response.json()

            thumbnail_sets = data.get("value", [])
            slides = []
            for i, thumb_set in enumerate(thumbnail_sets):
                slide_info = {
                    "slide_number": i + 1,
                    "id": thumb_set.get("id"),
                }

                # Each thumbnail set can have small, medium, large sizes
                for size in ("small", "medium", "large"):
                    thumb = thumb_set.get(size)
                    if thumb:
                        slide_info[size] = {
                            "url": thumb.get("url"),
                            "width": thumb.get("width"),
                            "height": thumb.get("height")
                        }

                slides.append(slide_info)

            result = {
                "item_id": item_id,
                "slides": slides,
                "slide_count": len(slides),
                "note": "Each slide has small, medium, and large thumbnail URLs. "
                        "Thumbnail URLs are temporary and will expire."
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error listing slides: {str(e)}"

    async def _copy_presentation(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Copy a presentation to a new file."""
        item_id = arguments["item_id"]
        new_name = arguments["new_name"]
        parent_folder_id = arguments.get("parent_folder_id")

        try:
            body: Dict[str, Any] = {"name": new_name}

            if parent_folder_id:
                body["parentReference"] = {"id": parent_folder_id}

            response = await self._make_authenticated_request(
                "POST",
                f"{DRIVE_API_BASE}/items/{item_id}/copy",
                oauth_cred,
                json=body
            )

            # The copy endpoint returns 202 Accepted with a Location header
            # for monitoring the async operation. The response body may be empty.
            location = None
            if hasattr(response, "headers"):
                location = response.headers.get("Location")

            result = {
                "status": "accepted",
                "item_id": item_id,
                "new_name": new_name,
                "monitor_url": location,
                "note": "Copy operation is asynchronous. Use the monitor_url "
                        "to check the status of the copy operation."
            }

            # If the response has a body (some Graph versions return it)
            try:
                data = response.json()
                if data:
                    result["copy_item"] = data
            except Exception:
                pass

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error copying presentation: {str(e)}"

    async def _move_presentation(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Move a presentation to a different OneDrive folder."""
        item_id = arguments["item_id"]
        destination_folder_id = arguments["destination_folder_id"]

        try:
            response = await self._make_authenticated_request(
                "PATCH",
                f"{DRIVE_API_BASE}/items/{item_id}",
                oauth_cred,
                json={
                    "parentReference": {"id": destination_folder_id}
                }
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "web_url": data.get("webUrl"),
                "new_parent_path": data.get("parentReference", {}).get("path"),
                "modified_time": data.get("lastModifiedDateTime")
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error moving presentation: {str(e)}"

    async def _delete_presentation(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Delete a presentation from OneDrive (moves to recycle bin)."""
        item_id = arguments["item_id"]

        try:
            await self._make_authenticated_request(
                "DELETE",
                f"{DRIVE_API_BASE}/items/{item_id}",
                oauth_cred
            )

            return json.dumps({
                "success": True,
                "item_id": item_id,
                "message": "Presentation deleted (moved to recycle bin)"
            }, indent=2)

        except Exception as e:
            return f"Error deleting presentation: {str(e)}"
