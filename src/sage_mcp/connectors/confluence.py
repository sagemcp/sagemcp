"""Confluence connector implementation.

This connector enables interaction with Confluence Cloud through OAuth 2.0.
Uses the Confluence REST API v2 for most operations, v1 for CQL search.
Requires OAuth app with scopes: read:confluence-content.all, write:confluence-content,
read:confluence-space.summary, offline_access

OAuth App Setup:
1. Go to https://developer.atlassian.com/console/myapps/
2. Create a new OAuth 2.0 integration
3. Add callback URL matching your SageMCP OAuth configuration
4. Enable required Confluence scopes
5. Note the Client ID and Client Secret for SageMCP configuration
"""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector


@register_connector(ConnectorType.CONFLUENCE)
class ConfluenceConnector(BaseConnector):
    """Confluence connector for accessing Confluence Cloud API."""

    def __init__(self):
        super().__init__()
        self._cloud_id_cache: Dict[str, str] = {}  # Cache cloudId per OAuth token

    @property
    def display_name(self) -> str:
        return "Confluence"

    @property
    def description(self) -> str:
        return "Access Confluence spaces, pages, comments, labels, and content search"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def _get_cloud_id(self, oauth_cred: OAuthCredential) -> str:
        """Get Confluence Cloud ID for the authenticated user.

        The cloudId is required to construct Confluence API endpoints.
        This uses the same Atlassian accessible-resources endpoint as Jira.
        Cached per OAuth token to minimize API calls.
        """
        cache_key = oauth_cred.access_token[:20]

        if cache_key in self._cloud_id_cache:
            return self._cloud_id_cache[cache_key]

        try:
            print("DEBUG: Fetching Confluence accessible resources to get cloudId")
            response = await self._make_authenticated_request(
                "GET",
                "https://api.atlassian.com/oauth/token/accessible-resources",
                oauth_cred
            )

            resources = response.json()
            print(f"DEBUG: Found {len(resources)} accessible Atlassian resources")

            if not resources:
                raise ValueError("No accessible Confluence resources found for this account")

            # Use the first accessible resource
            cloud_id = resources[0]["id"]
            self._cloud_id_cache[cache_key] = cloud_id

            print(f"DEBUG: Using cloudId: {cloud_id} ({resources[0].get('name', 'Unknown')})")
            return cloud_id

        except Exception as e:
            print(f"DEBUG: Error fetching Confluence cloudId: {str(e)}")
            raise

    def _get_api_base_url(self, cloud_id: str) -> str:
        """Construct Confluence REST API v2 base URL."""
        return f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/api/v2"

    def _get_api_v1_base_url(self, cloud_id: str) -> str:
        """Construct Confluence REST API v1 base URL (used for CQL search)."""
        return f"https://api.atlassian.com/ex/confluence/{cloud_id}/wiki/rest/api"

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Confluence tools."""
        tools = [
            # Space Management
            types.Tool(
                name="confluence_list_spaces",
                description="List Confluence spaces",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "default": 25,
                            "minimum": 1,
                            "maximum": 250,
                            "description": "Maximum number of spaces to return"
                        },
                        "type": {
                            "type": "string",
                            "enum": ["global", "personal"],
                            "description": "Filter by space type (optional)"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["current", "archived"],
                            "description": "Filter by space status (optional)"
                        }
                    }
                }
            ),
            types.Tool(
                name="confluence_get_space",
                description="Get detailed information about a Confluence space by its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "space_id": {
                            "type": "string",
                            "description": "The numeric ID of the space"
                        }
                    },
                    "required": ["space_id"]
                }
            ),

            # Page Management
            types.Tool(
                name="confluence_list_pages",
                description="List pages in Confluence, optionally filtered by space",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "space_id": {
                            "type": "string",
                            "description": "Filter by space ID (optional)"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 25,
                            "minimum": 1,
                            "maximum": 250,
                            "description": "Maximum number of pages to return"
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["id", "-id", "title", "-title", "created-date", "-created-date", "modified-date", "-modified-date"],
                            "description": "Sort order (prefix with - for descending)"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["current", "archived", "deleted", "trashed"],
                            "description": "Filter by page status (optional)"
                        }
                    }
                }
            ),
            types.Tool(
                name="confluence_get_page",
                description="Get a Confluence page by ID, including its body content in storage format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the page"
                        }
                    },
                    "required": ["page_id"]
                }
            ),
            types.Tool(
                name="confluence_create_page",
                description="Create a new page in a Confluence space. Body must be in Atlassian Storage Format (XHTML).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "space_id": {
                            "type": "string",
                            "description": "The numeric ID of the space to create the page in"
                        },
                        "title": {
                            "type": "string",
                            "description": "Page title"
                        },
                        "body": {
                            "type": "string",
                            "description": "Page body in Atlassian Storage Format (XHTML). Example: '<p>Hello world</p>'"
                        },
                        "parent_id": {
                            "type": "string",
                            "description": "Parent page ID to nest under (optional)"
                        }
                    },
                    "required": ["space_id", "title", "body"]
                }
            ),
            types.Tool(
                name="confluence_update_page",
                description="Update an existing Confluence page. Requires current version number (will be auto-incremented).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the page to update"
                        },
                        "title": {
                            "type": "string",
                            "description": "New page title"
                        },
                        "body": {
                            "type": "string",
                            "description": "New page body in Atlassian Storage Format (XHTML)"
                        },
                        "version_number": {
                            "type": "integer",
                            "description": "Current version number of the page (will be incremented by 1 for the update)"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["current", "draft"],
                            "default": "current",
                            "description": "Page status after update"
                        }
                    },
                    "required": ["page_id", "title", "body", "version_number"]
                }
            ),
            types.Tool(
                name="confluence_delete_page",
                description="Delete a Confluence page by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the page to delete"
                        }
                    },
                    "required": ["page_id"]
                }
            ),

            # Search
            types.Tool(
                name="confluence_search_content",
                description="Search Confluence content using CQL (Confluence Query Language). Example: type=page AND space.key=DEV AND text~'architecture'",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cql": {
                            "type": "string",
                            "description": "CQL query string (e.g., 'type=page AND space.key=DEV')"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 25,
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum number of results to return"
                        }
                    },
                    "required": ["cql"]
                }
            ),

            # Page Children
            types.Tool(
                name="confluence_get_page_children",
                description="Get child pages of a Confluence page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the parent page"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 25,
                            "minimum": 1,
                            "maximum": 250,
                            "description": "Maximum number of child pages to return"
                        }
                    },
                    "required": ["page_id"]
                }
            ),

            # Comments
            types.Tool(
                name="confluence_list_page_comments",
                description="Get footer comments on a Confluence page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the page"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 25,
                            "minimum": 1,
                            "maximum": 250,
                            "description": "Maximum number of comments to return"
                        }
                    },
                    "required": ["page_id"]
                }
            ),
            types.Tool(
                name="confluence_add_comment",
                description="Add a footer comment to a Confluence page. Body must be in Atlassian Storage Format.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the page to comment on"
                        },
                        "body": {
                            "type": "string",
                            "description": "Comment body in Atlassian Storage Format (XHTML). Example: '<p>Great work!</p>'"
                        }
                    },
                    "required": ["page_id", "body"]
                }
            ),

            # Labels
            types.Tool(
                name="confluence_get_page_labels",
                description="Get labels on a Confluence page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the page"
                        }
                    },
                    "required": ["page_id"]
                }
            ),
            types.Tool(
                name="confluence_add_label",
                description="Add a label to a Confluence page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the page"
                        },
                        "label": {
                            "type": "string",
                            "description": "Label name to add"
                        }
                    },
                    "required": ["page_id", "label"]
                }
            ),

            # History & Attachments
            types.Tool(
                name="confluence_get_page_history",
                description="Get version history of a Confluence page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the page"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 25,
                            "minimum": 1,
                            "maximum": 250,
                            "description": "Maximum number of versions to return"
                        }
                    },
                    "required": ["page_id"]
                }
            ),
            types.Tool(
                name="confluence_list_page_attachments",
                description="List attachments on a Confluence page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "The numeric ID of the page"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 25,
                            "minimum": 1,
                            "maximum": 250,
                            "description": "Maximum number of attachments to return"
                        }
                    },
                    "required": ["page_id"]
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Confluence resources."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return []

        try:
            cloud_id = await self._get_cloud_id(oauth_cred)
            base_url = self._get_api_base_url(cloud_id)

            # Get user's accessible spaces
            response = await self._make_authenticated_request(
                "GET",
                f"{base_url}/spaces",
                oauth_cred,
                params={"limit": 50}
            )
            data = response.json()
            spaces = data.get("results", [])

            resources = []

            for space in spaces:
                space_id = space["id"]
                space_name = space.get("name", "Unnamed")
                space_key = space.get("key", "")
                resources.append(types.Resource(
                    uri=f"confluence://space/{space_id}",
                    name=f"{space_key}: {space_name}",
                    description=f"Confluence space: {space.get('description', {}).get('plain', {}).get('value', 'No description')}"
                ))

            return resources

        except Exception as e:
            print(f"Error fetching Confluence resources: {e}")
            return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Confluence tool."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Confluence credentials"

        try:
            cloud_id = await self._get_cloud_id(oauth_cred)

            # Route to appropriate handler (tool_name arrives WITHOUT the confluence_ prefix)
            if tool_name == "list_spaces":
                return await self._list_spaces(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_space":
                return await self._get_space(cloud_id, arguments, oauth_cred)
            elif tool_name == "list_pages":
                return await self._list_pages(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_page":
                return await self._get_page(cloud_id, arguments, oauth_cred)
            elif tool_name == "create_page":
                return await self._create_page(cloud_id, arguments, oauth_cred)
            elif tool_name == "update_page":
                return await self._update_page(cloud_id, arguments, oauth_cred)
            elif tool_name == "delete_page":
                return await self._delete_page(cloud_id, arguments, oauth_cred)
            elif tool_name == "search_content":
                return await self._search_content(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_page_children":
                return await self._get_page_children(cloud_id, arguments, oauth_cred)
            elif tool_name == "list_page_comments":
                return await self._list_page_comments(cloud_id, arguments, oauth_cred)
            elif tool_name == "add_comment":
                return await self._add_comment(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_page_labels":
                return await self._get_page_labels(cloud_id, arguments, oauth_cred)
            elif tool_name == "add_label":
                return await self._add_label(cloud_id, arguments, oauth_cred)
            elif tool_name == "get_page_history":
                return await self._get_page_history(cloud_id, arguments, oauth_cred)
            elif tool_name == "list_page_attachments":
                return await self._list_page_attachments(cloud_id, arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Confluence tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Confluence resource."""
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Confluence credentials"

        try:
            cloud_id = await self._get_cloud_id(oauth_cred)
            base_url = self._get_api_base_url(cloud_id)

            # Parse resource path: space/{id} or page/{id}
            parts = resource_path.split("/", 1)
            if len(parts) < 2:
                return "Error: Invalid resource path"

            resource_type = parts[0]
            resource_id = parts[1]

            if resource_type == "space":
                response = await self._make_authenticated_request(
                    "GET",
                    f"{base_url}/spaces/{resource_id}",
                    oauth_cred
                )
                return json.dumps(response.json(), indent=2)

            elif resource_type == "page":
                response = await self._make_authenticated_request(
                    "GET",
                    f"{base_url}/pages/{resource_id}",
                    oauth_cred,
                    params={"body-format": "storage"}
                )
                return json.dumps(response.json(), indent=2)

            else:
                return "Error: Unsupported resource type"

        except Exception as e:
            return f"Error reading Confluence resource: {str(e)}"

    # -------------------------------------------------------------------------
    # Private implementation methods
    # -------------------------------------------------------------------------

    async def _list_spaces(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List Confluence spaces."""
        base_url = self._get_api_base_url(cloud_id)

        params: Dict[str, Any] = {
            "limit": arguments.get("limit", 25)
        }
        if "type" in arguments:
            params["type"] = arguments["type"]
        if "status" in arguments:
            params["status"] = arguments["status"]

        print("DEBUG: Listing Confluence spaces")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/spaces",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []

        for space in data.get("results", []):
            result.append({
                "id": space["id"],
                "key": space.get("key"),
                "name": space.get("name"),
                "type": space.get("type"),
                "status": space.get("status"),
                "description": space.get("description", {}).get("plain", {}).get("value")
            })

        print(f"DEBUG: Found {len(result)} spaces")
        return json.dumps(result, indent=2)

    async def _get_space(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get space details by ID."""
        base_url = self._get_api_base_url(cloud_id)
        space_id = arguments["space_id"]

        print(f"DEBUG: Fetching Confluence space: {space_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/spaces/{space_id}",
            oauth_cred
        )

        return json.dumps(response.json(), indent=2)

    async def _list_pages(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List pages, optionally filtered by space."""
        base_url = self._get_api_base_url(cloud_id)

        params: Dict[str, Any] = {
            "limit": arguments.get("limit", 25)
        }
        if "space_id" in arguments:
            params["space-id"] = arguments["space_id"]
        if "sort" in arguments:
            params["sort"] = arguments["sort"]
        if "status" in arguments:
            params["status"] = arguments["status"]

        print("DEBUG: Listing Confluence pages")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/pages",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = []

        for page in data.get("results", []):
            result.append({
                "id": page["id"],
                "title": page.get("title"),
                "status": page.get("status"),
                "spaceId": page.get("spaceId"),
                "createdAt": page.get("createdAt"),
                "version": page.get("version", {}).get("number")
            })

        print(f"DEBUG: Found {len(result)} pages")
        return json.dumps(result, indent=2)

    async def _get_page(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get page by ID including body content in storage format."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]

        print(f"DEBUG: Fetching Confluence page: {page_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/pages/{page_id}",
            oauth_cred,
            params={"body-format": "storage"}
        )

        return json.dumps(response.json(), indent=2)

    async def _create_page(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new page in a space."""
        base_url = self._get_api_base_url(cloud_id)

        payload: Dict[str, Any] = {
            "spaceId": arguments["space_id"],
            "status": "current",
            "title": arguments["title"],
            "body": {
                "representation": "storage",
                "value": arguments["body"]
            }
        }

        if "parent_id" in arguments:
            payload["parentId"] = arguments["parent_id"]

        print(f"DEBUG: Creating Confluence page '{arguments['title']}' in space {arguments['space_id']}")
        response = await self._make_authenticated_request(
            "POST",
            f"{base_url}/pages",
            oauth_cred,
            json=payload
        )

        result = response.json()
        print(f"DEBUG: Created page: {result.get('id')}")
        return json.dumps(result, indent=2)

    async def _update_page(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Update an existing page. Version number must increment."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]
        current_version = arguments["version_number"]
        status = arguments.get("status", "current")

        payload = {
            "id": page_id,
            "status": status,
            "title": arguments["title"],
            "body": {
                "representation": "storage",
                "value": arguments["body"]
            },
            "version": {
                "number": current_version + 1,
                "message": "Updated via SageMCP"
            }
        }

        print(f"DEBUG: Updating Confluence page: {page_id} (v{current_version} -> v{current_version + 1})")
        response = await self._make_authenticated_request(
            "PUT",
            f"{base_url}/pages/{page_id}",
            oauth_cred,
            json=payload
        )

        result = response.json()
        print(f"DEBUG: Page {page_id} updated to version {current_version + 1}")
        return json.dumps(result, indent=2)

    async def _delete_page(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Delete a page by ID."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]

        print(f"DEBUG: Deleting Confluence page: {page_id}")
        await self._make_authenticated_request(
            "DELETE",
            f"{base_url}/pages/{page_id}",
            oauth_cred
        )

        print(f"DEBUG: Page {page_id} deleted successfully")
        return json.dumps({"message": f"Page {page_id} deleted successfully"}, indent=2)

    async def _search_content(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search content using CQL. Uses v1 API endpoint."""
        # CQL search is on the v1 REST API path
        base_url = self._get_api_v1_base_url(cloud_id)
        cql = arguments["cql"]
        limit = arguments.get("limit", 25)

        params = {
            "cql": cql,
            "limit": limit
        }

        print(f"DEBUG: Searching Confluence with CQL: {cql}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/search",
            oauth_cred,
            params=params
        )

        data = response.json()
        result = {
            "totalSize": data.get("totalSize", 0),
            "results": []
        }

        for item in data.get("results", []):
            content = item.get("content", {})
            result["results"].append({
                "title": item.get("title"),
                "type": content.get("type"),
                "id": content.get("id"),
                "status": content.get("status"),
                "spaceKey": content.get("space", {}).get("key") if content.get("space") else None,
                "excerpt": item.get("excerpt"),
                "lastModified": item.get("lastModified"),
                "url": item.get("url")
            })

        print(f"DEBUG: Found {result['totalSize']} search results")
        return json.dumps(result, indent=2)

    async def _get_page_children(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get child pages of a page."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]
        limit = arguments.get("limit", 25)

        print(f"DEBUG: Fetching children of page: {page_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/pages/{page_id}/children",
            oauth_cred,
            params={"limit": limit}
        )

        data = response.json()
        result = []

        for page in data.get("results", []):
            result.append({
                "id": page["id"],
                "title": page.get("title"),
                "status": page.get("status"),
                "spaceId": page.get("spaceId"),
                "version": page.get("version", {}).get("number")
            })

        print(f"DEBUG: Found {len(result)} child pages")
        return json.dumps(result, indent=2)

    async def _list_page_comments(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get footer comments on a page."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]
        limit = arguments.get("limit", 25)

        print(f"DEBUG: Fetching comments for page: {page_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/pages/{page_id}/footer-comments",
            oauth_cred,
            params={"limit": limit}
        )

        data = response.json()
        result = []

        for comment in data.get("results", []):
            result.append({
                "id": comment["id"],
                "status": comment.get("status"),
                "title": comment.get("title"),
                "createdAt": comment.get("createdAt"),
                "version": comment.get("version", {}).get("number"),
                "body": comment.get("body")
            })

        print(f"DEBUG: Found {len(result)} comments")
        return json.dumps(result, indent=2)

    async def _add_comment(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Add a footer comment to a page."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]
        body = arguments["body"]

        payload = {
            "pageId": page_id,
            "body": {
                "representation": "storage",
                "value": body
            }
        }

        print(f"DEBUG: Adding comment to page: {page_id}")
        response = await self._make_authenticated_request(
            "POST",
            f"{base_url}/footer-comments",
            oauth_cred,
            json=payload
        )

        result = response.json()
        print("DEBUG: Comment added successfully")
        return json.dumps(result, indent=2)

    async def _get_page_labels(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get labels on a page."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]

        print(f"DEBUG: Fetching labels for page: {page_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/pages/{page_id}/labels",
            oauth_cred
        )

        data = response.json()
        result = []

        for label in data.get("results", []):
            result.append({
                "id": label.get("id"),
                "name": label.get("name"),
                "prefix": label.get("prefix")
            })

        print(f"DEBUG: Found {len(result)} labels")
        return json.dumps(result, indent=2)

    async def _add_label(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Add a label to a page."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]
        label = arguments["label"]

        # v2 API expects a list of label objects
        payload = [
            {
                "prefix": "global",
                "name": label
            }
        ]

        print(f"DEBUG: Adding label '{label}' to page: {page_id}")
        response = await self._make_authenticated_request(
            "POST",
            f"{base_url}/pages/{page_id}/labels",
            oauth_cred,
            json=payload
        )

        result = response.json()
        print(f"DEBUG: Label '{label}' added successfully")
        return json.dumps(result, indent=2)

    async def _get_page_history(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get version history of a page."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]
        limit = arguments.get("limit", 25)

        print(f"DEBUG: Fetching version history for page: {page_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/pages/{page_id}/versions",
            oauth_cred,
            params={"limit": limit}
        )

        data = response.json()
        result = []

        for version in data.get("results", []):
            result.append({
                "number": version.get("number"),
                "message": version.get("message"),
                "createdAt": version.get("createdAt"),
                "authorId": version.get("authorId"),
                "minorEdit": version.get("minorEdit")
            })

        print(f"DEBUG: Found {len(result)} versions")
        return json.dumps(result, indent=2)

    async def _list_page_attachments(self, cloud_id: str, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List attachments on a page."""
        base_url = self._get_api_base_url(cloud_id)
        page_id = arguments["page_id"]
        limit = arguments.get("limit", 25)

        print(f"DEBUG: Fetching attachments for page: {page_id}")
        response = await self._make_authenticated_request(
            "GET",
            f"{base_url}/pages/{page_id}/attachments",
            oauth_cred,
            params={"limit": limit}
        )

        data = response.json()
        result = []

        for attachment in data.get("results", []):
            result.append({
                "id": attachment.get("id"),
                "title": attachment.get("title"),
                "mediaType": attachment.get("mediaType"),
                "fileSize": attachment.get("fileSize"),
                "status": attachment.get("status"),
                "version": attachment.get("version", {}).get("number"),
                "createdAt": attachment.get("createdAt")
            })

        print(f"DEBUG: Found {len(result)} attachments")
        return json.dumps(result, indent=2)
