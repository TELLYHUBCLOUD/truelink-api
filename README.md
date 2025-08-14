# Multi-Purpose API Suite

A comprehensive FastAPI-based API suite featuring:
1. **TrueLink API v3.1** - Advanced URL resolution and direct link extraction
2. **File Upload API** - Secure file hosting with 20MB limit
3. **Social Media Download API** - Content download from 21+ platforms

## TrueLink API Endpoints

### Core Endpoints
- `GET /health` - Comprehensive health check with system information
- `GET /resolve` - Resolve a single URL with validation and error handling
- `POST /resolve-batch` - Resolve multiple URLs concurrently with rate limiting
- `GET /supported-domains` - List all supported domains with metadata
- `GET /direct` - Extract direct download links from a URL
- `GET /redirect` - Redirect to the first available direct download link
- `GET /download-stream` - Stream resolved content directly to client
- `GET /help` - Comprehensive API documentation
- `GET /docs` - Interactive Swagger UI documentation
- `GET /redoc` - Alternative ReDoc documentation

## File Upload API

### File Upload Service (`file_upload.py`)
- `POST /upload` - Upload files up to 20MB
- `GET /uploads/{filename}` - Access uploaded files
- `GET /health` - Service health check

**Features:**
- 20MB file size limit
- Automatic unique filename generation
- CORS enabled for cross-origin requests
- Static file serving
- Comprehensive error handling

**Usage:**
```bash
# Upload a file
curl -X POST "http://localhost:3000/upload" -F "file=@example.pdf"
```

## Social Media Download API

### Supported Platforms (21 services)
- **Video Platforms**: YouTube, TikTok, Vimeo, Dailymotion, Bilibili, Twitch, Streamable
- **Social Networks**: Instagram, Twitter/X, Facebook, Reddit, Snapchat, Tumblr, Pinterest
- **Audio Platforms**: Soundcloud, Spotify
- **International**: Ok.ru, VK, Rutube
- **Professional**: Loom
- **Emerging**: Bluesky

### Social Media Endpoints
- `GET /download?url={social_url}` - Download content from social media
- `GET /services` - List all supported platforms

**Usage:**
```bash
# Download from YouTube
curl "http://localhost:3000/download?url=https://youtube.com/watch?v=example"

# Download from TikTok
curl "http://localhost:3000/download?url=https://tiktok.com/@user/video/123"

# Download from Instagram
curl "http://localhost:3000/download?url=https://instagram.com/p/example"
```

**Response Format:**
```json
{
  "success": true,
  "data": {
    "title": "Video Title",
    "thumbnail": "https://...",
    "download_links": ["https://..."],
    "duration": "00:03:45"
  },
  "processing_time": 2.34,
  "service": "Youtube"
}
```

## Features

### Performance & Reliability
- **Concurrent Processing**: Batch requests with configurable concurrency limits
- **Request Validation**: Comprehensive input validation using Pydantic
- **Error Handling**: Detailed error responses with proper HTTP status codes
- **Timeout Management**: Configurable timeouts with automatic validation
- **Resource Management**: Proper cleanup of HTTP connections and sessions

### Security & Monitoring
- **CORS Support**: Configurable cross-origin resource sharing
- **Trusted Hosts**: Host validation middleware
- **Health Monitoring**: Detailed health checks with uptime and system info
- **Comprehensive Logging**: Structured logging with configurable levels
- **Performance Tracking**: Request timing and performance metrics

### Configuration
Environment variables for customization:
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `MAX_BATCH_SIZE`: Maximum URLs per batch request (default: 50)
- `DEFAULT_TIMEOUT`: Default request timeout in seconds (default: 20)
- `MAX_TIMEOUT`: Maximum allowed timeout (default: 120)
- `CONCURRENT_LIMIT`: Maximum concurrent requests (default: 8)
- `ENABLE_CORS`: Enable CORS middleware (default: true)
- `TRUSTED_HOSTS`: Comma-separated list of trusted hosts (default: *)

### File Upload Configuration
- `PORT`: Server port (default: 3000)
- Maximum file size: 20MB
- Supported file types: All formats
- Upload directory: `./uploads`

## Deploy on Render

1. Push repository to GitHub.
2. Create a new Web Service on Render and connect the repo.
3. Use the provided `render.yaml` or configure build/start commands manually.

## Docker Deployment

### TrueLink API
```bash
# Build the image
docker build -t truelink-api .

# Run the container
docker run -p 5000:5000 -e LOG_LEVEL=INFO truelink-api
```

### File Upload API
```bash
# Install dependencies
pip install -r requirements_upload.txt

# Run the file upload server
python file_upload.py

# Or with uvicorn directly
uvicorn file_upload:app --host 0.0.0.0 --port 3000 --reload
```

## Local Development

### TrueLink API
```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

### File Upload & Social Media API
```bash
# Install dependencies
pip install -r requirements_upload.txt

# Run the development server
python file_upload.py
```

## Notes

- **Automatic Updates**: Build process installs latest `truelink` version
- **Rate Limiting**: Semaphore-based concurrency control prevents provider overload
- **Data Serialization**: Intelligent conversion of complex objects to JSON
- **Resource Cleanup**: Automatic cleanup of HTTP sessions and connections
- **Error Recovery**: Comprehensive exception handling with meaningful error messages

### File Upload Features
- **Size Validation**: 20MB maximum file size with proper error handling
- **Unique Naming**: Timestamp-based filename generation to prevent conflicts
- **Static Serving**: Direct file access via `/uploads/{filename}` endpoint

## API Usage Examples

### Single URL Resolution
```bash
curl "http://localhost:5000/resolve?url=https://example.com/file&timeout=30"
```

### Batch Resolution
```bash
curl -X POST "http://localhost:5000/resolve-batch" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example1.com", "https://example2.com"]}'
```

### Direct Links Only
```bash
curl "http://localhost:5000/direct?url=https://example.com/file"
```

### Stream Download
```bash
curl "http://localhost:5000/download-stream?url=https://example.com/file" --output file.zip
```

### File Upload
```bash
curl -X POST "http://localhost:3000/upload" \
  -F "file=@document.pdf"
```

### Social Media Download
```bash
curl "http://localhost:3000/download?url=https://youtube.com/watch?v=dQw4w9WgXcQ"
curl "http://localhost:3000/download?url=https://tiktok.com/@user/video/123456"
```
