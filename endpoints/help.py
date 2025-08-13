"""
Help endpoint
"""
from fastapi import APIRouter

from config import Config, TRUELINK_AVAILABLE

router = APIRouter()

@router.get("/help")
async def help_page():
    """Comprehensive API documentation"""
    return {
        "api": "Advanced TrueLink API v3.1",
        "description": "High-performance API for resolving URLs to direct download links",
        "features": [
            "Single and batch URL resolution",
            "Direct link extraction",
            "Streaming downloads", 
            "Terabox support",
            "Comprehensive error handling",
            "Request validation",
            "Performance monitoring"
        ],
        "endpoints": {
            "/health": "Check API status and system information",
            "/resolve": "Resolve a single URL with optional parameters",
            "/resolve-batch": "Resolve multiple URLs concurrently (POST)",
            "/supported-domains": "List all supported domains",
            "/direct": "Extract only direct download links from a URL",
            "/redirect": "Redirect to the first resolved direct link",
            "/download-stream": "Stream resolved content directly to client",
            "/terabox": "Resolve Terabox links with NDUS cookie",
            "/jiosaavn/*": "JioSaavn music API endpoints for search and streaming",
            "/help": "Show this comprehensive help page",
            "/docs": "Interactive API documentation (Swagger UI)",
            "/redoc": "Alternative API documentation (ReDoc)"
        },
        "limits": {
            "max_batch_size": Config.MAX_BATCH_SIZE,
            "max_timeout": Config.MAX_TIMEOUT,
            "concurrent_limit": Config.CONCURRENT_LIMIT
        },
        "configuration": {
            "truelink_available": TRUELINK_AVAILABLE,
            "cors_enabled": Config.ENABLE_CORS,
            "log_level": Config.LOG_LEVEL
        }
    }