import os
import asyncio
import logging
from typing import Any, Optional, Dict, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Body, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, HttpUrl, Field, validator
import aiohttp
from truelink import TrueLinkResolver
import time
import json
from urllib.parse import quote
from requests import Session

# ---------- Configuration ----------
class Config:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "50"))
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "20"))
    MAX_TIMEOUT = int(os.getenv("MAX_TIMEOUT", "120"))
    CONCURRENT_LIMIT = int(os.getenv("CONCURRENT_LIMIT", "8"))
    ENABLE_CORS = os.getenv("ENABLE_CORS", "true").lower() == "true"
    TRUSTED_HOSTS = os.getenv("TRUSTED_HOSTS", "*").split(",")

# ---------- Logging Setup ----------
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
)
logger = logging.getLogger("truelink-api")

# ---------- Pydantic Models ----------
class BatchRequest(BaseModel):
    urls: List[HttpUrl] = Field(..., min_items=1, max_items=Config.MAX_BATCH_SIZE)
    
    @validator('urls')
    def validate_urls(cls, v):
        if len(v) > Config.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {Config.MAX_BATCH_SIZE} URLs allowed")
        return v

class ResolveResponse(BaseModel):
    url: str
    status: str
    type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    processing_time: Optional[float] = None

class BatchResponse(BaseModel):
    count: int
    results: List[ResolveResponse]
    total_processing_time: float

class DirectLinksResponse(BaseModel):
    url: str
    direct_links: List[str]
    count: int
    processing_time: float

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: float
    supported_domains_count: int

# ---------- Global Variables ----------
app_start_time = time.time()
resolver_instance = None

# ---------- Lifespan Management ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global resolver_instance
    logger.info("Starting TrueLink API...")
    
    # Initialize resolver
    resolver_instance = TrueLinkResolver(
        timeout=Config.DEFAULT_TIMEOUT,
        max_retries=3
    )
    
    logger.info("TrueLink API started successfully")
    yield
    
    logger.info("Shutting down TrueLink API...")
    # Cleanup if needed
    resolver_instance = None

# ---------- FastAPI App ----------
app = FastAPI(
    title="Advanced TrueLink API",
    version="3.0",
    description="High-performance API for resolving URLs to direct download links",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ---------- Middleware ----------
if Config.ENABLE_CORS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=Config.TRUSTED_HOSTS
)

# ---------- Exception Handlers ----------
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"ValueError: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": "Invalid input", "message": str(exc)}
    )

@app.exception_handler(asyncio.TimeoutError)
async def timeout_error_handler(request: Request, exc: asyncio.TimeoutError):
    logger.warning(f"Timeout error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        content={"error": "Request timeout", "message": "The request took too long to process"}
    )

# ---------- Utility Functions ----------
def to_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format with better error handling."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(item) for item in obj]
    if hasattr(obj, "dict"):
        try:
            return to_serializable(obj.dict())
        except Exception as e:
            logger.debug(f"Serialization error on dict(): {e}")
            return str(obj)
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {
            k: to_serializable(v) 
            for k, v in obj.__dict__.items() 
            if not k.startswith("_")
        }
    try:
        return json.loads(json.dumps(obj, default=str))
    except (TypeError, ValueError):
        return str(obj)

def validate_timeout(timeout: int) -> int:
    """Validate and clamp timeout value."""
    if timeout < 1:
        return 1
    if timeout > Config.MAX_TIMEOUT:
        return Config.MAX_TIMEOUT
    return timeout

def validate_retries(retries: int) -> int:
    """Validate and clamp retries value."""
    return max(0, min(retries, 10))

async def resolve_single(
    url: str, 
    timeout: int = Config.DEFAULT_TIMEOUT, 
    retries: int = 3, 
    use_cache: bool = True
) -> ResolveResponse:
    """Resolve a single URL with comprehensive error handling and timing."""
    start_time = time.time()
    timeout = validate_timeout(timeout)
    retries = validate_retries(retries)
    
    logger.debug(f"Resolving URL: {url} | Timeout: {timeout}s | Retries: {retries} | Cache: {use_cache}")
    
    try:
        resolver = TrueLinkResolver(timeout=timeout, max_retries=retries)
        
        if not resolver.is_supported(url):
            logger.warning(f"Unsupported URL: {url}")
            return ResolveResponse(
                url=url,
                status="unsupported",
                message="URL domain is not supported",
                processing_time=time.time() - start_time
            )

        result = await resolver.resolve(url, use_cache=use_cache)
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

