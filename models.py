"""
Pydantic models for TrueLink API
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, HttpUrl, Field, validator
from config import Settings

class BatchRequest(BaseModel):
    """Request model for batch URL resolution."""
    urls: List[HttpUrl] = Field(
        ..., 
        min_items=1, 
        max_items=Settings.MAX_BATCH_SIZE,
        description=f"List of URLs to resolve (max {Settings.MAX_BATCH_SIZE})"
    )
    
    @validator('urls')
    def validate_urls(cls, v):
        if len(v) > Settings.MAX_BATCH_SIZE:
            raise ValueError(f"Maximum {Settings.MAX_BATCH_SIZE} URLs allowed")
        return v

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
    success_count: Optional[int] = Field(None, description="Number of successful resolutions")
    error_count: Optional[int] = Field(None, description="Number of failed resolutions")

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

class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: Optional[float] = Field(None, description="Error timestamp")

class SupportedDomainsResponse(BaseModel):
    """Response model for supported domains."""
    count: int = Field(..., description="Number of supported domains")
    domains: List[str] = Field(..., description="List of supported domains")
    last_updated: float = Field(..., description="Last update timestamp")
    categories: Optional[Dict[str, List[str]]] = Field(None, description="Domains grouped by category")