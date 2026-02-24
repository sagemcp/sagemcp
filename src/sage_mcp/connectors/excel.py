"""Microsoft Excel connector implementation.

Uses Microsoft Graph API v1.0 to interact with Excel workbooks stored in
OneDrive. All workbook operations go through the drive items endpoint:
  https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/workbook/

OAuth provider: "microsoft" (Azure AD / Microsoft identity platform).
Scopes typically required: Files.ReadWrite, Files.ReadWrite.All.
"""

import json
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
DRIVE_BASE = f"{GRAPH_API_BASE}/me/drive"
EXCEL_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@register_connector(ConnectorType.EXCEL)
class ExcelConnector(BaseConnector):
    """Microsoft Excel connector for reading, writing, and managing workbooks via Microsoft Graph."""

    @property
    def display_name(self) -> str:
        return "Microsoft Excel"

    @property
    def description(self) -> str:
        return "Read, write, and manage Microsoft Excel workbooks in OneDrive"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Microsoft Excel tools."""
        tools = [
            types.Tool(
                name="excel_list_workbooks",
                description="List Excel workbooks (.xlsx) from the user's OneDrive. Optionally search by filename.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search_query": {
                            "type": "string",
                            "description": "Optional search query to filter workbooks by name"
                        },
                        "top": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 25,
                            "description": "Maximum number of workbooks to return"
                        }
                    }
                }
            ),
            types.Tool(
                name="excel_get_workbook",
                description="Get metadata for an Excel workbook (name, size, last modified, web URL) by its drive item ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        }
                    },
                    "required": ["item_id"]
                }
            ),
            types.Tool(
                name="excel_list_worksheets",
                description="List all worksheets (tabs) in an Excel workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        }
                    },
                    "required": ["item_id"]
                }
            ),
            types.Tool(
                name="excel_read_range",
                description="Read values from a cell range in a worksheet using A1 notation (e.g., 'A1:D10', 'B2:B50')",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        },
                        "worksheet": {
                            "type": "string",
                            "description": "Worksheet name or ID"
                        },
                        "range": {
                            "type": "string",
                            "description": "Cell range in A1 notation (e.g., 'A1:D10')"
                        }
                    },
                    "required": ["item_id", "worksheet", "range"]
                }
            ),
            types.Tool(
                name="excel_write_range",
                description="Write values to a cell range in a worksheet. Values are a 2D array where each inner array is a row.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        },
                        "worksheet": {
                            "type": "string",
                            "description": "Worksheet name or ID"
                        },
                        "range": {
                            "type": "string",
                            "description": "Cell range in A1 notation (e.g., 'A1:D3')"
                        },
                        "values": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {}
                            },
                            "description": "2D array of values to write, e.g., [['Name','Age'],['Alice',30]]"
                        }
                    },
                    "required": ["item_id", "worksheet", "range", "values"]
                }
            ),
            types.Tool(
                name="excel_append_rows",
                description="Append rows to an existing table in a workbook. Values are a 2D array of row data.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name or ID of the table to append rows to"
                        },
                        "values": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {}
                            },
                            "description": "2D array of row values to append, e.g., [['Alice',30],['Bob',25]]"
                        }
                    },
                    "required": ["item_id", "table_name", "values"]
                }
            ),
            types.Tool(
                name="excel_clear_range",
                description="Clear the contents of a cell range in a worksheet (formatting is preserved)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        },
                        "worksheet": {
                            "type": "string",
                            "description": "Worksheet name or ID"
                        },
                        "range": {
                            "type": "string",
                            "description": "Cell range in A1 notation to clear (e.g., 'A1:D10')"
                        }
                    },
                    "required": ["item_id", "worksheet", "range"]
                }
            ),
            types.Tool(
                name="excel_create_workbook",
                description="Create a new empty Excel workbook (.xlsx) in the user's OneDrive root folder",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Filename for the new workbook (should end in .xlsx)"
                        }
                    },
                    "required": ["filename"]
                }
            ),
            types.Tool(
                name="excel_add_worksheet",
                description="Add a new worksheet (tab) to an existing workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        },
                        "name": {
                            "type": "string",
                            "description": "Name for the new worksheet"
                        }
                    },
                    "required": ["item_id", "name"]
                }
            ),
            types.Tool(
                name="excel_delete_worksheet",
                description="Delete a worksheet (tab) from a workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        },
                        "worksheet": {
                            "type": "string",
                            "description": "Worksheet name or ID to delete"
                        }
                    },
                    "required": ["item_id", "worksheet"]
                }
            ),
            types.Tool(
                name="excel_list_tables",
                description="List all tables in an Excel workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        }
                    },
                    "required": ["item_id"]
                }
            ),
            types.Tool(
                name="excel_create_table",
                description="Create a table in a worksheet from a cell range. The range defines the table boundaries including headers.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        },
                        "worksheet": {
                            "type": "string",
                            "description": "Worksheet name or ID"
                        },
                        "address": {
                            "type": "string",
                            "description": "Cell range for the table in A1 notation (e.g., 'A1:D5')"
                        },
                        "has_headers": {
                            "type": "boolean",
                            "default": True,
                            "description": "Whether the first row of the range contains column headers"
                        }
                    },
                    "required": ["item_id", "worksheet", "address"]
                }
            ),
            types.Tool(
                name="excel_get_used_range",
                description="Get the used range (bounding rectangle of all cells with data) for a worksheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        },
                        "worksheet": {
                            "type": "string",
                            "description": "Worksheet name or ID"
                        }
                    },
                    "required": ["item_id", "worksheet"]
                }
            ),
            types.Tool(
                name="excel_run_formula",
                description="Write a formula to a specific cell and return the computed result. The formula is written, the cell is read back to get the calculated value.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The OneDrive item ID of the workbook"
                        },
                        "worksheet": {
                            "type": "string",
                            "description": "Worksheet name or ID"
                        },
                        "cell": {
                            "type": "string",
                            "description": "Target cell in A1 notation (e.g., 'Z1') where the formula will be written"
                        },
                        "formula": {
                            "type": "string",
                            "description": "Excel formula to evaluate (e.g., '=SUM(A1:A10)', '=AVERAGE(B2:B50)')"
                        }
                    },
                    "required": ["item_id", "worksheet", "cell", "formula"]
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Excel resources.

        Returns an empty list; workbook resources are populated dynamically
        via read_resource with path format 'workbook/{item_id}'.
        """
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Microsoft Excel tool.

        Args:
            connector: The connector configuration.
            tool_name: Tool name WITHOUT the 'excel_' prefix.
            arguments: Tool arguments from the client.
            oauth_cred: OAuth credential for Microsoft Graph API authentication.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Microsoft OAuth credentials"

        try:
            if tool_name == "list_workbooks":
                return await self._list_workbooks(arguments, oauth_cred)
            elif tool_name == "get_workbook":
                return await self._get_workbook(arguments, oauth_cred)
            elif tool_name == "list_worksheets":
                return await self._list_worksheets(arguments, oauth_cred)
            elif tool_name == "read_range":
                return await self._read_range(arguments, oauth_cred)
            elif tool_name == "write_range":
                return await self._write_range(arguments, oauth_cred)
            elif tool_name == "append_rows":
                return await self._append_rows(arguments, oauth_cred)
            elif tool_name == "clear_range":
                return await self._clear_range(arguments, oauth_cred)
            elif tool_name == "create_workbook":
                return await self._create_workbook(arguments, oauth_cred)
            elif tool_name == "add_worksheet":
                return await self._add_worksheet(arguments, oauth_cred)
            elif tool_name == "delete_worksheet":
                return await self._delete_worksheet(arguments, oauth_cred)
            elif tool_name == "list_tables":
                return await self._list_tables(arguments, oauth_cred)
            elif tool_name == "create_table":
                return await self._create_table(arguments, oauth_cred)
            elif tool_name == "get_used_range":
                return await self._get_used_range(arguments, oauth_cred)
            elif tool_name == "run_formula":
                return await self._run_formula(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Excel tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read an Excel resource.

        Supports path format: workbook/{item_id}
        Returns workbook metadata and worksheet names.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Microsoft OAuth credentials"

        try:
            parts = resource_path.split("/", 1)
            if len(parts) != 2 or parts[0] != "workbook":
                return "Error: Invalid resource path. Expected format: workbook/{item_id}"

            item_id = parts[1]

            # Get workbook metadata
            response = await self._make_authenticated_request(
                "GET",
                f"{DRIVE_BASE}/items/{item_id}",
                oauth_cred,
                params={"$select": "id,name,size,lastModifiedDateTime,webUrl"}
            )
            meta = response.json()

            # Get worksheet list
            ws_response = await self._make_authenticated_request(
                "GET",
                f"{DRIVE_BASE}/items/{item_id}/workbook/worksheets",
                oauth_cred
            )
            ws_data = ws_response.json()
            sheets = [ws.get("name", "Unknown") for ws in ws_data.get("value", [])]

            name = meta.get("name", "Untitled")
            url = meta.get("webUrl", "")

            return f"Workbook: {name}\nURL: {url}\nWorksheets: {', '.join(sheets)}"

        except Exception as e:
            return f"Error reading Excel resource: {str(e)}"

    # ------------------------------------------------------------------ #
    # Helper: build workbook API URL with proper encoding
    # ------------------------------------------------------------------ #

    def _workbook_url(self, item_id: str) -> str:
        """Return the base workbook URL for a drive item."""
        return f"{DRIVE_BASE}/items/{item_id}/workbook"

    def _worksheet_url(self, item_id: str, worksheet: str) -> str:
        """Return the URL for a specific worksheet, properly quoting the name."""
        encoded = quote(worksheet, safe="")
        return f"{self._workbook_url(item_id)}/worksheets/{encoded}"

    # ------------------------------------------------------------------ #
    # Tool implementation methods
    # ------------------------------------------------------------------ #

    async def _list_workbooks(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List Excel workbooks from OneDrive via the Graph API search endpoint."""
        search_query = arguments.get("search_query")
        top = arguments.get("top", 25)

        try:
            if search_query:
                # Use the drive search endpoint which searches file content and metadata
                response = await self._make_authenticated_request(
                    "GET",
                    f"{DRIVE_BASE}/root/search(q='{quote(search_query, safe='')}')",
                    oauth_cred,
                    params={
                        "$top": top,
                        "$select": "id,name,size,lastModifiedDateTime,webUrl,file",
                    }
                )
            else:
                # List children of root, filtered to .xlsx files
                response = await self._make_authenticated_request(
                    "GET",
                    f"{DRIVE_BASE}/root/children",
                    oauth_cred,
                    params={
                        "$top": top,
                        "$select": "id,name,size,lastModifiedDateTime,webUrl,file",
                        "$filter": "file ne null",
                    }
                )

            items = response.json().get("value", [])

            # Filter to Excel files only
            workbooks = []
            for item in items:
                mime = item.get("file", {}).get("mimeType", "")
                name = item.get("name", "")
                if mime == EXCEL_MIME_TYPE or name.lower().endswith(".xlsx"):
                    workbooks.append({
                        "id": item.get("id"),
                        "name": name,
                        "size": item.get("size"),
                        "last_modified": item.get("lastModifiedDateTime"),
                        "web_url": item.get("webUrl"),
                    })

            return json.dumps({"workbooks": workbooks, "count": len(workbooks)}, indent=2)

        except Exception as e:
            return f"Error listing workbooks: {str(e)}"

    async def _get_workbook(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get metadata for a specific workbook."""
        item_id = arguments["item_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{DRIVE_BASE}/items/{item_id}",
                oauth_cred,
                params={
                    "$select": "id,name,size,createdDateTime,lastModifiedDateTime,webUrl,createdBy,lastModifiedBy"
                }
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "size": data.get("size"),
                "created": data.get("createdDateTime"),
                "last_modified": data.get("lastModifiedDateTime"),
                "web_url": data.get("webUrl"),
                "created_by": data.get("createdBy", {}).get("user", {}).get("displayName"),
                "last_modified_by": data.get("lastModifiedBy", {}).get("user", {}).get("displayName"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting workbook: {str(e)}"

    async def _list_worksheets(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List all worksheets in a workbook."""
        item_id = arguments["item_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{self._workbook_url(item_id)}/worksheets",
                oauth_cred
            )
            data = response.json()

            worksheets = []
            for ws in data.get("value", []):
                worksheets.append({
                    "id": ws.get("id"),
                    "name": ws.get("name"),
                    "position": ws.get("position"),
                    "visibility": ws.get("visibility"),
                })

            return json.dumps({"worksheets": worksheets, "count": len(worksheets)}, indent=2)

        except Exception as e:
            return f"Error listing worksheets: {str(e)}"

    async def _read_range(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Read values from a cell range in a worksheet."""
        item_id = arguments["item_id"]
        worksheet = arguments["worksheet"]
        range_addr = arguments["range"]

        try:
            encoded_range = quote(range_addr, safe="")
            response = await self._make_authenticated_request(
                "GET",
                f"{self._worksheet_url(item_id, worksheet)}/range(address='{encoded_range}')",
                oauth_cred
            )
            data = response.json()

            result = {
                "address": data.get("address"),
                "row_count": data.get("rowCount"),
                "column_count": data.get("columnCount"),
                "values": data.get("values", []),
                "formulas": data.get("formulas", []),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error reading range: {str(e)}"

    async def _write_range(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Write values to a cell range in a worksheet."""
        item_id = arguments["item_id"]
        worksheet = arguments["worksheet"]
        range_addr = arguments["range"]
        values = arguments["values"]

        try:
            encoded_range = quote(range_addr, safe="")
            response = await self._make_authenticated_request(
                "PATCH",
                f"{self._worksheet_url(item_id, worksheet)}/range(address='{encoded_range}')",
                oauth_cred,
                json={"values": values}
            )
            data = response.json()

            result = {
                "address": data.get("address"),
                "row_count": data.get("rowCount"),
                "column_count": data.get("columnCount"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error writing range: {str(e)}"

    async def _append_rows(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Append rows to a table in a workbook."""
        item_id = arguments["item_id"]
        table_name = arguments["table_name"]
        values = arguments["values"]

        try:
            encoded_table = quote(table_name, safe="")
            response = await self._make_authenticated_request(
                "POST",
                f"{self._workbook_url(item_id)}/tables/{encoded_table}/rows/add",
                oauth_cred,
                json={"values": values}
            )
            data = response.json()

            result = {
                "index": data.get("index"),
                "values": data.get("values", []),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error appending rows: {str(e)}"

    async def _clear_range(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Clear contents of a cell range in a worksheet."""
        item_id = arguments["item_id"]
        worksheet = arguments["worksheet"]
        range_addr = arguments["range"]

        try:
            encoded_range = quote(range_addr, safe="")
            await self._make_authenticated_request(
                "POST",
                f"{self._worksheet_url(item_id, worksheet)}/range(address='{encoded_range}')/clear",
                oauth_cred,
                json={"applyTo": "Contents"}
            )

            return json.dumps({"success": True, "message": f"Range {range_addr} cleared"}, indent=2)

        except Exception as e:
            return f"Error clearing range: {str(e)}"

    async def _create_workbook(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new empty Excel workbook in OneDrive.

        Uses PUT with empty content to create a minimal .xlsx file.
        The Graph API auto-generates a valid workbook from the content type.
        """
        filename = arguments["filename"]

        # Ensure filename ends with .xlsx
        if not filename.lower().endswith(".xlsx"):
            filename = f"{filename}.xlsx"

        try:
            encoded_name = quote(filename, safe="")
            response = await self._make_authenticated_request(
                "PUT",
                f"{DRIVE_BASE}/root:/{encoded_name}:/content",
                oauth_cred,
                headers={"Content-Type": EXCEL_MIME_TYPE},
                content=b""
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "web_url": data.get("webUrl"),
                "size": data.get("size"),
                "created": data.get("createdDateTime"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error creating workbook: {str(e)}"

    async def _add_worksheet(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Add a new worksheet to a workbook."""
        item_id = arguments["item_id"]
        name = arguments["name"]

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{self._workbook_url(item_id)}/worksheets/add",
                oauth_cred,
                json={"name": name}
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "position": data.get("position"),
                "visibility": data.get("visibility"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error adding worksheet: {str(e)}"

    async def _delete_worksheet(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Delete a worksheet from a workbook."""
        item_id = arguments["item_id"]
        worksheet = arguments["worksheet"]

        try:
            await self._make_authenticated_request(
                "DELETE",
                self._worksheet_url(item_id, worksheet),
                oauth_cred
            )

            return json.dumps({"success": True, "message": f"Worksheet '{worksheet}' deleted"}, indent=2)

        except Exception as e:
            return f"Error deleting worksheet: {str(e)}"

    async def _list_tables(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List all tables in a workbook."""
        item_id = arguments["item_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{self._workbook_url(item_id)}/tables",
                oauth_cred
            )
            data = response.json()

            tables = []
            for table in data.get("value", []):
                tables.append({
                    "id": table.get("id"),
                    "name": table.get("name"),
                    "show_headers": table.get("showHeaders"),
                    "show_totals": table.get("showTotals"),
                    "style": table.get("style"),
                })

            return json.dumps({"tables": tables, "count": len(tables)}, indent=2)

        except Exception as e:
            return f"Error listing tables: {str(e)}"

    async def _create_table(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a table in a worksheet from a cell range."""
        item_id = arguments["item_id"]
        worksheet = arguments["worksheet"]
        address = arguments["address"]
        has_headers = arguments.get("has_headers", True)

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{self._worksheet_url(item_id, worksheet)}/tables/add",
                oauth_cred,
                json={
                    "address": address,
                    "hasHeaders": has_headers,
                }
            )
            data = response.json()

            result = {
                "id": data.get("id"),
                "name": data.get("name"),
                "show_headers": data.get("showHeaders"),
                "style": data.get("style"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error creating table: {str(e)}"

    async def _get_used_range(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get the used range of a worksheet (the bounding rectangle of all cells with data)."""
        item_id = arguments["item_id"]
        worksheet = arguments["worksheet"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{self._worksheet_url(item_id, worksheet)}/usedRange",
                oauth_cred
            )
            data = response.json()

            result = {
                "address": data.get("address"),
                "row_count": data.get("rowCount"),
                "column_count": data.get("columnCount"),
                "values": data.get("values", []),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting used range: {str(e)}"

    async def _run_formula(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Write a formula to a cell, then read back the computed result.

        This two-step approach (write formula, read value) works reliably
        because Microsoft Graph recalculates workbook formulas on write.
        """
        item_id = arguments["item_id"]
        worksheet = arguments["worksheet"]
        cell = arguments["cell"]
        formula = arguments["formula"]

        try:
            # Step 1: Write the formula to the target cell
            encoded_cell = quote(cell, safe="")
            await self._make_authenticated_request(
                "PATCH",
                f"{self._worksheet_url(item_id, worksheet)}/range(address='{encoded_cell}')",
                oauth_cred,
                json={"formulas": [[formula]]}
            )

            # Step 2: Read back the cell to get the computed value
            response = await self._make_authenticated_request(
                "GET",
                f"{self._worksheet_url(item_id, worksheet)}/range(address='{encoded_cell}')",
                oauth_cred
            )
            data = response.json()

            values = data.get("values", [[None]])
            formulas = data.get("formulas", [[None]])

            result = {
                "cell": cell,
                "formula": formulas[0][0] if formulas and formulas[0] else formula,
                "value": values[0][0] if values and values[0] else None,
                "address": data.get("address"),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error running formula: {str(e)}"
