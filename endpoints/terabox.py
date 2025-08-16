"""
Terabox resolution endpoint - Concurrent API execution with fallback
"""
import time
import logging
import asyncio
from urllib.parse import quote
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import HttpUrl, BaseModel
import aiohttp

from models import TeraboxResponse

logger = logging.getLogger(__name__)
router = APIRouter()

async def try_api_1(url: str, ndus: str, session: aiohttp.ClientSession) -> dict:
    api_url = f"https://nord.teraboxfast.com/?ndus={quote(ndus)}&url={quote(str(url))}"
    logger.debug(f"Trying API 1: {api_url}")
    
    try:
        async with session.get(api_url, timeout=15) as response:
            text_data = await response.text()
            try:
                data = await response.json()
            except Exception:
                logger.error(f"API 1 returned non-JSON: {text_data[:200]}")
                return {"success": False, "api": "API 1", "error": "Invalid JSON from API 1"}

            if all(k in data for k in ["file_name", "sizebytes", "thumb", "link", "direct_link"]):
                logger.info("API 1 successful")
                return {"success": True, "api": "API 1", "data": data}

            return {"success": False, "api": "API 1", "error": "Missing required fields"}
    except Exception as e:
        logger.warning(f"API 1 failed: {e}")
        return {"success": False, "api": "API 1", "error": str(e)}

async def try_api_2(url: str, session: aiohttp.ClientSession) -> dict:
    api_url = f"https://teradl1.tellycloudapi.workers.dev/api/api1?url={quote(str(url))}"
    logger.debug(f"Trying API 2: {api_url}")
    
    try:
        async with session.get(api_url, timeout=15) as response:
            text_data = await response.text()
            try:
                data = await response.json()
            except Exception:
                logger.error(f"API 2 returned non-JSON: {text_data[:200]}")
                return {"success": false, "api": "API 2", "error": "Invalid JSON from API 2"}

            if data.get("success") and "metadata" in data and "links" in data:
                logger.info("API 2 successful")
                return {"success": true, "api": "API 2", "data": data}

            return {"success": False, "api": "API 2", "error": "Missing required fields"}
    except Exception as e:
        logger.warning(f"API 2 failed: {e}")
        return {"success": False, "api": "API 2", "error": str(e)}

@router.get("/terabox", response_model=TeraboxResponse)
async def terabox_endpoint(
    url: HttpUrl = Query(..., description="Terabox share link"),
    ndus: str = Query(..., description="NDUS cookie value")
):
    start_time = time.time()
    
    if not ndus.strip():
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

    timeout = aiohttp.ClientTimeout(total=20, connect=10)
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    
    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers={"User-Agent": user_agent}
    ) as session:
        api1_result, api2_result = await asyncio.gather(
            try_api_1(str(url), ndus, session),
            try_api_2(str(url), session)
        )

    # Priority: API 1 > API 2, but merge if possible
    if api1_result.get("success"):
        data = api1_result["data"]
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
        return TeraboxResponse(
            status="success",
            file_name=metadata.get("file_name"),
            thumb=metadata.get("thumb"),
            size=metadata.get("size"),
            sizebytes=metadata.get("sizebytes"),
            dl1=links.get("dl1"),
            dl2=links.get("dl2"),
        )

    processing_time = time.time() - start_time
    logger.error(f"Both Terabox APIs failed for {url} in {processing_time:.2f}s")

    return TeraboxResponse(
        status="error",
        file_name=f"Both APIs failed. API 1: {api1_result.get('error')}, API 2: {api2_result.get('error')}"
    )



# --- Core Scraper Function ---
def get_diskwala_direct_link(url: str) -> dict | None:
    """
    Scrapes Diskwala page to find the direct download link.
    Returns a dictionary with link, filename, and size, or None on failure.
    """
    match = re.search(r'diskwala\.com/app/([a-f0-9]+)', url)
    if not match:
        return None

    file_id = match.group(1)
    download_page_url = f"https://www.diskwala.com/download/{file_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        page_response = requests.get(download_page_url, headers=headers, timeout=15)
        page_response.raise_for_status()

        soup = BeautifulSoup(page_response.text, "html.parser")
        download_button = soup.find("a", class_="btn-primary")
        if not download_button or "href" not in download_button.attrs:
            logger.error(f"Could not find download button for {url}")
            return None

        direct_link = download_button["href"]
        file_name_tag = soup.find("h5", class_="text-center")
        file_name = file_name_tag.get_text(strip=True) if file_name_tag else f"diskwala_{file_id}"
        size_info_tag = soup.find("p", class_="text-center text-primary")
        file_size = size_info_tag.get_text(strip=True) if size_info_tag else "Unknown size"

        return {"link": direct_link, "name": file_name, "size": file_size}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error scraping {url}: {e}")
        return None


# --- API Endpoint ---
@router.get("/diskwala")
async def diskwala_endpoint(url: str = Query(..., description="Diskwala file link")):
    """
    Extracts direct download link from a Diskwala URL.
    Returns JSON with file name, size, and link.
    """
    file_info = get_diskwala_direct_link(url)
    if not file_info:
        raise HTTPException(status_code=404, detail="Could not extract Diskwala link. File may be deleted or site changed.")

    return {
        "success": True,
        "source_url": url,
        "file": {
            "name": file_info["name"],
            "size": file_info["size"],
            "direct_link": file_info["link"]
        }
    }
