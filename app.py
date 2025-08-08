import os
import asyncio
import logging
from typing import Any, Optional
from fastapi import FastAPI, Query, Body, HTTPException, Response, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
import aiohttp
from truelink import TrueLinkResolver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("truelink-api")

app = FastAPI(title="Advanced TrueLink API", version="2.1", docs_url="/docs")

port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)


class BatchRequest(BaseModel):
    urls: list[str]

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
        except Exception:
            pass
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {k: to_serializable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return str(obj)

async def resolve_single(url: str, timeout: int = 20, retries: int = 3, use_cache: bool = True):
    resolver = TrueLinkResolver(timeout=timeout, max_retries=retries)
    if not resolver.is_supported(url):
        return {"url": url, "status": "unsupported"}
    try:
        result = await resolver.resolve(url, use_cache=use_cache)
        return {
            "url": url,
            "status": "success",
            "type": type(result).__name__,
            "data": to_serializable(result)
        }
    except Exception as exc:
        logger.exception("Error resolving %s", url)
        return {"url": url, "status": "error", "message": str(exc)}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/resolve")
async def resolve_url(
    url: str = Query(..., description="The URL to resolve"),
    timeout: int = Query(20, description="Timeout in seconds"),
    retries: int = Query(3, description="Max retries"),
    cache: bool = Query(True, description="Use cache (True/False)")
):
    result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result

@app.post("/resolve-batch")
async def resolve_batch(
    payload: BatchRequest = Body(..., description="List of URLs"),
    timeout: int = Query(20),
    retries: int = Query(3),
    cache: bool = Query(True)
):
    urls = payload.urls
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    sem = asyncio.Semaphore(8)

    async def sem_task(u):
        async with sem:
            return await resolve_single(u, timeout=timeout, retries=retries, use_cache=cache)

    tasks = [sem_task(u) for u in urls]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return {"count": len(results), "results": results}

@app.get("/supported-domains")
async def supported_domains():
    try:
        domains = TrueLinkResolver.get_supported_domains()
        return {"count": len(domains), "domains": domains}
    except Exception as exc:
        logger.exception("Error listing supported domains")
        raise HTTPException(status_code=500, detail=str(exc))

# New endpoints for "send direct" functionality

def extract_direct_links(resolved_data: dict) -> list[str]:
    """
    Attempt to extract direct download links from TrueLink result objects.
    This is heuristic — different providers put URLs in different fields.
    """
    links = []
    if not resolved_data or not isinstance(resolved_data, dict):
        return links
    data = resolved_data.get("data") or resolved_data.get("result") or resolved_data
    # Common fields
    possible_fields = ["direct_links", "files", "items", "url", "download_url", "direct_url", "links"]
    def walk(obj):
        if not obj:
            return
        if isinstance(obj, str):
            if obj.startswith("http"):
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
        if isinstance(obj, (list, tuple, set)):
            for it in obj:
                walk(it)
    walk(data)
    # dedupe, preserve order
    seen = set(); out = []
    for l in links:
        if l not in seen:
            seen.add(l); out.append(l)
    return out

@app.get("/direct")
async def get_direct(url: str = Query(..., description="URL to resolve and extract direct links"),
                     timeout: int = Query(20), retries: int = Query(3), cache: bool = Query(True)):
    result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to resolve"))
    direct_links = extract_direct_links(result)
    return {"url": url, "direct_links": direct_links, "count": len(direct_links)}

@app.get("/redirect")
async def redirect_to_direct(url: str = Query(..., description="Resolve and redirect to first direct link"),
                             timeout: int = Query(20), retries: int = Query(3), cache: bool = Query(True)):
    result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to resolve"))
    direct_links = extract_direct_links(result)
    if not direct_links:
        raise HTTPException(status_code=404, detail="No direct links found")
    return RedirectResponse(direct_links[0])

@app.get("/download-stream")
async def download_stream(url: str = Query(..., description="Resolve and stream the file via proxy (careful with bandwidth)"),
                          timeout: int = Query(60), retries: int = Query(3), cache: bool = Query(True)):
    result = await resolve_single(url, timeout=timeout, retries=retries, use_cache=cache)
    if result.get("status") != "success":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to resolve"))
    direct_links = extract_direct_links(result)
    if not direct_links:
        raise HTTPException(status_code=404, detail="No direct links found")

    first = direct_links[0]
    # Stream the first direct link through the server
    session_timeout = aiohttp.ClientTimeout(total=None, sock_connect=timeout, sock_read=timeout)
    async_session = aiohttp.ClientSession(timeout=session_timeout)
    try:
        resp = await async_session.get(first)
    except Exception as exc:
        await async_session.close()
        logger.exception("Error fetching direct URL: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
    if resp.status != 200:
        await async_session.close()
        raise HTTPException(status_code=resp.status, detail=f"Upstream returned {resp.status}")

    headers = {}
    content_type = resp.headers.get("Content-Type")
    if content_type:
        headers["Content-Type"] = content_type
    content_length = resp.headers.get("Content-Length")
    if content_length:
        headers["Content-Length"] = content_length

    async def stream_generator():
        try:
            async for chunk in resp.content.iter_chunked(1024 * 64):
                yield chunk
        finally:
            await resp.release()
            await async_session.close()

    return StreamingResponse(stream_generator(), headers=headers)
