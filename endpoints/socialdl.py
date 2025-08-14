"""
SocialDL API - Unified Social Media Downloader
"""
import logging
from urllib.parse import quote

import aiohttp
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

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
    quality: Optional[str] = None
    type: Optional[str] = None
    url: HttpUrl
    size: Optional[str] = None


class DownloadResponse(BaseModel):
    status: str
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[str] = None
    source: Optional[str] = None
    links: Optional[List[DownloadLink]] = None
    message: Optional[str] = None


class SocialDLResponse(BaseModel):
    # Generic “other platforms” schema from SocialDL (e.g., Dailymotion)
    platform: Optional[str] = None
    status: bool
    url: Optional[HttpUrl] = None
    filename: Optional[str] = None
    message: Optional[str] = None


class YouTubeDownloadResponse(BaseModel):
    # Exact YouTube shape you shared
    platform: str = "YouTube"
    status: bool
    title: Optional[str] = None
    thumb: Optional[HttpUrl] = None
    video: Optional[HttpUrl] = None
    video_hd: Optional[HttpUrl] = None
    audio: Optional[HttpUrl] = None
    quality: Optional[str] = None
    message: Optional[str] = None


class InstagramLink(BaseModel):
    type: str  # "video" or "image"
    url: HttpUrl


class InstagramResponse(BaseModel):
    platform: Optional[str] = "Instagram"
    status: bool
    thumbnail: Optional[str] = None
    videos: Optional[List[InstagramLink]] = None
    images: Optional[List[InstagramLink]] = None
    message: Optional[str] = None


# ---- Facebook nested response set ----
class FacebookVideoItem(BaseModel):
    resolution: Optional[str] = None
    thumbnail: Optional[str] = None
    url: Optional[HttpUrl] = None
    shouldRender: Optional[bool] = None


class FacebookData(BaseModel):
    thumbnail: List[str] = []
    url: List[HttpUrl] = []
    direct_video: List[HttpUrl] = []
    video_data: Optional[List[FacebookVideoItem]] = None


class FacebookResponse(BaseModel):
    platform: Optional[str] = "Facebook"
    status: bool
    data: Optional[FacebookData] = None
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

                if not isinstance(data, dict) or "services" not in data:
                    raise ValueError("Invalid response from SocialDL API")

                services = data["services"]
                if not isinstance(services, list):
                    raise ValueError("Invalid 'services' format from SocialDL API")

                return ServiceListResponse(
                    status="success",
                    total_services=len(services),
                    services=services,
                )
    except Exception as e:
        logger.error(f"Error fetching SocialDL services: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch services: {str(e)}",
        )


