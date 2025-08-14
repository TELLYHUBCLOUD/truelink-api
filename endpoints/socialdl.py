"""
SocialDL API - Unified Social Media Downloader
"""
import logging
from urllib.parse import quote
import aiohttp
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
router = APIRouter()

BASE_URL = "https://tele-social.vercel.app"

# ==========================
# Models
# ==========================

class ServiceListResponse(BaseModel):
    status: str
    total_services: int
    services: List[str]

class DownloadLink(BaseModel):
    quality: Optional[str]
    type: Optional[str]
    url: str
    size: Optional[str]

class DownloadResponse(BaseModel):
    status: str
    title: Optional[str]
    thumbnail: Optional[str]
    duration: Optional[str]
    source: Optional[str]
    links: Optional[List[DownloadLink]]
    message: Optional[str] = None

# ==========================
# Endpoints
# ==========================

@router.get("/socialdl/services", response_model=ServiceListResponse)
async def get_socialdl_services():
    """
    Fetch the list of supported social media services.
    """
    api_url = f"{BASE_URL}/services"
    logger.info("Fetching supported SocialDL services...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if not data or "services" not in data:
                    raise ValueError("Invalid response from SocialDL API")

                services = data["services"]
                return ServiceListResponse(
                    status="success",
                    total_services=len(services),
                    services=services
                )
    except Exception as e:
        logger.error(f"Error fetching SocialDL services: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch services: {str(e)}"
        )

@router.get("/socialdl", response_model=DownloadResponse)
async def download_social_media(
    url: HttpUrl = Query(..., description="URL of the social media post to download")
):
    """
    Download media from supported social media platforms.
    """
    api_url = f"{BASE_URL}/down?url={quote(str(url))}"
    logger.info(f"Downloading from SocialDL: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=20) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if not data or "links" not in data:
                    return DownloadResponse(
                        status="error",
                        message="Invalid response from SocialDL API"
                    )

                links = [
                    DownloadLink(
                        quality=link.get("quality"),
                        type=link.get("type"),
                        url=link.get("url"),
                        size=link.get("size")
                    )
                    for link in data.get("links", [])
                ]

                return DownloadResponse(
                    status="success",
                    title=data.get("title"),
                    thumbnail=data.get("thumbnail"),
                    duration=data.get("duration"),
                    source=data.get("source"),
                    links=links
                )
    except Exception as e:
        logger.error(f"Error downloading from SocialDL: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download media: {str(e)}"
        )
