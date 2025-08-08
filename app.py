import os
import asyncio
import logging
from typing import Any
from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
import aiohttp
from truelink import TrueLinkResolver

# ---------- Logging Setup ----------
logging.basicConfig(
    level=logging.DEBUG,  # Set DEBUG level
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("truelink-api")

app = FastAPI(title="Advanced TrueLink API", version="2.1", docs_url="/docs")


class BatchRequest(BaseModel):
    urls: list[str]


# ---------- Utility Functions ----------
def to_serializable(obj: Any):
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(i) for i in obj]
    if hasattr(obj, "dict"):
        try:
            return to_serializable(obj.dict())
        except Exception as e:
            logger.debug(f"Serialization error on dict(): {e}")
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {k: to_serializable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return str(obj)


async def resolve_single(url: str, timeout: int = 20, retries: int = 3, use_cache: bool = True):
    logger.debug(f"Resolving URL: {url} | Timeout: {timeout}s | Retries: {retries} | Cache: {use_cache}")
    resolver = TrueLinkResolver(timeout=timeout, max_retries=retries)

    if not resolver.is_supported(url):
        logger.warning(f"Unsupported URL: {url}")
        return {"url": url, "status": "unsupported"}

    try:
        result = await resolver.resolve(url, use_cache=use_cache)
        logger.debug(f"Resolved data for {url}: {result}")
        return {
            "url": url,
            "status": "success",
            "type": type(result).__name__,
            "data": to_serializable(result)
        }
    except Exception as exc:
        logger.exception(f"Error resolving {url}: {exc}")
        return {"url": url, "status": "error", "message": str(exc)}


# ---------- Health Check ----------
@app.get("/health")
async def health():
    logger.debug("Health check endpoint called")
    return {"status": "ok"}


# ---------- Single Resolve ----------
@app.get("/resolve")
async def resolve_url(
    url: str = Query(...),
    timeout: int = Query(20),
    retries: int = Query(3),
    cache: bool = Query(True)
):
    result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
    if result.get("status") == "error":
        logger.error(f"Resolve failed for {url}: {result.get('message')}")
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


# ---------- Batch Resolve ----------
@app.post("/resolve-batch")
async def resolve_batch(
    payload: BatchRequest,
    timeout: int = Query(20),
    retries: int = Query(3),
    cache: bool = Query(True)
):
    urls = payload.urls
    logger.debug(f"Batch resolve request for {len(urls)} URLs")
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    sem = asyncio.Semaphore(8)

    async def sem_task(u):
        async with sem:
            return await resolve_single(u, timeout=timeout, retries=retries, use_cache=cache)

    results = await asyncio.gather(*(sem_task(u) for u in urls))
    return {"count": len(results), "results": results}


# ---------- Supported Domains ----------
@app.get("/supported-domains")
async def supported_domains():
    try:
        domains = TrueLinkResolver.get_supported_domains()
        logger.debug(f"Supported domains: {domains}")
        return {"count": len(domains), "domains": domains}
    except Exception as exc:
        logger.exception("Error listing supported domains")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/help")
async def help_page():
    """
    Returns a list of available API endpoints with descriptions.
    """
    return {
        "api": "Advanced TrueLink API v2.1",
        "description": "Resolve URLs to direct download links using TrueLink.",
        "endpoints": {
            "/health": "Check API status.",
            "/resolve": "Resolve a single URL. Query: url, timeout, retries, cache",
            "/resolve-batch": "Resolve multiple URLs in one request (POST). Body: { urls: [..] }",
            "/supported-domains": "List all supported domains.",
            "/direct": "Get only the extracted direct download links for a URL.",
            "/redirect": "Redirect directly to the first resolved direct link.",
            "/download-stream": "Stream the resolved direct link content to the client.",
            "/help": "Show this help page."
        },
        "note": "For detailed parameters and response formats, visit /docs"
    }


# ---------- Direct Link Extraction ----------
def extract_direct_links(resolved_data: dict) -> list[str]:
    links = []
    possible_fields = ["direct_links", "files", "items", "url", "download_url", "direct_url", "links"]

    def walk(obj):
        if not obj:
            return
        if isinstance(obj, str) and obj.startswith("http"):
            links.append(obj)
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in possible_fields and v:
                    if isinstance(v, (list, tuple)):
                        for it in v:
                            walk(it)
                    else:
                        walk(v)
                else:
                    walk(v)
        elif isinstance(obj, (list, tuple, set)):
            for it in obj:
                walk(it)

    walk(resolved_data.get("data") or resolved_data)
    unique_links = list(dict.fromkeys(links))
    logger.debug(f"Extracted direct links: {unique_links}")
    return unique_links


# ---------- Direct Links ----------
@app.get("/direct")
async def get_direct(
    url: str = Query(...),
    timeout: int = Query(20),
    retries: int = Query(3),
    cache: bool = Query(True)
):
    result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to resolve"))
    direct_links = extract_direct_links(result)
    return {"url": url, "direct_links": direct_links, "count": len(direct_links)}


# ---------- Redirect ----------
@app.get("/redirect")
async def redirect_to_direct(
    url: str = Query(...),
    timeout: int = Query(20),
    retries: int = Query(3),
    cache: bool = Query(True)
):
    result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
    direct_links = extract_direct_links(result)
    if not direct_links:
        raise HTTPException(status_code=404, detail="No direct links found")
    return RedirectResponse(direct_links[0])


# ---------- Download Stream ----------
@app.get("/download-stream")
async def download_stream(
    url: str = Query(...),
    timeout: int = Query(60),
    retries: int = Query(3),
    cache: bool = Query(True)
):
    result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
    direct_links = extract_direct_links(result)
    if not direct_links:
        raise HTTPException(status_code=404, detail="No direct links found")

    first = direct_links[0]
    logger.debug(f"Starting streaming download from {first}")

    session_timeout = aiohttp.ClientTimeout(total=None, sock_connect=timeout, sock_read=timeout)
    async_session = aiohttp.ClientSession(timeout=session_timeout)
    try:
        resp = await async_session.get(first)
    except Exception as exc:
        await async_session.close()
        logger.exception(f"Error fetching direct URL: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))

    if resp.status != 200:
        await async_session.close()
        raise HTTPException(status_code=resp.status, detail=f"Upstream returned {resp.status}")

    headers = {}
    if resp.headers.get("Content-Type"):
        headers["Content-Type"] = resp.headers["Content-Type"]
    if resp.headers.get("Content-Length"):
        headers["Content-Length"] = resp.headers["Content-Length"]

    async def stream_generator():
        try:
            async for chunk in resp.content.iter_chunked(1024 * 64):
                yield chunk
        finally:
            await resp.release()
            await async_session.close()

    return StreamingResponse(stream_generator(), headers=headers)