def extract_direct_links(resolved_data: Dict[str, Any]) -> List[str]:
    """Extract direct download links from resolved data with improved logic."""
    links = []
    possible_fields = [
        "direct_links", "files", "items", "url", "download_url", 
        "direct_url", "links", "file_url", "download_link"
    ]

    def is_valid_url(url_str: str) -> bool:
        """Check if string is a valid HTTP/HTTPS URL."""
        return isinstance(url_str, str) and url_str.startswith(("http://", "https://"))

    def walk(obj, depth=0):
        """Recursively walk through data structure to find URLs."""
        if depth > 10:  # Prevent infinite recursion
            return
        
        if not obj:
            return
            
        if is_valid_url(obj):
            if obj not in links:  # Avoid duplicates
                links.append(obj)
            return
            
        if isinstance(obj, dict):
            # Prioritize known fields
            for field in possible_fields:
                if field in obj and obj[field]:
                    walk(obj[field], depth + 1)
            
            # Walk through other fields
            for k, v in obj.items():
                if k not in possible_fields:
                    walk(v, depth + 1)
                    
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                walk(item, depth + 1)

    data = resolved_data.get("data", resolved_data)
    walk(data)
    
    logger.debug(f"Extracted {len(links)} direct links")
    return links

# ---------- API Endpoints ----------
@app.get("/health", response_model=HealthResponse)
async def health():
    """Enhanced health check with system information."""
    try:
        uptime = time.time() - app_start_time
        domains = TrueLinkResolver.get_supported_domains()
        
        return HealthResponse(
            status="healthy",
            version="3.0",
            uptime=uptime,
            supported_domains_count=len(domains)
        )
    except Exception as exc:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(exc)}"
        )

@app.get("/help")
async def help_page():
    """Comprehensive API documentation."""
    return {
        "api": "Advanced TrueLink API v3.0",
        "description": "High-performance API for resolving URLs to direct download links",
        "features": [
            "Single and batch URL resolution",
            "Direct link extraction",
            "Streaming downloads",
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
            "/help": "Show this comprehensive help page",
            "/docs": "Interactive API documentation (Swagger UI)",
            "/redoc": "Alternative API documentation (ReDoc)"
        },
        "limits": {
            "max_batch_size": Config.MAX_BATCH_SIZE,
            "max_timeout": Config.MAX_TIMEOUT,
            "concurrent_limit": Config.CONCURRENT_LIMIT
        }
    }

@app.get("/resolve", response_model=ResolveResponse)
async def resolve_url(
    url: HttpUrl = Query(..., description="URL to resolve"),
    timeout: int = Query(Config.DEFAULT_TIMEOUT, ge=1, le=Config.MAX_TIMEOUT, description="Request timeout in seconds"),
    retries: int = Query(3, ge=0, le=10, description="Number of retry attempts"),
    cache: bool = Query(True, description="Enable/disable caching")
):
    """Resolve a single URL with comprehensive validation and error handling."""
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
    """Resolve multiple URLs concurrently with rate limiting."""
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
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception in batch processing for {urls[i]}: {result}")
                processed_results.append(ResolveResponse(
                    url=urls[i],
                    status="error",
                    message=str(result),
                    processing_time=0
                ))
            else:
                processed_results.append(result)
        
        total_time = time.time() - start_time
        logger.info(f"Batch processing completed in {total_time:.2f}s")
        
        return BatchResponse(
            count=len(processed_results),
            results=processed_results,
            total_processing_time=total_time
        )
        
    except Exception as exc:
        logger.exception("Batch processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(exc)}"
        )