@router.get("/socialdl", response_model=SocialDLResponse)
async def download_social_media(
    url: HttpUrl = Query(..., description="URL of the social media post to download"),
):
    """
    Generic passthrough for platforms that return:
    { platform, status, url, filename } (e.g., Dailymotion).
    Also strips the 'Tg: @teleservices_api' prefix from filename if present.
    """
    api_url = f"{BASE_URL}/down?url={quote(str(url))}"
    logger.info(f"Downloading from SocialDL: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if not isinstance(data, dict):
                    return SocialDLResponse(
                        platform=None,
                        status=False,
                        message="Invalid response from SocialDL API",
                    )

                # Clean filename if present
                filename = data.get("filename")
                if isinstance(filename, str) and "Tg: @teleservices_api" in filename:
                    data["filename"] = filename.replace("Tg: @teleservices_api", "").strip()

                # Some platforms may use "status": true/false; ensure bool
                data["status"] = bool(data.get("status", False))

                # Let Pydantic validate/shape it
                return SocialDLResponse(**data)

    except Exception as e:
        logger.error(f"Error downloading from SocialDL: {e}")
        return SocialDLResponse(
            platform=None,
            status=False,
            message=f"Failed to download media: {e}",
        )


@router.get("/youtube", response_model=YouTubeDownloadResponse)
async def download_youtube(
    url: HttpUrl = Query(..., description="YouTube video URL")
):
    """
    YouTube special endpoint – matches the exact structure you provided.
    """
    api_url = f"{BASE_URL}/down?url={quote(str(url))}"
    logger.info(f"Downloading YouTube: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()
    except Exception as e:
        logger.error(f"YouTube request error: {e}")
        return YouTubeDownloadResponse(
            platform="YouTube",
            status=False,
            message=f"Request error: {e}",
        )

    if isinstance(data, dict) and data.get("platform") == "YouTube" and data.get("status") is True:
        # Return as-is; Pydantic will coerce as needed
        return YouTubeDownloadResponse(**data)

    # Fallback for API errors / unexpected shapes
    return YouTubeDownloadResponse(
        platform="YouTube",
        status=False,
        message=data.get("message", "Unknown error from SocialDL API") if isinstance(data, dict) else "Invalid response from SocialDL API",
    )


@router.get("/instagram", response_model=InstagramResponse)
async def download_instagram(
    url: HttpUrl = Query(..., description="Instagram post or reel URL")
):
    """
    Instagram endpoint – maps the nested `data` structure:
    - thumbnail: first item (if any)
    - direct_video: list -> videos
    - images: list -> images
    """
    api_url = f"{BASE_URL}/down?url={quote(str(url))}"
    logger.info(f"Downloading from Instagram: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=30) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if not isinstance(data, dict) or "data" not in data:
                    return InstagramResponse(
                        status=False, message="Invalid Instagram API response"
                    )

                ig_data = data["data"] or {}
                status_flag = bool(data.get("status", False))

                # Videos
                videos: List[InstagramLink] = []
                for v in ig_data.get("direct_video", []) or []:
                    try:
                        videos.append(InstagramLink(type="video", url=v))
                    except Exception:
                        # Skip bad URLs
                        continue

                # Images
                images: List[InstagramLink] = []
                for img in ig_data.get("images", []) or []:
                    try:
                        images.append(InstagramLink(type="image", url=img))
                    except Exception:
                        continue

                # Thumbnail (take first if present)
                thumb = None
                thumbs = ig_data.get("thumbnail")
                if isinstance(thumbs, list) and thumbs:
                    thumb = thumbs[0]

                return InstagramResponse(
                    status=status_flag,
                    thumbnail=thumb,
                    videos=videos or None,
                    images=images or None,
                )

    except Exception as e:
        logger.error(f"Error downloading Instagram media: {e}")
        return InstagramResponse(
            status=False, message=f"Failed to download Instagram media: {e}"
        )


@router.get("/facebook", response_model=FacebookResponse)
async def download_facebook(
    url: HttpUrl = Query(..., description="Facebook video URL")
):
    """
    Facebook endpoint – matches the nested response set you provided:
    {
      "platform": "Facebook",
      "status": true,
      "data": {
        "thumbnail": [...],
        "url": [...],
        "direct_video": [...],
        "video_data": [{ resolution, thumbnail, url, shouldRender }]
      }
    }
    """
    api_url = f"{BASE_URL}/down?url={quote(str(url))}"
    logger.info(f"Downloading from Facebook: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=30) as resp:
                resp.raise_for_status()
                raw = await resp.json()

                if not isinstance(raw, dict):
                    return FacebookResponse(
                        platform="Facebook",
                        status=False,
                        message="Invalid response from SocialDL API",
                    )

                # Coerce "status" to bool
                status_flag = bool(raw.get("status", False))
                platform = raw.get("platform", "Facebook")

                payload = FacebookResponse(platform=platform, status=status_flag)

                # Map nested data if present
                raw_data = raw.get("data")
                if isinstance(raw_data, dict):
                    # Normalize lists
                    thumb_list = raw_data.get("thumbnail") or []
                    url_list = raw_data.get("url") or []
                    direct_list = raw_data.get("direct_video") or []
                    video_data_list = raw_data.get("video_data") or None

                    # Validate/convert items
                    safe_video_data: Optional[List[FacebookVideoItem]] = None
                    if isinstance(video_data_list, list):
                        safe_video_data = []
                        for item in video_data_list:
                            if not isinstance(item, dict):
                                continue
                            try:
                                safe_video_data.append(FacebookVideoItem(**item))
                            except Exception:
                                # Skip invalid entries
                                continue
                        if not safe_video_data:
                            safe_video_data = None

                    # Build FacebookData with URL validation
                    try:
                        fb_data = FacebookData(
                            thumbnail=thumb_list if isinstance(thumb_list, list) else [],
                            url=[u for u in url_list if isinstance(u, str)],
                            direct_video=[d for d in direct_list if isinstance(d, str)],
                            video_data=safe_video_data,
                        )
                        payload.data = fb_data
                    except Exception as ve:
                        logger.warning(f"Facebook data mapping issue: {ve}")
                        # If mapping fails, still return a failure with message
                        return FacebookResponse(
                            platform=platform,
                            status=False,
                            message=f"Malformed Facebook data: {ve}",
                        )
                else:
                    # Some older responses might be flat; provide a clear message
                    if status_flag:
                        logger.warning("Facebook response missing 'data' key despite status true")

                return payload

    except Exception as e:
        logger.error(f"Error downloading from Facebook: {e}")
        return FacebookResponse(
            platform="Facebook",
            status=False,
            message=f"Failed to download Facebook media: {e}",
        )
