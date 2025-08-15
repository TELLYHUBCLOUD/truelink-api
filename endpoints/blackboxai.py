"""
BlackBox AI endpoint for code generation and AI assistance
"""
import time
import logging
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
import aiohttp

logger = logging.getLogger(__name__)
router = APIRouter()

# BlackBox AI API Base URL
BLACKBOXAI_BASE_URL = "https://www.blackbox.ai/api"

class BlackBoxAIRequest(BaseModel):
    """Request model for BlackBox AI"""
    query: str = Field(..., min_length=1, max_length=2000, description="Query or code request")
    language: Optional[str] = Field("python", description="Programming language")
    mode: Optional[str] = Field("code", description="Response mode: code, explain, debug, optimize")

class BlackBoxAIResponse(BaseModel):
    """Response model for BlackBox AI"""
    success: bool = Field(..., description="Request success status")
    data: Optional[Dict[str, Any]] = Field(None, description="AI response data")
    message: Optional[str] = Field(None, description="Error message if any")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    query: Optional[str] = Field(None, description="Original query")
    language: Optional[str] = Field(None, description="Programming language used")

async def make_blackboxai_request(endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make request to BlackBox AI API with error handling"""
    url = f"{BLACKBOXAI_BASE_URL}/{endpoint.lstrip('/')}"
    
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        try:
            if data:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"BlackBox AI API error: HTTP {response.status}"
                        )
            else:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"BlackBox AI API error: HTTP {response.status}"
                        )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="BlackBox AI API timeout - please try again"
            )
        except aiohttp.ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"BlackBox AI API unavailable: {str(e)}"
            )

@router.post("/blackboxai/generate", response_model=BlackBoxAIResponse)
async def blackboxai_generate_code(request: BlackBoxAIRequest):
    """Generate code using BlackBox AI"""
    start_time = time.time()
    
    try:
        logger.info(f"BlackBox AI code generation: {request.query[:100]}...")
        
        # Prepare request data
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Generate {request.language} code for: {request.query}"
                }
            ],
            "id": f"blackbox-{int(time.time())}",
            "previewToken": None,
            "userId": None,
            "codeModelMode": True,
            "agentMode": {},
            "trendingAgentMode": {},
            "isMicMode": False,
            "maxTokens": 1024,
            "playgroundTopP": 0.9,
            "playgroundTemperature": 0.1,
            "isChromeExt": False,
            "githubToken": None,
            "clickedAnswer2": False,
            "clickedAnswer3": False,
            "clickedForceWebSearch": False,
            "visitFromDelta": False,
            "mobileClient": False
        }
        
        result = await make_blackboxai_request("chat", request_data)
        processing_time = time.time() - start_time
        
        return BlackBoxAIResponse(
            success=True,
            data=result,
            processing_time=processing_time,
            query=request.query,
            language=request.language
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"BlackBox AI generation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code generation failed: {str(exc)}"
        )

@router.get("/blackboxai/explain", response_model=BlackBoxAIResponse)
async def blackboxai_explain_code(
    code: str = Query(..., min_length=1, max_length=5000, description="Code to explain"),
    language: str = Query("python", description="Programming language")
):
    """Explain code using BlackBox AI"""
    start_time = time.time()
    
    try:
        logger.info(f"BlackBox AI code explanation for {language}")
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Explain this {language} code:\n\n```{language}\n{code}\n```"
                }
            ],
            "id": f"blackbox-explain-{int(time.time())}",
            "previewToken": None,
            "userId": None,
            "codeModelMode": True,
            "agentMode": {},
            "trendingAgentMode": {},
            "isMicMode": False,
            "maxTokens": 1024,
            "playgroundTopP": 0.9,
            "playgroundTemperature": 0.1,
            "isChromeExt": False,
            "githubToken": None,
            "clickedAnswer2": False,
            "clickedAnswer3": False,
            "clickedForceWebSearch": False,
            "visitFromDelta": False,
            "mobileClient": False
        }
        
        result = await make_blackboxai_request("chat", request_data)
        processing_time = time.time() - start_time
        
        return BlackBoxAIResponse(
            success=True,
            data=result,
            processing_time=processing_time,
            query=f"Explain {language} code",
            language=language
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"BlackBox AI explanation error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code explanation failed: {str(exc)}"
        )

@router.get("/blackboxai/debug", response_model=BlackBoxAIResponse)
async def blackboxai_debug_code(
    code: str = Query(..., min_length=1, max_length=5000, description="Code to debug"),
    error: Optional[str] = Query(None, description="Error message if any"),
    language: str = Query("python", description="Programming language")
):
    """Debug code using BlackBox AI"""
    start_time = time.time()
    
    try:
        logger.info(f"BlackBox AI code debugging for {language}")
        
        debug_prompt = f"Debug this {language} code and fix any issues:\n\n```{language}\n{code}\n```"
        if error:
            debug_prompt += f"\n\nError message: {error}"
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": debug_prompt
                }
            ],
            "id": f"blackbox-debug-{int(time.time())}",
            "previewToken": None,
            "userId": None,
            "codeModelMode": True,
            "agentMode": {},
            "trendingAgentMode": {},
            "isMicMode": False,
            "maxTokens": 1024,
            "playgroundTopP": 0.9,
            "playgroundTemperature": 0.1,
            "isChromeExt": False,
            "githubToken": None,
            "clickedAnswer2": False,
            "clickedAnswer3": False,
            "clickedForceWebSearch": False,
            "visitFromDelta": False,
            "mobileClient": False
        }
        
        result = await make_blackboxai_request("chat", request_data)
        processing_time = time.time() - start_time
        
        return BlackBoxAIResponse(
            success=True,
            data=result,
            processing_time=processing_time,
            query=f"Debug {language} code",
            language=language
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"BlackBox AI debugging error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code debugging failed: {str(exc)}"
        )

@router.get("/blackboxai/optimize", response_model=BlackBoxAIResponse)
async def blackboxai_optimize_code(
    code: str = Query(..., min_length=1, max_length=5000, description="Code to optimize"),
    language: str = Query("python", description="Programming language"),
    focus: str = Query("performance", description="Optimization focus: performance, readability, memory")
):
    """Optimize code using BlackBox AI"""
    start_time = time.time()
    
    try:
        logger.info(f"BlackBox AI code optimization for {language} (focus: {focus})")
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Optimize this {language} code for {focus}:\n\n```{language}\n{code}\n```"
                }
            ],
            "id": f"blackbox-optimize-{int(time.time())}",
            "previewToken": None,
            "userId": None,
            "codeModelMode": True,
            "agentMode": {},
            "trendingAgentMode": {},
            "isMicMode": False,
            "maxTokens": 1024,
            "playgroundTopP": 0.9,
            "playgroundTemperature": 0.1,
            "isChromeExt": False,
            "githubToken": None,
            "clickedAnswer2": False,
            "clickedAnswer3": False,
            "clickedForceWebSearch": False,
            "visitFromDelta": False,
            "mobileClient": False
        }
        
        result = await make_blackboxai_request("chat", request_data)
        processing_time = time.time() - start_time
        
        return BlackBoxAIResponse(
            success=True,
            data=result,
            processing_time=processing_time,
            query=f"Optimize {language} code for {focus}",
            language=language
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"BlackBox AI optimization error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code optimization failed: {str(exc)}"
        )

@router.get("/blackboxai/convert", response_model=BlackBoxAIResponse)
async def blackboxai_convert_code(
    code: str = Query(..., min_length=1, max_length=5000, description="Code to convert"),
    from_language: str = Query(..., description="Source programming language"),
    to_language: str = Query(..., description="Target programming language")
):
    """Convert code from one language to another using BlackBox AI"""
    start_time = time.time()
    
    try:
        logger.info(f"BlackBox AI code conversion: {from_language} -> {to_language}")
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Convert this {from_language} code to {to_language}:\n\n```{from_language}\n{code}\n```"
                }
            ],
            "id": f"blackbox-convert-{int(time.time())}",
            "previewToken": None,
            "userId": None,
            "codeModelMode": True,
            "agentMode": {},
            "trendingAgentMode": {},
            "isMicMode": False,
            "maxTokens": 1024,
            "playgroundTopP": 0.9,
            "playgroundTemperature": 0.1,
            "isChromeExt": False,
            "githubToken": None,
            "clickedAnswer2": False,
            "clickedAnswer3": False,
            "clickedForceWebSearch": False,
            "visitFromDelta": False,
            "mobileClient": False
        }
        
        result = await make_blackboxai_request("chat", request_data)
        processing_time = time.time() - start_time
        
        return BlackBoxAIResponse(
            success=True,
            data=result,
            processing_time=processing_time,
            query=f"Convert {from_language} to {to_language}",
            language=to_language
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"BlackBox AI conversion error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code conversion failed: {str(exc)}"
        )

@router.get("/blackboxai/chat", response_model=BlackBoxAIResponse)
async def blackboxai_chat(
    message: str = Query(..., min_length=1, max_length=2000, description="Message to send to BlackBox AI"),
    context: Optional[str] = Query(None, description="Additional context for the conversation")
):
    """General chat with BlackBox AI"""
    start_time = time.time()
    
    try:
        logger.info(f"BlackBox AI chat: {message[:100]}...")
        
        full_message = message
        if context:
            full_message = f"Context: {context}\n\nQuestion: {message}"
        
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": full_message
                }
            ],
            "id": f"blackbox-chat-{int(time.time())}",
            "previewToken": None,
            "userId": None,
            "codeModelMode": False,
            "agentMode": {},
            "trendingAgentMode": {},
            "isMicMode": False,
            "maxTokens": 1024,
            "playgroundTopP": 0.9,
            "playgroundTemperature": 0.7,
            "isChromeExt": False,
            "githubToken": None,
            "clickedAnswer2": False,
            "clickedAnswer3": False,
            "clickedForceWebSearch": False,
            "visitFromDelta": False,
            "mobileClient": False
        }
        
        result = await make_blackboxai_request("chat", request_data)
        processing_time = time.time() - start_time
        
        return BlackBoxAIResponse(
            success=True,
            data=result,
            processing_time=processing_time,
            query=message
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"BlackBox AI chat error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(exc)}"
        )