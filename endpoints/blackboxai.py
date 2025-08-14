"""
Blackbox AI API - Unified Access for Chat, Image, and PDF
"""
import logging
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)
router = APIRouter()

# Set your Blackbox API key here
BLACKBOX_API_KEY = "sk-HdAIUyoPn08GMxTMEhN4bA"

# ============================
# Pydantic Models
# ============================

class ChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = "blackboxai/deepseek/deepseek-chat:free"

class ChatResponse(BaseModel):
    status: str
    result: dict

class ImageResponse(BaseModel):
    status: str
    result: dict

class PDFResponse(BaseModel):
    status: str
    result: dict
    
FREE_MODELS = [
    "blackboxai/qwen/qwq-32b:free",
    "blackboxai/mistralai/mistral-nemo:free",
    "blackboxai/deepseek/deepseek-r1-0528:free",
    "blackboxai/qwen/qwen3-30b-a3b:free",
    "blackboxai/deepseek/deepseek-v3-base:free",
    "blackboxai/mistralai/mistral-small-24b-instruct-2501:free",
    "blackboxai/agentica-org/deepcoder-14b-preview:free",
    "blackboxai/deepseek/deepseek-r1-distill-llama-70b:free",
    "blackboxai/tngtech/deepseek-r1t-chimera:free",
    "blackboxai/sarvamai/sarvam-m:free",
    "blackboxai/microsoft/mai-ds-r1:free",
    "blackboxai/openrouter/cypher-alpha:free",
    "blackboxai/meta-llama/llama-3.2-11b-vision-instruct:free",
    "blackboxai/moonshotai/kimi-dev-72b:free",
    "blackboxai/cognitivecomputations/dolphin3.0-mistral-24b:free",
    "blackboxai/qwen/qwen3-14b:free",
    "blackboxai/thudm/glm-z1-32b:free",
    "blackboxai/nousresearch/deephermes-3-llama-3-8b-preview:free",
    "blackboxai/google/gemma-3-4b-it:free",
    "blackboxai/deepseek/deepseek-chat:free",
    "blackboxai/meta-llama/llama-4-scout:free",
    "blackboxai/mistralai/mistral-small-3.1-24b-instruct:free",
    "blackboxai/qwen/qwen-2.5-72b-instruct:free",
    "blackboxai/qwen/qwen3-32b:free",
    "blackboxai/qwen/qwen2.5-vl-32b-instruct:free",
    "blackboxai/deepseek/deepseek-r1:free",
    "blackboxai/mistralai/mistral-7b-instruct:free",
    "blackboxai/cognitivecomputations/dolphin3.0-r1-mistral-24b:free",
    "blackboxai/google/gemma-2-9b-it:free",
    "blackboxai/thudm/glm-4-32b:free",
    "blackboxai/deepseek/deepseek-r1-distill-qwen-14b:free",
    "blackboxai/google/gemma-3n-e4b-it:free",
    "blackboxai/deepseek/deepseek-chat-v3-0324:free",
    "blackboxai/nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
    "blackboxai/meta-llama/llama-4-maverick:free",
    "blackboxai/qwen/qwen3-8b:free",
    "blackboxai/google/gemma-3-12b-it:free",
    "blackboxai/google/gemini-2.0-flash-exp:free",
    "blackboxai/qwen/qwen2.5-vl-72b-instruct:free",
    "blackboxai/shisa-ai/shisa-v2-llama3.3-70b:free",
    "blackboxai/mistralai/mistral-small-3.2-24b-instruct:free",
    "blackboxai/arliai/qwq-32b-arliai-rpr-v1:free",
    "blackboxai/deepseek/deepseek-r1-0528-qwen3-8b:free",
    "blackboxai/qwen/qwen3-235b-a22b:free",
    "blackboxai/google/gemma-3-27b-it:free",
    "blackboxai/nvidia/llama-3.3-nemotron-super-49b-v1:free",
    "blackboxai/meta-llama/llama-3.3-70b-instruct:free",
    "blackboxai/qwen/qwen-2.5-coder-32b-instruct:free",
    "blackboxai/featherless/qwerky-72b:free",
    "blackboxai/rekaai/reka-flash-3:free",
    "blackboxai/moonshotai/kimi-vl-a3b-thinking:free",
    "blackboxai/mistralai/devstral-small:free"
]



# ============================
# Helper: Call Blackbox API
# ============================
async def blackbox_request(endpoint: str, payload: dict = None, files: dict = None):
    url = f"https://api.blackbox.ai/api/{endpoint}"
    headers = {
        "Authorization": f"Bearer {BLACKBOX_API_KEY}"
    }

    try:
        async with aiohttp.ClientSession() as session:
            if files:
                form_data = aiohttp.FormData()
                for k, v in payload.items():
                    form_data.add_field(k, str(v))
                for name, file_obj in files.items():
                    form_data.add_field(name, file_obj[1], filename=file_obj[0], content_type=file_obj[2])
                async with session.post(url, headers=headers, data=form_data) as resp:
                    data = await resp.json()
            else:
                async with session.post(url, headers=headers, json=payload) as resp:
                    data = await resp.json()

        return data

    except Exception as e:
        logger.error(f"Blackbox API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Blackbox API request failed: {str(e)}"
        )


# ============================
# Endpoints
# ============================
# List all free models
@router.get("/blackboxai/models/free")
async def list_free_models():
    return {"status": "success", "models": FREE_MODELS}

@router.post("/blackbox/chat", response_model=ChatResponse)
async def blackbox_chat(request: ChatRequest):
    """
    Send a text prompt to Blackbox AI (chat models only).
    """
    logger.info(f"Blackbox Chat request: {request.model}")
    result = await blackbox_request("chat", {"prompt": request.prompt, "model": request.model})

    return {"status": "success", "result": result}


@router.post("/blackbox/image", response_model=ImageResponse)
async def blackbox_image(
    prompt: str = Form(...),
    model: Optional[str] = Form("blackboxai/mistralai/mistral-small-3.2-24b-instruct:free"),
    file: Optional[UploadFile] = File(None)
):
    """
    Send a text + optional image to Blackbox AI image endpoint.
    """
    files = None
    if file:
        files = {
            "file": (file.filename, await file.read(), file.content_type or "application/octet-stream")
        }

    logger.info(f"Blackbox Image request: {model}")
    result = await blackbox_request("image", {"prompt": prompt, "model": model}, files)

    return {"status": "success", "result": result}


@router.post("/blackbox/pdf", response_model=PDFResponse)
async def blackbox_pdf(
    prompt: str = Form(...),
    model: Optional[str] = Form("blackboxai/deepseek/deepseek-r1:free"),
    file: UploadFile = File(...)
):
    """
    Send a PDF + prompt to Blackbox AI PDF endpoint.
    """
    files = {
        "file": (file.filename, await file.read(), file.content_type or "application/pdf")
    }

    logger.info(f"Blackbox PDF request: {model}")
    result = await blackbox_request("pdf", {"prompt": prompt, "model": model}, files)

    return {"status": "success", "result": result}
