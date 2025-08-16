from fastapi import APIRouter, Query, HTTPException
from urllib.parse import quote_plus
import aiohttp
import logging
import asyncio
import time
import re
from cloudscraper import create_scraper
from itertools import cycle
import random
from requests import Session
from bs4 import BeautifulSoup
from urllib.parse import urlparse

router = APIRouter()
logger = logging.getLogger(__name__)

# Bypass endpoint remains the same
async def bypass(url: str) -> str:
    try:
        encoded_url = quote_plus(url)
        api_url = f"https://iwoozie.baby/api/free/bypass?url={encoded_url}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://thebypasser.com/",
            "Origin": "https://thebypasser.com",
            "Accept": "*/*",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                api_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Bypass API error: {response.status} - {error_text}")
                    raise ValueError(f"API returned {response.status}")
                
                data = await response.json()
                if not data.get("success") or not data.get("result"):
                    raise ValueError("Invalid API response format")
                
                return data["result"]
                
    except Exception as e:
        logger.exception("Bypass failed")
        raise HTTPException(status_code=400, detail=f"Bypass failed: {str(e)}")

@router.get("/linkvertise")
async def bypass_endpoint(url: str = Query(..., description="The URL to bypass")):
    result = await bypass(url)
    return {"success": True, "bypassed_url": result}

#---------------------------------------------------------------------
def mediafire(url: str) -> str:
    """
    Extracts direct MediaFire download link from a given URL.

    Args:
        url (str): MediaFire share link

    Returns:
        str: Direct download link or error message
    """
    # Regex pattern to detect direct MediaFire links
    direct_pattern = r"https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+"

    # If URL already contains direct download
    final_link = re.findall(direct_pattern, url)
    if final_link:
        return final_link[0]

    # Otherwise scrape the page
    cget = create_scraper().request
    try:
        url = cget("get", url).url
        page = cget("get", url).text
    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"

    # Search for download link inside page source
    final_link = re.findall(r"\'(" + direct_pattern + r")\'", page)
    if not final_link:
        return "ERROR: No links found in this page"

    return final_link[0]

@app.get("/mediafire")
def mediafire_endpoint(url: str):
     return {"success": True, "bypassed_url": mediafire(url)}

##------------------------------------------------------------------------------------

def hxfile(url: str) -> str:
    """
    Extracts direct download link from Hxfile URLs.
    
    Args:
        url (str): Hxfile link
    
    Returns:
        str: Direct download link or error message
    """
    sess = Session()
    try:
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.152 Safari/537.36",
        }

        # Extract file id from URL path
        file_id = urlparse(url).path.strip("/")

        data = {
            "op": "download2",
            "id": file_id,
            "rand": "",
            "referer": "",
            "method_free": "",
            "method_premium": "",
        }

        response = sess.post(url, headers=headers, data=data)
        soup = BeautifulSoup(response.text, "html.parser")

        if btn := soup.find("a", class_="btn btn-dow"):
            return btn["href"]
        if unique := soup.find("a", id="uniqueExpirylink"):
            return unique["href"]

        return "ERROR: No download link found"

    except Exception as e:
        return f"ERROR: {e.__class__.__name__}"
      
@app.get("/hxfile")
def hxfile_endpoint(url: str):
    return {"success": True, "bypassed_url": hxfile(url)}
  ##-------------------------------------------------------------------------------
  
