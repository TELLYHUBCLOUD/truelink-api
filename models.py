"""
Pydantic models for TrueLink API
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, HttpUrl, Field, validator
from config import Config

class BatchRequest(BaseModel):
    """Request model for batch URL resolution."""
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
        validated_urls = []
        for url in v:
            url_str = str(url)
            from utils import is_valid_url
            if not is_valid_url(url_str):
                raise ValueError(f"Invalid URL: {url_str}")
            validated_urls.append(url_str)
        return validated_urls

class ResolveResponse(BaseModel):
    """Response model for URL resolution."""
    url: str = Field(..., description="Original URL")
    status: str = Field(..., description="Resolution status")
    type: Optional[str] = Field(None, description="Type of resolved data")
    data: Optional[Dict[str, Any]] = Field(None, description="Resolved data")
    message: Optional[str] = Field(None, description="Status message or error details")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")

class BatchResponse(BaseModel):
    """Response model for batch URL resolution."""
    count: int = Field(..., description="Number of URLs processed")
    results: List[ResolveResponse] = Field(..., description="Resolution results")
    total_processing_time: float = Field(..., description="Total processing time in seconds")
    success_count: int = Field(..., description="Number of successful resolutions")
    error_count: int = Field(..., description="Number of failed resolutions")

class DirectLinksResponse(BaseModel):
    """Response model for direct links extraction."""
    url: str = Field(..., description="Original URL")
    direct_links: List[str] = Field(..., description="Extracted direct download links")
    count: int = Field(..., description="Number of direct links found")
    processing_time: float = Field(..., description="Processing time in seconds")

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    uptime: float = Field(..., description="Service uptime in seconds")
    supported_domains_count: int = Field(..., description="Number of supported domains")
    memory_usage: Optional[Dict[str, Any]] = Field(None, description="Memory usage statistics")
    system_info: Optional[Dict[str, Any]] = Field(None, description="System information")

class TeraboxResponse(BaseModel):
    """Response model for Terabox resolution."""
    status: str = Field(..., description="Response status")
    file_name: Optional[str] = Field(None, description="File name")
    thumb: Optional[str] = Field(None, description="Thumbnail URL")
    link: Optional[str] = Field(None, description="Original link")
    direct_link: Optional[str] = Field(None, description="Direct download link")
    sizebytes: Optional[int] = Field(None, description="File size in bytes")
    dl1: Optional[str] = Field(None, description="Download link 1")
    dl2: Optional[str] = Field(None, description="Download link 2")
    size: Optional[str] = Field(None, description="Human readable file size")
    message: Optional[str] = Field(None, description="Error message if any")