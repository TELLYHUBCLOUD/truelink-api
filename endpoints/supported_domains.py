"""
Supported domains endpoint
"""
import time
import logging
from fastapi import APIRouter, HTTPException, status

from config import TRUELINK_AVAILABLE

try:
    from truelink import TrueLinkResolver
except ImportError:
    TrueLinkResolver = None

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/supported-domains")
async def supported_domains():
    """Get list of supported domains with caching"""
    try:
        if TRUELINK_AVAILABLE and TrueLinkResolver:
            domains = TrueLinkResolver.get_supported_domains()
        else:
            from utils import FallbackResolver
            domains = FallbackResolver.get_supported_domains()
            
        sorted_domains = sorted(domains)
        
        logger.debug(f"Retrieved {len(sorted_domains)} supported domains")
        
        return {
            "count": len(sorted_domains),
            "domains": sorted_domains,
            "last_updated": time.time(),
            "truelink_available": TRUELINK_AVAILABLE
        }
    except Exception as exc:
        logger.exception("Error retrieving supported domains")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve supported domains: {str(exc)}"
        )