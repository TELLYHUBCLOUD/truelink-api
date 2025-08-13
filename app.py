"""
Advanced TrueLink API v3.1 - Main Application
High-performance FastAPI-based HTTP API for URL resolution
"""
import os
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

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
    jiosaavn_router
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
    version="3.1",
    description="High-performance API for resolving URLs to direct download links with modular architecture",
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

# ---------- Include Routers ----------
app.include_router(root_router, tags=["Root"])
app.include_router(health_router, tags=["Health"])
app.include_router(help_router, tags=["Help"])
app.include_router(resolve_router, tags=["Resolution"])
app.include_router(batch_router, tags=["Batch"])
app.include_router(direct_router, tags=["Direct Links"])
app.include_router(redirect_router, tags=["Redirect"])
app.include_router(download_stream_router, tags=["Streaming"])
app.include_router(supported_domains_router, tags=["Domains"])
app.include_router(terabox_router, tags=["Terabox"])
app.include_router(jiosaavn_router, tags=["JioSaavn"])

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