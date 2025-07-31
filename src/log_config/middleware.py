from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import structlog
from typing import Optional


logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Skip logging for health check endpoints
        if request.url.path == "/health":
            return await call_next(request)
        
        # Extract basic request information only
        client_ip = self.get_client_ip(request)
        method = request.method
        path = str(request.url.path)
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log basic request info only (no user session data)
        logger.info(
            "API Request",
            method=method,
            path=path,
            client_ip=client_ip,
            response_status=response.status_code,
            processing_time=processing_time,
        )
        
        return response
    
    def get_client_ip(self, request: Request) -> Optional[str]:
        # Try to get real IP from common headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
            
        return request.client.host if request.client else None
    
    # Removed detailed logging methods - only basic request info is logged now