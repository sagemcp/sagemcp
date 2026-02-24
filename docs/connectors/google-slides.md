# Google Slides Connector

The Google Slides connector provides integration with the Google Slides API and Google Drive API, enabling Claude Desktop to create, manage, and edit presentations, slides, text content, and speaker notes through OAuth 2.0 authentication.

## Features

- **11 comprehensive tools** covering presentation management, slide operations, text editing, and speaker notes
- **Full OAuth 2.0 authentication** with Google account access
- **Slide layout support** with 11 predefined layout options
- **Find-and-replace** across entire presentations
- **Speaker notes** read and write support

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
   - Search for and enable **Google Slides API**
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
   - Add Google Slides connector
   - Complete OAuth authorization flow

### Required OAuth Scopes

The Google Slides connector requests these scopes:
- `https://www.googleapis.com/auth/presentations` - Read and write access to Google Slides presentations
- `https://www.googleapis.com/auth/drive.readonly` - Read-only access to Google Drive (for listing presentations)

## Available Tools

### Presentation Management

#### `google_slides_list_presentations`
List Google Slides presentations accessible to the user.

**Parameters:**
- `page_size` (optional): Number of presentations to return (1-100, default: 20)
- `order_by` (optional): Sort order -- `modifiedTime`, `modifiedTime desc`, `name`, `name desc`, `createdTime`, `createdTime desc` (default: `modifiedTime desc`)

#### `google_slides_get_presentation`
Get detailed metadata and structure of a Google Slides presentation.

**Parameters:**
- `presentation_id` (required): The ID of the Google Slides presentation

#### `google_slides_create_presentation`
Create a new Google Slides presentation with a title.

**Parameters:**
- `title` (required): Title of the new presentation

### Slide Operations

#### `google_slides_get_slide`
Get details of a specific slide by its 0-based index in the presentation.

**Parameters:**
- `presentation_id` (required): The ID of the Google Slides presentation
- `slide_index` (required): 0-based index of the slide to retrieve

#### `google_slides_add_slide`
Add a new slide to a presentation at an optional position with a layout.

**Parameters:**
- `presentation_id` (required): The ID of the Google Slides presentation
- `insertion_index` (optional): 0-based index where the new slide should be inserted. Omit to append at end.
- `layout` (optional): Predefined slide layout -- `BLANK`, `TITLE`, `TITLE_AND_BODY`, `TITLE_ONLY`, `CAPTION_ONLY`, `MAIN_POINT`, `BIG_NUMBER`, `SECTION_HEADER`, `SECTION_TITLE_AND_DESCRIPTION`, `ONE_COLUMN_TEXT`, `TITLE_AND_TWO_COLUMNS` (default: `BLANK`)

#### `google_slides_delete_slide`
Delete a slide from a presentation by its object ID.

**Parameters:**
- `presentation_id` (required): The ID of the Google Slides presentation
- `slide_object_id` (required): The object ID of the slide to delete

#### `google_slides_duplicate_slide`
Duplicate an existing slide in the presentation.

**Parameters:**
- `presentation_id` (required): The ID of the Google Slides presentation
- `slide_object_id` (required): The object ID of the slide to duplicate

### Text Content

#### `google_slides_add_text`
Insert text into a shape (text box) on a slide by its object ID.

**Parameters:**
- `presentation_id` (required): The ID of the Google Slides presentation
- `object_id` (required): The object ID of the shape/text box to insert text into
- `text` (required): The text to insert
- `insertion_index` (optional): Character index within the shape where text should be inserted, 0-based (default: 0)

#### `google_slides_replace_text`
Find and replace all occurrences of text across the entire presentation.

**Parameters:**
- `presentation_id` (required): The ID of the Google Slides presentation
- `find_text` (required): The text to search for
- `replace_text` (required): The text to replace with
- `match_case` (optional): Whether the search should be case-sensitive (default: true)

### Speaker Notes

#### `google_slides_get_speaker_notes`
Get the speaker notes for a specific slide by its 0-based index.

**Parameters:**
- `presentation_id` (required): The ID of the Google Slides presentation
- `slide_index` (required): 0-based index of the slide

#### `google_slides_update_speaker_notes`
Update the speaker notes for a specific slide.

**Parameters:**
- `presentation_id` (required): The ID of the Google Slides presentation
- `slide_object_id` (optional): The object ID of the slide whose notes to update
- `notes_object_id` (required): The object ID of the notes shape (from `slideProperties.notesPage`)
- `text` (required): The new speaker notes text

## Usage Examples

### Example 1: List Presentations

```typescript
"Show me my recent Google Slides presentations"

// This will call google_slides_list_presentations with:
{
  "page_size": 20,
  "order_by": "modifiedTime desc"
}
```

### Example 2: Create a Presentation with Slides

```typescript
"Create a new presentation called 'Q4 Review'"

// This will call google_slides_create_presentation with:
{
  "title": "Q4 Review"
}

// Then add a title slide:
// google_slides_add_slide with:
{
  "presentation_id": "abc123",
  "layout": "TITLE"
}
```

### Example 3: Replace Text Across Slides

```typescript
"Replace all occurrences of '2024' with '2025' in my presentation"

// This will call google_slides_replace_text with:
{
  "presentation_id": "abc123",
  "find_text": "2024",
  "replace_text": "2025"
}
```

### Example 4: Read Speaker Notes

```typescript
"What are the speaker notes on slide 3?"

// This will call google_slides_get_speaker_notes with:
{
  "presentation_id": "abc123",
  "slide_index": 2
}
```

## Troubleshooting

### Common Issues

**Issue**: "Invalid or expired Google OAuth credentials"
- **Solution**: Re-authorize the connector through the SageMCP web interface

**Issue**: "The caller does not have permission" or 403 error
- **Solution**: Ensure the presentation is shared with the authenticated user, or that you own it. Check that both the Slides API and Drive API are enabled in Google Cloud Console.

**Issue**: "Slide index out of range"
- **Solution**: Slide indices are 0-based. Use `get_presentation` to check the total slide count before accessing by index.

**Issue**: "Invalid object ID" on text or delete operations
- **Solution**: Object IDs are internal identifiers, not indices. Use `get_slide` to retrieve the object IDs of elements on a slide before modifying them.

**Issue**: "Rate Limit Exceeded" (429)
- **Solution**: Google Slides API has per-user and per-project quotas (typically 300 requests per minute per project). Batch operations where possible.

### Debug Mode

The connector includes debug logging. Check application logs for detailed API requests:
```
DEBUG: Making Google Slides API request to /v1/presentations/{id}
DEBUG: Google Slides API returned 200
```

## API Reference

- **Google Slides API Documentation**: https://developers.google.com/slides/api/reference/rest
- **Google Drive API Documentation**: https://developers.google.com/drive/api/reference/rest/v3
- **Predefined Layouts**: https://developers.google.com/slides/api/reference/rest/v1/presentations.pages#PredefinedLayout
- **Batch Update Requests**: https://developers.google.com/slides/api/reference/rest/v1/presentations/batchUpdate
- **Usage Limits**: https://developers.google.com/slides/api/limits

## Source Code

Implementation: `src/sage_mcp/connectors/google_slides.py`
