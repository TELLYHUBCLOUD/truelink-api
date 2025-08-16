"""
Redirect to direct link endpoint (debug-friendly)
"""
import logging
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import RedirectResponse

from config import Config
from utils import resolve_single, extract_direct_links

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/redirect")
async def redirect_to_direct(
    url: str = Query(..., description="URL to resolve and redirect"),
    timeout: int = Query(Config.DEFAULT_TIMEOUT, ge=1, le=Config.MAX_TIMEOUT, description="Request timeout in seconds"),
    retries: int = Query(3, ge=0, le=10, description="Number of retry attempts"),
    cache: bool = Query(True, description="Enable/disable caching")
):
    """
    Resolve the given URL and redirect to the first available direct link.
    This version:
    - Accepts any valid string URL (not just strict HttpUrl)
    - Adds full debug logging for traceability
    - Handles unexpected resolver returns safely
    """
    try:
        logger.debug(f"Starting redirect for: {url}")
        logger.debug(f"Params: timeout={timeout}, retries={retries}, cache={cache}")

        # Call the resolver
        result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
        logger.debug(f"Resolver returned: {result}")

        # Validate result object
        if not hasattr(result, "status"):
            raise RuntimeError(f"Unexpected resolver return type: {type(result)}")

        if result.status != "success":
            logger.warning(f"Resolver failed with status={result.status}, message={getattr(result, 'message', '')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=getattr(result, "message", "Failed to resolve URL")
            )

        # Extract direct links
        direct_links = extract_direct_links(getattr(result, "data", {}) or {})
        logger.debug(f"Extracted direct links: {direct_links}")

        if not direct_links:
            logger.warning(f"No direct links found for {url}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No direct download links found"
            )

        first_link = direct_links[0]
        logger.info(f"Redirecting to first direct link: {first_link}")

        return RedirectResponse(url=first_link, status_code=status.HTTP_302_FOUND)

    except HTTPException:
        raise  # Pass through known HTTP errors
    except Exception as exc:
        logger.exception("Unexpected error in redirect_to_direct")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Redirect failed: {str(exc)}"
        )
