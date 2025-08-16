"""
Utility functions for TrueLink API
"""
import os
import asyncio
import logging
import time
import json
import psutil
from typing import Any, Optional, Dict, List
from urllib.parse import urlparse
import requests

from config import TRUELINK_AVAILABLE, Config

if TRUELINK_AVAILABLE:
    try:
        from truelink import TrueLinkResolver
    except ImportError:
        TrueLinkResolver = None

logger = logging.getLogger(__name__)

import re
from urllib.parse import urlparse, parse_qs

def is_valid_url(url: str) -> bool:
    """Validate if a string is a proper URL"""
    try:
        # Basic sanitization
        url = url.strip()
        if len(url) > 2048:  # Reasonable URL length limit
            return False
            
        # Check for malicious patterns
        malicious_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'file:',
            r'ftp:'
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
                
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ('http', 'https')
    except Exception:
        return False

def get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage statistics"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss,
            "vms": memory_info.vms,
            "percent": process.memory_percent(),
            "available": psutil.virtual_memory().available,
            "total": psutil.virtual_memory().total
        }
    except Exception as e:
        logger.warning(f"Could not get memory usage: {e}")
        return {}

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    try:
        return {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(),
            "disk_usage": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free
            }
        }
    except Exception as e:
        logger.warning(f"Could not get system info: {e}")
        return {}

def to_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format with improved error handling"""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): to_serializable(v) for k, v in obj.items()}
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return to_serializable(obj.dict())
        except Exception as e:
            logger.debug(f"Serialization error on dict(): {e}")
            return str(obj)
    if hasattr(obj, "__dict__"):
        return {
            k: to_serializable(v) 
            for k, v in obj.__dict__.items() 
            if not k.startswith("_")
        }
    try:
        return json.loads(json.dumps(obj, default=str))
    except (TypeError, ValueError, RecursionError):
        return str(obj)

def validate_timeout(timeout: int) -> int:
    """Validate and clamp timeout value"""
    return max(1, min(timeout, Config.MAX_TIMEOUT))

def validate_retries(retries: int) -> int:
    """Validate and clamp retries value"""
    return max(0, min(retries, 10))

def extract_direct_links(resolved_data: Dict[str, Any]) -> List[str]:
    """Extract direct download links from resolved data with improved logic"""
    links = set()  # Use set to avoid duplicates
    possible_fields = [
        "direct_links", "files", "items", "url", "download_url", 
        "direct_url", "links", "file_url", "download_link", "dl_link",
        "downloadUrl", "direct_link", "dl1", "dl2"
    ]

    def is_valid_download_url(url_str: str) -> bool:
        """Check if string is a valid download URL"""
        if not isinstance(url_str, str):
            return False
        if not url_str.startswith(("http://", "https://")):
            return False
        # Skip invalid protocols and empty URLs
        if any(protocol in url_str.lower() for protocol in ["javascript:", "mailto:", "tel:", "data:"]):
            return False
        if len(url_str.strip()) < 10:  # Too short to be valid URL
            return False
        return True

    def walk_data(obj, depth=0):
        """Recursively walk through data structure to find URLs"""
        if depth > 15:  # Prevent infinite recursion
            return
        
        if not obj:
            return
            
        if is_valid_download_url(obj):
            links.add(obj)
            return
            
        if isinstance(obj, dict):
            for field in possible_fields:
                if field in obj and obj[field]:
                    walk_data(obj[field], depth + 1)
            
            # Also check nested structures
            for k, v in obj.items():
                if k not in possible_fields:
                    walk_data(v, depth + 1)
                    
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                walk_data(item, depth + 1)

    data = resolved_data.get("data", resolved_data)
    walk_data(data)
    
    result_links = list(links)
    logger.debug(f"Extracted {len(result_links)} direct links")
    return result_links

class FallbackResolver:
    """Fallback resolver when TrueLink is not available"""
    
    def __init__(self, timeout: int = 20, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def is_supported(self, url: str) -> bool:
        """Check if URL is supported (basic implementation)"""
        return is_valid_url(url)
    
    async def resolve(self, url: str, use_cache: bool = True) -> Dict[str, Any]:
        """Basic URL resolution"""
        try:
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            return {
                "url": response.url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "final_url": response.url
            }
        except Exception as e:
            raise Exception(f"Failed to resolve URL: {str(e)}")
    
    @staticmethod
    def get_supported_domains() -> List[str]:
        """Return basic supported domains"""
        return ["example.com", "test.com"]  # Placeholder

async def resolve_single(
    url: str, 
    timeout: int = Config.DEFAULT_TIMEOUT, 
    retries: int = 3, 
    use_cache: bool = True
):
    """Resolve a single URL with comprehensive error handling and timing"""
    from models import ResolveResponse
    
    start_time = time.time()
    timeout = validate_timeout(timeout)
    retries = validate_retries(retries)
    
    logger.debug(f"Resolving URL: {url} | Timeout: {timeout}s | Retries: {retries} | Cache: {use_cache}")
    
    try:
        # Use TrueLink if available, otherwise use fallback
        if TRUELINK_AVAILABLE and TrueLinkResolver:
            resolver = TrueLinkResolver(timeout=timeout, max_retries=retries)
        else:
            resolver = FallbackResolver(timeout=timeout, max_retries=retries)
        
        if not resolver.is_supported(url):
            logger.warning(f"Unsupported URL: {url}")
            return ResolveResponse(
                url=url,
                status="unsupported",
                message="URL domain is not supported",
                processing_time=time.time() - start_time
            )

        # Handle async/sync resolver methods
        if TRUELINK_AVAILABLE and hasattr(resolver, 'resolve') and asyncio.iscoroutinefunction(resolver.resolve):
            result = await resolver.resolve(url, use_cache=use_cache)
        else:
            # Run in thread pool for sync operations
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, resolver.resolve, url, use_cache)
        
        processing_time = time.time() - start_time
        
        logger.debug(f"Successfully resolved {url} in {processing_time:.2f}s")
        
        return ResolveResponse(
            url=url,
            status="success",
            type=type(result).__name__,
            data=to_serializable(result),
            processing_time=processing_time
        )
        
    except asyncio.TimeoutError:
        processing_time = time.time() - start_time
        logger.warning(f"Timeout resolving {url} after {processing_time:.2f}s")
        return ResolveResponse(
            url=url,
            status="timeout",
            message=f"Request timed out after {timeout}s",
            processing_time=processing_time
        )
    except Exception as exc:
        processing_time = time.time() - start_time
        logger.exception(f"Error resolving {url}: {exc}")
        return ResolveResponse(
            url=url,
            status="error",
            message=str(exc),
            processing_time=processing_time
        )

async def cleanup_resources(response, session):
    """Helper function to cleanup HTTP resources"""
    try:
        if response and not response.closed:
            response.close()
    except Exception as e:
        logger.error(f"Error closing response: {e}")
    
    try:
        if session and not session.closed:
            await session.close()
    except Exception as e:
        logger.error(f"Error closing session: {e}")
