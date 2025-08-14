# Python File Upload Server

A FastAPI-based file upload server that replicates the functionality of the Express.js version.

## Features

- ✅ File upload with 20MB size limit
- ✅ Unique filename generation with timestamps
- ✅ CORS support for cross-origin requests
- ✅ Static file serving for uploaded files
- ✅ File listing endpoint (bonus feature)
- ✅ File deletion endpoint (bonus feature)
- ✅ Comprehensive error handling
- ✅ HTML client for testing uploads

## Installation

1. Install dependencies:
```bash
pip install -r requirements_fileserver.txt
```

2. Run the server:
```bash
python file_server.py
```

The server will start on `http://localhost:3000` (or the port specified in the `PORT` environment variable).

## API Endpoints

### Upload File
- **POST** `/upload`
- Upload a single file (max 20MB)
- Returns: `{"success": true, "url": "file_url", "filename": "unique_filename"}`

### Access Files
- **GET** `/uploads/{filename}`
- Access uploaded files directly

### List Files (Bonus)
- **GET** `/files`
- List all uploaded files with metadata

### Delete File (Bonus)
- **DELETE** `/uploads/{filename}`
- Delete an uploaded file

## Usage Examples

### Using curl
```bash
# Upload a file
curl -X POST -F "file=@example.txt" http://localhost:3000/upload

# List files
curl http://localhost:3000/files

# Delete a file
curl -X DELETE http://localhost:3000/uploads/filename.txt
```

### Using the HTML Client
1. Open `upload_client.html` in your browser
2. Drag and drop files or click to select
3. Click "Upload Files" to upload

### Using Python requests
```python
import requests

# Upload file
with open('example.txt', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:3000/upload', files=files)
    print(response.json())
```

## Testing

Run the test script:
```bash
python test_upload.py
```

## Key Differences from Express.js Version

1. **Enhanced Error Handling**: More detailed error responses
2. **Bonus Endpoints**: File listing and deletion capabilities
3. **Better File Metadata**: Returns file size and original filename
4. **Type Safety**: Uses Pydantic models for request/response validation
5. **Async Support**: Built on FastAPI's async foundation

## Configuration

- **Upload Directory**: `uploads/` (created automatically)
- **Max File Size**: 20MB
- **Allowed Origins**: All origins (configurable in CORS middleware)
- **Default Port**: 3000 (configurable via `PORT` environment variable)

## File Structure

```
├── file_server.py          # Main server file
├── requirements_fileserver.txt  # Python dependencies
├── test_upload.py          # Test script
├── upload_client.html      # HTML client for testing
├── uploads/                # Upload directory (auto-created)
└── README_fileserver.md    # This file
```