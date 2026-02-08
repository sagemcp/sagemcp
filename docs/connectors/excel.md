# Microsoft Excel Connector

The Excel connector provides comprehensive integration with Microsoft Graph API v1.0 for managing Excel workbooks stored in OneDrive, enabling Claude Desktop to read, write, create, and manage workbooks, worksheets, tables, and formulas through OAuth 2.0 authentication with Azure AD.

## Features

- **14 comprehensive tools** covering workbook CRUD, cell read/write, tables, formulas, and worksheet management
- **Microsoft OAuth 2.0 (Azure AD)** authentication with delegated permissions
- **A1 notation support** for familiar cell range addressing
- **Table operations** for structured data management with headers and auto-formatting
- **Formula evaluation** with write-and-readback for computed results

## OAuth Setup

### Prerequisites

- A Microsoft account (personal or Microsoft 365 / work / school)
- Access to the [Azure Portal](https://portal.azure.com/) to register an application
- Excel workbooks stored in OneDrive

### Step-by-Step Configuration

1. **Register an Azure AD Application**
   - Go to Azure Portal > Azure Active Directory > App registrations
   - Click "New registration"
   - Fill in the details:
     - **Name**: `SageMCP` (or your preferred name)
     - **Supported account types**: "Accounts in any organizational directory and personal Microsoft accounts"
     - **Redirect URI**: Select "Web" and enter `http://localhost:8000/api/v1/oauth/callback/microsoft`
   - Click "Register"

2. **Configure API Permissions**
   - In your app registration, go to "API permissions"
   - Click "Add a permission" > "Microsoft Graph" > "Delegated permissions"
   - Add the following permissions:
     - `Files.ReadWrite`
     - `User.Read`
   - Click "Grant admin consent" if you have admin access (optional but recommended)

3. **Get Credentials**
   - Go to "Certificates & secrets" > "New client secret"
   - Note the **Application (client) ID** from the Overview page
   - Note the **Client Secret** value (copy immediately -- it is only shown once)

4. **Configure SageMCP**
   - Add to your `.env` file:
     ```env
     MICROSOFT_CLIENT_ID=your_client_id_here
     MICROSOFT_CLIENT_SECRET=your_client_secret_here
     ```

5. **Add Connector in SageMCP**
   - Open SageMCP web interface
   - Create or select a tenant
   - Add Excel connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The Excel connector requests these delegated permissions:
- `Files.ReadWrite` - Read and write access to the user's files in OneDrive
- `User.Read` - Sign in and read user profile

## Available Tools

### Workbook Management

#### `excel_list_workbooks`
List Excel workbooks (.xlsx) from the user's OneDrive. Optionally search by filename.

**Parameters:**
- `search_query` (optional): Optional search query to filter workbooks by name
- `top` (optional): Maximum number of workbooks to return (1-100, default: 25)

#### `excel_get_workbook`
Get metadata for an Excel workbook (name, size, last modified, web URL) by its drive item ID.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook

#### `excel_create_workbook`
Create a new empty Excel workbook (.xlsx) in the user's OneDrive root folder.

**Parameters:**
- `filename` (required): Filename for the new workbook (should end in .xlsx)

### Worksheet Management

#### `excel_list_worksheets`
List all worksheets (tabs) in an Excel workbook.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook

#### `excel_add_worksheet`
Add a new worksheet (tab) to an existing workbook.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook
- `name` (required): Name for the new worksheet

#### `excel_delete_worksheet`
Delete a worksheet (tab) from a workbook.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook
- `worksheet` (required): Worksheet name or ID to delete

### Cell Operations

#### `excel_read_range`
Read values from a cell range in a worksheet using A1 notation (e.g., `A1:D10`, `B2:B50`).

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook
- `worksheet` (required): Worksheet name or ID
- `range` (required): Cell range in A1 notation (e.g., `A1:D10`)

#### `excel_write_range`
Write values to a cell range in a worksheet. Values are a 2D array where each inner array is a row.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook
- `worksheet` (required): Worksheet name or ID
- `range` (required): Cell range in A1 notation (e.g., `A1:D3`)
- `values` (required): 2D array of values to write (e.g., `[["Name","Age"],["Alice",30]]`)

#### `excel_append_rows`
Append rows to an existing table in a workbook. Values are a 2D array of row data.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook
- `table_name` (required): Name or ID of the table to append rows to
- `values` (required): 2D array of row values to append (e.g., `[["Alice",30],["Bob",25]]`)

#### `excel_clear_range`
Clear the contents of a cell range in a worksheet (formatting is preserved).

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook
- `worksheet` (required): Worksheet name or ID
- `range` (required): Cell range in A1 notation to clear (e.g., `A1:D10`)

#### `excel_get_used_range`
Get the used range (bounding rectangle of all cells with data) for a worksheet.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook
- `worksheet` (required): Worksheet name or ID

### Table Operations

#### `excel_list_tables`
List all tables in an Excel workbook.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook

#### `excel_create_table`
Create a table in a worksheet from a cell range. The range defines the table boundaries including headers.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook
- `worksheet` (required): Worksheet name or ID
- `address` (required): Cell range for the table in A1 notation (e.g., `A1:D5`)
- `has_headers` (optional): Whether the first row of the range contains column headers (default: true)

### Formulas

#### `excel_run_formula`
Write a formula to a specific cell and return the computed result. The formula is written, the cell is read back to get the calculated value.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the workbook
- `worksheet` (required): Worksheet name or ID
- `cell` (required): Target cell in A1 notation (e.g., `Z1`) where the formula will be written
- `formula` (required): Excel formula to evaluate (e.g., `=SUM(A1:A10)`, `=AVERAGE(B2:B50)`)

## Usage Examples

### Example 1: Read Spreadsheet Data

```typescript
"Read the data from my Sales Report workbook"

// This will call excel_read_range with:
{
  "item_id": "01ABCDEFG...",
  "worksheet": "Sheet1",
  "range": "A1:F50"
}
```

### Example 2: Write Data to a Workbook

```typescript
"Add the team members to the workbook"

// This will call excel_write_range with:
{
  "item_id": "01ABCDEFG...",
  "worksheet": "Sheet1",
  "range": "A1:C4",
  "values": [
    ["Name", "Role", "Start Date"],
    ["Alice", "Engineer", "2024-01-15"],
    ["Bob", "Designer", "2024-02-01"],
    ["Carol", "PM", "2024-03-10"]
  ]
}
```

### Example 3: Run a Formula

```typescript
"Calculate the sum of column A in my workbook"

// This will call excel_run_formula with:
{
  "item_id": "01ABCDEFG...",
  "worksheet": "Sheet1",
  "cell": "Z1",
  "formula": "=SUM(A1:A100)"
}
```

### Example 4: Create a Table from Data

```typescript
"Create a table from the data in A1 through D10"

// This will call excel_create_table with:
{
  "item_id": "01ABCDEFG...",
  "worksheet": "Sheet1",
  "address": "A1:D10",
  "has_headers": true
}
```

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Microsoft OAuth credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "Access denied" or 403 error
- **Solution**: Ensure the app registration has `Files.ReadWrite` delegated permission. Admin consent may be required for organizational accounts.

**Issue**: "Item not found" error
- **Solution**: The `item_id` is the OneDrive item ID, not the filename. Use `excel_list_workbooks` to find the correct item ID for your workbook.

**Issue**: "The requested range exceeds the grid limits"
- **Solution**: Verify the range is within the worksheet dimensions. Use `excel_get_used_range` to discover the current data boundaries.

**Issue**: "Workbook session has expired"
- **Solution**: Microsoft Graph workbook sessions have a timeout. The connector uses sessionless operations, but complex operations may encounter this. Retry the request.

**Issue**: "Request rate limit exceeded" (429)
- **Solution**: Microsoft Graph has throttling limits. Back off and retry. Typical limits are ~10,000 requests per 10 minutes.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Excel API request to /me/drive/items/{id}/workbook/worksheets/Sheet1/range(address='A1:D10')
DEBUG: Excel API returned 200
```

## API Reference

- **Microsoft Graph Excel API**: https://learn.microsoft.com/en-us/graph/api/resources/excel
- **Workbook Operations**: https://learn.microsoft.com/en-us/graph/api/resources/workbook
- **Range Operations**: https://learn.microsoft.com/en-us/graph/api/resources/range
- **Table Operations**: https://learn.microsoft.com/en-us/graph/api/resources/table
- **Throttling Guidance**: https://learn.microsoft.com/en-us/graph/throttling

## Source Code

Implementation: `src/sage_mcp/connectors/excel.py`
