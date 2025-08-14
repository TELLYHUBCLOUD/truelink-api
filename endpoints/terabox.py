"""
Terabox resolution endpoint
"""
import time
import logging
import asyncio
from urllib.parse import quote
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import HttpUrl
import aiohttp

from models import TeraboxResponse

logger = logging.getLogger(__name__)
router = APIRouter()

async def try_api_1(url: str, ndus: str, session: aiohttp.ClientSession) -> dict:
    """Try first Terabox API"""
    api_url = f"https://nord.teraboxfast.com/?ndus={quote(ndus)}&url={quote(str(url))}"
    logger.debug(f"Trying API 1: {api_url}")
    
    try:
        async with session.get(api_url, timeout=15) as response:
            response.raise_for_status()
            data = await response.json()
            
            # Check if response has required fields
            if all(key in data for key in ["file_name", "sizebytes", "thumb", "link", "direct_link"]):
                logger.info("API 1 successful")
                return {
                    "success": True,
                    "api": "API 1",
                    "data": data
                }
    except Exception as e:
        logger.warning(f"API 1 failed: {e}")
    
    return {"success": False, "api": "API 1", "error": "Failed"}

async def try_api_2(url: str, session: aiohttp.ClientSession) -> dict:
    """Try second Terabox API"""
    api_url = f"https://teradl1.tellycloudapi.workers.dev/api/api1?url={quote(str(url))}"
    logger.debug(f"Trying API 2: {api_url}")
    
    try:
        async with session.get(api_url, timeout=15) as response:
            response.raise_for_status()
            data = await response.json()
            
            # Check fallback API format
            if data.get("success") and "metadata" in data and "links" in data:
                metadata = data["metadata"]
                links = data["links"]
                dl1 = links.get("dl1")
                dl2 = links.get("dl2")
                
                if dl1 or dl2:
                    logger.info("API 2 successful")
                    return {
                        "success": True,
                        "api": "API 2",
                        "data": data
                    }
    except Exception as e:
        logger.warning(f"API 2 failed: {e}")
    
    return {"success": False, "api": "API 2", "error": "Failed"}

@router.get("/terabox", response_model=TeraboxResponse)
async def terabox_endpoint(
    url: HttpUrl = Query(..., description="Terabox share link"),
    ndus: str = Query(..., description="NDUS cookie value")
):
    """Resolve Terabox link using both APIs concurrently and return best result"""
    start_time = time.time()
    
    if not ndus or len(ndus.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NDUS cookie value is required"
        )

    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    logger.info(f"Processing Terabox URL: {url}")
    logger.info("Running both APIs concurrently...")

    # Create aiohttp session with proper configuration
    timeout = aiohttp.ClientTimeout(total=20, connect=10)
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    
    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers={"User-Agent": user_agent}
    ) as session:
        
        # Run both APIs concurrently
        try:
            results = await asyncio.gather(
                try_api_1(str(url), ndus, session),
                try_api_2(str(url), session),
                return_exceptions=True
            )
            
            api1_result, api2_result = results
            
            # Handle exceptions
            if isinstance(api1_result, Exception):
                logger.error(f"API 1 exception: {api1_result}")
                api1_result = {"success": False, "api": "API 1", "error": str(api1_result)}
            
            if isinstance(api2_result, Exception):
                logger.error(f"API 2 exception: {api2_result}")
                api2_result = {"success": False, "api": "API 2", "error": str(api2_result)}
            
            # Process results - prioritize API 1 if both succeed
            if api1_result.get("success"):
                data = api1_result["data"]
                logger.info("Returning API 1 result")
                return TeraboxResponse(
                    status="success",
                    file_name=data.get("file_name"),
                    thumb=data.get("thumb"),
                    link=data.get("link"),
                    direct_link=data.get("direct_link"),
                    sizebytes=data.get("sizebytes")
                )
            
            elif api2_result.get("success"):
                data = api2_result["data"]
                metadata = data.get("metadata", {})
                links = data.get("links", {})
                logger.info("Returning API 2 result")
                return TeraboxResponse(
                    status="success",
                    file_name=metadata.get("file_name"),
                    thumb=metadata.get("thumb"),
                    size=metadata.get("size"),
                    sizebytes=metadata.get("sizebytes"),
                    dl1=links.get("dl1"),
                    dl2=links.get("dl2")
                )
            
        except Exception as e:
            logger.exception(f"Concurrent API execution failed: {e}")
    
    # If both APIs failed
    processing_time = time.time() - start_time
    logger.warning(f"Both Terabox APIs failed for URL: {url} in {processing_time:.2f}s")
    
    return TeraboxResponse(
        status="error",
        message=f"Both APIs failed. API 1: {api1_result.get('error', 'Unknown error')}. API 2: {api2_result.get('error', 'Unknown error')}. Please check the URL and NDUS cookie."
    )