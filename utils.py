"""
Utility functions for TrueLink API
"""
import json
import logging
import time
from typing import Any, Dict, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    """
    Validate if a string is a proper URL.
    
    Args:
        url: String to validate
        
    Returns:
        bool: True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ('http', 'https')
    except Exception:
        return False

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file operations.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]
    
    return filename or 'unnamed_file'

def format_bytes(bytes_count: int) -> str:
    """
    Format bytes into human readable format.
    
    Args:
        bytes_count: Number of bytes
        
    Returns:
        str: Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"

def calculate_processing_time(start_time: float) -> float:
    """
    Calculate processing time from start time.
    
    Args:
        start_time: Start time from time.time()
        
    Returns:
        float: Processing time in seconds
    """
    return round(time.time() - start_time, 3)

def extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: URL string
        
    Returns:
        str: Domain name
    """
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return "unknown"

def safe_json_serialize(obj: Any) -> Any:
    """
    Safely serialize objects to JSON-compatible format.
    
    Args:
        obj: Object to serialize
        
    Returns:
        Any: JSON-serializable object
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [safe_json_serialize(item) for item in obj]
    if hasattr(obj, "dict"):
        try:
            return safe_json_serialize(obj.dict())
        except Exception as e:
            logger.debug(f"Serialization error on dict(): {e}")
            return str(obj)
    if isinstance(obj, dict):
        return {str(k): safe_json_serialize(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {
            k: safe_json_serialize(v) 
            for k, v in obj.__dict__.items() 
            if not k.startswith("_")
        }
    try:
        return json.loads(json.dumps(obj, default=str))
    except (TypeError, ValueError):
        return str(obj)

class PerformanceMonitor:
    """Simple performance monitoring utility."""
    
    def __init__(self):
        self.start_time = time.time()
        self.checkpoints = {}
    
    def checkpoint(self, name: str) -> float:
        """Add a checkpoint and return elapsed time."""
        elapsed = time.time() - self.start_time
        self.checkpoints[name] = elapsed
        return elapsed
    
    def get_summary(self) -> Dict[str, float]:
        """Get performance summary."""
        return {
            "total_time": time.time() - self.start_time,
            "checkpoints": self.checkpoints.copy()
        }