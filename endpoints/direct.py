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
    url: HttpUrl = Query(..., description="Source URL to extract direct download links from"),
    timeout: int = Query(Config.DEFAULT_TIMEOUT, ge=1, le=Config.MAX_TIMEOUT, description="Max time to wait for resolution"),
    retries: int = Query(3, ge=0, le=10, description="Number of retries on failure"),
    cache: bool = Query(True, description="Use cached result if available")
):
    """
    Extract direct download links from a given URL.
    Returns:
        - url: The original input URL
        - direct_links: List of extracted direct download links
        - count: Number of links found
        - processing_time: Time taken to process the request (seconds)
    """
    start_time = time.time()
    logger.info(f"[DIRECT] Resolving URL: {url} | timeout={timeout}s, retries={retries}, cache={cache}")

    try:
        # Resolve URL to structured data
        result = await resolve_single(str(url), timeout=timeout, retries=retries, use_cache=cache)

        if result.status != "success":
            logger.warning(f"[DIRECT] Resolution failed: status={result.status}, message={result.message}")
            status_map = {
                "unsupported": status.HTTP_400_BAD_REQUEST,
                "timeout": status.HTTP_408_REQUEST_TIMEOUT
            }
            raise HTTPException(
                status_code=status_map.get(result.status, status.HTTP_500_INTERNAL_SERVER_ERROR),
                detail=result.message or f"Failed to resolve URL (status: {result.status})"
            )

        # Extract links
        direct_links = extract_direct_links(result.data or {})
        processing_time = round(time.time() - start_time, 4)

        if not direct_links:
            logger.info(f"[DIRECT] No direct links found for URL: {url}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No direct download links found for the given URL"
            )

        logger.info(f"[DIRECT] Found {len(direct_links)} link(s) in {processing_time}s")
        return DirectLinksResponse(
            url=str(url),
            direct_links=direct_links,
            count=len(direct_links),
            processing_time=processing_time
        )

    except HTTPException:
        raise  # Re-throw for FastAPI to handle
    except Exception as e:
        logger.exception(f"[DIRECT] Unexpected error while processing URL {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
