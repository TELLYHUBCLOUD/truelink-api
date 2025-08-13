"""
Single URL resolution endpoint
"""
import logging
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import HttpUrl

from models import ResolveResponse
from config import Config
from utils import resolve_single

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/resolve", response_model=ResolveResponse)
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