# Google Sheets Connector

The Google Sheets connector provides comprehensive integration with the Google Sheets API and Google Drive API, enabling Claude Desktop to read, write, format, and manage spreadsheets and their individual sheets through OAuth 2.0 authentication.

## Features

- **14 comprehensive tools** covering spreadsheet CRUD, cell read/write, formatting, search, and batch operations
- **Full OAuth 2.0 authentication** with Google account access
- **A1 notation support** for familiar cell range addressing
- **Batch update support** for executing multiple operations in a single request

## OAuth Setup

### Prerequisites

- A Google account
- Access to the Google Cloud Console to create OAuth credentials

### Step-by-Step Configuration

1. **Create Google OAuth Credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/) > APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Web application" as the application type
   - Fill in the details:
     - **Name**: `SageMCP` (or your preferred name)
     - **Authorized redirect URIs**: `http://localhost:8000/api/v1/oauth/callback/google`
   - Click "Create"

2. **Enable Required APIs**
   - In the Google Cloud Console, go to APIs & Services > Library
   - Search for and enable **Google Sheets API**
   - Search for and enable **Google Drive API**

3. **Get Credentials**
   - Note the **Client ID**
   - Note the **Client Secret**
   - Save both credentials securely

4. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     GOOGLE_CLIENT_ID=your_client_id_here
     GOOGLE_CLIENT_SECRET=your_client_secret_here
     ```

5. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add Google Sheets connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The Google Sheets connector requests these scopes:
- `https://www.googleapis.com/auth/spreadsheets` - Read and write access to Google Sheets
- `https://www.googleapis.com/auth/drive.readonly` - Read-only access to Google Drive (for listing and searching spreadsheets)

## Available Tools

### Spreadsheet Management

#### `google_sheets_list_spreadsheets`
List Google Sheets spreadsheets accessible to the user. Use owner_email to find sheets owned by a specific person.

**Parameters:**
- `page_size` (optional): Number of spreadsheets to return (1-100, default: 20)
- `order_by` (optional): Sort order -- `modifiedTime`, `modifiedTime desc`, `name`, `name desc`, `createdTime`, `createdTime desc` (default: `modifiedTime desc`)
- `owner_email` (optional): Filter spreadsheets owned by this email address

#### `google_sheets_get_spreadsheet`
Get detailed metadata about a specific Google Sheets spreadsheet including sheet names, row/column counts, and properties.

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `fields` (optional): Specific fields to return (default: `spreadsheetId,properties,sheets.properties,spreadsheetUrl`)

#### `google_sheets_create_spreadsheet`
Create a new Google Sheets spreadsheet with optional sheet names.

**Parameters:**
- `title` (required): Title of the new spreadsheet
- `sheet_names` (optional): Array of sheet/tab names to create (defaults to a single 'Sheet1')

#### `google_sheets_search_spreadsheets`
Search for Google Sheets spreadsheets by name. Use owner_email to filter by owner.

**Parameters:**
- `query` (required): Search query (searches in spreadsheet name)
- `page_size` (optional): Number of results to return (1-100, default: 20)
- `owner_email` (optional): Filter spreadsheets owned by this email address

### Cell Operations

#### `google_sheets_read_range`
Read values from a range of cells in a Google Sheets spreadsheet using A1 notation (e.g., `Sheet1!A1:D10`, `A1:B5`).

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `range` (required): The A1 notation range to read (e.g., `Sheet1!A1:D10`, `A1:B5`, `Sheet1`)
- `major_dimension` (optional): Whether to return data organized by `ROWS` or `COLUMNS` (default: `ROWS`)
- `value_render_option` (optional): How values should be rendered -- `FORMATTED_VALUE`, `UNFORMATTED_VALUE`, `FORMULA` (default: `FORMATTED_VALUE`)

#### `google_sheets_write_range`
Write values to a range of cells in a Google Sheets spreadsheet. Values are provided as a 2D array (list of rows).

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `range` (required): The A1 notation range to write to (e.g., `Sheet1!A1:D3`)
- `values` (required): 2D array of values to write, where each inner array is a row (e.g., `[["Name","Age"],["Alice",30]]`)
- `value_input_option` (optional): How input data should be interpreted -- `USER_ENTERED` (parses formulas and numbers) or `RAW` (stores as-is) (default: `USER_ENTERED`)

#### `google_sheets_append_rows`
Append rows of data after the last row with content in a Google Sheets spreadsheet.

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `range` (required): The A1 notation of the table to append to (e.g., `Sheet1!A:D`, `Sheet1`)
- `values` (required): 2D array of values to append, where each inner array is a row
- `value_input_option` (optional): How input data should be interpreted -- `USER_ENTERED` or `RAW` (default: `USER_ENTERED`)

#### `google_sheets_clear_range`
Clear all values from a range of cells in a Google Sheets spreadsheet (formatting is preserved).

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `range` (required): The A1 notation range to clear (e.g., `Sheet1!A1:D10`)

### Sheet (Tab) Management

