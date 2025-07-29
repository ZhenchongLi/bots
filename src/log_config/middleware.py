from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
import time
import orjson as json
import structlog
from typing import Dict, Any, Optional
import asyncio

from src.database.connection import AsyncSessionLocal
from src.database.repository import RequestLogRepository


logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Skip logging for health check endpoints
        if request.url.path == "/health":
            return await call_next(request)
        
        # Extract request information
        client_ip = self.get_client_ip(request)
        method = request.method
        path = str(request.url.path)
        query_params = dict(request.query_params)
        headers = dict(request.headers)
        
        # Read request body
        request_body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    request_body = json.loads(body.decode())
            except:
                request_body = None
                
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Extract response information
        response_headers = dict(response.headers)
        response_status = response.status_code
        
        # Read response body for JSON responses
        response_body = None
        if (
            hasattr(response, 'body') 
            and response_headers.get("content-type", "").startswith("application/json")
        ):
            try:
                if hasattr(response, 'body'):
                    response_body = json.loads(response.body.decode())
            except:
                response_body = None
        
        # Log to structured logger
        await self.log_to_structlog(
            method=method,
            path=path,
            client_ip=client_ip,
            request_headers=headers,
            request_body=request_body,
            response_status=response_status,
            response_headers=response_headers,
            response_body=response_body,
            processing_time=processing_time,
        )
        
        # Log to database
        await self.log_to_database(
            method=method,
            path=path,
            client_ip=client_ip,
            request_headers=headers,
            request_body=request_body,
            response_status=response_status,
            response_headers=response_headers,
            response_body=response_body,
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
    
    async def log_to_structlog(
        self,
        method: str,
        path: str,
        client_ip: Optional[str],
        request_headers: Dict[str, str],
        request_body: Optional[Dict[str, Any]],
        response_status: int,
        response_headers: Dict[str, str],
        response_body: Optional[Dict[str, Any]],
        processing_time: float,
    ):
        logger.info(
            "API Request",
            method=method,
            path=path,
            client_ip=client_ip,
            response_status=response_status,
            processing_time=processing_time,
            request_headers=request_headers,
            request_body=request_body,
            response_headers=response_headers,
            response_body=response_body,
        )
    
    async def log_to_database(
        self,
        method: str,
        path: str,
        client_ip: Optional[str],
        request_headers: Dict[str, str],
        request_body: Optional[Dict[str, Any]],
        response_status: int,
        response_headers: Dict[str, str],
        response_body: Optional[Dict[str, Any]],
        processing_time: float,
    ):
        try:
            async with AsyncSessionLocal() as session:
                repo = RequestLogRepository(session)
                await repo.create_log(
                    method=method,
                    path=path,
                    client_ip=client_ip,
                    request_headers=request_headers,
                    request_body=request_body,
                    response_status=response_status,
                    response_headers=response_headers,
                    response_body=response_body,
                    processing_time=processing_time,
                )
        except Exception as e:
            logger.error("Failed to log to database", error=str(e))