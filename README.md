# TrueLink API v3.3 (Production Ready)

A high-performance FastAPI-based HTTP API built around the `truelink` Python library with comprehensive URL resolution, batch processing, direct link extraction, streaming downloads, and JioSaavn music integration.

## 🚀 Features

### Core Functionality
- **Single & Batch URL Resolution**: Resolve URLs individually or in batches with concurrency control
- **Direct Link Extraction**: Extract direct download links from resolved URLs
- **Streaming Downloads**: Stream content directly to clients without server storage
- **Terabox Support**: Specialized Terabox link resolution with dual API fallback
- **JioSaavn Integration**: Complete music API with search, streaming, and metadata
- **BlackBox AI Integration**: AI-powered code generation, debugging, and optimization

### Performance & Reliability
- **Concurrent Processing**: Batch requests with configurable concurrency limits (default: 5)
- **Request Validation**: Comprehensive input validation using Pydantic models
- **Error Handling**: Detailed error responses with proper HTTP status codes
- **Timeout Management**: Configurable timeouts with automatic validation
- **Resource Management**: Proper cleanup of HTTP connections and sessions
- **Fallback Systems**: Multiple API endpoints with automatic failover

### Security & Monitoring
- **CORS Support**: Configurable cross-origin resource sharing
- **Trusted Hosts**: Host validation middleware for security
- **Health Monitoring**: Detailed health checks with uptime and system info
- **Comprehensive Logging**: Structured logging with configurable levels
- **Performance Tracking**: Request timing and performance metrics
- **Input Sanitization**: Protection against malicious inputs

## 📋 API Endpoints

### Core Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Comprehensive health check with system information |
| `/resolve` | GET | Resolve a single URL with validation and error handling |
| `/resolve-batch` | POST | Resolve multiple URLs concurrently with rate limiting |
| `/supported-domains` | GET | List all supported domains with metadata |
| `/direct` | GET | Extract direct download links from a URL |
| `/redirect` | GET | Redirect to the first available direct download link |
| `/download-stream` | GET | Stream resolved content directly to client |
| `/terabox` | GET | Resolve Terabox links with NDUS cookie |
| `/help` | GET | Comprehensive API documentation |
| `/docs` | GET | Interactive Swagger UI documentation |
| `/redoc` | GET | Alternative ReDoc documentation |

### JioSaavn Music API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/jiosaavn/search` | GET | Global search (songs, albums, artists, playlists) |
| `/jiosaavn/search/songs` | GET | Search for songs with pagination |
| `/jiosaavn/search/albums` | GET | Search for albums with pagination |
| `/jiosaavn/search/artists` | GET | Search for artists with pagination |
| `/jiosaavn/search/playlists` | GET | Search for playlists with pagination |
| `/jiosaavn/songs` | GET | Get songs by IDs or direct link |
| `/jiosaavn/songs/{id}` | GET | Get song details by ID |
| `/jiosaavn/songs/{id}/suggestions` | GET | Get song suggestions for infinite playback |
| `/jiosaavn/albums` | GET | Get album details by ID or link |
| `/jiosaavn/artists` | GET | Get artist details by ID or link |
| `/jiosaavn/artists/{id}` | GET | Get artist by ID with songs and albums |
| `/jiosaavn/artists/{id}/songs` | GET | Get artist's songs with sorting |
| `/jiosaavn/artists/{id}/albums` | GET | Get artist's albums with sorting |
| `/jiosaavn/playlists` | GET | Get playlist details by ID or link |

### BlackBox AI Code Assistant
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/blackboxai/generate` | POST | Generate code using AI based on description |
| `/blackboxai/explain` | GET | Explain and analyze existing code |
| `/blackboxai/debug` | GET | Debug and fix code issues |
| `/blackboxai/optimize` | GET | Optimize code for performance or readability |
| `/blackboxai/convert` | GET | Convert code between programming languages |
| `/blackboxai/chat` | GET | General AI chat for programming questions |

## ⚙️ Configuration

Environment variables for customization:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MAX_BATCH_SIZE` | `25` | Maximum URLs per batch request |
| `DEFAULT_TIMEOUT` | `20` | Default request timeout in seconds |
| `MAX_TIMEOUT` | `120` | Maximum allowed timeout |
| `CONCURRENT_LIMIT` | `5` | Maximum concurrent requests |
| `ENABLE_CORS` | `true` | Enable CORS middleware |
| `TRUSTED_HOSTS` | `*` | Comma-separated list of trusted hosts |
| `CHUNK_SIZE` | `65536` | Streaming chunk size in bytes |

## 🚀 Deployment

### Deploy on Render

1. Push repository to GitHub
2. Create a new Web Service on Render and connect the repo
3. Use the provided `render.yaml` or configure build/start commands manually:
   - **Build Command**: `python3 -m ensurepip --upgrade && pip install --upgrade pip && pip install --upgrade truelink && pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port 10000`

### Docker Deployment

