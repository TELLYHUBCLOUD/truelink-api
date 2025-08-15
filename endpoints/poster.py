from fastapi import APIRouter, Query, HTTPException
from aiohttp import ClientSession

router = APIRouter()

# Platform patterns & APIs
PLATFORMS = {
    "primevideo": {
        "pattern": "primevideo.com",
        "api": "https://primevideo.pbx1bots.workers.dev/?url="
    },
    "appletv": {
        "pattern": "tv.apple.com",
        "api": "https://appletv.pbx1bots.workers.dev/?url="
    },
    "airtelxstream": {
        "pattern": "airtelxstream.in",
        "api": "https://airtelxstream.pbx1bots.workers.dev/?url="
    },
    "zee5": {
        "pattern": "zee5.com",
        "api": "https://zee5.pbx1bots.workers.dev/?url="
    },
    "stage": {
        "pattern": "stage.in",
        "api": "https://stage.pbx1bots.workers.dev/?url="
    }
}
@router.get("/platforms")
async def get_supported_platforms():
    """Returns all supported platforms with patterns & API endpoints."""
    return [
        {
            "pattern": info["pattern"]
        }
        for name, info in PLATFORMS.items()
    ]

@router.get("/poster")
async def get_poster(url: str = Query(..., description="Content URL from supported platforms")):
    platform_info = None
    for name, info in PLATFORMS.items():
        if info["pattern"] in url:
            platform_info = info
            break

    if not platform_info:
        raise HTTPException(status_code=400, detail="Unsupported platform URL")

    api_url = platform_info["api"] + url

    async with ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail="Failed to fetch data")
            data = await resp.json()

    return {
        "type": data.get("type", "movie"),
        "title": data.get("title", "Unknown Title"),
        "year": data.get("year"),
        "landscape": data.get("landscape"),
        "portrait": data.get("portrait"),
        "platform": platform_info["pattern"]
    }
