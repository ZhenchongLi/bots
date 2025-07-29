from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any
import orjson as json
import time

from src.core.model_manager import model_manager
from src.core.platform_clients import PlatformClientFactory

router = APIRouter()


@router.get("/models")
async def list_models():
    """List available models in OpenAI API format."""
    models = model_manager.get_models_list()
    return {
        "object": "list",
        "data": models
    }


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "openai-proxy"}


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_openai_request(request: Request, path: str):
    start_time = time.time()
    
    try:
        # Extract request data
        method = request.method
        headers = dict(request.headers)
        query_params = dict(request.query_params)
        
        # Get request body
        json_data = None
        
        if method in ["POST", "PUT", "PATCH"]:
            try:
                json_data = await request.json()
                
                # Process model validation and mapping
                if json_data and isinstance(json_data, dict):
                    try:
                        json_data, actual_model = model_manager.process_model_request(json_data)
                    except ValueError as e:
                        raise HTTPException(status_code=400, detail=str(e))
                        
            except json.JSONDecodeError:
                # Handle non-JSON requests
                pass
        
        # Check if model is available
        if not model_manager.is_model_available():
            raise HTTPException(status_code=503, detail="Model is not available or not configured")
        
        # Get model configuration
        model_config = model_manager.get_model_config()
        
        # Create platform-specific client
        client = PlatformClientFactory.create_client(
            model_config.get("type", "openai"), 
            model_config
        )
        
        # Make request to the appropriate platform API
        response_data = await client.make_request(
            method=method,
            path=f"/{path}",
            headers=headers,
            json_data=json_data,
            params=query_params,
        )
        
        processing_time = time.time() - start_time
        
        # TODO: Log request and response (will be implemented in logging middleware)
        
        # Return response
        if response_data["json"]:
            return JSONResponse(
                content=response_data["json"],
                status_code=response_data["status_code"],
                headers={k: v for k, v in response_data["headers"].items() 
                        if k.lower() not in ['content-length', 'transfer-encoding']},
            )
        else:
            # Handle non-JSON responses
            return StreamingResponse(
                iter([response_data["content"]]),
                status_code=response_data["status_code"],
                headers={k: v for k, v in response_data["headers"].items() 
                        if k.lower() not in ['content-length', 'transfer-encoding']},
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")