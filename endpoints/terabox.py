"""
Terabox resolution endpoint
"""
import time
import logging
from urllib.parse import quote
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import HttpUrl
from requests import Session

from models import TeraboxResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/terabox", response_model=TeraboxResponse)
async def terabox_endpoint(
    url: HttpUrl = Query(..., description="Terabox share link"),
    ndus: str = Query(..., description="NDUS cookie value")
):
    """Resolve Terabox link to a direct download link using fallback APIs"""
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

    apis = [
        f"https://nord.teraboxfast.com/?ndus={quote(ndus)}&url={quote(str(url))}",
        f"https://teradl1.tellycloudapi.workers.dev/api/api1?url={quote(str(url))}",
    ]

    logger.info(f"Processing Terabox URL: {url}")

    with Session() as session:
        session.headers.update({"User-Agent": user_agent})
        
        for i, api_url in enumerate(apis, 1):
            try:
                logger.debug(f"Trying API {i}: {api_url}")
                response = session.get(api_url, timeout=15)
                response.raise_for_status()
                req = response.json()
                
                # Case 1: Direct link from first API
                if all(key in req for key in ["file_name", "sizebytes", "thumb", "link", "direct_link"]):
                    logger.info(f"Successfully resolved Terabox URL using API {i}")
                    return TeraboxResponse(
                        status="success",
                        file_name=req["file_name"],
                        thumb=req["thumb"],
                        link=req["link"],
                        direct_link=req["direct_link"],
                        sizebytes=req["sizebytes"]
                    )

                # Case 2: Fallback API format
                if req.get("success") and "metadata" in req and "links" in req:
                    metadata = req["metadata"]
                    links = req["links"]
                    dl1 = links.get("dl1")
                    dl2 = links.get("dl2")
                    
                    if dl1 or dl2:
                        logger.info(f"Successfully resolved Terabox URL using API {i} (fallback format)")
                        return TeraboxResponse(
                            status="success",
                            file_name=metadata.get("file_name"),
                            thumb=metadata.get("thumb"),
                            size=metadata.get("size"),
                            sizebytes=metadata.get("sizebytes"),
                            dl1=dl1,
                            dl2=dl2
                        )
                        
            except Exception as e:
                logger.warning(f"API {i} failed: {e}")
                continue

    # If nothing worked
    processing_time = time.time() - start_time
    logger.warning(f"All Terabox APIs failed for URL: {url}")
    
    return TeraboxResponse(
        status="error",
        message="File not found or all API requests failed. Please check the URL and NDUS cookie."
    )