```bash
# Build the image
docker build -t truelink-api .

# Run the container
docker run -p 5000:5000 -e LOG_LEVEL=INFO truelink-api

# Run with custom configuration
docker run -p 5000:5000 \
  -e LOG_LEVEL=DEBUG \
  -e MAX_BATCH_SIZE=50 \
  -e CONCURRENT_LIMIT=10 \
  truelink-api
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
uvicorn app:app --host 0.0.0.0 --port 5000 --reload

# Run with custom log level
LOG_LEVEL=DEBUG uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

## 📖 API Usage Examples

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

### Terabox Resolution
```bash
curl "http://localhost:5000/terabox?url=https://terabox.com/s/1abc&ndus=your_ndus_cookie"
```

### JioSaavn Music Search
```bash
# Global search
curl "http://localhost:5000/jiosaavn/search?query=arijit singh"

# Search songs with pagination
curl "http://localhost:5000/jiosaavn/search/songs?query=bollywood&page=0&limit=20"

# Get song by ID
curl "http://localhost:5000/jiosaavn/songs/3IoDK8qI"

# Get artist details
curl "http://localhost:5000/jiosaavn/artists/1274170"

# Get playlist
curl "http://localhost:5000/jiosaavn/playlists?id=82914609"

# Generate Python code
curl -X POST "http://localhost:5000/blackboxai/generate" \
  -H "Content-Type: application/json" \
  -d '{"query": "create a function to sort a list", "language": "python"}'

# Explain code
curl "http://localhost:5000/blackboxai/explain?code=def%20hello():%20print('world')&language=python"

# Debug code
curl "http://localhost:5000/blackboxai/debug?code=print(hello)&error=NameError&language=python"
```

## 🏗️ Architecture

### Modular Design
```
├── app.py                 # Main FastAPI application
├── config.py             # Configuration management
├── models.py             # Pydantic data models
├── utils.py              # Utility functions
└── endpoints/            # Modular endpoint structure
    ├── __init__.py       # Router exports
    ├── health.py         # Health monitoring
    ├── resolve.py        # Single URL resolution
    ├── batch.py          # Batch processing
    ├── direct.py         # Direct link extraction
    ├── redirect.py       # URL redirection
    ├── download_stream.py # Streaming downloads
    ├── supported_domains.py # Domain listing
    ├── terabox.py        # Terabox integration
    ├── jiosaavn.py       # JioSaavn music API
    ├── root.py           # Root endpoint
    └── help.py           # Documentation
```

### Key Components

- **FastAPI Framework**: High-performance async web framework
- **Pydantic Models**: Data validation and serialization
- **aiohttp**: Async HTTP client for external API calls
- **Concurrent Processing**: asyncio-based concurrency control
- **Error Handling**: Comprehensive exception management
- **Logging**: Structured logging with performance metrics

## 🔧 Technical Details

### Performance Optimizations
- **Connection Pooling**: Reuse HTTP connections for better performance
- **Async Processing**: Non-blocking I/O operations throughout
- **Semaphore Control**: Prevent resource exhaustion with concurrency limits
- **Streaming Responses**: Memory-efficient large file handling
- **Caching**: Domain list caching to reduce API calls

### Error Handling
- **Timeout Management**: Configurable timeouts with graceful degradation
- **Retry Logic**: Automatic retries with exponential backoff
- **Fallback Systems**: Multiple API endpoints for reliability
- **Detailed Logging**: Comprehensive error tracking and debugging

### Security Features
- **Input Validation**: Comprehensive URL and parameter validation
- **CORS Configuration**: Secure cross-origin request handling
- **Host Validation**: Trusted host middleware for security
- **Resource Limits**: Prevent abuse with configurable limits

## 📊 Monitoring & Health

### Health Check Response
```json
{
  "status": "healthy",
  "version": "3.3",
  "uptime": 3600.5,
  "supported_domains_count": 150,
  "memory_usage": {
    "rss": 52428800,
    "vms": 104857600,
    "percent": 5.2
  },
  "system_info": {
    "cpu_count": 4,
    "cpu_percent": 15.3
  }
}
```

### Logging Format
```
2024-01-15 10:30:45 [INFO] truelink-api:45 - Batch resolve started for 5 URLs
2024-01-15 10:30:46 [DEBUG] truelink-api:67 - Resolved https://example.com in 1.23s - Status: success
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Visit `/docs` for interactive API documentation
- **Help Endpoint**: Visit `/help` for comprehensive API information
- **Health Check**: Visit `/health` for system status
- **Issues**: Report bugs and feature requests on GitHub

## 🔄 Changelog

### v3.3 (Current)
- ✅ Fixed JioSaavn path parameter errors
- ✅ Improved Terabox concurrent API execution
- ✅ Enhanced error handling and logging
- ✅ Optimized performance and resource usage
- ✅ Updated documentation and examples

### v3.2
- ✅ Added JioSaavn music API integration
- ✅ Implemented modular endpoint architecture
- ✅ Enhanced batch processing with better concurrency

### v3.1
- ✅ Added Terabox support with dual API fallback
- ✅ Improved streaming downloads
- ✅ Enhanced error handling and validation

---

**Built with ❤️ using FastAPI, Python, and modern async technologies**