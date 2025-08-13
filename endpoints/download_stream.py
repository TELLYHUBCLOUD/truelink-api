"""
Download streaming endpoint
"""
import logging
import asyncio
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import HttpUrl
import aiohttp

from config import Config
from utils import resolve_single, extract_direct_links, cleanup_resources

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/download-stream")
async def download_stream(
    url: HttpUrl = Query(...),
    timeout: int = Query(60, ge=1, le=Config.MAX_TIMEOUT),
    retries: int = Query(3, ge=0, le=10),
    cache: bool = Query(True)
):
    """Stream content from resolved direct download link with improved error handling"""
    result = await resolve_single(str(url), timeout=timeout, retries=retries, use_cache=cache)
    direct_links = extract_direct_links(result.data or {})
    
    if not direct_links:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No direct download links found"
        )

    target_url = direct_links[0]
    logger.info(f"Starting stream download from: {target_url}")

    # Create session with proper configuration
    connector = aiohttp.TCPConnector(
        limit=100, 
        limit_per_host=30,
        keepalive_timeout=30,
        enable_cleanup_closed=True
    )
    
    session_timeout = aiohttp.ClientTimeout(
        total=None,
        sock_connect=timeout,
        sock_read=timeout
    )
    
    session = None
    response = None
    
    try:
        session = aiohttp.ClientSession(
            timeout=session_timeout,
            connector=connector,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        response = await session.get(target_url)
        
        if response.status != 200:
            raise HTTPException(
                status_code=response.status,
                detail=f"Upstream server returned status {response.status}"
            )

        # Prepare response headers
        headers = {}
        content_type = response.headers.get("Content-Type")
        if content_type:
            headers["Content-Type"] = content_type
            
        content_length = response.headers.get("Content-Length")
        if content_length:
            headers["Content-Length"] = content_length
            
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition:
            headers["Content-Disposition"] = content_disposition

        async def stream_generator():
            try:
                async for chunk in response.content.iter_chunked(Config.CHUNK_SIZE):
                    yield chunk
            except asyncio.CancelledError:
                logger.warning(f"Client disconnected during stream: {target_url}")
                raise
            except Exception as exc:
                logger.error(f"Streaming error for {target_url}: {exc}")
                raise
            finally:
                # Cleanup resources
                await cleanup_resources(response, session)

        return StreamingResponse(
            stream_generator(),
            headers=headers,
            media_type=content_type or "application/octet-stream"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions after cleanup
        await cleanup_resources(response, session)
        raise
    except Exception as exc:
        logger.exception(f"Error in download_stream: {exc}")
        await cleanup_resources(response, session)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming failed: {str(exc)}"
        )