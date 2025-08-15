"""
Endpoints package for TrueLink API
"""
from .health import router as health_router
from .resolve import router as resolve_router
from .batch import router as batch_router
from .direct import router as direct_router
from .redirect import router as redirect_router
from .download_stream import router as download_stream_router
from .supported_domains import router as supported_domains_router
from .terabox import router as terabox_router
from .root import router as root_router
from .help import router as help_router
from .jiosaavn import router as jiosaavn_router
from .blackboxai import router as blackboxai_router
from .monkeybypass import router as monkeybypass_router 
from .poster import router as poster_router
from .linkvertise import router as linkvertise_router 


__all__ = [
    "health_router",
    "resolve_router", 
    "batch_router",
    "direct_router",
    "redirect_router",
    "download_stream_router",
    "supported_domains_router",
    "terabox_router",
    "root_router",
    "help_router",
    "jiosaavn_router",
    "blackboxai_router",
    "monkeybypass_router",
    "poster_router",
    "linkvertise"
]
