# TrueLink API v3.0 (Advanced)

A high-performance FastAPI-based HTTP API built around the `truelink` Python library.
Features comprehensive URL resolution, batch processing, direct link extraction, and streaming downloads.

## Endpoints

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

## Deploy on Render

1. Push repository to GitHub.
2. Create a new Web Service on Render and connect the repo.
3. Use the provided `render.yaml` or configure build/start commands manually.

## Docker Deployment

```bash
# Build the image
docker build -t truelink-api .

# Run the container
docker run -p 5000:5000 -e LOG_LEVEL=INFO truelink-api
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

## Notes

- **Automatic Updates**: Build process installs latest `truelink` version
- **Rate Limiting**: Semaphore-based concurrency control prevents provider overload
- **Data Serialization**: Intelligent conversion of complex objects to JSON
- **Resource Cleanup**: Automatic cleanup of HTTP sessions and connections
- **Error Recovery**: Comprehensive exception handling with meaningful error messages

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
