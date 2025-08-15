from fastapi import APIRouter, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
import aiohttp
import os

router = APIRouter()

BLACKBOX_MODELS = [
    "blackboxai/microsoft/mai-ds-r1:free",
    "blackboxai/google/gemma-3-4b-it:free",
    "blackboxai/featherless/qwerky-72b:free",
    "blackboxai/google/gemma-2-9b-it:free",
    "blackboxai/thudm/glm-4-32b:free",
    "blackboxai/cognitivecomputations/dolphin3.0-mistral-24b:free",
    "blackboxai/deepseek/deepseek-chat-v3-0324:free",
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
BLACKBOX_API_KEY = os.getenv("BLACKBOX_API_KEY")  # Store in environment variable

HEADERS = {
    "Authorization": f"Bearer {BLACKBOX_API_KEY}"
}

@router.get("/models")
async def list_models():
    return {"models": BLACKBOX_MODELS}

@router.post("/text")
async def blackbox_text(
    prompt: str = Form(...),
    model: str = Query(default="blackboxai/mistralai/mistral-nemo:free")
):
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.post(f"{BLACKBOX_API_URL}/chat", json=payload) as resp:
            data = await resp.json()
    return data

@router.post("/image")
async def blackbox_image(
    prompt: str = Form(...),
    file: UploadFile = File(...)
):
    form_data = aiohttp.FormData()
    form_data.add_field("prompt", prompt)
    form_data.add_field(
        "file", await file.read(),
        filename=file.filename,
        content_type=file.content_type
    )

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.post(f"{BLACKBOX_API_URL}/image", data=form_data) as resp:
            result = await resp.json()
    return result

@router.post("/pdf")
async def blackbox_pdf(
    prompt: str = Form(...),
    file: UploadFile = File(...)
):
    form_data = aiohttp.FormData()
    form_data.add_field("prompt", prompt)
    form_data.add_field(
        "file", await file.read(),
        filename=file.filename,
        content_type=file.content_type
    )

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.post(f"{BLACKBOX_API_URL}/pdf", data=form_data) as resp:
            result = await resp.json()
    return result
