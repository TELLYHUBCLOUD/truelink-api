"""
Redirect to direct link endpoint
"""
import logging
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import HttpUrl

from config import Config
from utils import resolve_single, extract_direct_links

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/redirect")
async def redirect_to_direct(
    url: HttpUrl = Query(...),
    timeout: int = Query(Config.DEFAULT_TIMEOUT, ge=1, le=Config.MAX_TIMEOUT),
    retries: int = Query(3, ge=0, le=10),
    cache: bool = Query(True)
):
    """Redirect to the first available direct download link"""
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