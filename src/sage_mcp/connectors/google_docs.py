"""Google Docs connector implementation."""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


@register_connector(ConnectorType.GOOGLE_DOCS)
class GoogleDocsConnector(BaseConnector):
    """Google Docs connector for accessing Google Docs API."""

    @property
    def display_name(self) -> str:
        return "Google Docs"

    @property
    def description(self) -> str:
        return "Access Google Docs documents, create, read, update, and export documents"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Google Docs tools."""
        tools = [
            types.Tool(
                name="google_docs_list_documents",
                description="List Google Docs documents accessible to the user. Use owner_email to find docs owned by a specific person.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of documents to return"
                        },
                        "order_by": {
                            "type": "string",
                            "enum": ["modifiedTime", "name", "createdTime"],
                            "default": "modifiedTime desc",
                            "description": "Sort order for documents"
                        },
                        "owner_email": {
                            "type": "string",
                            "description": "Filter documents owned by this email address. Use get_user_external_accounts to resolve a user's Google email first."
                        }
                    }
                }
            ),
            types.Tool(
                name="google_docs_get_document",
                description="Get detailed metadata about a specific Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Doc"
                        }
                    },
                    "required": ["document_id"]
                }
            ),
            types.Tool(
                name="google_docs_read_document_content",
                description="Read the full content of a Google Doc as structured text",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Doc"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["structured", "plain_text"],
                            "default": "plain_text",
                            "description": "Format of the returned content"
                        }
                    },
                    "required": ["document_id"]
                }
            ),
            types.Tool(
                name="google_docs_search_documents",
                description="Search for Google Docs by title or content. Use owner_email to find docs owned by a specific person.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (searches in document name)"
                        },
                        "page_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of results to return"
                        },
                        "owner_email": {
                            "type": "string",
                            "description": "Filter documents owned by this email address. Use get_user_external_accounts to resolve a user's Google email first."
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="google_docs_create_document",
                description="Create a new Google Doc with optional initial content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the new document"
                        },
                        "initial_content": {
                            "type": "string",
                            "description": "Optional initial text content"
                        }
                    },
                    "required": ["title"]
                }
            ),
            types.Tool(
                name="google_docs_append_text",
                description="Append text to the end of a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Doc"
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to append to the document"
                        }
                    },
                    "required": ["document_id", "text"]
                }
            ),
            types.Tool(
                name="google_docs_insert_text",
                description="Insert text at a specific position in a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Doc"
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to insert"
                        },
                        "index": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Position to insert text (1-based index)"
                        }
                    },
                    "required": ["document_id", "text", "index"]
                }
            ),
            types.Tool(
                name="google_docs_export_document",
                description="Export a Google Doc in various formats (PDF, TXT, HTML, DOCX)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Doc"
                        },
                        "mime_type": {
                            "type": "string",
                            "enum": [
                                "application/pdf",
                                "text/plain",
                                "text/html",
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            ],
                            "default": "application/pdf",
                            "description": "Export format MIME type"
                        }
                    },
                    "required": ["document_id"]
                }
            ),
            types.Tool(
                name="google_docs_get_permissions",
                description="Get sharing permissions for a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Doc"
                        }
                    },
                    "required": ["document_id"]
                }
            ),
            types.Tool(
                name="google_docs_list_shared_documents",
                description="List Google Docs that have been shared with the user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of documents to return"
                        }
                    }
                }
            )
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Google Docs resources."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        try:
            # List user's Google Docs
            response = await self._make_authenticated_request(
                "GET",
                "https://www.googleapis.com/drive/v3/files",
                oauth_cred,
                params={
                    "q": "mimeType='application/vnd.google-apps.document'",
                    "pageSize": 50,
                    "fields": "files(id, name, modifiedTime, webViewLink)"
                }
            )
            files = response.json().get("files", [])

            resources = []
            for file in files:
                resources.append(types.Resource(
                    uri=f"google-docs://document/{file['id']}",
                    name=file["name"],
                    description=f"Google Doc (Modified: {file.get('modifiedTime', 'Unknown')})",
                    mimeType="application/vnd.google-apps.document"
                ))

            return resources

        except Exception as e:
            print(f"Error fetching Google Docs resources: {e}")
            return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Google Docs tool."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            if tool_name == "list_documents":
                return await self._list_documents(arguments, oauth_cred)
            elif tool_name == "get_document":
                return await self._get_document(arguments, oauth_cred)
            elif tool_name == "read_document_content":
                return await self._read_document_content(arguments, oauth_cred)
            elif tool_name == "search_documents":
                return await self._search_documents(arguments, oauth_cred)
            elif tool_name == "create_document":
                return await self._create_document(arguments, oauth_cred)
            elif tool_name == "append_text":
                return await self._append_text(arguments, oauth_cred)
            elif tool_name == "insert_text":
                return await self._insert_text(arguments, oauth_cred)
            elif tool_name == "export_document":
                return await self._export_document(arguments, oauth_cred)
            elif tool_name == "get_permissions":
                return await self._get_permissions(arguments, oauth_cred)
            elif tool_name == "list_shared_documents":
                return await self._list_shared_documents(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Google Docs tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Google Docs resource."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            # Parse resource path: document/document_id
            parts = resource_path.split("/", 1)
            if len(parts) != 2 or parts[0] != "document":
                return "Error: Invalid resource path. Expected format: document/{document_id}"

            document_id = parts[1]

            # Get document content
            response = await self._make_authenticated_request(
                "GET",
                f"https://docs.googleapis.com/v1/documents/{document_id}",
                oauth_cred
            )
            doc_data = response.json()

            # Extract plain text content
            content = self._extract_plain_text(doc_data)
            title = doc_data.get("title", "Untitled")

            return f"Document: {title}\n\n{content}"

        except Exception as e:
            return f"Error reading Google Docs resource: {str(e)}"

    # Tool implementation methods

    async def _list_documents(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List Google Docs documents."""
        page_size = arguments.get("page_size", 20)
        order_by = arguments.get("order_by", "modifiedTime desc")
        owner_email = arguments.get("owner_email")

        try:
            query = "mimeType='application/vnd.google-apps.document'"
            if owner_email:
                query += f" and '{owner_email}' in owners"

            response = await self._make_authenticated_request(
                "GET",
                "https://www.googleapis.com/drive/v3/files",
                oauth_cred,
                params={
                    "q": query,
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

            return json.dumps({"documents": result, "count": len(result)}, indent=2)

        except Exception as e:
            return f"Error listing documents: {str(e)}"

    async def _get_document(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get document metadata."""
        document_id = arguments["document_id"]

        try:
            # Get document metadata from Docs API
            doc_response = await self._make_authenticated_request(
                "GET",
                f"https://docs.googleapis.com/v1/documents/{document_id}",
                oauth_cred
            )
            doc_data = doc_response.json()

            # Get additional metadata from Drive API
            drive_response = await self._make_authenticated_request(
                "GET",
                f"https://www.googleapis.com/drive/v3/files/{document_id}",
                oauth_cred,
                params={"fields": "id, name, createdTime, modifiedTime, webViewLink, owners, permissions, starred, size"}
            )
            drive_data = drive_response.json()

            result = {
                "document_id": doc_data["documentId"],
                "title": doc_data["title"],
                "created_time": drive_data.get("createdTime"),
                "modified_time": drive_data.get("modifiedTime"),
                "web_view_link": drive_data.get("webViewLink"),
                "owners": [owner.get("displayName") for owner in drive_data.get("owners", [])],
                "starred": drive_data.get("starred", False),
                "revision_id": doc_data.get("revisionId")
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting document: {str(e)}"

    async def _read_document_content(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Read document content."""
        document_id = arguments["document_id"]
        format_type = arguments.get("format", "plain_text")

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"https://docs.googleapis.com/v1/documents/{document_id}",
                oauth_cred
            )
            doc_data = response.json()

            if format_type == "plain_text":
                content = self._extract_plain_text(doc_data)
                return f"Title: {doc_data['title']}\n\n{content}"
            else:
                # Return structured format
                return json.dumps({
                    "title": doc_data["title"],
                    "document_id": doc_data["documentId"],
                    "body": doc_data.get("body", {}),
                    "revision_id": doc_data.get("revisionId")
                }, indent=2)

        except Exception as e:
            return f"Error reading document content: {str(e)}"

    async def _search_documents(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search for documents by name."""
        query = arguments["query"]
        page_size = arguments.get("page_size", 20)
        owner_email = arguments.get("owner_email")

        try:
            drive_query = f"mimeType='application/vnd.google-apps.document' and name contains '{query}'"
            if owner_email:
                drive_query += f" and '{owner_email}' in owners"

            response = await self._make_authenticated_request(
                "GET",
                "https://www.googleapis.com/drive/v3/files",
                oauth_cred,
                params={
                    "q": drive_query,
                    "pageSize": page_size,
                    "fields": "files(id, name, createdTime, modifiedTime, webViewLink)"
                }
            )

            files = response.json().get("files", [])
            result = []
            for file in files:
                result.append({
                    "id": file["id"],
                    "name": file["name"],
                    "modified_time": file.get("modifiedTime"),
                    "web_view_link": file.get("webViewLink")
                })

            return json.dumps({"results": result, "count": len(result)}, indent=2)

        except Exception as e:
            return f"Error searching documents: {str(e)}"

    async def _create_document(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new document."""
        title = arguments["title"]
        initial_content = arguments.get("initial_content")

        try:
            # Create document
            response = await self._make_authenticated_request(
                "POST",
                "https://docs.googleapis.com/v1/documents",
                oauth_cred,
                json={"title": title}
            )
            doc_data = response.json()
            document_id = doc_data["documentId"]

            # Add initial content if provided
            if initial_content:
                await self._make_authenticated_request(
                    "POST",
                    f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
                    oauth_cred,
                    json={
                        "requests": [
                            {
                                "insertText": {
                                    "location": {"index": 1},
                                    "text": initial_content
                                }
                            }
                        ]
                    }
                )

            result = {
                "document_id": document_id,
                "title": title,
                "web_view_link": f"https://docs.google.com/document/d/{document_id}/edit"
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error creating document: {str(e)}"

    async def _append_text(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Append text to document."""
        document_id = arguments["document_id"]
        text = arguments["text"]

        try:
            # Get current document to find end index
            doc_response = await self._make_authenticated_request(
                "GET",
                f"https://docs.googleapis.com/v1/documents/{document_id}",
                oauth_cred
            )
            doc_data = doc_response.json()
            end_index = doc_data["body"]["content"][-1]["endIndex"] - 1

            # Append text
            await self._make_authenticated_request(
                "POST",
                f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
                oauth_cred,
                json={
                    "requests": [
                        {
                            "insertText": {
                                "location": {"index": end_index},
                                "text": text
                            }
                        }
                    ]
                }
            )

            return json.dumps({"success": True, "message": "Text appended successfully"}, indent=2)

        except Exception as e:
            return f"Error appending text: {str(e)}"

    async def _insert_text(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Insert text at specific position."""
        document_id = arguments["document_id"]
        text = arguments["text"]
        index = arguments["index"]

        try:
            await self._make_authenticated_request(
                "POST",
                f"https://docs.googleapis.com/v1/documents/{document_id}:batchUpdate",
                oauth_cred,
                json={
                    "requests": [
                        {
                            "insertText": {
                                "location": {"index": index},
                                "text": text
                            }
                        }
                    ]
                }
            )

            return json.dumps({"success": True, "message": f"Text inserted at index {index}"}, indent=2)

        except Exception as e:
            return f"Error inserting text: {str(e)}"

    async def _export_document(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Export document in specified format."""
        document_id = arguments["document_id"]
        mime_type = arguments.get("mime_type", "application/pdf")

        # Map mime types to extensions
        mime_to_ext = {
            "application/pdf": "pdf",
            "text/plain": "txt",
            "text/html": "html",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"
        }

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"https://www.googleapis.com/drive/v3/files/{document_id}/export",
                oauth_cred,
                params={"mimeType": mime_type}
            )

            # For text formats, return content directly
            if mime_type in ["text/plain", "text/html"]:
                content = response.text
                return f"Exported content:\n\n{content}"
            else:
                # For binary formats, return download info
                extension = mime_to_ext.get(mime_type, "bin")
                result = {
                    "success": True,
                    "message": f"Document can be exported as {extension}",
                    "mime_type": mime_type,
                    "export_url": f"https://www.googleapis.com/drive/v3/files/{document_id}/export?mimeType={mime_type}",
                    "note": "Binary export requires direct API call with authentication"
                }
                return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error exporting document: {str(e)}"

    async def _get_permissions(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get document permissions."""
        document_id = arguments["document_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"https://www.googleapis.com/drive/v3/files/{document_id}/permissions",
                oauth_cred,
                params={"fields": "permissions(id, type, role, emailAddress, displayName)"}
            )

            permissions = response.json().get("permissions", [])
            result = []
            for perm in permissions:
                result.append({
                    "id": perm.get("id"),
                    "type": perm.get("type"),
                    "role": perm.get("role"),
                    "email": perm.get("emailAddress"),
                    "display_name": perm.get("displayName")
                })

            return json.dumps({"permissions": result, "count": len(result)}, indent=2)

        except Exception as e:
            return f"Error getting permissions: {str(e)}"

    async def _list_shared_documents(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List documents shared with user."""
        page_size = arguments.get("page_size", 20)

        try:
            response = await self._make_authenticated_request(
                "GET",
                "https://www.googleapis.com/drive/v3/files",
                oauth_cred,
                params={
                    "q": "mimeType='application/vnd.google-apps.document' and sharedWithMe=true",
                    "pageSize": page_size,
                    "fields": "files(id, name, modifiedTime, webViewLink, owners, sharingUser)"
                }
            )

            files = response.json().get("files", [])
            result = []
            for file in files:
                result.append({
                    "id": file["id"],
                    "name": file["name"],
                    "modified_time": file.get("modifiedTime"),
                    "web_view_link": file.get("webViewLink"),
                    "owners": [owner.get("displayName") for owner in file.get("owners", [])],
                    "shared_by": file.get("sharingUser", {}).get("displayName")
                })

            return json.dumps({"shared_documents": result, "count": len(result)}, indent=2)

        except Exception as e:
            return f"Error listing shared documents: {str(e)}"

    # Helper methods

    def _extract_plain_text(self, doc_data: Dict[str, Any]) -> str:
        """Extract plain text from document structure."""
        content = doc_data.get("body", {}).get("content", [])
        text_parts = []

        for element in content:
            if "paragraph" in element:
                paragraph = element["paragraph"]
                for text_element in paragraph.get("elements", []):
                    if "textRun" in text_element:
                        text_parts.append(text_element["textRun"].get("content", ""))

        return "".join(text_parts)
