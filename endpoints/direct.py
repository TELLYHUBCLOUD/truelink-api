"""
Direct links extraction endpoint
"""
import time
import logging
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import HttpUrl

from models import DirectLinksResponse
from config import Config
from utils import resolve_single, extract_direct_links

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/direct", response_model=DirectLinksResponse)
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