from fastapi import APIRouter, Query, HTTPException
from aiohttp import ClientSession

router = APIRouter()

# Mapping platforms to API endpoints
PLATFORM_APIS = {
    "primevideo": "https://primevideo.pbx1bots.workers.dev/?url=",
    "appletv": "https://appletv.pbx1bots.workers.dev/?url=",
    "airtelxstream": "https://airtelxstream.pbx1bots.workers.dev/?url=",
    "zee5": "https://zee5.pbx1bots.workers.dev/?url=",
    "stage": "https://stage.pbx1bots.workers.dev/?url="
}

@router.get("/poster")
async def get_poster(platform: str = Query(..., description="Platform name"),
                     url: str = Query(..., description="Content URL")):
    platform = platform.lower()
    if platform not in PLATFORM_APIS:
        raise HTTPException(status_code=400, detail="Unsupported platform")

    api_url = PLATFORM_APIS[platform] + url

    async with ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail="Failed to fetch data")
            data = await resp.json()

    # Extracting fields from the API response
    return {
        "type": data.get("type", "movie"),
        "title": data.get("title", "Unknown Title"),
        "year": data.get("year", None),
        "landscape": data.get("landscape"),
        "portrait": data.get("portrait")
    }
