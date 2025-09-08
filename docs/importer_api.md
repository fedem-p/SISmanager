# Importer API Endpoints Documentation

This document describes the REST API endpoints for the SISmanager importer functionality.

## Base URL
All endpoints are prefixed with the importer blueprint base URL.

## Endpoints

### 1. Upload Files
**POST** `/api/upload`

Upload one or more XLSX/XLS files for processing.

**Request:**
- Content-Type: `multipart/form-data`
- Body: Form data with `files` field containing one or more files

**Response:**
```json
{
  "message": "Successfully uploaded N file(s)",
  "files": [
    {
      "id": "uuid-string",
      "original_name": "filename.xlsx",
      "filename": "uuid_filename.xlsx",
      "size": 12345,
      "status": "uploaded"
    }
  ]
}
```

**Error Codes:**
- 400: No files provided, no files selected, file too large, or invalid file type
- 500: Internal server error

---

### 2. Process File
**POST** `/api/process/<file_id>`

Process an uploaded file using the XLSXImporter service.

**Request Body (optional):**
```json
{
  "columns_to_keep": ["column1", "column2", "column3"]
}
```

**Response:**
```json
{
  "message": "Successfully processed filename.xlsx",
  "rows_processed": 150
}
```

**Error Codes:**
- 404: File not found
- 200: File already processed
- 500: Processing error

---

### 3. Remove Duplicates
**POST** `/api/remove-duplicates/<file_id>`

Remove duplicates from a processed file.

**Request Body (optional):**
```json
{
  "mode": "forceful"
}
```
- `mode`: "forceful" (default) or "soft"

**Response:**
```json
{
  "message": "Successfully removed duplicates"
}
```

**Error Codes:**
- 404: File not found
- 400: File not processed yet
- 200: Duplicates already removed
- 500: Error removing duplicates

---

### 4. Export File
**POST** `/api/export/<file_id>`

Export processed file to XLSX format.

**Request Body (optional):**
```json
{
  "columns": ["orderCode", "idOrderPos", "descrizioneMateriale", "codiceMateriale"]
}
```

**Response:**
```json
{
  "message": "Successfully exported filename.xlsx",
  "download_url": "/api/download/<file_id>"
}
```

**Error Codes:**
- 404: File not found
- 400: File not processed yet
- 500: Export error

---

### 5. Download File
**GET** `/api/download/<file_id>`

Download the exported XLSX file.

**Response:**
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- File attachment with exported data

**Error Codes:**
- 404: File not found or not exported yet
- 400: File not exported yet
- 500: Download error

---

### 6. Get File Status
**GET** `/api/status/<file_id>`

Get the processing status of a specific file.

**Response:**
```json
{
  "file_info": {
    "id": "uuid-string",
    "original_name": "filename.xlsx",
    "filename": "uuid_filename.xlsx",
    "size": 12345,
    "status": "uploaded"
  },
  "processed": true,
  "duplicates_removed": false,
  "exported": true,
  "download_url": "/api/download/<file_id>",
  "error": null
}
```

**Error Codes:**
- 404: File not found
- 500: Server error

---

### 7. Get All Files Status
**GET** `/api/status`

Get the processing status of all uploaded files.

**Response:**
```json
{
  "file_id_1": {
    "file_info": {...},
    "processed": true,
    "duplicates_removed": false,
    "exported": true,
    "download_url": "/api/download/file_id_1",
    "error": null
  },
  "file_id_2": {
    "file_info": {...},
    "processed": false,
    "duplicates_removed": false,
    "exported": false,
    "error": "Processing failed: some error"
  }
}
```

**Error Codes:**
- 500: Server error

---

### 8. Cleanup File
**DELETE** `/api/cleanup/<file_id>`

Remove uploaded and exported files from the server and clear processing status.

**Response:**
```json
{
  "message": "File cleaned up successfully"
}
```

**Error Codes:**
- 404: File not found
- 500: Cleanup error

---

## File Processing Workflow

The typical workflow for processing files is:

1. **Upload** files using `/api/upload`
2. **Process** each file using `/api/process/<file_id>`
3. **Remove duplicates** (optional) using `/api/remove-duplicates/<file_id>`
4. **Export** processed data using `/api/export/<file_id>`
5. **Download** the exported file using `/api/download/<file_id>`
6. **Cleanup** files when done using `/api/cleanup/<file_id>`

You can check the status at any time using `/api/status/<file_id>` or `/api/status`.

## File Constraints

- **Allowed file types:** `.xlsx`, `.xls`
- **Maximum file size:** 16MB
- **Upload directory:** `data/uploads/`

## Error Handling

All endpoints return appropriate HTTP status codes and JSON error messages:

```json
{
  "error": "Descriptive error message"
}
```

Common error scenarios:
- File not found (404)
- Invalid file type (400)
- File too large (400)
- Processing not complete (400)
- Internal server errors (500)
