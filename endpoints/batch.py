"""
Batch URL resolution endpoint (Improved)
"""
import time
import asyncio
import logging
from fastapi import APIRouter, Query, HTTPException, status

from models import BatchRequest, BatchResponse, ResolveResponse
from config import Config
from utils import resolve_single

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/resolve-batch", response_model=BatchResponse)
async def resolve_batch(
    payload: BatchRequest,
    timeout: int = Query(Config.DEFAULT_TIMEOUT, ge=1, le=Config.MAX_TIMEOUT),
    retries: int = Query(3, ge=0, le=10),
    cache: bool = Query(True)
):
    """
    Resolve multiple URLs concurrently with rate limiting & detailed logging.
    """
    start_time = time.time()
    urls = [str(url) for url in payload.urls]

    if not urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No URLs provided"
        )

    if len(urls) > Config.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many URLs. Maximum allowed: {Config.MAX_BATCH_SIZE}"
        )

    logger.info(f"Batch resolve started for {len(urls)} URLs")

    semaphore = asyncio.Semaphore(Config.CONCURRENT_LIMIT)

    async def resolve_with_semaphore(url: str) -> ResolveResponse:
        async with semaphore:
            url_start = time.time()
            try:
                result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
                result.processing_time = round(time.time() - url_start, 3)
                logger.debug(f"Resolved {url} in {result.processing_time}s - Status: {result.status}")
                return result
            except asyncio.CancelledError:
                logger.warning(f"Cancelled resolution for {url}")
                raise
            except Exception as e:
                logger.error(f"Error resolving {url}: {e}")
                return ResolveResponse(
                    url=url,
                    status="error",
                    message=str(e),
                    processing_time=round(time.time() - url_start, 3)
                )

    try:
        results = await asyncio.gather(
            *(resolve_with_semaphore(url) for url in urls),
            return_exceptions=False  # We handle errors inside the function
        )

        success_count = sum(1 for r in results if r.status == "success")
        error_count = len(results) - success_count
        total_time = round(time.time() - start_time, 3)

        logger.info(
            f"Batch processing completed in {total_time}s - "
            f"Success: {success_count}, Errors: {error_count}"
        )

        return BatchResponse(
            count=len(results),
            results=results,
            total_processing_time=total_time,
            success_count=success_count,
            error_count=error_count
        )

    except Exception as exc:
        logger.exception("Batch processing failed unexpectedly")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {exc}"
        )
