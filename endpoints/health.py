"""
Health check endpoint
"""
import time
import logging
from fastapi import APIRouter, HTTPException, status

from models import HealthResponse
from utils import get_memory_usage, get_system_info
from config import TRUELINK_AVAILABLE, app_start_time

try:
    from truelink import TrueLinkResolver
except ImportError:
    TrueLinkResolver = None

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health():
    """Enhanced health check with system information"""
    try:
        uptime = time.time() - app_start_time
        
        # Get supported domains count
        domains_count = 0
        try:
            if TRUELINK_AVAILABLE and TrueLinkResolver:
                domains = TrueLinkResolver.get_supported_domains()
                domains_count = len(domains)
            else:
                from utils import FallbackResolver
                domains_count = len(FallbackResolver.get_supported_domains())
        except Exception as e:
            logger.warning(f"Could not get supported domains: {e}")
        
        return HealthResponse(
            status="healthy",
            version="3.3",
            uptime=uptime,
            supported_domains_count=domains_count,
            memory_usage=get_memory_usage(),
            system_info=get_system_info()
        )
    except Exception as exc:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(exc)}"
        )