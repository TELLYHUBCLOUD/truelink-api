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
LARAVEL_SESSION = "eyJpdiI6InlqZ3ZrcjBvTEM1NE9jQnpNM3phTlE9PSIsInZhbHVlIjoibThwemlnWEQ5TjYzaklQbmZwYkYyXC8xeEI5aHk3ZG1cL21hQlM5ZDU5RTE1c0EwOWlBUGE4SkVXUmozSkwyYm1CIiwibWFjIjoiZWQ5ZDFkMzdjNmY3ZmY2MDI0NTQ0MGI4ZTY5YjdjNjVlYzU3ZmEyY2ZjNzY2ZTI4ZDcxNjg4NTY5ZjQ4Yzk1ZiJ9"
XSRF_TOKEN = "eyJpdiI6IjIwM2d4XC96U1hhYWNjdUhOSXl4RjRRPT0iLCJ2YWx1ZSI6Ilc5RFBGSTNhTWRvYjlzYkZHZDE0WXk2c3BRMFN1c1hXUVM1MVJnSmdoQm9kblwvdnlIa2YyNnRBVXpQeWd0ZUFKIiwibWFjIjoiMmZlNTNkNGU4YTkzNTQ1OTgyNmUxNzJiYzU4NzQyNGZjZGI3MjE4M2NmYjcxY2RiMWExN2RjNWRmN2M2ZGZkMCJ9"
GDTOT_CRYPT = "b0lDek5LSCt6ZjVRR2EwZnY4T1EvVndqeDRtbCtTWmMwcGNuKy8wYWpDaz0%3D"
HUBDRIVE_CRYPT = "N25hV1pxMXZWUTdFWEh6L2Q2WFJyQWo2NGJEcWN6R2E5ci91aG8zSFF5Zz0%3D"
DRIVEFIRE_CRYPT = "cnhXOGVQNVlpeFZlM2lvTmN6Z2FPVWJiSjVBbWdVN0dWOEpvR3hHbHFLVT0%3D"
KATDRIVE_CRYPT = "bzQySHVKSkY0bEczZHlqOWRsSHZCazBkOGFDak9HWXc1emRTL1F6Rm9ubz0%3D"
DIRECT_INDEX = "https://tellymirror.tellymirror.workers.dev"
TERA_COOKIE = "YvZNLrCteHuiHhOL5JkRGyt7mwk2eJ0crYm0-ZBu"


# Validate configuration on startup
Config.validate()