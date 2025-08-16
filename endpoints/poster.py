from fastapi import APIRouter, Query, HTTPException
from aiohttp import ClientSession

router = APIRouter()
logger = logging.getLogger(__name__)

API_BASE = "https://cool-poster.tellycloudapi.workers.dev/"

@router.get("/platforms")
async def get_supported_platforms():
    """Fetch supported platforms from external API"""
    async with ClientSession() as session:
        async with session.get(f"{API_BASE}?platforms=1") as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail="Failed to fetch platforms")
            data = await resp.json()

    return data  # already formatted like requested


@router.get("/poster")
async def get_poster(url: str = Query(..., description="Content URL from supported platforms")):
    """Fetch poster & metadata for given content URL"""
    api_url = f"{API_BASE}?url={url}"

    async with ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail="Failed to fetch poster")
            data = await resp.json()

    return data  # already matches desired output
✅ Example outputs: