import os
import asyncio
import logging
import time
import json
import psutil
from typing import Any, Optional, Dict, List
from contextlib import asynccontextmanager
from urllib.parse import quote, urlparse

from fastapi import FastAPI, Query, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, HttpUrl, Field, validator
import aiohttp
import requests
from requests import Session

# Try to import truelink, fallback if not available
try:
    from truelink import TrueLinkResolver
    TRUELINK_AVAILABLE = True
except ImportError:
    TRUELINK_AVAILABLE = False
    logging.warning("TrueLink library not available, using fallback implementation")

# ---------- Configuration ----------
class Config:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "50"))
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "20"))
    MAX_TIMEOUT = int(os.getenv("MAX_TIMEOUT", "120"))
    CONCURRENT_LIMIT = int(os.getenv("CONCURRENT_LIMIT", "8"))
    ENABLE_CORS = os.getenv("ENABLE_CORS", "true").lower() == "true"
    TRUSTED_HOSTS = [host.strip() for host in os.getenv("TRUSTED_HOSTS", "*").split(",")]
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "65536"))  # 64KB

    @classmethod
    def validate(cls):
        """Validate configuration values"""
        if cls.MAX_BATCH_SIZE <= 0:
            raise ValueError("MAX_BATCH_SIZE must be positive")
        if cls.DEFAULT_TIMEOUT <= 0:
            raise ValueError("DEFAULT_TIMEOUT must be positive")
        if cls.MAX_TIMEOUT < cls.DEFAULT_TIMEOUT:
            raise ValueError("MAX_TIMEOUT must be >= DEFAULT_TIMEOUT")
        if cls.CONCURRENT_LIMIT <= 0:
            raise ValueError("CONCURRENT_LIMIT must be positive")

# Validate configuration on startup
try:
    Config.validate()
except ValueError as e:
    logging.error(f"Configuration error: {e}")
    raise

# ---------- Logging Setup ----------
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("api.log") if os.access(".", os.W_OK) else logging.NullHandler()
    ]
)
logger = logging.getLogger("truelink-api")

# ---------- Pydantic Models ----------
class BatchRequest(BaseModel):
    urls: List[HttpUrl] = Field(
        ..., 
        min_items=1, 
        max_items=Config.MAX_BATCH_SIZE,
        description=f"List of URLs to resolve (max {Config.MAX_BATCH_SIZE})"
    )
    
    @validator('urls')
    def validate_urls(cls, v):
        if len(v) > Config.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {Config.MAX_BATCH_SIZE} URLs allowed")
        # Convert to strings and validate
        validated_urls = []
        for url in v:
            url_str = str(url)
            if not is_valid_url(url_str):
                raise ValueError(f"Invalid URL: {url_str}")
            validated_urls.append(url_str)
        return validated_urls

class ResolveResponse(BaseModel):
    url: str = Field(..., description="Original URL")
    status: str = Field(..., description="Resolution status")
    type: Optional[str] = Field(None, description="Type of resolved data")
    data: Optional[Dict[str, Any]] = Field(None, description="Resolved data")
    message: Optional[str] = Field(None, description="Status message or error details")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")

class BatchResponse(BaseModel):
    count: int = Field(..., description="Number of URLs processed")
    results: List[ResolveResponse] = Field(..., description="Resolution results")
    total_processing_time: float = Field(..., description="Total processing time in seconds")
    success_count: int = Field(..., description="Number of successful resolutions")
    error_count: int = Field(..., description="Number of failed resolutions")

class DirectLinksResponse(BaseModel):
    url: str = Field(..., description="Original URL")
    direct_links: List[str] = Field(..., description="Extracted direct download links")
    count: int = Field(..., description="Number of direct links found")
    processing_time: float = Field(..., description="Processing time in seconds")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    uptime: float = Field(..., description="Service uptime in seconds")
    supported_domains_count: int = Field(..., description="Number of supported domains")
    memory_usage: Optional[Dict[str, Any]] = Field(None, description="Memory usage statistics")
    system_info: Optional[Dict[str, Any]] = Field(None, description="System information")

