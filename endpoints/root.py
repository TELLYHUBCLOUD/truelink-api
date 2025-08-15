"""
Root endpoint
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Advanced TrueLink API v3.3",
        "documentation": "/docs",
        "help": "/help",
        "health": "/health",
        "features": [
            "Single and batch URL resolution",
            "Direct link extraction", 
            "Streaming downloads",
            "Terabox support",
            "JioSaavn music API integration",
            "Comprehensive error handling"
        ]
    }