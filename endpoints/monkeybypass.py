import asyncio
from fastapi import APIRouter, Query, HTTPException
from pydantic import HttpUrl
from playwright.async_api import async_playwright
import os
import logging
import sys

router = APIRouter()
logger = logging.getLogger(__name__)

# Function to ensure Playwright browsers are installed
async def install_playwright_browsers():
    try:
        logger.info("Checking Playwright browser installation")
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            await browser.close()
        logger.info("Playwright browsers are installed")
    except Exception as e:
        logger.error(f"Browser not installed: {str(e)}")
        logger.info("Attempting to install browsers...")
        
        # Install browsers using Playwright CLI
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "playwright", "install", "chromium",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            logger.error(f"Browser installation failed: {stderr.decode()}")
            raise RuntimeError("Failed to install Playwright browsers")
        
        logger.info("Successfully installed browsers")

# Read the Tampermonkey script from file
TAMPERMONKEY_SCRIPT = ""
try:
    with open('tscript.txt', 'r', encoding='utf-8') as f:
        TAMPERMONKEY_SCRIPT = f.read()
    logger.info("Successfully loaded Tampermonkey script")
except Exception as e:
    logger.error(f"Failed to load Tampermonkey script: {str(e)}")
    TAMPERMONKEY_SCRIPT = "console.error('Tampermonkey script failed to load!');"

@router.get("/tmonkey/bypass")
async def tmonkey_bypass(url: HttpUrl = Query(..., description="URL to bypass Cloudflare protection")):
    if not TAMPERMONKEY_SCRIPT:
        raise HTTPException(
            status_code=500,
            detail="Tampermonkey script not loaded. Check server logs."
        )
    
    try:
        # Ensure browsers are installed
        await install_playwright_browsers()
        
        async with async_playwright() as p:
            # Launch browser with enhanced stealth settings
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials"
                ],
                # Point to the correct browser path
                executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
            )
            
            # Create isolated context
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="en-US",
                timezone_id="America/New_York",
                java_script_enabled=True,
                ignore_https_errors=True
            )
            
            # Block unnecessary resources
            await context.route("**/*.{png,jpg,jpeg,svg,gif,webp}", lambda route: route.abort())
            await context.route("**/*.css", lambda route: route.abort())
            await context.route("**/*.woff*", lambda route: route.abort())
            
            page = await context.new_page()
            
            # Set timeout for navigation
            navigation_timeout = 45000  # 45 seconds
            wait_timeout = 10000       # 10 seconds
            
            try:
                await page.goto(str(url), 
                               wait_until="domcontentloaded", 
                               timeout=navigation_timeout)
            except Exception as nav_error:
                logger.warning(f"Navigation warning: {str(nav_error)}")
            
            # Wait for Cloudflare challenge
            await asyncio.sleep(8)
            
            # Inject Tampermonkey script
            injection_result = await page.evaluate(TAMPERMONKEY_SCRIPT)
            
            # Wait for bypass to execute
            await page.wait_for_timeout(5000)
            
            # Get final page state
            final_url = page.url
            content = await page.content()
            
            await browser.close()
            
            return {
                "status": "success",
                "final_url": final_url,
                "content_length": len(content),
                "injection_result": injection_result
            }

    except Exception as e:
        logger.exception("Bypass operation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Bypass failed: {str(e)}"
        )