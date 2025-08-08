import asyncio
import logging
from typing import Any
from fastapi import FastAPI, Query, Body, HTTPException
from pydantic import BaseModel
from truelink import TrueLinkResolver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("truelink-api")

app = FastAPI(title="Advanced TrueLink API", version="2.0", docs_url="/docs")

class BatchRequest(BaseModel):
    urls: list[str]

def to_serializable(obj: Any):
    """
    Convert LinkResult/FolderResult/FileItem or arbitrary objects to serializable dicts.
    Tries several heuristics: __dict__, dataclasses, lists, tuples, primitives.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(i) for i in obj]
    # Pydantic models
    if hasattr(obj, "dict"):
        try:
            return to_serializable(obj.dict())
        except Exception:
            pass
    # dict-like
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    # Generic object with __dict__
    if hasattr(obj, "__dict__"):
        return {k: to_serializable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    # Fallback to string
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
    # Limit concurrency to avoid blasting providers
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

# Local run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=10000, reload=True)
