"""
Download streaming endpoint with debug logging
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
logger.setLevel(logging.DEBUG)  # Enable debug-level logs
router = APIRouter()

@router.get("/download-stream")
async def download_stream(
    url: HttpUrl = Query(...),
    timeout: int = Query(60, ge=1, le=Config.MAX_TIMEOUT),
    retries: int = Query(3, ge=0, le=10),
    cache: bool = Query(True)
):
    logger.debug(f"Received /download-stream request: url={url}, timeout={timeout}, retries={retries}, cache={cache}")

    try:
        logger.debug("Resolving direct link using resolve_single...")
        result = await resolve_single(str(url), timeout=timeout, retries=retries, use_cache=cache)
        logger.debug(f"Resolve result: {result}")

        logger.debug("Extracting direct download links...")
        direct_links = extract_direct_links(result.data or {})
        logger.debug(f"Extracted direct links: {direct_links}")

        if not direct_links:
            logger.error("No direct download links found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No direct download links found"
            )

        target_url = direct_links[0]
        logger.info(f"Selected direct link: {target_url}")

        logger.debug("Creating aiohttp session connector...")
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=10,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )

        logger.debug("Setting up aiohttp client timeout...")
        session_timeout = aiohttp.ClientTimeout(
            total=None,
            sock_connect=timeout,
            sock_read=timeout
        )

        session = None
        response = None

        try:
            logger.debug("Creating aiohttp ClientSession...")
            session = aiohttp.ClientSession(
                timeout=session_timeout,
                connector=connector,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )

            logger.debug(f"Sending GET request to target URL: {target_url}")
            response = await session.get(target_url)
            logger.debug(f"Received response: status={response.status}, headers={dict(response.headers)}")

            if response.status != 200:
                logger.error(f"Upstream server returned non-200 status: {response.status}")
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Upstream server returned status {response.status}"
                )

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

            logger.debug(f"Prepared response headers: {headers}")

            async def stream_generator():
                try:
                    logger.debug("Starting stream_generator...")
                    async for chunk in response.content.iter_chunked(Config.CHUNK_SIZE):
                        logger.debug(f"Streaming chunk of size: {len(chunk)} bytes")
                        yield chunk
                except asyncio.CancelledError:
                    logger.warning(f"Client disconnected during stream: {target_url}")
                    raise
                except Exception as exc:
                    logger.error(f"Streaming error for {target_url}: {exc}")
                    raise
                finally:
                    logger.debug("Cleaning up resources in stream_generator...")
                    await cleanup_resources(response, session)

            logger.debug("Returning StreamingResponse to client.")
            return StreamingResponse(
                stream_generator(),
                headers=headers,
                media_type=content_type or "application/octet-stream"
            )

        except HTTPException:
            logger.debug("HTTPException raised inside try block; cleaning up...")
            await cleanup_resources(response, session)
            raise
        except Exception as exc:
            logger.exception(f"Error in download_stream: {exc}")
            await cleanup_resources(response, session)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Streaming failed: {str(exc)}"
            )

    except HTTPException as http_err:
        logger.debug(f"Reraising HTTPException: {http_err.detail}")
        raise
    except Exception as exc:
        logger.exception(f"Unhandled exception in /download-stream: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unhandled error: {str(exc)}"
        )
