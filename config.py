"""
Configuration management for TrueLink API
"""
import os
from typing import List

class Settings:
    """Application settings with environment variable support."""
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # API Limits
    MAX_BATCH_SIZE: int = int(os.getenv("MAX_BATCH_SIZE", "50"))
    DEFAULT_TIMEOUT: int = int(os.getenv("DEFAULT_TIMEOUT", "20"))
    MAX_TIMEOUT: int = int(os.getenv("MAX_TIMEOUT", "120"))
    CONCURRENT_LIMIT: int = int(os.getenv("CONCURRENT_LIMIT", "8"))
    
    # Security
    ENABLE_CORS: bool = os.getenv("ENABLE_CORS", "true").lower() == "true"
    TRUSTED_HOSTS: List[str] = os.getenv("TRUSTED_HOSTS", "*").split(",")
    
    # Performance
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "65536"))  # 64KB
    CONNECTION_POOL_SIZE: int = int(os.getenv("CONNECTION_POOL_SIZE", "100"))
    
    # Cache (for future implementation)
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    
    @classmethod
    def validate(cls) -> None:
        """Validate configuration values."""
        if cls.MAX_BATCH_SIZE <= 0:
            raise ValueError("MAX_BATCH_SIZE must be positive")
        if cls.DEFAULT_TIMEOUT <= 0:
            raise ValueError("DEFAULT_TIMEOUT must be positive")
        if cls.MAX_TIMEOUT < cls.DEFAULT_TIMEOUT:
            raise ValueError("MAX_TIMEOUT must be >= DEFAULT_TIMEOUT")
        if cls.CONCURRENT_LIMIT <= 0:
            raise ValueError("CONCURRENT_LIMIT must be positive")

# Validate settings on import
Settings.validate()