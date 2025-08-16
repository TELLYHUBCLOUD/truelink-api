from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from fastapi.responses import JSONResponse
import aiohttp
import logging


logger = logging.getLogger(__name__)
router = APIRouter()

# Deduplicated model list
BLACKBOX_MODELS = [
    "blackboxai/microsoft/mai-ds-r1:free",
    "blackboxai/google/gemma-3-4b-it:free",
    "blackboxai/featherless/qwerky-72b:free",
    "blackboxai/google/gemma-2-9b-it:free",
    "blackboxai/thudm/glm-4-32b:free",
    "blackboxai/cognitivecomputations/dolphin3.0-mistral-24b:free",
    "blackboxai/deepseek/deepseek-chat-v3-0324:free",
    "blackboxai/openrouter/cypher-alpha:free",
    "blackboxai/google/gemma-3-12b-it:free",
    "blackboxai/meta-llama/llama-3.3-70b-instruct:free",
    "blackboxai/deepseek/deepseek-r1-0528:free",
    "blackboxai/tngtech/deepseek-r1t-chimera:free",
    "blackboxai/qwen/qwen2.5-vl-72b-instruct:free",
    "blackboxai/nousresearch/deephermes-3-llama-3-8b-preview:free",
    "blackboxai/qwen/qwen2.5-vl-32b-instruct:free",
    "blackboxai/nvidia/llama-3.3-nemotron-super-49b-v1:free",
    "blackboxai/google/gemma-3n-e4b-it:free",
    "blackboxai/meta-llama/llama-4-scout:free",
    "blackboxai/mistralai/mistral-7b-instruct:free",
    "blackboxai/deepseek/deepseek-r1-0528-qwen3-8b:free",
    "blackboxai/shisa-ai/shisa-v2-llama3.3-70b:free",
    "blackboxai/qwen/qwen3-8b:free",
    "blackboxai/mistralai/mistral-small-24b-instruct-2501:free",
    "blackboxai/meta-llama/llama-4-maverick:free",
    "blackboxai/arliai/qwq-32b-arliai-rpr-v1:free",
    "blackboxai/moonshotai/kimi-vl-a3b-thinking:free",
    "blackboxai/cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
    "blackboxai/moonshotai/kimi-dev-72b:free",
    "blackboxai/qwen/qwen-2.5-72b-instruct:free",
    "blackboxai/deepseek/deepseek-chat:free",
    "blackboxai/meta-llama/llama-3.2-11b-vision-instruct:free",
    "blackboxai/mistralai/mistral-small-3.2-24b-instruct:free",
    "blackboxai/qwen/qwen3-14b:free",
    "blackboxai/mistralai/devstral-small:free",
    "blackboxai/qwen/qwen-2.5-coder-32b-instruct:free",
    "blackboxai/thudm/glm-z1-32b:free",
    "blackboxai/nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
    "blackboxai/sarvamai/sarvam-m:free",
    "blackboxai/qwen/qwen3-30b-a3b:free",
    "blackboxai/qwen/qwen3-235b-a22b:free",
    "blackboxai/deepseek/deepseek-v3-base:free",
    "blackboxai/deepseek/deepseek-r1-distill-llama-70b:free",
    "blackboxai/qwen/qwen3-32b:free",
    "blackboxai/deepseek/deepseek-r1:free",
    "blackboxai/mistralai/mistral-small-3.1-24b-instruct:free",
    "blackboxai/agentica-org/deepcoder-14b-preview:free",
    "blackboxai/google/gemini-2.0-flash-exp:free",
    "blackboxai/rekaai/reka-flash-3:free",
    "blackboxai/deepseek/deepseek-r1-distill-qwen-14b:free",
    "blackboxai/google/gemma-3-27b-it:free",
    "blackboxai/qwen/qwq-32b:free",
    "blackboxai/mistralai/mistral-nemo:free"
]

BLACKBOX_API_URL = "https://api.blackbox.ai/api"

import os

def get_headers():
    """Dynamically get headers with API key from environment"""
    api_key = os.getenv("BLACKBOX_API_KEY")
    if not api_key:
        logger.error("BLACKBOX_API_KEY environment variable not set")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error"
        )
    return {"Authorization": f"Bearer {api_key}"}

@router.get("/models")
async def list_models():
    return {"models": BLACKBOX_MODELS}

@router.post("/text")
async def blackbox_text(
    prompt: str = Form(...),
    model: str = Query(default="blackboxai/mistralai/mistral-nemo:free")
):
    # Validate requested model
    if model not in BLACKBOX_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model. Use /models to see available options"
        )
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        headers = get_headers()
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                f"{BLACKBOX_API_URL}/chat", 
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    error_detail = await resp.text()
                    logger.error(f"Blackbox API error: {resp.status} - {error_detail}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"Blackbox API responded with error: {error_detail}"
                    )
                return await resp.json()
                
    except aiohttp.ClientError as e:
        logger.exception("Network error during Blackbox API call")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )

async def handle_file_upload(endpoint: str, prompt: str, file: UploadFile):
    """Generic file upload handler for Blackbox APIs"""
    # Validate file size (max 10MB)
    file.file.seek(0, 2)  # Go to end of file
    file_size = file.file.tell()
    file.file.seek(0)  # Reset file position
    
    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=413,
            detail="File too large. Max size is 10MB"
        )
        
    form_data = aiohttp.FormData()
    form_data.add_field("prompt", prompt)
    form_data.add_field(
        "file", 
        await file.read(),
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream"
    )
    
    try:
        headers = get_headers()
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                f"{BLACKBOX_API_URL}/{endpoint}",
                data=form_data,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    error_detail = await resp.text()
                    logger.error(f"Blackbox {endpoint} API error: {resp.status} - {error_detail}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"Blackbox API error: {error_detail}"
                    )
                return await resp.json()
                
    except aiohttp.ClientError as e:
        logger.exception(f"Network error during Blackbox {endpoint} API call")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )

@router.post("/image")
async def blackbox_image(
    prompt: str = Form(...),
    file: UploadFile = File(...)
):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Only image files are supported"
        )
        
    return await handle_file_upload("image", prompt, file)

@router.post("/pdf")
async def blackbox_pdf(
    prompt: str = Form(...),
    file: UploadFile = File(...)
):
    # Validate file type
    if file.content_type != "application/pdf":
        # Check filename as fallback
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
    
    return await handle_file_upload("pdf", prompt, file)
