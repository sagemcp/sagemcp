"""Google Sheets connector implementation."""

import json
from typing import Any, Dict, List, Optional

from mcp import types

from ..models.connector import Connector, ConnectorType
from ..models.oauth_credential import OAuthCredential
from .base import BaseConnector
from .registry import register_connector

SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3/files"
SHEETS_MIME_TYPE = "application/vnd.google-apps.spreadsheet"


@register_connector(ConnectorType.GOOGLE_SHEETS)
class GoogleSheetsConnector(BaseConnector):
    """Google Sheets connector for reading, writing, and managing spreadsheets."""

    @property
    def display_name(self) -> str:
        return "Google Sheets"

    @property
    def description(self) -> str:
        return "Read, write, and manage Google Sheets spreadsheets"

    @property
    def requires_oauth(self) -> bool:
        return True

    async def get_tools(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Tool]:
        """Get available Google Sheets tools."""
        tools = [
            types.Tool(
                name="google_sheets_list_spreadsheets",
                description="List Google Sheets spreadsheets accessible to the user. Use owner_email to find sheets owned by a specific person.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 20,
                            "description": "Number of spreadsheets to return"
                        },
                        "order_by": {
                            "type": "string",
                            "enum": ["modifiedTime", "modifiedTime desc", "name", "name desc", "createdTime", "createdTime desc"],
                            "default": "modifiedTime desc",
                            "description": "Sort order for spreadsheets (append ' desc' for descending)"
                        },
                        "owner_email": {
                            "type": "string",
                            "description": "Filter spreadsheets owned by this email address"
                        }
                    }
                }
            ),
            types.Tool(
                name="google_sheets_get_spreadsheet",
                description="Get detailed metadata about a specific Google Sheets spreadsheet including sheet names, row/column counts, and properties",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "fields": {
                            "type": "string",
                            "description": "Specific fields to return (e.g., 'spreadsheetId,properties,sheets.properties'). Omit to return all metadata.",
                            "default": "spreadsheetId,properties,sheets.properties,spreadsheetUrl"
                        }
                    },
                    "required": ["spreadsheet_id"]
                }
            ),
            types.Tool(
                name="google_sheets_read_range",
                description="Read values from a range of cells in a Google Sheets spreadsheet using A1 notation (e.g., 'Sheet1!A1:D10', 'A1:B5')",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "range": {
                            "type": "string",
                            "description": "The A1 notation range to read (e.g., 'Sheet1!A1:D10', 'A1:B5', 'Sheet1')"
                        },
                        "major_dimension": {
                            "type": "string",
                            "enum": ["ROWS", "COLUMNS"],
                            "default": "ROWS",
                            "description": "Whether to return data organized by rows or columns"
                        },
                        "value_render_option": {
                            "type": "string",
                            "enum": ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
                            "default": "FORMATTED_VALUE",
                            "description": "How values should be rendered (FORMATTED_VALUE shows display values, FORMULA shows formulas)"
                        }
                    },
                    "required": ["spreadsheet_id", "range"]
                }
            ),
            types.Tool(
                name="google_sheets_write_range",
                description="Write values to a range of cells in a Google Sheets spreadsheet. Values are provided as a 2D array (list of rows).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "range": {
                            "type": "string",
                            "description": "The A1 notation range to write to (e.g., 'Sheet1!A1:D3')"
                        },
                        "values": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {}
                            },
                            "description": "2D array of values to write, where each inner array is a row (e.g., [['Name','Age'],['Alice',30]])"
                        },
                        "value_input_option": {
                            "type": "string",
                            "enum": ["USER_ENTERED", "RAW"],
                            "default": "USER_ENTERED",
                            "description": "How input data should be interpreted (USER_ENTERED parses formulas and numbers, RAW stores as-is)"
                        }
                    },
                    "required": ["spreadsheet_id", "range", "values"]
                }
            ),
            types.Tool(
                name="google_sheets_append_rows",
                description="Append rows of data after the last row with content in a Google Sheets spreadsheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "range": {
                            "type": "string",
                            "description": "The A1 notation of the table to append to (e.g., 'Sheet1!A:D', 'Sheet1')"
                        },
                        "values": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {}
                            },
                            "description": "2D array of values to append, where each inner array is a row"
                        },
                        "value_input_option": {
                            "type": "string",
                            "enum": ["USER_ENTERED", "RAW"],
                            "default": "USER_ENTERED",
                            "description": "How input data should be interpreted"
                        }
                    },
                    "required": ["spreadsheet_id", "range", "values"]
                }
            ),
            types.Tool(
                name="google_sheets_clear_range",
                description="Clear all values from a range of cells in a Google Sheets spreadsheet (formatting is preserved)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "range": {
                            "type": "string",
                            "description": "The A1 notation range to clear (e.g., 'Sheet1!A1:D10')"
                        }
                    },
                    "required": ["spreadsheet_id", "range"]
                }
            ),
            types.Tool(
                name="google_sheets_create_spreadsheet",
                description="Create a new Google Sheets spreadsheet with optional sheet names",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the new spreadsheet"
                        },
                        "sheet_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of sheet/tab names to create (defaults to a single 'Sheet1')"
                        }
                    },
                    "required": ["title"]
                }
            ),
            types.Tool(
                name="google_sheets_add_sheet",
                description="Add a new sheet (tab) to an existing Google Sheets spreadsheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the new sheet/tab"
                        },
                        "row_count": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 1000,
                            "description": "Number of rows in the new sheet"
                        },
                        "column_count": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 26,
                            "description": "Number of columns in the new sheet"
                        }
                    },
                    "required": ["spreadsheet_id", "title"]
                }
            ),
            types.Tool(
                name="google_sheets_delete_sheet",
                description="Delete a sheet (tab) from a Google Sheets spreadsheet by its sheet ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "sheet_id": {
                            "type": "integer",
                            "description": "The numeric ID of the sheet/tab to delete (use get_sheet_metadata to find sheet IDs)"
                        }
                    },
                    "required": ["spreadsheet_id", "sheet_id"]
                }
            ),
            types.Tool(
                name="google_sheets_get_sheet_metadata",
                description="Get metadata for all sheets (tabs) in a spreadsheet, including sheet IDs, titles, row/column counts, and frozen rows/columns",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        }
                    },
                    "required": ["spreadsheet_id"]
                }
            ),
            types.Tool(
                name="google_sheets_batch_update",
                description="Execute one or more batch update requests on a spreadsheet. Supports any Sheets API batchUpdate request type (addSheet, deleteSheet, updateCells, mergeCells, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "requests": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Array of Sheets API batchUpdate request objects (see Google Sheets API docs for available request types)"
                        }
                    },
                    "required": ["spreadsheet_id", "requests"]
                }
            ),
            types.Tool(
                name="google_sheets_find_and_replace",
                description="Find and replace text across a spreadsheet or within a specific sheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "find": {
                            "type": "string",
                            "description": "The text to find"
                        },
                        "replacement": {
                            "type": "string",
                            "description": "The text to replace matches with"
                        },
                        "sheet_id": {
                            "type": "integer",
                            "description": "Optional numeric sheet ID to limit search to a specific sheet. Omit to search all sheets."
                        },
                        "match_case": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether the search is case-sensitive"
                        },
                        "match_entire_cell": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to match the entire cell content"
                        },
                        "search_by_regex": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether the find string is a regular expression"
                        }
                    },
                    "required": ["spreadsheet_id", "find", "replacement"]
                }
            ),
            types.Tool(
                name="google_sheets_format_range",
                description="Apply formatting to a range of cells (bold, italic, font size, background color, text color). Colors use RGB floats 0-1.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the Google Sheets spreadsheet"
                        },
                        "sheet_id": {
                            "type": "integer",
                            "description": "The numeric sheet ID (use get_sheet_metadata to find this)"
                        },
                        "start_row": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Start row index (0-based)"
                        },
                        "end_row": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "End row index (exclusive, 0-based)"
                        },
                        "start_column": {
                            "type": "integer",
                            "minimum": 0,
                            "description": "Start column index (0-based)"
                        },
                        "end_column": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "End column index (exclusive, 0-based)"
                        },
                        "bold": {
                            "type": "boolean",
                            "description": "Whether to make text bold"
                        },
                        "italic": {
                            "type": "boolean",
                            "description": "Whether to make text italic"
                        },
                        "font_size": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Font size in points"
                        },
                        "background_color": {
                            "type": "object",
                            "properties": {
                                "red": {"type": "number", "minimum": 0, "maximum": 1},
                                "green": {"type": "number", "minimum": 0, "maximum": 1},
                                "blue": {"type": "number", "minimum": 0, "maximum": 1}
                            },
                            "description": "Background color as RGB floats (0-1), e.g., {\"red\": 1, \"green\": 0.9, \"blue\": 0.8}"
                        },
                        "text_color": {
                            "type": "object",
                            "properties": {
                                "red": {"type": "number", "minimum": 0, "maximum": 1},
                                "green": {"type": "number", "minimum": 0, "maximum": 1},
                                "blue": {"type": "number", "minimum": 0, "maximum": 1}
                            },
                            "description": "Text color as RGB floats (0-1)"
                        }
                    },
                    "required": ["spreadsheet_id", "sheet_id", "start_row", "end_row", "start_column", "end_column"]
                }
            ),
            types.Tool(
                name="google_sheets_search_spreadsheets",
                description="Search for Google Sheets spreadsheets by name. Use owner_email to filter by owner.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (searches in spreadsheet name)"
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
                            "description": "Filter spreadsheets owned by this email address"
                        }
                    },
                    "required": ["query"]
                }
            ),
        ]

        return tools

    async def get_resources(self, connector: Connector, oauth_cred: Optional[OAuthCredential] = None) -> List[types.Resource]:
        """Get available Google Sheets resources.

        Returns an empty list; spreadsheet resources are populated dynamically
        via read_resource with path format 'spreadsheet/{id}'.
        """
        return []

    async def execute_tool(
        self,
        connector: Connector,
        tool_name: str,
        arguments: Dict[str, Any],
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Execute a Google Sheets tool.

        Args:
            connector: The connector configuration.
            tool_name: Tool name WITHOUT the 'google_sheets_' prefix.
            arguments: Tool arguments from the client.
            oauth_cred: OAuth credential for API authentication.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            if tool_name == "list_spreadsheets":
                return await self._list_spreadsheets(arguments, oauth_cred)
            elif tool_name == "get_spreadsheet":
                return await self._get_spreadsheet(arguments, oauth_cred)
            elif tool_name == "read_range":
                return await self._read_range(arguments, oauth_cred)
            elif tool_name == "write_range":
                return await self._write_range(arguments, oauth_cred)
            elif tool_name == "append_rows":
                return await self._append_rows(arguments, oauth_cred)
            elif tool_name == "clear_range":
                return await self._clear_range(arguments, oauth_cred)
            elif tool_name == "create_spreadsheet":
                return await self._create_spreadsheet(arguments, oauth_cred)
            elif tool_name == "add_sheet":
                return await self._add_sheet(arguments, oauth_cred)
            elif tool_name == "delete_sheet":
                return await self._delete_sheet(arguments, oauth_cred)
            elif tool_name == "get_sheet_metadata":
                return await self._get_sheet_metadata(arguments, oauth_cred)
            elif tool_name == "batch_update":
                return await self._batch_update(arguments, oauth_cred)
            elif tool_name == "find_and_replace":
                return await self._find_and_replace(arguments, oauth_cred)
            elif tool_name == "format_range":
                return await self._format_range(arguments, oauth_cred)
            elif tool_name == "search_spreadsheets":
                return await self._search_spreadsheets(arguments, oauth_cred)
            else:
                return f"Unknown tool: {tool_name}"

        except Exception as e:
            return f"Error executing Google Sheets tool '{tool_name}': {str(e)}"

    async def read_resource(
        self,
        connector: Connector,
        resource_path: str,
        oauth_cred: Optional[OAuthCredential] = None
    ) -> str:
        """Read a Google Sheets resource.

        Supports path format: spreadsheet/{spreadsheet_id}
        Returns spreadsheet metadata and sheet names.
        """
        if not oauth_cred or not self.validate_oauth_credential(oauth_cred):
            return "Error: Invalid or expired Google OAuth credentials"

        try:
            parts = resource_path.split("/", 1)
            if len(parts) != 2 or parts[0] != "spreadsheet":
                return "Error: Invalid resource path. Expected format: spreadsheet/{spreadsheet_id}"

            spreadsheet_id = parts[1]

            response = await self._make_authenticated_request(
                "GET",
                f"{SHEETS_API_BASE}/{spreadsheet_id}",
                oauth_cred,
                params={"fields": "spreadsheetId,properties,sheets.properties,spreadsheetUrl"}
            )
            data = response.json()

            title = data.get("properties", {}).get("title", "Untitled")
            sheets = [
                s.get("properties", {}).get("title", "Unknown")
                for s in data.get("sheets", [])
            ]
            url = data.get("spreadsheetUrl", "")

            return f"Spreadsheet: {title}\nURL: {url}\nSheets: {', '.join(sheets)}"

        except Exception as e:
            return f"Error reading Google Sheets resource: {str(e)}"

    # ------------------------------------------------------------------ #
    # Tool implementation methods
    # ------------------------------------------------------------------ #

    async def _list_spreadsheets(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """List Google Sheets spreadsheets via the Drive API."""
        page_size = arguments.get("page_size", 20)
        order_by = arguments.get("order_by", "modifiedTime desc")
        owner_email = arguments.get("owner_email")

        try:
            query = f"mimeType='{SHEETS_MIME_TYPE}'"
            if owner_email:
                query += f" and '{owner_email}' in owners"

            response = await self._make_authenticated_request(
                "GET",
                DRIVE_API_BASE,
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

            return json.dumps({"spreadsheets": result, "count": len(result)}, indent=2)

        except Exception as e:
            return f"Error listing spreadsheets: {str(e)}"

    async def _get_spreadsheet(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get spreadsheet metadata from the Sheets API."""
        spreadsheet_id = arguments["spreadsheet_id"]
        fields = arguments.get("fields", "spreadsheetId,properties,sheets.properties,spreadsheetUrl")

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{SHEETS_API_BASE}/{spreadsheet_id}",
                oauth_cred,
                params={"fields": fields}
            )
            data = response.json()

            result = {
                "spreadsheet_id": data.get("spreadsheetId"),
                "title": data.get("properties", {}).get("title"),
                "locale": data.get("properties", {}).get("locale"),
                "time_zone": data.get("properties", {}).get("timeZone"),
                "url": data.get("spreadsheetUrl"),
                "sheets": []
            }

            for sheet in data.get("sheets", []):
                props = sheet.get("properties", {})
                result["sheets"].append({
                    "sheet_id": props.get("sheetId"),
                    "title": props.get("title"),
                    "index": props.get("index"),
                    "row_count": props.get("gridProperties", {}).get("rowCount"),
                    "column_count": props.get("gridProperties", {}).get("columnCount"),
                    "frozen_row_count": props.get("gridProperties", {}).get("frozenRowCount", 0),
                    "frozen_column_count": props.get("gridProperties", {}).get("frozenColumnCount", 0)
                })

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting spreadsheet: {str(e)}"

    async def _read_range(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Read values from a cell range using the Sheets API values.get endpoint."""
        spreadsheet_id = arguments["spreadsheet_id"]
        range_notation = arguments["range"]
        major_dimension = arguments.get("major_dimension", "ROWS")
        value_render_option = arguments.get("value_render_option", "FORMATTED_VALUE")

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_notation}",
                oauth_cred,
                params={
                    "majorDimension": major_dimension,
                    "valueRenderOption": value_render_option
                }
            )
            data = response.json()

            result = {
                "range": data.get("range"),
                "major_dimension": data.get("majorDimension"),
                "values": data.get("values", [])
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error reading range: {str(e)}"

    async def _write_range(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Write values to a cell range using the Sheets API values.update endpoint."""
        spreadsheet_id = arguments["spreadsheet_id"]
        range_notation = arguments["range"]
        values = arguments["values"]
        value_input_option = arguments.get("value_input_option", "USER_ENTERED")

        try:
            response = await self._make_authenticated_request(
                "PUT",
                f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_notation}",
                oauth_cred,
                params={"valueInputOption": value_input_option},
                json={"values": values}
            )
            data = response.json()

            result = {
                "updated_range": data.get("updatedRange"),
                "updated_rows": data.get("updatedRows"),
                "updated_columns": data.get("updatedColumns"),
                "updated_cells": data.get("updatedCells")
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error writing range: {str(e)}"

    async def _append_rows(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Append rows to a spreadsheet using the Sheets API values.append endpoint."""
        spreadsheet_id = arguments["spreadsheet_id"]
        range_notation = arguments["range"]
        values = arguments["values"]
        value_input_option = arguments.get("value_input_option", "USER_ENTERED")

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_notation}:append",
                oauth_cred,
                params={
                    "valueInputOption": value_input_option,
                    "insertDataOption": "INSERT_ROWS"
                },
                json={"values": values}
            )
            data = response.json()

            updates = data.get("updates", {})
            result = {
                "updated_range": updates.get("updatedRange"),
                "updated_rows": updates.get("updatedRows"),
                "updated_columns": updates.get("updatedColumns"),
                "updated_cells": updates.get("updatedCells")
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error appending rows: {str(e)}"

    async def _clear_range(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Clear values from a cell range using the Sheets API values.clear endpoint."""
        spreadsheet_id = arguments["spreadsheet_id"]
        range_notation = arguments["range"]

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_notation}:clear",
                oauth_cred,
                json={}
            )
            data = response.json()

            result = {
                "cleared_range": data.get("clearedRange"),
                "spreadsheet_id": data.get("spreadsheetId")
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error clearing range: {str(e)}"

    async def _create_spreadsheet(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Create a new spreadsheet using the Sheets API."""
        title = arguments["title"]
        sheet_names = arguments.get("sheet_names")

        try:
            body: Dict[str, Any] = {
                "properties": {"title": title}
            }

            if sheet_names:
                body["sheets"] = [
                    {"properties": {"title": name}}
                    for name in sheet_names
                ]

            response = await self._make_authenticated_request(
                "POST",
                SHEETS_API_BASE,
                oauth_cred,
                json=body
            )
            data = response.json()

            sheets = [
                {
                    "sheet_id": s.get("properties", {}).get("sheetId"),
                    "title": s.get("properties", {}).get("title")
                }
                for s in data.get("sheets", [])
            ]

            result = {
                "spreadsheet_id": data.get("spreadsheetId"),
                "title": data.get("properties", {}).get("title"),
                "url": data.get("spreadsheetUrl"),
                "sheets": sheets
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error creating spreadsheet: {str(e)}"

    async def _add_sheet(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Add a new sheet (tab) to an existing spreadsheet via batchUpdate."""
        spreadsheet_id = arguments["spreadsheet_id"]
        title = arguments["title"]
        row_count = arguments.get("row_count", 1000)
        column_count = arguments.get("column_count", 26)

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate",
                oauth_cred,
                json={
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {
                                    "title": title,
                                    "gridProperties": {
                                        "rowCount": row_count,
                                        "columnCount": column_count
                                    }
                                }
                            }
                        }
                    ]
                }
            )
            data = response.json()

            replies = data.get("replies", [])
            if replies and "addSheet" in replies[0]:
                new_props = replies[0]["addSheet"].get("properties", {})
                result = {
                    "sheet_id": new_props.get("sheetId"),
                    "title": new_props.get("title"),
                    "index": new_props.get("index"),
                    "row_count": new_props.get("gridProperties", {}).get("rowCount"),
                    "column_count": new_props.get("gridProperties", {}).get("columnCount")
                }
            else:
                result = {"success": True, "message": f"Sheet '{title}' added"}

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error adding sheet: {str(e)}"

    async def _delete_sheet(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Delete a sheet (tab) from a spreadsheet via batchUpdate."""
        spreadsheet_id = arguments["spreadsheet_id"]
        sheet_id = arguments["sheet_id"]

        try:
            await self._make_authenticated_request(
                "POST",
                f"{SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate",
                oauth_cred,
                json={
                    "requests": [
                        {
                            "deleteSheet": {
                                "sheetId": sheet_id
                            }
                        }
                    ]
                }
            )

            return json.dumps({"success": True, "message": f"Sheet {sheet_id} deleted"}, indent=2)

        except Exception as e:
            return f"Error deleting sheet: {str(e)}"

    async def _get_sheet_metadata(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Get metadata for all sheets in a spreadsheet."""
        spreadsheet_id = arguments["spreadsheet_id"]

        try:
            response = await self._make_authenticated_request(
                "GET",
                f"{SHEETS_API_BASE}/{spreadsheet_id}",
                oauth_cred,
                params={"fields": "sheets.properties"}
            )
            data = response.json()

            sheets = []
            for sheet in data.get("sheets", []):
                props = sheet.get("properties", {})
                grid = props.get("gridProperties", {})
                sheets.append({
                    "sheet_id": props.get("sheetId"),
                    "title": props.get("title"),
                    "index": props.get("index"),
                    "sheet_type": props.get("sheetType"),
                    "row_count": grid.get("rowCount"),
                    "column_count": grid.get("columnCount"),
                    "frozen_row_count": grid.get("frozenRowCount", 0),
                    "frozen_column_count": grid.get("frozenColumnCount", 0),
                    "hidden": props.get("hidden", False),
                    "right_to_left": props.get("rightToLeft", False)
                })

            return json.dumps({"sheets": sheets, "count": len(sheets)}, indent=2)

        except Exception as e:
            return f"Error getting sheet metadata: {str(e)}"

    async def _batch_update(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Execute arbitrary batchUpdate requests against the Sheets API."""
        spreadsheet_id = arguments["spreadsheet_id"]
        requests = arguments["requests"]

        try:
            response = await self._make_authenticated_request(
                "POST",
                f"{SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate",
                oauth_cred,
                json={"requests": requests}
            )
            data = response.json()

            result = {
                "spreadsheet_id": data.get("spreadsheetId"),
                "replies": data.get("replies", []),
                "reply_count": len(data.get("replies", []))
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error executing batch update: {str(e)}"

    async def _find_and_replace(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Find and replace text in a spreadsheet via batchUpdate."""
        spreadsheet_id = arguments["spreadsheet_id"]
        find_text = arguments["find"]
        replacement = arguments["replacement"]
        sheet_id = arguments.get("sheet_id")
        match_case = arguments.get("match_case", False)
        match_entire_cell = arguments.get("match_entire_cell", False)
        search_by_regex = arguments.get("search_by_regex", False)

        try:
            find_replace_request: Dict[str, Any] = {
                "find": find_text,
                "replacement": replacement,
                "matchCase": match_case,
                "matchEntireCell": match_entire_cell,
                "searchByRegex": search_by_regex,
                "allSheets": sheet_id is None
            }

            if sheet_id is not None:
                find_replace_request["sheetId"] = sheet_id

            response = await self._make_authenticated_request(
                "POST",
                f"{SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate",
                oauth_cred,
                json={
                    "requests": [
                        {"findReplace": find_replace_request}
                    ]
                }
            )
            data = response.json()

            replies = data.get("replies", [])
            if replies and "findReplace" in replies[0]:
                fr = replies[0]["findReplace"]
                result = {
                    "occurrences_changed": fr.get("occurrencesChanged", 0),
                    "values_changed": fr.get("valuesChanged", 0),
                    "sheets_changed": fr.get("sheetsChanged", 0),
                    "formulas_changed": fr.get("formulasChanged", 0),
                    "rows_changed": fr.get("rowsChanged", 0)
                }
            else:
                result = {"occurrences_changed": 0, "message": "No matches found"}

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error in find and replace: {str(e)}"

    async def _format_range(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Apply formatting to a cell range via batchUpdate with repeatCell."""
        spreadsheet_id = arguments["spreadsheet_id"]
        sheet_id = arguments["sheet_id"]
        start_row = arguments["start_row"]
        end_row = arguments["end_row"]
        start_column = arguments["start_column"]
        end_column = arguments["end_column"]

        bold = arguments.get("bold")
        italic = arguments.get("italic")
        font_size = arguments.get("font_size")
        background_color = arguments.get("background_color")
        text_color = arguments.get("text_color")

        try:
            # Build the cell format and fields mask
            cell_format: Dict[str, Any] = {}
            fields_parts = []

            # Text format properties (bold, italic, font size)
            text_format: Dict[str, Any] = {}
            if bold is not None:
                text_format["bold"] = bold
                fields_parts.append("userEnteredFormat.textFormat.bold")
            if italic is not None:
                text_format["italic"] = italic
                fields_parts.append("userEnteredFormat.textFormat.italic")
            if font_size is not None:
                text_format["fontSize"] = font_size
                fields_parts.append("userEnteredFormat.textFormat.fontSize")
            if text_color is not None:
                text_format["foregroundColor"] = text_color
                fields_parts.append("userEnteredFormat.textFormat.foregroundColor")

            if text_format:
                cell_format["textFormat"] = text_format

            if background_color is not None:
                cell_format["backgroundColor"] = background_color
                fields_parts.append("userEnteredFormat.backgroundColor")

            if not fields_parts:
                return json.dumps({"error": "No formatting options specified"}, indent=2)

            request_body = {
                "requests": [
                    {
                        "repeatCell": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": start_row,
                                "endRowIndex": end_row,
                                "startColumnIndex": start_column,
                                "endColumnIndex": end_column
                            },
                            "cell": {
                                "userEnteredFormat": cell_format
                            },
                            "fields": ",".join(fields_parts)
                        }
                    }
                ]
            }

            await self._make_authenticated_request(
                "POST",
                f"{SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate",
                oauth_cred,
                json=request_body
            )

            result = {
                "success": True,
                "message": f"Formatting applied to rows {start_row}-{end_row}, columns {start_column}-{end_column}",
                "applied": {k: v for k, v in [
                    ("bold", bold),
                    ("italic", italic),
                    ("font_size", font_size),
                    ("background_color", background_color),
                    ("text_color", text_color),
                ] if v is not None}
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error formatting range: {str(e)}"

    async def _search_spreadsheets(self, arguments: Dict[str, Any], oauth_cred: OAuthCredential) -> str:
        """Search for spreadsheets by name via the Drive API."""
        query = arguments["query"]
        page_size = arguments.get("page_size", 20)
        owner_email = arguments.get("owner_email")

        try:
            drive_query = f"mimeType='{SHEETS_MIME_TYPE}' and name contains '{query}'"
            if owner_email:
                drive_query += f" and '{owner_email}' in owners"

            response = await self._make_authenticated_request(
                "GET",
                DRIVE_API_BASE,
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
            return f"Error searching spreadsheets: {str(e)}"
