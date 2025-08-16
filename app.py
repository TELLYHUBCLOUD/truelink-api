"""
Advanced TrueLink API v3.2 - Main Application
High-performance FastAPI-based HTTP API for URL resolution
"""
import os
import logging
import time
import traceback
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from config import Config, TRUELINK_AVAILABLE, app_start_time
from endpoints import (
    health_router,
    resolve_router,
    batch_router,
    direct_router,
    redirect_router,
    download_stream_router,
    supported_domains_router,
    terabox_router,
    root_router,
    help_router,
    jiosaavn_router,
    blackboxai_router,
    monkeybypass_router,
    poster_router,
    linkvertise_router,
    scrap_router,
    dllink_router
)

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

# ---------- Lifespan Management ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting TrueLink API...")
    logger.info(f"TrueLink available: {TRUELINK_AVAILABLE}")
    logger.info("TrueLink API started successfully")
    yield
    logger.info("Shutting down TrueLink API...")

# ---------- FastAPI App ----------
app = FastAPI(
    title="Advanced TrueLink API",
    version="3.3",
    description="High-performance API for resolving URLs to direct download links with JioSaavn music integration",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ---------- Middleware ----------
app.add_middleware(GZipMiddleware, minimum_size=1000)

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

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {str(e)} - {process_time:.3f}s")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

# ---------- Exception Handlers ----------
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"ValueError from {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Invalid input", 
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
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
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path),
            "request_id": str(id(request))
        }
    )

# ---------- Include Routers ----------
app.include_router(root_router, tags=["System info"])
app.include_router(health_router, tags=["System info"])
app.include_router(help_router, tags=["System info"])
app.include_router(supported_domains_router, tags=["Truelink library"])
app.include_router(direct_router, tags=["Truelink library"])
app.include_router(redirect_router, tags=["Truelink library"])
app.include_router(download_stream_router, tags=["Truelink library"])
app.include_router(resolve_router, tags=["Truelink library"])
app.include_router(batch_router, tags=["Truelink library"])
app.include_router(jiosaavn_router, tags=["JioSaavn API"])
app.include_router(blackboxai_router, tags=["BlackBox AI"])
app.include_router(monkeybypass_router, tags=["Tamper Monkey"])
app.include_router(terabox_router, tags=["Terabox API"])
app.include_router(poster_router, tags=["Poster Scrap"])
app.include_router(linkvertise_router, tags=["Link Bypass"])
app.include_router(scrap_router, tags=["Link Bypass"])
app.include_router(dllink_router, tags=["Link Bypass"])






if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        log_level=Config.LOG_LEVEL.lower(),
        access_log=True,
        reload=False
    )
