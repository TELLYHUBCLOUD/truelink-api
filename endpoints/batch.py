"""
Batch URL resolution endpoint
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
    """Resolve multiple URLs concurrently with rate limiting"""
    start_time = time.time()
    urls = [str(url) for url in payload.urls]
    
    logger.info(f"Batch resolve request for {len(urls)} URLs")
    
    # Use semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(Config.CONCURRENT_LIMIT)

    async def semaphore_task(url: str):
        async with semaphore:
            return await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)

    try:
        results = await asyncio.gather(
            *[semaphore_task(url) for url in urls],
            return_exceptions=True
        )
        
        # Handle any exceptions that occurred
        processed_results = []
        success_count = 0
        error_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception in batch processing for {urls[i]}: {result}")
                processed_results.append(ResolveResponse(
                    url=urls[i],
                    status="error",
                    message=str(result),
                    processing_time=0
                ))
                error_count += 1
            else:
                processed_results.append(result)
                if result.status == "success":
                    success_count += 1
                else:
                    error_count += 1
        
        total_time = time.time() - start_time
        logger.info(f"Batch processing completed in {total_time:.2f}s - Success: {success_count}, Errors: {error_count}")
        
        return BatchResponse(
            count=len(processed_results),
            results=processed_results,
            total_processing_time=total_time,
            success_count=success_count,
            error_count=error_count
        )
        
    except Exception as exc:
        logger.exception("Batch processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch processing failed: {str(exc)}"
        )