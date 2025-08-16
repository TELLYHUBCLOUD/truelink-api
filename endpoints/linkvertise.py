from fastapi import APIRouter, Query, HTTPException
from urllib.parse import quote_plus
import aiohttp
import logging
import asyncio
import time
import requests
from itertools import cycle
import random

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

# New endpoints for test link generation and bypass testing
class TestLinkGenerator:
    def __init__(self):
        self.popular_urls = [
            "https://www.google.com",
            "https://www.youtube.com",
            "https://www.github.com",
            "https://www.stackoverflow.com",
            "https://www.wikipedia.org",
            "https://www.reddit.com",
            "https://www.twitter.com",
            "https://www.facebook.com",
            "https://www.instagram.com",
            "https://www.linkedin.com",
            "https://www.amazon.com",
            "https://www.netflix.com",
            "https://www.spotify.com",
            "https://www.apple.com",
            "https://www.microsoft.com",
            "https://www.discord.com",
            "https://www.twitch.tv",
            "https://www.tiktok.com",
            "https://www.pinterest.com",
            "https://www.dropbox.com"
        ]
        self.services = {
            "TinyURL": self.generate_tinyurl,
            "is.gd": self.generate_is_gd,
            "v.gd": self.generate_v_gd,
        }

    def generate_tinyurl(self, long_url: str) -> str:
        """Generate a TinyURL shortened link"""
        try:
            api_url = f"https://tinyurl.com/api-create.php?url={quote_plus(long_url)}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200 and response.text.startswith('https://tinyurl.com/'):
                return response.text.strip()
            logger.error(f"TinyURL failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"TinyURL error: {e}")
        return ""

    def generate_is_gd(self, long_url: str) -> str:
        """Generate an is.gd shortened link"""
        try:
            api_url = f"https://is.gd/create.php?format=simple&url={quote_plus(long_url)}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200 and response.text.startswith('https://is.gd/'):
                return response.text.strip()
            logger.error(f"is.gd failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"is.gd error: {e}")
        return ""

    def generate_v_gd(self, long_url: str) -> str:
        """Generate a v.gd shortened link"""
        try:
            api_url = f"https://v.gd/create.php?format=simple&url={quote_plus(long_url)}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200 and response.text.startswith('https://v.gd/'):
                return response.text.strip()
            logger.error(f"v.gd failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"v.gd error: {e}")
        return ""

    async def generate_links(self, count: int = 10) -> list:
        """Generate test shortened links"""
        results = []
        url_cycle = cycle(self.popular_urls)
        
        while len(results) < count:
            url = next(url_cycle)
            service_name, generator = random.choice(list(self.services.items()))
            
            try:
                # Run blocking operation in thread
                short_url = await asyncio.to_thread(generator, url)
                if short_url:
                    results.append({
                        "service": service_name,
                        "original_url": url,
                        "short_url": short_url,
                        "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                    logger.info(f"Generated {service_name} link: {short_url}")
                else:
                    logger.warning(f"{service_name} failed for {url}")
                
                # Be polite to the shortening services
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error generating link: {str(e)}")
        
        return results

@router.get("/generate-test-links")
async def generate_test_links(
    count: int = Query(10, description="Number of test links to generate", ge=1, le=50)
):
    """Generate working shortened URLs for testing purposes"""
    generator = TestLinkGenerator()
    links = await generator.generate_links(count)
    return {
        "success": True,
        "count": len(links),
        "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
        "links": links
    }

@router.get("/test-bypass")
async def test_bypass_endpoint(
    count: int = Query(5, description="Number of test bypasses to perform", ge=1, le=20)
):
    """Test bypass functionality with generated links"""
    generator = TestLinkGenerator()
    test_links = await generator.generate_links(count)
    results = []
    
    for link in test_links:
        try:
            bypassed_url = await bypass(link["short_url"])
            results.append({
                **link,
                "bypassed_url": bypassed_url,
                "bypass_success": True,
                "bypassed_at": time.strftime('%Y-%m-%d %H:%M:%S')
            })
        except HTTPException as e:
            results.append({
                **link,
                "bypassed_url": None,
                "bypass_success": False,
                "error": e.detail,
                "bypassed_at": time.strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception as e:
            results.append({
                **link,
                "bypassed_url": None,
                "bypass_success": False,
                "error": str(e),
                "bypassed_at": time.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Add delay between bypass attempts
        await asyncio.sleep(1)
    
    success_count = sum(1 for r in results if r["bypass_success"])
    return {
        "success": True,
        "tested_at": time.strftime('%Y-%m-%d %H:%M:%S'),
        "success_rate": f"{success_count}/{count}",
        "results": results
    }