#### `google_sheets_add_sheet`
Add a new sheet (tab) to an existing Google Sheets spreadsheet.

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `title` (required): Title of the new sheet/tab
- `row_count` (optional): Number of rows in the new sheet (default: 1000)
- `column_count` (optional): Number of columns in the new sheet (default: 26)

#### `google_sheets_delete_sheet`
Delete a sheet (tab) from a Google Sheets spreadsheet by its sheet ID.

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `sheet_id` (required): The numeric ID of the sheet/tab to delete (use `get_sheet_metadata` to find sheet IDs)

#### `google_sheets_get_sheet_metadata`
Get metadata for all sheets (tabs) in a spreadsheet, including sheet IDs, titles, row/column counts, and frozen rows/columns.

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet

### Advanced Operations

#### `google_sheets_batch_update`
Execute one or more batch update requests on a spreadsheet. Supports any Sheets API batchUpdate request type (addSheet, deleteSheet, updateCells, mergeCells, etc.).

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `requests` (required): Array of Sheets API batchUpdate request objects (see [Google Sheets API docs](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request) for available request types)

#### `google_sheets_find_and_replace`
Find and replace text across a spreadsheet or within a specific sheet.

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `find` (required): The text to find
- `replacement` (required): The text to replace matches with
- `sheet_id` (optional): Numeric sheet ID to limit search to a specific sheet. Omit to search all sheets.
- `match_case` (optional): Whether the search is case-sensitive (default: false)
- `match_entire_cell` (optional): Whether to match the entire cell content (default: false)
- `search_by_regex` (optional): Whether the find string is a regular expression (default: false)

#### `google_sheets_format_range`
Apply formatting to a range of cells (bold, italic, font size, background color, text color). Colors use RGB floats 0-1.

**Parameters:**
- `spreadsheet_id` (required): The ID of the Google Sheets spreadsheet
- `sheet_id` (required): The numeric sheet ID (use `get_sheet_metadata` to find this)
- `start_row` (required): Start row index (0-based)
- `end_row` (required): End row index (exclusive, 0-based)
- `start_column` (required): Start column index (0-based)
- `end_column` (required): End column index (exclusive, 0-based)
- `bold` (optional): Whether to make text bold
- `italic` (optional): Whether to make text italic
- `font_size` (optional): Font size in points
- `background_color` (optional): Background color as RGB floats (0-1), e.g., `{"red": 1, "green": 0.9, "blue": 0.8}`
- `text_color` (optional): Text color as RGB floats (0-1)

## Usage Examples

### Example 1: Read Spreadsheet Data

```typescript
"Read the sales data from my Q4 Report spreadsheet"

// This will call google_sheets_read_range with:
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
  "range": "Sheet1!A1:F50"
}
```

### Example 2: Write Data to a Sheet

```typescript
"Add the team members to the spreadsheet"

// This will call google_sheets_write_range with:
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
  "range": "Sheet1!A1:C4",
  "values": [
    ["Name", "Role", "Start Date"],
    ["Alice", "Engineer", "2024-01-15"],
    ["Bob", "Designer", "2024-02-01"],
    ["Carol", "PM", "2024-03-10"]
  ]
}
```

### Example 3: Search for a Spreadsheet

```typescript
"Find my budget spreadsheets"

// This will call google_sheets_search_spreadsheets with:
{
  "query": "budget"
}
```

### Example 4: Format Header Row

```typescript
"Make the header row bold with a blue background"

// This will call google_sheets_format_range with:
{
  "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
  "sheet_id": 0,
  "start_row": 0,
  "end_row": 1,
  "start_column": 0,
  "end_column": 6,
  "bold": true,
  "background_color": {"red": 0.8, "green": 0.9, "blue": 1.0}
}
```

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Google OAuth credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "The caller does not have permission" or 403 error
- **Solution**: Ensure the spreadsheet is shared with the authenticated user, or that you own the spreadsheet. Check that both the Sheets API and Drive API are enabled in Google Cloud Console.

**Issue**: "Unable to parse range" error
- **Solution**: Verify A1 notation is correct. Sheet names with spaces must be quoted in the range (e.g., `'My Sheet'!A1:D10`). Use `get_sheet_metadata` to confirm sheet names.

**Issue**: "Rate Limit Exceeded" (429)
- **Solution**: Google Sheets API has per-user and per-project quotas (typically 300 requests per minute per project). Batch multiple operations using `batch_update` where possible.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Google Sheets API request to /v4/spreadsheets/{id}/values/Sheet1!A1:D10
DEBUG: Google Sheets API returned 200
```

## API Reference

- **Google Sheets API Documentation**: https://developers.google.com/sheets/api/reference/rest
- **Google Drive API Documentation**: https://developers.google.com/drive/api/reference/rest/v3
- **A1 Notation Guide**: https://developers.google.com/sheets/api/guides/concepts#cell
- **Batch Update Requests**: https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request
- **Usage Limits**: https://developers.google.com/sheets/api/limits

## Source Code

Implementation: `src/sage_mcp/connectors/google_sheets.py`
