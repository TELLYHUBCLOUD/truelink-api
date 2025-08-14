"""
File Upload and Social Media Download API
FastAPI-based server with file upload and social media content download capabilities
"""
import os
import time
import logging
import aiohttp
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, File, UploadFile, HTTPException, status, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="File Upload & Social Media Download API",
    version="1.0.0",
    description="API for file uploads and social media content downloads"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Constants
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
SOCIAL_API_BASE = "https://tele-social.vercel.app"
SUPPORTED_SERVICES = [
    "Bilibili", "Bluesky", "Dailymotion", "Facebook", "Instagram", "Loom",
    "Ok", "Pinterest", "Reddit", "Rutube", "Snapchat", "Soundcloud",
    "Streamable", "Tiktok", "Tumblr", "Twitch", "Twitter", "Vimeo",
    "Vk", "Youtube", "Spotify"
]

# Pydantic models
class UploadResponse(BaseModel):
    success: bool
    url: str
    filename: str
    size: int
    upload_time: float

class SocialDownloadResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    processing_time: float
    service: Optional[str] = None

class ServicesResponse(BaseModel):
    services: List[str]
    count: int

def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename with timestamp"""
    # Replace spaces with underscores and add timestamp
    clean_name = original_filename.replace(" ", "_")
    timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
    name, ext = os.path.splitext(clean_name)
    return f"{timestamp}-{name}{ext}"

def validate_file_size(file_size: int) -> bool:
    """Validate file size against limit"""
    return file_size <= MAX_FILE_SIZE

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "File Upload & Social Media Download API",
        "endpoints": {
            "/upload": "POST - Upload files (max 20MB)",
            "/download": "GET - Download social media content",
            "/services": "GET - List supported social media platforms",
            "/uploads/{filename}": "GET - Access uploaded files"
        },
        "max_file_size": "20MB",
        "supported_services": len(SUPPORTED_SERVICES)
    }

@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file with size validation and unique naming
    Maximum file size: 20MB
    """
    start_time = time.time()
    
    try:
        # Read file content to check size
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if not validate_file_size(file_size):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)"
            )
        
        # Generate unique filename
        unique_filename = generate_unique_filename(file.filename)
        file_path = UPLOAD_DIR / unique_filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Generate file URL (you might want to use request.url.hostname in production)
        file_url = f"http://localhost:3000/uploads/{unique_filename}"
        
        processing_time = time.time() - start_time
        
        logger.info(f"File uploaded successfully: {unique_filename} ({file_size} bytes)")
        
        return UploadResponse(
            success=True,
            url=file_url,
            filename=unique_filename,
            size=file_size,
            upload_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@app.get("/services", response_model=ServicesResponse)
async def get_supported_services():
    """Get list of supported social media platforms"""
    return ServicesResponse(
        services=SUPPORTED_SERVICES,
        count=len(SUPPORTED_SERVICES)
    )

@app.get("/download", response_model=SocialDownloadResponse)
async def download_social_media(
    url: HttpUrl = Query(..., description="Social media URL to download"),
    timeout: int = Query(30, ge=5, le=120, description="Request timeout in seconds")
):
    """
    Download content from supported social media platforms
    
    Supported platforms: Bilibili, Bluesky, Dailymotion, Facebook, Instagram, 
    Loom, Ok, Pinterest, Reddit, Rutube, Snapchat, Soundcloud, Streamable, 
    Tiktok, Tumblr, Twitch, Twitter, Vimeo, Vk, Youtube, Spotify
    """
    start_time = time.time()
    url_str = str(url)
    
    # Detect service from URL
    detected_service = detect_service_from_url(url_str)
    
    logger.info(f"Processing social media download: {url_str} (detected: {detected_service})")
    
    try:
        # Make request to social media API
        api_url = f"{SOCIAL_API_BASE}/down"
        
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            params = {"url": url_str}
            
            async with session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    processing_time = time.time() - start_time
                    
                    logger.info(f"Social media download successful for {url_str}")
                    
                    return SocialDownloadResponse(
                        success=True,
                        data=data,
                        processing_time=processing_time,
                        service=detected_service
                    )
                else:
                    error_text = await response.text()
                    logger.warning(f"Social API returned {response.status}: {error_text}")
                    
                    processing_time = time.time() - start_time
                    return SocialDownloadResponse(
                        success=False,
                        message=f"API returned status {response.status}: {error_text}",
                        processing_time=processing_time,
                        service=detected_service
                    )
                    
    except asyncio.TimeoutError:
        processing_time = time.time() - start_time
        logger.warning(f"Timeout downloading from {url_str}")
        return SocialDownloadResponse(
            success=False,
            message=f"Request timed out after {timeout} seconds",
            processing_time=processing_time,
            service=detected_service
        )
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error downloading from {url_str}: {e}")
        return SocialDownloadResponse(
            success=False,
            message=f"Download failed: {str(e)}",
            processing_time=processing_time,
            service=detected_service
        )

def detect_service_from_url(url: str) -> Optional[str]:
    """Detect social media service from URL"""
    url_lower = url.lower()
    
    service_patterns = {
        "youtube": ["youtube.com", "youtu.be"],
        "tiktok": ["tiktok.com"],
        "instagram": ["instagram.com"],
        "twitter": ["twitter.com", "x.com"],
        "facebook": ["facebook.com", "fb.com"],
        "reddit": ["reddit.com"],
        "vimeo": ["vimeo.com"],
        "dailymotion": ["dailymotion.com"],
        "soundcloud": ["soundcloud.com"],
        "spotify": ["spotify.com"],
        "twitch": ["twitch.tv"],
        "pinterest": ["pinterest.com"],
        "tumblr": ["tumblr.com"],
        "snapchat": ["snapchat.com"],
        "bilibili": ["bilibili.com"],
        "ok": ["ok.ru"],
        "vk": ["vk.com"],
        "rutube": ["rutube.ru"],
        "loom": ["loom.com"],
        "streamable": ["streamable.com"],
        "bluesky": ["bsky.app"]
    }
    
    for service, patterns in service_patterns.items():
        if any(pattern in url_lower for pattern in patterns):
            return service.title()
    
    return "Unknown"

@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    """Serve uploaded files"""
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileResponse(file_path)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "upload_dir": str(UPLOAD_DIR),
        "max_file_size": MAX_FILE_SIZE,
        "supported_services": len(SUPPORTED_SERVICES)
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(
        "file_upload:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )