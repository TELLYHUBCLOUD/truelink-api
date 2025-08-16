"""
Configuration management for TrueLink API
"""
import os
import time
from typing import List

# Try to import truelink, fallback if not available
try:
    from truelink import TrueLinkResolver
    TRUELINK_AVAILABLE = True
except ImportError:
    TRUELINK_AVAILABLE = False

# Global variables
app_start_time = time.time()

class Config:
    """Application configuration with environment variable support"""
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "25"))
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "20"))
    MAX_TIMEOUT = int(os.getenv("MAX_TIMEOUT", "120"))
    CONCURRENT_LIMIT = int(os.getenv("CONCURRENT_LIMIT", "5"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "65536"))
    ENABLE_CORS = os.getenv("ENABLE_CORS", "true").lower() == "true"
    TRUSTED_HOSTS = [host.strip() for host in os.getenv("TRUSTED_HOSTS", "*").split(",")]
    
    # Security settings
    MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "10485760"))  # 10MB
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # 1 hour
    
    # API Keys (should be set via environment)
    BLACKBOX_API_KEY = os.getenv("BLACKBOX_API_KEY")
    
    # Sensitive data (move to environment variables)
    LARAVEL_SESSION = os.getenv("LARAVEL_SESSION")
    XSRF_TOKEN = os.getenv("XSRF_TOKEN")
    GDTOT_CRYPT = os.getenv("GDTOT_CRYPT")
    HUBDRIVE_CRYPT = os.getenv("HUBDRIVE_CRYPT")
    DRIVEFIRE_CRYPT = os.getenv("DRIVEFIRE_CRYPT")
    KATDRIVE_CRYPT = os.getenv("KATDRIVE_CRYPT")
    DIRECT_INDEX = os.getenv("DIRECT_INDEX", "https://tellymirror.tellymirror.workers.dev")
    TERA_COOKIE = os.getenv("TERA_COOKIE")

    @classmethod
    def validate(cls):
        """Validate configuration values"""
        if cls.MAX_BATCH_SIZE <= 0:
            raise ValueError("MAX_BATCH_SIZE must be positive")
        if cls.DEFAULT_TIMEOUT <= 0:
            raise ValueError("DEFAULT_TIMEOUT must be positive")
        if cls.MAX_TIMEOUT < cls.DEFAULT_TIMEOUT:
            raise ValueError("MAX_TIMEOUT must be >= DEFAULT_TIMEOUT")
        if cls.CONCURRENT_LIMIT <= 0:
            raise ValueError("CONCURRENT_LIMIT must be positive")


# Validate configuration on startup
Config.validate()
