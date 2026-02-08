"""Google Slides connector implementation."""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


@register_connector(ConnectorType.GOOGLE_SLIDES)
class GoogleSlidesConnector(BaseConnector):
    """Google Slides connector for creating and managing presentations."""

    @property
    def display_name(self) -> str:
        return "Google Slides"

    @property
    def description(self) -> str:
        return "Create and manage Google Slides presentations"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Google Slides tools."""
        tools = [
            types.Tool(
                name="google_slides_list_presentations",
                description="List Google Slides presentations accessible to the user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of presentations to return"
                        },
                        "order_by": {
                            "type": "string",
                            "enum": [
                                "modifiedTime",
                                "modifiedTime desc",
                                "name",
                                "name desc",
                                "createdTime",
                                "createdTime desc"
                            ],
                            "default": "modifiedTime desc",
                            "description": "Sort order for presentations"
                        }
                    }
                }
            ),
            types.Tool(
                name="google_slides_get_presentation",
                description="Get detailed metadata and structure of a Google Slides presentation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "presentation_id": {
                            "type": "string",
                            "description": "The ID of the Google Slides presentation"
                        }
                    },
                    "required": ["presentation_id"]
                }
            ),
            types.Tool(
                name="google_slides_get_slide",
                description="Get details of a specific slide by its 0-based index in the presentation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "presentation_id": {
                            "type": "string",
                            "description": "The ID of the Google Slides presentation"
                        },
                        "slide_index": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "0-based index of the slide to retrieve"
                        }
                    },
                    "required": ["presentation_id", "slide_index"]
                }
            ),
            types.Tool(
                name="google_slides_create_presentation",
                description="Create a new Google Slides presentation with a title",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the new presentation"
                        }
                    },
                    "required": ["title"]
                }
            ),
            types.Tool(
                name="google_slides_add_slide",
                description="Add a new slide to a presentation at an optional position with a layout",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "presentation_id": {
                            "type": "string",
                            "description": "The ID of the Google Slides presentation"
                        },
                        "insertion_index": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "0-based index where the new slide should be inserted. Omit to append at end."
                        },
                        "layout": {
                            "type": "string",
                            "enum": [
                                "BLANK",
                                "TITLE",
                                "TITLE_AND_BODY",
                                "TITLE_ONLY",
                                "CAPTION_ONLY",
                                "MAIN_POINT",
                                "BIG_NUMBER",
                                "SECTION_HEADER",
                                "SECTION_TITLE_AND_DESCRIPTION",
                                "ONE_COLUMN_TEXT",
                                "TITLE_AND_TWO_COLUMNS"
                            ],
                            "default": "BLANK",
                            "description": "Predefined slide layout to use"
                        }
                    },
                    "required": ["presentation_id"]
                }
            ),
            types.Tool(
                name="google_slides_delete_slide",
                description="Delete a slide from a presentation by its object ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "presentation_id": {
                            "type": "string",
                            "description": "The ID of the Google Slides presentation"
                        },
                        "slide_object_id": {
                            "type": "string",
                            "description": "The object ID of the slide to delete"
                        }
                    },
                    "required": ["presentation_id", "slide_object_id"]
                }
            ),
            types.Tool(
                name="google_slides_add_text",
                description="Insert text into a shape (text box) on a slide by its object ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "presentation_id": {
                            "type": "string",
                            "description": "The ID of the Google Slides presentation"
                        },
                        "object_id": {
                            "type": "string",
                            "description": "The object ID of the shape/text box to insert text into"
                        },
                        "text": {
                            "type": "string",
                            "description": "The text to insert"
                        },
                        "insertion_index": {
                            "type": "integer",
                            "minimum": 0,
                            "default": 0,
                            "description": "Character index within the shape where text should be inserted (0-based)"
                        }
                    },
                    "required": ["presentation_id", "object_id", "text"]
                }
            ),
            types.Tool(
                name="google_slides_replace_text",
                description="Find and replace all occurrences of text across the entire presentation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "presentation_id": {
                            "type": "string",
                            "description": "The ID of the Google Slides presentation"
                        },
                        "find_text": {
                            "type": "string",
                            "description": "The text to search for"
                        },
                        "replace_text": {
                            "type": "string",
                            "description": "The text to replace with"
                        },
                        "match_case": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether the search should be case-sensitive"
                        }
                    },
                    "required": ["presentation_id", "find_text", "replace_text"]
                }
            ),
            types.Tool(
                name="google_slides_get_speaker_notes",
                description="Get the speaker notes for a specific slide by its 0-based index",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "presentation_id": {
                            "type": "string",
                            "description": "The ID of the Google Slides presentation"
                        },
                        "slide_index": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "0-based index of the slide"
                        }
                    },
                    "required": ["presentation_id", "slide_index"]
                }
            ),
            types.Tool(
                name="google_slides_update_speaker_notes",
                description="Update the speaker notes for a specific slide",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "presentation_id": {
                            "type": "string",
                            "description": "The ID of the Google Slides presentation"
                        },
                        "slide_object_id": {
                            "type": "string",
                            "description": "The object ID of the slide whose notes to update"
                        },
                        "notes_object_id": {
                            "type": "string",
                            "description": "The object ID of the notes shape (from slideProperties.notesPage)"
                        },
                        "text": {
                            "type": "string",
                            "description": "The new speaker notes text"
                        }
                    },
                    "required": ["presentation_id", "notes_object_id", "text"]
                }
            ),
            types.Tool(
                name="google_slides_duplicate_slide",
                description="Duplicate an existing slide in the presentation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "presentation_id": {
                            "type": "string",
                            "description": "The ID of the Google Slides presentation"
                        },
                        "slide_object_id": {
                            "type": "string",
                            "description": "The object ID of the slide to duplicate"
                        }
                    },
                    "required": ["presentation_id", "slide_object_id"]
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Google Slides resources. Returns empty list."""
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Google Slides tool.

        Args:
            connector: The connector configuration.
            tool_name: Tool name WITHOUT the 'google_slides_' prefix.
            arguments: Tool arguments from the client.
            oauth_cred: OAuth credential for Google API access.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            if tool_name == "list_presentations":
                return await self._list_presentations(arguments, oauth_cred)
            elif tool_name == "get_presentation":
                return await self._get_presentation(arguments, oauth_cred)
            elif tool_name == "get_slide":
                return await self._get_slide(arguments, oauth_cred)
            elif tool_name == "create_presentation":
                return await self._create_presentation(arguments, oauth_cred)
            elif tool_name == "add_slide":
                return await self._add_slide(arguments, oauth_cred)
            elif tool_name == "delete_slide":
                return await self._delete_slide(arguments, oauth_cred)
            elif tool_name == "add_text":
                return await self._add_text(arguments, oauth_cred)
            elif tool_name == "replace_text":
                return await self._replace_text(arguments, oauth_cred)
            elif tool_name == "get_speaker_notes":
                return await self._get_speaker_notes(arguments, oauth_cred)
            elif tool_name == "update_speaker_notes":
                return await self._update_speaker_notes(arguments, oauth_cred)
            elif tool_name == "duplicate_slide":
                return await self._duplicate_slide(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Google Slides tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Google Slides resource.

        Expected path format: presentation/{presentation_id}
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            parts = resource_path.split("/", 1)
            if len(parts) != 2 or parts[0] != "presentation":
                return "Error: Invalid resource path. Expected format: presentation/{presentation_id}"

            presentation_id = parts[1]

            response = await self._make_authenticated_request(
                "GET",
                f"https://slides.googleapis.com/v1/presentations/{presentation_id}",
                oauth_cred
            )
            data = response.json()

            title = data.get("title", "Untitled")
            slides = data.get("slides", [])
            slide_count = len(slides)

            slide_summaries = []
            for i, slide in enumerate(slides):
                object_id = slide.get("objectId", "")
                layout = slide.get("slideProperties", {}).get("layoutObjectId", "unknown")
                element_count = len(slide.get("pageElements", []))
                slide_summaries.append(
                    f"  Slide {i}: objectId={object_id}, layout={layout}, elements={element_count}"
                )

            summary = "\n".join(slide_summaries) if slide_summaries else "  (no slides)"
            return f"Presentation: {title}\nSlides: {slide_count}\n{summary}"

        except Exception as e:
            return f"Error reading Google Slides resource: {str(e)}"

    # --- Tool implementation methods ---

    async def _list_presentations(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List Google Slides presentations via Drive API."""
        page_size = arguments.get("page_size", 20)
        order_by = arguments.get("order_by", "modifiedTime desc")

        response = await self._make_authenticated_request(
            "GET",
            "https://www.googleapis.com/drive/v3/files",
            oauth_cred,
            params={
                "q": "mimeType='application/vnd.google-apps.presentation'",
                "pageSize": page_size,
                "orderBy": order_by,
                "fields": "files(id, name, createdTime, modifiedTime, webViewLink, owners, starred)"
            }
        )

        files = response.json().get("files", [])
        result = []
        for file in files:
            result.append({
                "id": file["id"],
                "name": file["name"],
                "created_time": file.get("createdTime"),
                "modified_time": file.get("modifiedTime"),
                "web_view_link": file.get("webViewLink"),
                "owners": [owner.get("displayName") for owner in file.get("owners", [])],
                "starred": file.get("starred", False)
            })

        return json.dumps({"presentations": result, "count": len(result)}, indent=2)

    async def _get_presentation(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get presentation metadata and structure."""
        presentation_id = arguments["presentation_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}",
            oauth_cred
        )
        data = response.json()

        slides_summary = []
        for i, slide in enumerate(data.get("slides", [])):
            slides_summary.append({
                "index": i,
                "object_id": slide.get("objectId"),
                "layout_object_id": slide.get("slideProperties", {}).get("layoutObjectId"),
                "element_count": len(slide.get("pageElements", []))
            })

        result = {
            "presentation_id": data.get("presentationId"),
            "title": data.get("title"),
            "locale": data.get("locale"),
            "slide_count": len(data.get("slides", [])),
            "slides": slides_summary,
            "page_size": data.get("pageSize"),
            "revision_id": data.get("revisionId")
        }

        return json.dumps(result, indent=2)

    async def _get_slide(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get a specific slide by 0-based index."""
        presentation_id = arguments["presentation_id"]
        slide_index = arguments["slide_index"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}",
            oauth_cred
        )
        data = response.json()
        slides = data.get("slides", [])

        if slide_index < 0 or slide_index >= len(slides):
            return json.dumps({
                "error": f"Slide index {slide_index} out of range. Presentation has {len(slides)} slides (0-{len(slides) - 1})."
            }, indent=2)

        slide = slides[slide_index]

        elements = []
        for elem in slide.get("pageElements", []):
            element_info = {
                "object_id": elem.get("objectId"),
                "size": elem.get("size"),
                "transform": elem.get("transform")
            }
            if "shape" in elem:
                shape = elem["shape"]
                element_info["type"] = "shape"
                element_info["shape_type"] = shape.get("shapeType")
                # Extract text content if present
                text_content = self._extract_text_from_element(shape)
                if text_content:
                    element_info["text"] = text_content
            elif "image" in elem:
                element_info["type"] = "image"
                element_info["content_url"] = elem["image"].get("contentUrl")
            elif "table" in elem:
                element_info["type"] = "table"
                element_info["rows"] = elem["table"].get("rows")
                element_info["columns"] = elem["table"].get("columns")
            elif "line" in elem:
                element_info["type"] = "line"
            elif "sheetsChart" in elem:
                element_info["type"] = "sheets_chart"
            else:
                element_info["type"] = "other"
            elements.append(element_info)

        result = {
            "slide_index": slide_index,
            "object_id": slide.get("objectId"),
            "layout_object_id": slide.get("slideProperties", {}).get("layoutObjectId"),
            "elements": elements
        }

        return json.dumps(result, indent=2)

    async def _create_presentation(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new presentation."""
        title = arguments["title"]

        response = await self._make_authenticated_request(
            "POST",
            "https://slides.googleapis.com/v1/presentations",
            oauth_cred,
            json={"title": title}
        )
        data = response.json()

        result = {
            "presentation_id": data.get("presentationId"),
            "title": data.get("title"),
            "slide_count": len(data.get("slides", [])),
            "web_view_link": f"https://docs.google.com/presentation/d/{data.get('presentationId')}/edit"
        }

        return json.dumps(result, indent=2)

    async def _add_slide(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Add a new slide to the presentation."""
        presentation_id = arguments["presentation_id"]
        insertion_index = arguments.get("insertion_index")
        layout = arguments.get("layout", "BLANK")

        create_slide_request: Dict[str, Any] = {
            "slideLayoutReference": {
                "predefinedLayout": layout
            }
        }

        if insertion_index is not None:
            create_slide_request["insertionIndex"] = insertion_index

        response = await self._make_authenticated_request(
            "POST",
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
            oauth_cred,
            json={
                "requests": [
                    {"createSlide": create_slide_request}
                ]
            }
        )
        data = response.json()

        # Extract the new slide's object ID from the reply
        replies = data.get("replies", [])
        new_slide_id = None
        if replies and "createSlide" in replies[0]:
            new_slide_id = replies[0]["createSlide"].get("objectId")

        result = {
            "success": True,
            "new_slide_object_id": new_slide_id,
            "layout": layout,
            "insertion_index": insertion_index
        }

        return json.dumps(result, indent=2)

    async def _delete_slide(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Delete a slide from the presentation."""
        presentation_id = arguments["presentation_id"]
        slide_object_id = arguments["slide_object_id"]

        await self._make_authenticated_request(
            "POST",
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
            oauth_cred,
            json={
                "requests": [
                    {
                        "deleteObject": {
                            "objectId": slide_object_id
                        }
                    }
                ]
            }
        )

        return json.dumps({
            "success": True,
            "message": f"Slide '{slide_object_id}' deleted successfully"
        }, indent=2)

    async def _add_text(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Insert text into a shape on a slide."""
        presentation_id = arguments["presentation_id"]
        object_id = arguments["object_id"]
        text = arguments["text"]
        insertion_index = arguments.get("insertion_index", 0)

        await self._make_authenticated_request(
            "POST",
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
            oauth_cred,
            json={
                "requests": [
                    {
                        "insertText": {
                            "objectId": object_id,
                            "insertionIndex": insertion_index,
                            "text": text
                        }
                    }
                ]
            }
        )

        return json.dumps({
            "success": True,
            "message": f"Text inserted into object '{object_id}' at index {insertion_index}"
        }, indent=2)

    async def _replace_text(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Find and replace text across the entire presentation."""
        presentation_id = arguments["presentation_id"]
        find_text = arguments["find_text"]
        replace_text = arguments["replace_text"]
        match_case = arguments.get("match_case", True)

        response = await self._make_authenticated_request(
            "POST",
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
            oauth_cred,
            json={
                "requests": [
                    {
                        "replaceAllText": {
                            "containsText": {
                                "text": find_text,
                                "matchCase": match_case
                            },
                            "replaceText": replace_text
                        }
                    }
                ]
            }
        )
        data = response.json()

        # Extract the number of occurrences replaced from the reply
        replies = data.get("replies", [])
        occurrences = 0
        if replies and "replaceAllText" in replies[0]:
            occurrences = replies[0]["replaceAllText"].get("occurrencesChanged", 0)

        return json.dumps({
            "success": True,
            "find_text": find_text,
            "replace_text": replace_text,
            "occurrences_changed": occurrences
        }, indent=2)

    async def _get_speaker_notes(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get speaker notes for a specific slide by index."""
        presentation_id = arguments["presentation_id"]
        slide_index = arguments["slide_index"]

        response = await self._make_authenticated_request(
            "GET",
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}",
            oauth_cred
        )
        data = response.json()
        slides = data.get("slides", [])

        if slide_index < 0 or slide_index >= len(slides):
            return json.dumps({
                "error": f"Slide index {slide_index} out of range. Presentation has {len(slides)} slides (0-{len(slides) - 1})."
            }, indent=2)

        slide = slides[slide_index]
        notes_page = slide.get("slideProperties", {}).get("notesPage", {})
        notes_elements = notes_page.get("pageElements", [])

        notes_text = ""
        notes_object_id = None
        for elem in notes_elements:
            shape = elem.get("shape", {})
            if shape.get("placeholder", {}).get("type") == "BODY":
                notes_object_id = elem.get("objectId")
                notes_text = self._extract_text_from_element(shape)
                break

        result = {
            "slide_index": slide_index,
            "slide_object_id": slide.get("objectId"),
            "notes_object_id": notes_object_id,
            "speaker_notes": notes_text
        }

        return json.dumps(result, indent=2)

    async def _update_speaker_notes(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Update speaker notes for a slide.

        This clears existing notes text and inserts new text into the notes shape.
        The notes_object_id can be obtained from get_speaker_notes.
        """
        presentation_id = arguments["presentation_id"]
        notes_object_id = arguments["notes_object_id"]
        text = arguments["text"]

        # First, delete all existing text in the notes shape, then insert new text.
        # We need to know the current text length to build the deleteText range.
        # Use deleteText with a range covering the whole shape, then insertText.
        requests = [
            {
                "deleteText": {
                    "objectId": notes_object_id,
                    "textRange": {
                        "type": "ALL"
                    }
                }
            },
            {
                "insertText": {
                    "objectId": notes_object_id,
                    "insertionIndex": 0,
                    "text": text
                }
            }
        ]

        await self._make_authenticated_request(
            "POST",
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
            oauth_cred,
            json={"requests": requests}
        )

        return json.dumps({
            "success": True,
            "message": f"Speaker notes updated for notes shape '{notes_object_id}'"
        }, indent=2)

    async def _duplicate_slide(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Duplicate a slide in the presentation."""
        presentation_id = arguments["presentation_id"]
        slide_object_id = arguments["slide_object_id"]

        response = await self._make_authenticated_request(
            "POST",
            f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate",
            oauth_cred,
            json={
                "requests": [
                    {
                        "duplicateObject": {
                            "objectId": slide_object_id
                        }
                    }
                ]
            }
        )
        data = response.json()

        # Extract the new object ID from the reply
        replies = data.get("replies", [])
        new_object_id = None
        if replies and "duplicateObject" in replies[0]:
            object_ids_mapping = replies[0]["duplicateObject"].get("objectIdsMapping", {})
            # The mapping contains source_id -> new_id pairs; the slide itself is one entry
            new_object_id = object_ids_mapping.get(slide_object_id)

        return json.dumps({
            "success": True,
            "source_slide_object_id": slide_object_id,
            "new_slide_object_id": new_object_id
        }, indent=2)

    # --- Helper methods ---

    def _extract_text_from_element(self, shape: Dict[str, Any]) -> str:
        """Extract plain text content from a shape's textElements.

        Iterates through the shape's text content and concatenates all textRun
        content strings. Returns empty string if no text is found.
        """
        text_content = shape.get("text", {}).get("textElements", [])
        parts = []
        for text_elem in text_content:
            if "textRun" in text_elem:
                parts.append(text_elem["textRun"].get("content", ""))
        return "".join(parts)
