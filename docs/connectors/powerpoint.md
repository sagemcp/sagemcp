# Microsoft PowerPoint Connector

The PowerPoint connector provides integration with Microsoft Graph API v1.0 for managing PowerPoint presentations stored in OneDrive, enabling Claude Desktop to list, create, copy, move, delete, export, and inspect presentations through OAuth 2.0 authentication with Azure AD.

## Features

- **10 comprehensive tools** covering file management, slide thumbnails, PDF export, and content preview
- **Microsoft OAuth 2.0 (Azure AD)** authentication with delegated permissions
- **OneDrive integration** for cloud-based presentation management
- **PDF export** for converting presentations to PDF format
- **Slide thumbnails** for visual inspection without downloading binary files

## OAuth Setup

### Prerequisites

- A Microsoft account (personal or Microsoft 365 / work / school)
- Access to the [Azure Portal](https://portal.azure.com/) to register an application
- PowerPoint presentations stored in OneDrive

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
   - Add PowerPoint connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The PowerPoint connector requests these delegated permissions:
- `Files.ReadWrite` - Read and write access to the user's files in OneDrive
- `User.Read` - Sign in and read user profile

## Available Tools

### Presentation Management

#### `powerpoint_list_presentations`
List PowerPoint (.pptx) files from the user's OneDrive. Optionally filter by search query.

**Parameters:**
- `search_query` (optional): Optional search term to filter presentations by name
- `top` (optional): Maximum number of results to return (1-100, default: 25)

#### `powerpoint_get_presentation`
Get metadata for a specific PowerPoint presentation (file size, created/modified dates, download URL, etc.).

**Parameters:**
- `item_id` (required): The OneDrive item ID of the presentation

#### `powerpoint_create_presentation`
Create a new empty PowerPoint presentation on OneDrive. The filename should end with .pptx.

**Parameters:**
- `filename` (required): Name of the new file (should end with .pptx, e.g., `My Presentation.pptx`)

#### `powerpoint_copy_presentation`
Copy a PowerPoint presentation to a new file, optionally in a different folder.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the presentation to copy
- `new_name` (required): Name for the copied file (e.g., `Copy of Presentation.pptx`)
- `parent_folder_id` (optional): Optional OneDrive folder ID to copy into. Omit to copy in the same folder.

#### `powerpoint_move_presentation`
Move a PowerPoint presentation to a different OneDrive folder.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the presentation to move
- `destination_folder_id` (required): The OneDrive folder ID to move the presentation into

#### `powerpoint_delete_presentation`
Delete a PowerPoint presentation from OneDrive. This moves the file to the recycle bin.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the presentation to delete

### Slide Inspection

#### `powerpoint_list_slides`
List slide thumbnails for a PowerPoint presentation. Returns thumbnail URLs and dimensions for each slide.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the presentation

#### `powerpoint_get_slide_content`
Get a preview/embed URL for a PowerPoint presentation. Useful for inspecting slide content without downloading the binary file.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the presentation

### Export & Upload

#### `powerpoint_export_pdf`
Export a PowerPoint presentation as a PDF. Returns the PDF download URL or content metadata.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the presentation to export

#### `powerpoint_upload_presentation`
Get the upload URL for updating an existing PowerPoint file. Returns the endpoint and instructions for direct Graph API upload.

**Parameters:**
- `item_id` (required): The OneDrive item ID of the presentation to update

## Usage Examples

### Example 1: List Presentations

```typescript
"Show me my PowerPoint presentations"

// This will call powerpoint_list_presentations with:
{
  "top": 25
}
```

### Example 2: Search for a Presentation

```typescript
"Find my Q4 review presentation"

// This will call powerpoint_list_presentations with:
{
  "search_query": "Q4 review",
  "top": 10
}
```

### Example 3: Get Slide Thumbnails

```typescript
"Show me the slides in this presentation"

// This will call powerpoint_list_slides with:
{
  "item_id": "01ABCDEFG..."
}
```

### Example 4: Export to PDF

```typescript
"Export this presentation as a PDF"

// This will call powerpoint_export_pdf with:
{
  "item_id": "01ABCDEFG..."
}
```

### Example 5: Copy a Presentation

```typescript
"Make a copy of this presentation called 'Q4 Review - Draft'"

// This will call powerpoint_copy_presentation with:
{
  "item_id": "01ABCDEFG...",
  "new_name": "Q4 Review - Draft.pptx"
}
```

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Microsoft OAuth credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "Access denied" or 403 error
- **Solution**: Ensure the app registration has `Files.ReadWrite` delegated permission. Admin consent may be required for organizational accounts.

**Issue**: "Item not found" error
- **Solution**: The `item_id` is the OneDrive item ID, not the filename. Use `powerpoint_list_presentations` to find the correct item ID.

**Issue**: "Copy operation returns 202 with no immediate result"
- **Solution**: The copy operation is asynchronous in Microsoft Graph. The response includes a `monitor_url` that can be polled to check the copy status. The copied file will appear in OneDrive once the operation completes.

**Issue**: "Cannot preview or export presentation"
- **Solution**: The presentation must be a valid .pptx file stored in OneDrive. Corrupted files or non-PowerPoint files renamed to .pptx will fail. Verify the file opens correctly in PowerPoint Online.

**Issue**: "Request rate limit exceeded" (429)
- **Solution**: Microsoft Graph has throttling limits. Back off and retry. Typical limits are ~10,000 requests per 10 minutes.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making PowerPoint API request to /me/drive/items/{id}
DEBUG: PowerPoint API returned 200
```

## API Reference

- **Microsoft Graph Drive Items API**: https://learn.microsoft.com/en-us/graph/api/resources/driveitem
- **Thumbnails API**: https://learn.microsoft.com/en-us/graph/api/driveitem-list-thumbnails
- **File Content & Conversion**: https://learn.microsoft.com/en-us/graph/api/driveitem-get-content-format
- **Copy Operations**: https://learn.microsoft.com/en-us/graph/api/driveitem-copy
- **Throttling Guidance**: https://learn.microsoft.com/en-us/graph/throttling

## Source Code

Implementation: `src/sage_mcp/connectors/powerpoint.py`
