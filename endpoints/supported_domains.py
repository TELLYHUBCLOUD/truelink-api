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

try:
    from utils import FallbackResolver
except ImportError:
    FallbackResolver = None

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache to avoid re-fetching repeatedly
_domains_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 60  # seconds

@router.get("/supported-domains")
async def supported_domains():
    """Get list of supported domains with caching"""
    try:
        # Use cache if fresh
        if _domains_cache["data"] and time.time() - _domains_cache["timestamp"] < CACHE_TTL:
            return _domains_cache["data"]

        if TRUELINK_AVAILABLE and TrueLinkResolver:
            domains = TrueLinkResolver.get_supported_domains()
        elif FallbackResolver:
            domains = FallbackResolver.get_supported_domains()
        else:
            raise RuntimeError("No resolver available")

        sorted_domains = sorted(set(domains))

        result = {
            "count": len(sorted_domains),
            "domains": sorted_domains,
            "last_updated": time.time(),
            "truelink_available": bool(TRUELINK_AVAILABLE and TrueLinkResolver)
        }

        _domains_cache["data"] = result
        _domains_cache["timestamp"] = time.time()

        logger.debug(f"Retrieved {len(sorted_domains)} supported domains")
        return result

    except Exception as exc:
        logger.exception("Error retrieving supported domains")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve supported domains: {str(exc)}"
        )
