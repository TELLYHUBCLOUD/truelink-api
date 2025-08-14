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
BLACKBOX_API_KEY = "YOUR_BLACKBOX_API_KEY"

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
