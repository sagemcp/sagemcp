"""Notion connector implementation for accessing Notion API."""

import json
from typing import Any, Dict, List, Optional

import httpx
from mcp import types
from mcp.types import ToolAnnotations

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


@register_connector(ConnectorType.NOTION)
class NotionConnector(BaseConnector):
    """Notion connector for accessing Notion databases, pages, and blocks."""

    NOTION_API_BASE = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    @property
    def display_name(self) -> str:
        """Return display name for the connector."""
        return "Notion"

    @property
    def description(self) -> str:
        """Return description of the connector."""
        return "Access and manage Notion databases, pages, and blocks"

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
        """Make an authenticated request to Notion API.

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
        headers["Notion-Version"] = self.NOTION_VERSION
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
        """Get available Notion tools.

        Args:
            connector: The connector configuration
            oauth_cred: OAuth credential (optional)

        Returns:
            List of available tools
        """
        tools = [
            types.Tool(
                name="notion_list_databases",
                description="List all Notion databases accessible to the integration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {
                            "type": "integer",
                            "description": "Number of databases to return (max 100)",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20
                        }
                    }
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    idempotentHint=True,
                    openWorldHint=True,
                    riskLevel="low",
                )
            ),
            types.Tool(
                name="notion_search",
                description="Search for pages and databases by title",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to match against page/database titles"
                        },
                        "filter": {
                            "type": "string",
                            "description": "Filter results by type: 'page' or 'database'",
                            "enum": ["page", "database"]
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of results to return (max 100)",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20
                        }
                    },
                    "required": ["query"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    idempotentHint=True,
                    openWorldHint=True,
                    riskLevel="low",
                )
            ),
            types.Tool(
                name="notion_get_page",
                description="Get a Notion page by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The ID of the page to retrieve"
                        }
                    },
                    "required": ["page_id"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    idempotentHint=True,
                    openWorldHint=True,
                    riskLevel="low",
                )
            ),
            types.Tool(
                name="notion_get_page_content",
                description="Get the content blocks of a Notion page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The ID of the page to retrieve content from"
                        },
                        "format": {
                            "type": "string",
                            "description": "Format of the output: 'plain_text' or 'structured'",
                            "enum": ["plain_text", "structured"],
                            "default": "plain_text"
                        }
                    },
                    "required": ["page_id"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    idempotentHint=True,
                    openWorldHint=True,
                    riskLevel="low",
                )
            ),
            types.Tool(
                name="notion_get_database",
                description="Get a Notion database by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "The ID of the database to retrieve"
                        }
                    },
                    "required": ["database_id"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    idempotentHint=True,
                    openWorldHint=True,
                    riskLevel="low",
                )
            ),
            types.Tool(
                name="notion_query_database",
                description="Query a Notion database to retrieve pages/entries",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "The ID of the database to query"
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of results to return (max 100)",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20
                        }
                    },
                    "required": ["database_id"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    idempotentHint=True,
                    openWorldHint=True,
                    riskLevel="low",
                )
            ),
            types.Tool(
                name="notion_create_page",
                description="Create a new page in a Notion database or as a child of another page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "The ID of the parent database or page"
                        },
                        "parent_type": {
                            "type": "string",
                            "description": "Type of parent: 'database_id' or 'page_id'",
                            "enum": ["database_id", "page_id"],
                            "default": "database_id"
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the new page"
                        },
                        "content": {
                            "type": "string",
                            "description": "Optional plain text content to add to the page"
                        }
                    },
                    "required": ["parent_id", "title"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=True,
                    riskLevel="medium",
                )
            ),
            types.Tool(
                name="notion_append_block_children",
                description="Append blocks (content) to a page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The ID of the page to append content to"
                        },
                        "content": {
                            "type": "string",
                            "description": "Plain text content to append to the page"
                        }
                    },
                    "required": ["page_id", "content"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=True,
                    riskLevel="medium",
                )
            ),
            types.Tool(
                name="notion_update_page",
                description="Update a page's properties (title, metadata)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The ID of the page to update"
                        },
                        "title": {
                            "type": "string",
                            "description": "New title for the page"
                        }
                    },
                    "required": ["page_id", "title"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=False,
                    destructiveHint=True,
                    idempotentHint=True,
                    openWorldHint=True,
                    riskLevel="high",
                )
            ),
            types.Tool(
                name="notion_get_block",
                description="Get a specific block by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "block_id": {
                            "type": "string",
                            "description": "The ID of the block to retrieve"
                        }
                    },
                    "required": ["block_id"]
                },
                annotations=ToolAnnotations(
                    readOnlyHint=True,
                    idempotentHint=True,
                    openWorldHint=True,
                    riskLevel="low",
                )
            )
        ]
        return tools

    async def get_resources(
        self,
        connector: Connector,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> List[types.Resource]:
        """Get available Notion resources.

        Args:
            connector: The connector configuration
            oauth_cred: OAuth credential (optional)

        Returns:
            List of available resources
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        try:
            # Search for all pages and databases
            response = await self._make_authenticated_request(
                "POST",
                f"{self.NOTION_API_BASE}/search",
                oauth_cred,
                json={"page_size": 50}
            )
            results = response.json().get("results", [])

            resources = []
            for item in results:
                item_type = item.get("object")
                item_id = item.get("id")

                # Get title based on type
                title = "Untitled"
                if item_type == "page":
                    properties = item.get("properties", {})
                    title_prop = properties.get("title", {})
                    if isinstance(title_prop, dict) and "title" in title_prop:
                        title_array = title_prop["title"]
                        if title_array and len(title_array) > 0:
                            title = title_array[0].get("plain_text", "Untitled")
                elif item_type == "database":
                    title_array = item.get("title", [])
                    if title_array and len(title_array) > 0:
                        title = title_array[0].get("plain_text", "Untitled")

                resources.append(types.Resource(
                    uri=f"notion://{item_type}/{item_id}",
                    name=title,
                    description=f"Notion {item_type.capitalize()}",
                    mimeType=f"application/vnd.notion.{item_type}"
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
        """Execute a Notion tool.

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
            if tool_name == "list_databases":
                return await self._list_databases(arguments, oauth_cred)
            elif tool_name == "search":
                return await self._search(arguments, oauth_cred)
            elif tool_name == "get_page":
                return await self._get_page(arguments, oauth_cred)
            elif tool_name == "get_page_content":
                return await self._get_page_content(arguments, oauth_cred)
            elif tool_name == "get_database":
                return await self._get_database(arguments, oauth_cred)
            elif tool_name == "query_database":
                return await self._query_database(arguments, oauth_cred)
            elif tool_name == "create_page":
                return await self._create_page(arguments, oauth_cred)
            elif tool_name == "append_block_children":
                return await self._append_block_children(arguments, oauth_cred)
            elif tool_name == "update_page":
                return await self._update_page(arguments, oauth_cred)
            elif tool_name == "get_block":
                return await self._get_block(arguments, oauth_cred)
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
        """Read a Notion resource.

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

            if resource_type == "page":
                # Get page content
                response = await self._make_authenticated_request(
                    "GET",
                    f"{self.NOTION_API_BASE}/pages/{resource_id}",
                    oauth_cred
                )
                page_data = response.json()

                # Get page blocks
                blocks_response = await self._make_authenticated_request(
                    "GET",
                    f"{self.NOTION_API_BASE}/blocks/{resource_id}/children",
                    oauth_cred
                )
                blocks_data = blocks_response.json()

                # Extract title
                title = self._extract_page_title(page_data)

                # Extract content
                content = self._extract_plain_text_from_blocks(blocks_data.get("results", []))

                return f"Page: {title}\n\n{content}"

            elif resource_type == "database":
                # Get database info
                response = await self._make_authenticated_request(
                    "GET",
                    f"{self.NOTION_API_BASE}/databases/{resource_id}",
                    oauth_cred
                )
                db_data = response.json()

                # Extract database title
                title_array = db_data.get("title", [])
                title = title_array[0].get("plain_text", "Untitled") if title_array else "Untitled"

                # Get database schema
                properties = db_data.get("properties", {})
                schema_info = "\n".join([
                    f"  - {name}: {prop.get('type')}"
                    for name, prop in properties.items()
                ])

                return f"Database: {title}\n\nProperties:\n{schema_info}"

            else:
                return f"Error: Unknown resource type: {resource_type}"

        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error reading resource: {str(e)}"

    # Tool implementation methods

    async def _list_databases(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """List all Notion databases."""
        page_size = arguments.get("page_size", 20)

        response = await self._make_authenticated_request(
            "POST",
            f"{self.NOTION_API_BASE}/search",
            oauth_cred,
            json={
                "filter": {"property": "object", "value": "database"},
                "page_size": page_size
            }
        )

        data = response.json()
        results = data.get("results", [])

        databases = []
        for db in results:
            title_array = db.get("title", [])
            title = title_array[0].get("plain_text", "Untitled") if title_array else "Untitled"

            databases.append({
                "id": db.get("id"),
                "title": title,
                "created_time": db.get("created_time"),
                "last_edited_time": db.get("last_edited_time"),
                "url": db.get("url")
            })

        return json.dumps({
            "databases": databases,
            "count": len(databases),
            "has_more": data.get("has_more", False)
        }, indent=2)

    async def _search(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Search for pages and databases."""
        query = arguments.get("query", "")
        filter_type = arguments.get("filter")
        page_size = arguments.get("page_size", 20)

        search_params: Dict[str, Any] = {
            "query": query,
            "page_size": page_size
        }

        if filter_type:
            search_params["filter"] = {"property": "object", "value": filter_type}

        response = await self._make_authenticated_request(
            "POST",
            f"{self.NOTION_API_BASE}/search",
            oauth_cred,
            json=search_params
        )

        data = response.json()
        results = data.get("results", [])

        items = []
        for item in results:
            item_type = item.get("object")

            # Extract title based on type
            if item_type == "page":
                title = self._extract_page_title(item)
            elif item_type == "database":
                title_array = item.get("title", [])
                title = title_array[0].get("plain_text", "Untitled") if title_array else "Untitled"
            else:
                title = "Untitled"

            items.append({
                "id": item.get("id"),
                "type": item_type,
                "title": title,
                "created_time": item.get("created_time"),
                "last_edited_time": item.get("last_edited_time"),
                "url": item.get("url")
            })

        return json.dumps({
            "results": items,
            "count": len(items),
            "has_more": data.get("has_more", False)
        }, indent=2)

    async def _get_page(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Get a Notion page by ID."""
        page_id = arguments["page_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{self.NOTION_API_BASE}/pages/{page_id}",
            oauth_cred
        )

        page_data = response.json()

        return json.dumps({
            "id": page_data.get("id"),
            "created_time": page_data.get("created_time"),
            "last_edited_time": page_data.get("last_edited_time"),
            "archived": page_data.get("archived"),
            "url": page_data.get("url"),
            "properties": page_data.get("properties", {})
        }, indent=2)

    async def _get_page_content(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Get the content blocks of a Notion page."""
        page_id = arguments["page_id"]
        format_type = arguments.get("format", "plain_text")

        # Get page metadata
        page_response = await self._make_authenticated_request(
            "GET",
            f"{self.NOTION_API_BASE}/pages/{page_id}",
            oauth_cred
        )
        page_data = page_response.json()
        title = self._extract_page_title(page_data)

        # Get page blocks
        blocks_response = await self._make_authenticated_request(
            "GET",
            f"{self.NOTION_API_BASE}/blocks/{page_id}/children",
            oauth_cred
        )
        blocks_data = blocks_response.json()

        if format_type == "plain_text":
            content = self._extract_plain_text_from_blocks(blocks_data.get("results", []))
            return f"Title: {title}\n\n{content}"
        else:
            return json.dumps({
                "title": title,
                "page_id": page_id,
                "blocks": blocks_data.get("results", [])
            }, indent=2)

    async def _get_database(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Get a Notion database by ID."""
        database_id = arguments["database_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{self.NOTION_API_BASE}/databases/{database_id}",
            oauth_cred
        )

        db_data = response.json()

        title_array = db_data.get("title", [])
        title = title_array[0].get("plain_text", "Untitled") if title_array else "Untitled"

        return json.dumps({
            "id": db_data.get("id"),
            "title": title,
            "created_time": db_data.get("created_time"),
            "last_edited_time": db_data.get("last_edited_time"),
            "url": db_data.get("url"),
            "properties": db_data.get("properties", {})
        }, indent=2)

    async def _query_database(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Query a Notion database."""
        database_id = arguments["database_id"]
        page_size = arguments.get("page_size", 20)

        response = await self._make_authenticated_request(
            "POST",
            f"{self.NOTION_API_BASE}/databases/{database_id}/query",
            oauth_cred,
            json={"page_size": page_size}
        )

        data = response.json()
        results = data.get("results", [])

        pages = []
        for page in results:
            title = self._extract_page_title(page)

            pages.append({
                "id": page.get("id"),
                "title": title,
                "created_time": page.get("created_time"),
                "last_edited_time": page.get("last_edited_time"),
                "url": page.get("url"),
                "properties": page.get("properties", {})
            })

        return json.dumps({
            "pages": pages,
            "count": len(pages),
            "has_more": data.get("has_more", False)
        }, indent=2)

    async def _create_page(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Create a new page in Notion."""
        parent_id = arguments["parent_id"]
        parent_type = arguments.get("parent_type", "database_id")
        title = arguments["title"]
        content = arguments.get("content")

        # Build parent object
        parent = {parent_type: parent_id}

        # Build properties
        properties = {
            "title": {
                "title": [{"text": {"content": title}}]
            }
        }

        # Build children blocks if content is provided
        children = []
        if content:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            })

        page_data: Dict[str, Any] = {
            "parent": parent,
            "properties": properties
        }

        if children:
            page_data["children"] = children

        response = await self._make_authenticated_request(
            "POST",
            f"{self.NOTION_API_BASE}/pages",
            oauth_cred,
            json=page_data
        )

        result = response.json()

        return json.dumps({
            "id": result.get("id"),
            "url": result.get("url"),
            "created_time": result.get("created_time")
        }, indent=2)

    async def _append_block_children(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Append blocks to a page."""
        page_id = arguments["page_id"]
        content = arguments["content"]

        # Create paragraph block
        children = [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content}}]
            }
        }]

        response = await self._make_authenticated_request(
            "PATCH",
            f"{self.NOTION_API_BASE}/blocks/{page_id}/children",
            oauth_cred,
            json={"children": children}
        )

        result = response.json()

        return json.dumps({
            "status": "success",
            "blocks_added": len(result.get("results", []))
        }, indent=2)

    async def _update_page(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Update a page's properties."""
        page_id = arguments["page_id"]
        title = arguments["title"]

        properties = {
            "title": {
                "title": [{"text": {"content": title}}]
            }
        }

        response = await self._make_authenticated_request(
            "PATCH",
            f"{self.NOTION_API_BASE}/pages/{page_id}",
            oauth_cred,
            json={"properties": properties}
        )

        result = response.json()

        return json.dumps({
            "id": result.get("id"),
            "url": result.get("url"),
            "last_edited_time": result.get("last_edited_time")
        }, indent=2)

    async def _get_block(
        self,
        arguments: Dict[str, Any],
        oauth_cred: OAuthCredential
    ) -> str:
        """Get a specific block by ID."""
        block_id = arguments["block_id"]

        response = await self._make_authenticated_request(
            "GET",
            f"{self.NOTION_API_BASE}/blocks/{block_id}",
            oauth_cred
        )

        block_data = response.json()

        return json.dumps(block_data, indent=2)

    # Helper methods

    def _extract_page_title(self, page_data: Dict[str, Any]) -> str:
        """Extract title from page properties."""
        properties = page_data.get("properties", {})

        # Look for title property
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                title_array = prop_value.get("title", [])
                if title_array and len(title_array) > 0:
                    return title_array[0].get("plain_text", "Untitled")

        return "Untitled"

    def _extract_plain_text_from_blocks(self, blocks: List[Dict[str, Any]]) -> str:
        """Extract plain text from Notion blocks."""
        text_parts = []

        for block in blocks:
            block_type = block.get("type")

            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3",
                              "bulleted_list_item", "numbered_list_item", "to_do", "quote"]:
                block_content = block.get(block_type, {})
                rich_text = block_content.get("rich_text", [])

                for text_element in rich_text:
                    if text_element.get("type") == "text":
                        text_parts.append(text_element.get("plain_text", ""))

                text_parts.append("\n")

            elif block_type == "code":
                code_content = block.get("code", {})
                rich_text = code_content.get("rich_text", [])

                code_text = "".join([
                    text_element.get("plain_text", "")
                    for text_element in rich_text
                    if text_element.get("type") == "text"
                ])

                text_parts.append(f"```\n{code_text}\n```\n")

        return "".join(text_parts)
