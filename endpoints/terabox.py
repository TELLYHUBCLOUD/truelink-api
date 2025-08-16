import time
import logging
import asyncio
import re  # Added missing import
from urllib.parse import quote
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import JSONResponse  # Added missing import
from pydantic import HttpUrl, BaseModel
import aiohttp
import requests  # Added missing import
from bs4 import BeautifulSoup  # Added missing import
from models import TeraboxResponse

logger = logging.getLogger(__name__)
router = APIRouter()
executor = ThreadPoolExecutor(max_workers=4)  # Thread pool for blocking operations

# --- Terabox Endpoint Improvements ---
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

            # Fixed: Check for essential fields
            if all(k in data for k in ["file_name", "sizebytes", "thumb", "link", "direct_link"]):
                logger.info("API 1 successful")
                return {"success": True, "api": "API 1", "data": data}

            return {"success": False, "api": "API 1", "error": "Missing required fields"}
    except Exception as e:
        logger.warning(f"API 1 failed: {str(e)}")
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
                return {"success": false, "api": "API 2", "error": "Invalid JSON from API 2"}  # Fixed boolean

            # Fixed boolean and field check
            if data.get("success") and "metadata" in data and "links" in data:
                logger.info("API 2 successful")
                return {"success": true, "api": "API 2", "data": data}  # Fixed boolean

            return {"success": false, "api": "API 2", "error": "Missing required fields"}
    except Exception as e:
        logger.warning(f"API 2 failed: {str(e)}")
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

    logger.info(f"Processing Terabox URL: {url}")

    timeout = aiohttp.ClientTimeout(total=25, connect=15)
    connector = aiohttp.TCPConnector(limit_per_host=2)
    
    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    ) as session:
        api1_result, api2_result = await asyncio.gather(
            try_api_1(str(url), ndus, session),
            try_api_2(str(url), session)
        )

    # Process results
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
        message=f"API1: {api1_result.get('error', 'Unknown')} | API2: {api2_result.get('error', 'Unknown')}"
    )


# --- Diskwala Endpoint Improvements ---
def get_diskwala_direct_link(url: str) -> dict | None:
    """Synchronous version to run in thread"""
    match = re.search(r'diskwala\.com/app/([a-f0-9]+)', url)
    if not match:
        return None

    file_id = match.group(1)
    download_page_url = f"https://www.diskwala.com/download/{file_id}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    try:
        page_response = requests.get(download_page_url, headers=headers, timeout=20)
        page_response.raise_for_status()

        soup = BeautifulSoup(page_response.text, "html.parser")
        
        # More robust element finding
        download_button = soup.find("a", class_=lambda x: x and "btn-primary" in x.split())
        if not download_button or not download_button.get("href"):
            logger.error(f"Download button not found for {url}")
            return None

        direct_link = download_button["href"]
        
        # Improved element search
        file_name_tag = soup.find("h5", class_=lambda x: x and "text-center" in x.split())
        file_name = file_name_tag.get_text(strip=True) if file_name_tag else f"diskwala_{file_id}"
        
        size_info_tag = soup.find("p", class_=lambda x: x and "text-center" in x.split() and "text-primary" in x.split())
        file_size = size_info_tag.get_text(strip=True) if size_info_tag else "Unknown"

        return {"link": direct_link, "name": file_name, "size": file_size}

    except Exception as e:
        logger.error(f"Diskwala error: {str(e)}")
        return None

@router.get("/diskwala")
async def diskwala_endpoint(url: str = Query(..., description="Diskwala file link")):
    """Async wrapper for synchronous scraper"""
    try:
        # Run blocking operation in thread pool
        file_info = await asyncio.get_event_loop().run_in_executor(
            executor, 
            get_diskwala_direct_link, 
            url
        )
        
        if not file_info:
            raise HTTPException(status_code=404, detail="Link extraction failed")
            
        return {
            "success": True,
            "source_url": url,
            "file": {
                "name": file_info["name"],
                "size": file_info["size"],
                "direct_link": file_info["link"]
            }
        }
    except Exception as e:
        logger.error(f"Diskwala endpoint error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# --- Selenium Helper Functions --- (MODIFIED)
def setup_driver():
    """Create reusable driver configuration with local imports"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--window-size=1280,720")
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
    except ImportError:
        logger.error("Selenium dependencies not installed. Install with: pip install selenium webdriver-manager")
        return None
    except Exception as e:
        logger.error(f"Driver setup failed: {str(e)}")
        return None

def get_dropgalaxy_direct_link(url: str) -> str | None:
    try:
        driver = setup_driver()
        if not driver:
            return None
            
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        button = wait.until(EC.element_to_be_clickable((By.ID, "direct_download")))
        button.click()
        link = wait.until(
            EC.presence_of_element_located((By.ID, "downloadbtn"))
        ).get_attribute("href")
        return link
    except Exception as e:
        logger.error(f"DropGalaxy error: {str(e)}")
        return None
    finally:
        if 'driver' in locals():
            driver.quit()

def get_upfiles_direct_link(url: str) -> str | None:
    try:
        driver = setup_driver()
        if not driver:
            return None
            
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        btn = wait.until(EC.element_to_be_clickable((By.ID, "btn_download")))
        btn.click()
        wait.until(EC.url_changes(url))
        return driver.current_url
    except Exception as e:
        logger.error(f"UpFiles error: {str(e)}")
        return None
    finally:
        if 'driver' in locals():
            driver.quit()

# --- File Hosting Endpoints --- (ADDED ERROR HANDLING)
@router.get("/dropgalaxy")
async def dropgalaxy_api(url: str = Query(..., description="DropGalaxy file URL")):
    try:
        link = await asyncio.get_event_loop().run_in_executor(
            executor, 
            get_dropgalaxy_direct_link, 
            url
        )
        
        if not link:
            raise HTTPException(
                status_code=500,
                detail="Selenium dependencies not installed or scraping failed"
            )
            
        return {
            "success": True,
            "host": "DropGalaxy",
            "source_url": url,
            "direct_link": link
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "host": "DropGalaxy",
                "error": str(e)
            }
        )

@router.get("/upfiles")
async def upfiles_api(url: str = Query(..., description="UpFiles.com file URL")):
    try:
        link = await asyncio.get_event_loop().run_in_executor(
            executor, 
            get_upfiles_direct_link, 
            url
        )
        
        if not link:
            raise HTTPException(
                status_code=500,
                detail="Selenium dependencies not installed or scraping failed"
            )
            
        return {
            "success": True,
            "host": "UpFiles",
            "source_url": url,
            "direct_link": link
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "host": "UpFiles",
                "error": str(e)
            }
        )