class TeraboxResponse(BaseModel):
    status: str = Field(..., description="Response status")
    file_name: Optional[str] = Field(None, description="File name")
    thumb: Optional[str] = Field(None, description="Thumbnail URL")
    size: Optional[str] = Field(None, description="Human readable file size")
    sizebytes: Optional[int] = Field(None, description="File size in bytes")    
    link: Optional[str] = Field(None, description="Original link")
    direct_link: Optional[str] = Field(None, description="Direct download link")
    dl1: Optional[str] = Field(None, description="Download link 1")
    dl2: Optional[str] = Field(None, description="Download link 2")


# ---------- Global Variables ----------
app_start_time = time.time()
resolver_instance = None

# ---------- Utility Functions ----------
def is_valid_url(url: str) -> bool:
    """Validate if a string is a proper URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ('http', 'https')
    except Exception:
        return False

def get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage statistics"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss,
            "vms": memory_info.vms,
            "percent": process.memory_percent(),
            "available": psutil.virtual_memory().available,
            "total": psutil.virtual_memory().total
        }
    except Exception as e:
        logger.warning(f"Could not get memory usage: {e}")
        return {}

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    try:
        return {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(),
            "disk_usage": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free
            }
        }
    except Exception as e:
        logger.warning(f"Could not get system info: {e}")
        return {}

def to_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format with improved error handling"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return to_serializable(obj.dict())
        except Exception as e:
            logger.debug(f"Serialization error on dict(): {e}")
            return str(obj)
    if hasattr(obj, "__dict__"):
        return {
            k: to_serializable(v) 
            for k, v in obj.__dict__.items() 
            if not k.startswith("_")
        }
    try:
        # Try JSON serialization with default string conversion
        return json.loads(json.dumps(obj, default=str))
    except (TypeError, ValueError, RecursionError):
        return str(obj)

def validate_timeout(timeout: int) -> int:
    """Validate and clamp timeout value"""
    return max(1, min(timeout, Config.MAX_TIMEOUT))

def validate_retries(retries: int) -> int:
    """Validate and clamp retries value"""
    return max(0, min(retries, 10))

def extract_direct_links(resolved_data: Dict[str, Any]) -> List[str]:
    """Extract direct download links from resolved data with improved logic"""
    links = set()  # Use set to avoid duplicates
    possible_fields = [
        "direct_links", "files", "items", "url", "download_url", 
        "direct_url", "links", "file_url", "download_link", "dl_link"
    ]

    def is_valid_download_url(url_str: str) -> bool:
        """Check if string is a valid download URL"""
        if not isinstance(url_str, str):
            return False
        if not url_str.startswith(("http://", "https://")):
            return False
        # Avoid obvious non-download URLs
        if any(domain in url_str.lower() for domain in ["javascript:", "mailto:", "tel:"]):
            return False
        return True

    def walk_data(obj, depth=0):
        """Recursively walk through data structure to find URLs"""
        if depth > 15:  # Prevent infinite recursion
            return
        
        if not obj:
            return
            
        if is_valid_download_url(obj):
            links.add(obj)
            return
            
        if isinstance(obj, dict):
            # Prioritize known fields first
            for field in possible_fields:
                if field in obj and obj[field]:
                    walk_data(obj[field], depth + 1)
            
            # Walk through other fields
            for k, v in obj.items():
                if k not in possible_fields:
                    walk_data(v, depth + 1)
                    
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                walk_data(item, depth + 1)

    data = resolved_data.get("data", resolved_data)
    walk_data(data)
    
    result_links = list(links)
    logger.debug(f"Extracted {len(result_links)} direct links")
    return result_links

# ---------- Fallback Resolver ----------
class FallbackResolver:
    """Fallback resolver when TrueLink is not available"""
    
    def __init__(self, timeout: int = 20, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def is_supported(self, url: str) -> bool:
        """Check if URL is supported (basic implementation)"""
        return is_valid_url(url)
    
    async def resolve(self, url: str, use_cache: bool = True) -> Dict[str, Any]:
        """Basic URL resolution"""
        try:
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            return {
                "url": response.url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "final_url": response.url
            }
        except Exception as e:
            raise Exception(f"Failed to resolve URL: {str(e)}")
    
    @staticmethod
    def get_supported_domains() -> List[str]:
        """Return basic supported domains"""
        return ["example.com", "test.com"]  # Placeholder

async def resolve_single(
    url: str, 
    timeout: int = Config.DEFAULT_TIMEOUT, 
    retries: int = 3, 
    use_cache: bool = True
) -> ResolveResponse:
    """Resolve a single URL with comprehensive error handling and timing"""
    start_time = time.time()
    timeout = validate_timeout(timeout)
    retries = validate_retries(retries)
    
    logger.debug(f"Resolving URL: {url} | Timeout: {timeout}s | Retries: {retries} | Cache: {use_cache}")
    
    try:
        # Use TrueLink if available, otherwise use fallback
        if TRUELINK_AVAILABLE:
            resolver = TrueLinkResolver(timeout=timeout, max_retries=retries)
        else:
            resolver = FallbackResolver(timeout=timeout, max_retries=retries)
        
        if not resolver.is_supported(url):
            logger.warning(f"Unsupported URL: {url}")
            return ResolveResponse(
                url=url,
                status="unsupported",
                message="URL domain is not supported",
                processing_time=time.time() - start_time
            )

        # Handle async/sync resolver methods
        if TRUELINK_AVAILABLE and hasattr(resolver, 'resolve') and asyncio.iscoroutinefunction(resolver.resolve):
            result = await resolver.resolve(url, use_cache=use_cache)
        else:
            # Run in thread pool for sync operations
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, resolver.resolve, url, use_cache)
        
        processing_time = time.time() - start_time
        
        logger.debug(f"Successfully resolved {url} in {processing_time:.2f}s")
        
        return ResolveResponse(
            url=url,
            status="success",
            type=type(result).__name__,
            data=to_serializable(result),
            processing_time=processing_time
        )
        
    except asyncio.TimeoutError:
        processing_time = time.time() - start_time
        logger.warning(f"Timeout resolving {url} after {processing_time:.2f}s")
        return ResolveResponse(
            url=url,
            status="timeout",
            message=f"Request timed out after {timeout}s",
            processing_time=processing_time
        )
    except Exception as exc:
        processing_time = time.time() - start_time
        logger.exception(f"Error resolving {url}: {exc}")
        return ResolveResponse(
            url=url,
            status="error",
            message=str(exc),
            processing_time=processing_time
        )

# ---------- Lifespan Management ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global resolver_instance
    logger.info("Starting TrueLink API...")
    
    # Initialize resolver if available
    if TRUELINK_AVAILABLE:
        try:
            resolver_instance = TrueLinkResolver(
                timeout=Config.DEFAULT_TIMEOUT,
                max_retries=3
            )
            logger.info("TrueLink resolver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TrueLink resolver: {e}")
            resolver_instance = None
    else:
        logger.info("Using fallback resolver")
        resolver_instance = FallbackResolver()
    
    logger.info("TrueLink API started successfully")
    yield
    
    logger.info("Shutting down TrueLink API...")
    # Cleanup if needed
    resolver_instance = None

# ---------- FastAPI App ----------
app = FastAPI(
    title="Advanced TrueLink API",
    version="3.1",
    description="High-performance API for resolving URLs to direct download links with improved error handling",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ---------- Middleware ----------
if Config.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if "*" in Config.TRUSTED_HOSTS else Config.TRUSTED_HOSTS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=Config.TRUSTED_HOSTS
)

# ---------- Exception Handlers ----------
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"ValueError from {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Invalid input", 
            "message": str(exc),
            "timestamp": time.time()
        }
    )

@app.exception_handler(asyncio.TimeoutError)
async def timeout_error_handler(request: Request, exc: asyncio.TimeoutError):
    logger.warning(f"Timeout error from {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        content={
            "error": "Request timeout", 
            "message": "The request took too long to process",
            "timestamp": time.time()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception from {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": time.time()
        }
    )

# ---------- API Endpoints ----------
@app.get("/health", response_model=HealthResponse)
async def health():
    """Enhanced health check with system information"""
    try:
        uptime = time.time() - app_start_time
        
        # Get supported domains count
        domains_count = 0
        try:
            if TRUELINK_AVAILABLE:
                domains = TrueLinkResolver.get_supported_domains()
                domains_count = len(domains)
            else:
                domains_count = len(FallbackResolver.get_supported_domains())
        except Exception as e:
            logger.warning(f"Could not get supported domains: {e}")
        
        return HealthResponse(
            status="healthy",
            version="3.1",
            uptime=uptime,
            supported_domains_count=domains_count,
            memory_usage=get_memory_usage(),
            system_info=get_system_info()
        )
    except Exception as exc:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(exc)}"
        )

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Advanced TrueLink API v3.1",
        "documentation": "/docs",
        "help": "/help",
        "health": "/health",
        "features": [
            "Single and batch URL resolution",
            "Direct link extraction", 
            "Streaming downloads",
            "Terabox support",
            "Comprehensive error handling"
        ]
    }

@app.get("/help")
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

@app.get("/resolve", response_model=ResolveResponse)
async def resolve_url(
    url: HttpUrl = Query(..., description="URL to resolve"),
    timeout: int = Query(Config.DEFAULT_TIMEOUT, ge=1, le=Config.MAX_TIMEOUT, description="Request timeout in seconds"),
    retries: int = Query(3, ge=0, le=10, description="Number of retry attempts"),
    cache: bool = Query(True, description="Enable/disable caching")
):
    """Resolve a single URL with comprehensive validation and error handling"""
    result = await resolve_single(str(url), timeout=timeout, retries=retries, use_cache=cache)
    
    if result.status == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.message
        )
    elif result.status == "timeout":
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=result.message
        )
    elif result.status == "unsupported":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message
        )
    
    return result

@app.post("/resolve-batch", response_model=BatchResponse)
async def resolve_batch(
    payload: BatchRequest,
    timeout: int = Query(Config.DEFAULT_TIMEOUT, ge=1, le=Config.MAX_TIMEOUT),
    retries: int = Query(3, ge=0, le=10),
    cache: bool = Query(True)
):
    """Resolve multiple URLs concurrently with rate limiting"""
    start_time = time.time()
    urls = [str(url) for url in payload.urls]
    
    logger.info(f"Batch resolve request for {len(urls)} URLs")
    
    # Use semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(Config.CONCURRENT_LIMIT)

    async def semaphore_task(url: str):
        async with semaphore:
            return await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)

    try:
        results = await asyncio.gather(
            *[semaphore_task(url) for url in urls],
            return_exceptions=True
        )
        
        # Handle any exceptions that occurred
        processed_results = []
        success_count = 0
        error_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception in batch processing for {urls[i]}: {result}")
                processed_results.append(ResolveResponse(
                    url=urls[i],
                    status="error",
                    message=str(result),
                    processing_time=0
                ))
                error_count += 1
            else:
                processed_results.append(result)
                if result.status == "success":
                    success_count += 1
                else:
                    error_count += 1
        
        total_time = time.time() - start_time
        logger.info(f"Batch processing completed in {total_time:.2f}s - Success: {success_count}, Errors: {error_count}")
        
        return BatchResponse(
            count=len(processed_results),
            results=processed_results,
            total_processing_time=total_time,
            success_count=success_count,
            error_count=error_count
        )
        
    except Exception as exc:
        logger.exception("Batch processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(exc)}"
        )

@app.get("/supported-domains")
async def supported_domains():
    """Get list of supported domains with caching"""
    try:
        if TRUELINK_AVAILABLE:
            domains = TrueLinkResolver.get_supported_domains()
        else:
            domains = FallbackResolver.get_supported_domains()
            
        sorted_domains = sorted(domains)
        
        logger.debug(f"Retrieved {len(sorted_domains)} supported domains")
        
        return {
            "count": len(sorted_domains),
            "domains": sorted_domains,
            "last_updated": time.time(),
            "truelink_available": TRUELINK_AVAILABLE
        }
    except Exception as exc:
        logger.exception("Error retrieving supported domains")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve supported domains: {str(exc)}"
        )

@app.get("/direct", response_model=DirectLinksResponse)
async def get_direct(
    url: HttpUrl = Query(...),
    timeout: int = Query(Config.DEFAULT_TIMEOUT, ge=1, le=Config.MAX_TIMEOUT),
    retries: int = Query(3, ge=0, le=10),
    cache: bool = Query(True)
):
    """Extract direct download links from a URL"""
    start_time = time.time()
    result = await resolve_single(str(url), timeout=timeout, retries=retries, use_cache=cache)
    
    if result.status != "success":
        if result.status == "unsupported":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
        elif result.status == "timeout":
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=result.message)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.message)
    
    direct_links = extract_direct_links(result.data or {})
    processing_time = time.time() - start_time
    
    return DirectLinksResponse(
        url=str(url),
        direct_links=direct_links,
        count=len(direct_links),
        processing_time=processing_time
    )

@app.get("/redirect")
async def redirect_to_direct(
    url: HttpUrl = Query(...),
    timeout: int = Query(Config.DEFAULT_TIMEOUT, ge=1, le=Config.MAX_TIMEOUT),
    retries: int = Query(3, ge=0, le=10),
    cache: bool = Query(True)
):
    """Redirect to the first available direct download link"""
    result = await resolve_single(str(url), timeout=timeout, retries=retries, use_cache=cache)
    
    if result.status != "success":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message or "Failed to resolve URL"
        )
    
    direct_links = extract_direct_links(result.data or {})
    
    if not direct_links:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No direct download links found"
        )
    
    logger.info(f"Redirecting to: {direct_links[0]}")
    return RedirectResponse(url=direct_links[0], status_code=status.HTTP_302_FOUND)

@app.get("/download-stream")
async def download_stream(
    url: HttpUrl = Query(...),
    timeout: int = Query(60, ge=1, le=Config.MAX_TIMEOUT),
    retries: int = Query(3, ge=0, le=10),
    cache: bool = Query(True)
):
    """Stream content from resolved direct download link with improved error handling"""
    result = await resolve_single(str(url), timeout=timeout, retries=retries, use_cache=cache)
    direct_links = extract_direct_links(result.data or {})
    
    if not direct_links:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No direct download links found"
        )

    target_url = direct_links[0]
    logger.info(f"Starting stream download from: {target_url}")

    # Create session with proper configuration
    connector = aiohttp.TCPConnector(
        limit=100, 
        limit_per_host=30,
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
    
    session_timeout = aiohttp.ClientTimeout(
        total=None,
        sock_connect=timeout,
        sock_read=timeout
    )
    
    session = None
    response = None
    
    try:
        session = aiohttp.ClientSession(
            timeout=session_timeout,
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        response = await session.get(target_url)
        
        if response.status != 200:
            raise HTTPException(
                status_code=response.status,
                detail=f"Upstream server returned status {response.status}"
            )

        # Prepare response headers
        headers = {}
        content_type = response.headers.get("Content-Type")
        if content_type:
            headers["Content-Type"] = content_type
            
        content_length = response.headers.get("Content-Length")
        if content_length:
            headers["Content-Length"] = content_length
            
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition:
            headers["Content-Disposition"] = content_disposition

        async def stream_generator():
            try:
                async for chunk in response.content.iter_chunked(Config.CHUNK_SIZE):
                    yield chunk
            except asyncio.CancelledError:
                logger.warning(f"Client disconnected during stream: {target_url}")
                raise
            except Exception as exc:
                logger.error(f"Streaming error for {target_url}: {exc}")
                raise
            finally:
                # Cleanup resources
                try:
                    if response and not response.closed:
                        response.close()
                except Exception as cleanup_exc:
                    logger.error(f"Error closing response: {cleanup_exc}")
                
                try:
                    if session and not session.closed:
                        await session.close()
                except Exception as cleanup_exc:
                    logger.error(f"Error closing session: {cleanup_exc}")

        return StreamingResponse(
            stream_generator(),
            headers=headers,
            media_type=content_type or "application/octet-stream"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions after cleanup
        await cleanup_resources(response, session)
        raise
    except Exception as exc:
        logger.exception(f"Error in download_stream: {exc}")
        await cleanup_resources(response, session)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming failed: {str(exc)}"
        )

async def cleanup_resources(response, session):
    """Helper function to cleanup HTTP resources"""
    try:
        if response and not response.closed:
            response.close()
    except Exception as e:
        logger.error(f"Error closing response: {e}")
    
    try:
        if session and not session.closed:
            await session.close()
    except Exception as e:
        logger.error(f"Error closing session: {e}")

@app.get("/terabox", response_model=TeraboxResponse)
async def terabox_endpoint(
    url: HttpUrl = Query(..., description="Terabox share link"),
    ndus: str = Query(..., description="NDUS cookie value")
):
    """Resolve Terabox link to a direct download link using fallback APIs"""
    start_time = time.time()
    
    if not ndus or len(ndus.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NDUS cookie value is required"
        )

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    apis = [
        f"https://nord.teraboxfast.com/?ndus={quote(ndus)}&url={quote(str(url))}",
        f"https://teradl1.tellycloudapi.workers.dev/api/api1?url={quote(str(url))}",
    ]

    logger.info(f"Processing Terabox URL: {url}")

    with Session() as session:
        session.headers.update({"User-Agent": user_agent})
        
        for i, api_url in enumerate(apis, 1):
            try:
                logger.debug(f"Trying API {i}: {api_url}")
                response = session.get(api_url, timeout=15)
                response.raise_for_status()
                req = response.json()
                
                # Case 1: Direct link from first API
                if all(key in req for key in ["file_name", "sizebytes", "thumb", "link", "direct_link"]):
                    logger.info(f"Successfully resolved Terabox URL using API {i}")
                    return TeraboxResponse(
                        status="success",
                        file_name=req["file_name"],
                        thumb=req["thumb"],
                        link=req["link"],
                        direct_link=req["direct_link"],
                        sizebytes=req["sizebytes"]
                    )

                # Case 2: Fallback API format
                if req.get("success") and "metadata" in req and "links" in req:
                    metadata = req["metadata"]
                    links = req["links"]
                    dl1 = links.get("dl1")
                    dl2 = links.get("dl2")
                    
                    if dl1 or dl2:
                        logger.info(f"Successfully resolved Terabox URL using API {i} (fallback format)")
                        return TeraboxResponse(
                            status="success",
                            file_name=metadata.get("file_name"),
                            thumb=metadata.get("thumb"),
                            size=metadata.get("size"),
                            sizebytes=metadata.get("sizebytes"),
                            dl1=dl1,
                            dl2=dl2
                        )
                        
            except requests.exceptions.RequestException as e:
                logger.warning(f"API {i} request failed: {e}")
                continue
            except (ValueError, KeyError) as e:
                logger.warning(f"API {i} response parsing failed: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error with API {i}: {e}")
                continue

    # If nothing worked
    processing_time = time.time() - start_time
    logger.warning(f"All Terabox APIs failed for URL: {url}")
    
    return TeraboxResponse(
        status="error",
        message="File not found or all API requests failed. Please check the URL and NDUS cookie."
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        log_level=Config.LOG_LEVEL.lower(),
        access_log=True,
        reload=False  # Disable reload in production
    )