@app.get("/supported-domains")
async def supported_domains():
    """Get list of supported domains with caching."""
    try:
        domains = TrueLinkResolver.get_supported_domains()
        sorted_domains = sorted(domains)
        
        logger.debug(f"Retrieved {len(sorted_domains)} supported domains")
        
        return {
            "count": len(sorted_domains),
            "domains": sorted_domains,
            "last_updated": time.time()
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
    """Extract direct download links from a URL."""
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
    """Redirect to the first available direct download link."""
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
    """Stream content from resolved direct download link."""
    result = await resolve_single(str(url), timeout=timeout, retries=retries, use_cache=cache)
    direct_links = extract_direct_links(result.data or {})
    
    if not direct_links:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No direct download links found"
        )

    target_url = direct_links[0]
    logger.info(f"Starting stream download from: {target_url}")

    connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
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
            connector=connector
        )
        
        response = await session.get(target_url)
        
        if response.status != 200:
            await response.release()
            await session.close()
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
                chunk_size = 64 * 1024  # 64KB chunks
                async for chunk in response.content.iter_chunked(chunk_size):
                    yield chunk
            except asyncio.CancelledError:
                logger.warning(f"Client disconnected during stream: {target_url}")
                raise
            except Exception as exc:
                logger.error(f"Streaming error for {target_url}: {exc}")
                raise
            finally:
                try:
                    if response and not response.closed:
                        await response.release()
                except Exception as cleanup_exc:
                    logger.error(f"Error releasing response: {cleanup_exc}")
                finally:
                    try:
                        if session and not session.closed:
                            await session.close()
                    except Exception as cleanup_exc:
                        logger.error(f"Error closing session: {cleanup_exc}")

        return StreamingResponse(
            stream_generator(),
            headers=headers,
            media_type=content_type
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        if response and not response.closed:
            await response.release()
        if session and not session.closed:
            await session.close()
        raise
    except Exception as exc:
        logger.exception(f"Error in download_stream: {exc}")
        
        # Cleanup resources
        try:
            if response and not response.closed:
                await response.release()
        except Exception:
            pass
        try:
            if session and not session.closed:
                await session.close()
        except Exception:
            pass
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming failed: {str(exc)}"
        )


@app.get("/terabox")
async def terabox_endpoint(
    url: HttpUrl = Query(..., description="Terabox share link"),
    ndus: str = Query(..., description="NDUS cookie value")
):
    """
    Resolve Terabox link to a direct download link using fallback APIs.
    """


    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    apis = [
        f"https://nord.teraboxfast.com/?ndus={quote(ndus)}&url={quote(str(url))}",
        f"https://teradl1.tellycloudapi.workers.dev/api/api1?url={quote(str(url))}",
    ]

    with Session() as session:
        for api_url in apis:
            try:
                req = session.get(
                    api_url, headers={"User-Agent": user_agent}, timeout=15
                ).json()
            except Exception:
                continue  # Try next API

            # Case 1: Direct link from first API
            if (
                "file_name" in req
                and "sizebytes" in req
                and "thumb" in req
                and "link" in req
                and "direct_link" in req
            ):
                return {
                    "status": "success",
                    "file_name": req["file_name"],
                    "thumb": req["thumb"],
                    "link": req["link"],
                    "direct_link": req["direct_link"],
                    "sizebytes": req["sizebytes"],
                }

            # Case 2: Fallback API format
            if req.get("success") and "metadata" in req and "links" in req:
                dl2 = req["links"].get("dl2")
                dl1 = req["links"].get("dl1")
                if dl1 or dl2:
                    return {
                        "status": "success",
                        "file_name": req["metadata"].get("file_name"),
                        "thumb": req["metadata"].get("thumb"),
                        "size": req["metadata"].get("size"),
                        "sizebytes": req["metadata"].get("sizebytes"),
                        "dl1": dl1,
                        "dl2": dl2,
                    }

    # If nothing worked
    return {
        "status": "error",
        "message": "File not found or all API requests failed."
    }

# ---------- Root Endpoint ----------
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Advanced TrueLink API v3.0",
        "documentation": "/docs",
        "help": "/help",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        log_level=Config.LOG_LEVEL.lower(),
        access_log=True
    )
