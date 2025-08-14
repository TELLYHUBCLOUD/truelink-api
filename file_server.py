"""
Python FastAPI File Upload Server
Equivalent to the Express.js file upload server
"""
import os
import time
import shutil
from pathlib import Path
from typing import Optional
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="File Upload Server",
    description="Python FastAPI equivalent of Express.js file upload server",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("uploads")
PUBLIC_DIR = Path("public")
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB in bytes

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
PUBLIC_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
if PUBLIC_DIR.exists():
    app.mount("/public", StaticFiles(directory="public"), name="public")

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by replacing spaces with underscores"""
    return filename.replace(" ", "_")

def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename with timestamp"""
    timestamp = int(time.time() * 1000)  # milliseconds like Date.now()
    sanitized_name = sanitize_filename(original_filename)
    return f"{timestamp}-{sanitized_name}"

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "File Upload Server",
        "endpoints": {
            "upload": "POST /upload - Upload a file",
            "files": "GET /uploads/{filename} - Access uploaded files"
        }
    }

@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Upload a single file
    Equivalent to the Express.js POST /upload endpoint
    """
    try:
        # Check file size
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Generate unique filename
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
        
        unique_filename = generate_unique_filename(file.filename)
        file_path = UPLOAD_DIR / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Generate file URL
        base_url = f"{request.url.scheme}://{request.headers.get('host', 'localhost')}"
        file_url = f"{base_url}/uploads/{unique_filename}"
        
        logger.info(f"File uploaded successfully: {unique_filename}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "url": file_url,
                "filename": unique_filename,
                "original_filename": file.filename,
                "size": file.size
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )

@app.get("/uploads/{filename}")
async def get_file(filename: str):
    """
    Serve uploaded files
    This is handled by StaticFiles middleware, but we can add custom logic here if needed
    """
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileResponse(file_path)

@app.get("/files")
async def list_files():
    """
    List all uploaded files (bonus endpoint)
    """
    try:
        files = []
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "url": f"/uploads/{file_path.name}"
                })
        
        return {
            "success": True,
            "count": len(files),
            "files": sorted(files, key=lambda x: x["created"], reverse=True)
        }
        
    except Exception as e:
        logger.error(f"List files error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )

@app.delete("/uploads/{filename}")
async def delete_file(filename: str):
    """
    Delete an uploaded file (bonus endpoint)
    """
    try:
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        file_path.unlink()
        logger.info(f"File deleted: {filename}")
        
        return {
            "success": True,
            "message": f"File {filename} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(
        "file_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )