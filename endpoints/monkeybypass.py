import asyncio
from fastapi import APIRouter, Query, HTTPException
from pydantic import HttpUrl
from playwright.async_api import async_playwright
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

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
                ]
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
            
            # Capture console logs
            console_logs = []
            def log_handler(msg):
                console_logs.append({
                    "type": msg.type,
                    "text": msg.text,
                    "location": {
                        "url": msg.location["url"],
                        "line": msg.location["lineNumber"],
                        "column": msg.location["columnNumber"]
                    }
                })
            page.on("console", log_handler)
            
            # Capture network errors
            network_errors = []
            def response_handler(response):
                if response.status >= 400:
                    network_errors.append({
                        "url": response.url,
                        "status": response.status,
                        "method": response.request.method,
                        "resource": response.request.resource_type
                    })
            page.on("response", response_handler)
            
            await browser.close()
            
            return {
                "status": "success",
                "final_url": final_url,
                "content_length": len(content),
                "console_logs": console_logs,
                "network_errors": network_errors,
                "injection_result": injection_result
            }

    except Exception as e:
        logger.exception("Bypass operation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Bypass failed: {str(e)}"
        )