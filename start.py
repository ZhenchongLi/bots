#!/usr/bin/env python3
"""
Startup script for the OpenAI API Proxy service.
"""
import uvicorn
import os
from src.config.settings import settings


def main():
    """Start the uvicorn server with proper configuration."""
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        workers=1,  # Use 1 worker for SQLite compatibility
        access_log=True,
        use_colors=True,
    )


if __name__ == "__main__":
    main()