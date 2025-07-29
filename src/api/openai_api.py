from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import orjson as json
import time
import uuid
from datetime import datetime

from src.models.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatChoice,
    ChatMessage,
    Usage,
    ModelListResponse,
    ModelInfo,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingData,
    CompletionRequest,
    CompletionResponse,
    CompletionChoice,
    ErrorResponse,
    ErrorDetail,
    Role
)
from src.core.model_manager import model_manager
from src.core.platform_clients import PlatformClientFactory

router = APIRouter(prefix="/v1")


@router.get("/models", response_model=ModelListResponse)
async def list_models():
    """List available models in OpenAI API format."""
    models = model_manager.get_models_list()
    
    model_data = []
    for model in models:
        model_info = ModelInfo(
            id=model.get("id", "unknown"),
            created=int(datetime.now().timestamp()),
            owned_by=model.get("owned_by", "openai")
        )
        model_data.append(model_info)
    
    return ModelListResponse(data=model_data)


@router.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """Create a chat completion, matching OpenAI API format exactly."""
    try:
        # Validate model availability
        if not model_manager.is_model_available():
            raise HTTPException(
                status_code=503,
                detail="Model is not available or not configured"
            )
        
        # Process model request
        request_dict = request.model_dump()
        try:
            processed_request, actual_model = model_manager.process_model_request(request_dict)
        except ValueError as e:
            error_response = ErrorResponse(
                error=ErrorDetail(
                    message=str(e),
                    type="invalid_request_error",
                    param="model"
                )
            )
            return JSONResponse(
                status_code=400,
                content=error_response.model_dump()
            )
        
        # Get model configuration
        model_config = model_manager.get_model_config()
        
        # Create platform-specific client
        client = PlatformClientFactory.create_client(
            model_config.get("type", "openai"),
            model_config
        )
        
        # Convert messages to proper format for the platform
        messages = []
        for msg in request.messages:
            messages.append({
                "role": msg.role.value,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
                **({"tool_calls": msg.tool_calls} if msg.tool_calls else {}),
                **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {})
            })
        
        # Prepare request data
        request_data = {
            "model": actual_model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "n": request.n,
            "stream": request.stream,
            "stop": request.stop,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "logit_bias": request.logit_bias,
            "user": request.user,
            "tools": request.tools,
            "tool_choice": request.tool_choice
        }
        
        # Remove None values
        request_data = {k: v for k, v in request_data.items() if v is not None}
        
        # Make request to platform
        response_data = await client.make_request(
            method="POST",
            path="/chat/completions",
            headers={"Content-Type": "application/json"},
            json_data=request_data
        )
        
        if request.stream:
            # Handle streaming response
            async def generate_stream():
                # This would need to be implemented based on the actual streaming response
                # For now, return the response as is
                yield f"data: {json.dumps(response_data['json']).decode()}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # Return standard response
            if response_data["json"]:
                return JSONResponse(
                    content=response_data["json"],
                    status_code=response_data["status_code"]
                )
            else:
                raise HTTPException(status_code=500, detail="Invalid response from upstream")
                
    except HTTPException:
        raise
    except Exception as e:
        error_response = ErrorResponse(
            error=ErrorDetail(
                message=f"Internal server error: {str(e)}",
                type="server_error"
            )
        )
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )


@router.post("/completions")
async def create_completion(request: CompletionRequest):
    """Create a completion, matching OpenAI API format exactly."""
    try:
        # Validate model availability
        if not model_manager.is_model_available():
            raise HTTPException(
                status_code=503,
                detail="Model is not available or not configured"
            )
        
        # Process model request
        request_dict = request.model_dump()
        try:
            processed_request, actual_model = model_manager.process_model_request(request_dict)
        except ValueError as e:
            error_response = ErrorResponse(
                error=ErrorDetail(
                    message=str(e),
                    type="invalid_request_error",
                    param="model"
                )
            )
            return JSONResponse(
                status_code=400,
                content=error_response.model_dump()
            )
        
        # Get model configuration
        model_config = model_manager.get_model_config()
        
        # Create platform-specific client
        client = PlatformClientFactory.create_client(
            model_config.get("type", "openai"),
            model_config
        )
        
        # Prepare request data
        request_data = request.model_dump(exclude_none=True)
        request_data["model"] = actual_model
        
        # Make request to platform
        response_data = await client.make_request(
            method="POST",
            path="/completions",
            headers={"Content-Type": "application/json"},
            json_data=request_data
        )
        
        if request.stream:
            # Handle streaming response
            async def generate_stream():
                yield f"data: {json.dumps(response_data['json']).decode()}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # Return standard response
            if response_data["json"]:
                return JSONResponse(
                    content=response_data["json"],
                    status_code=response_data["status_code"]
                )
            else:
                raise HTTPException(status_code=500, detail="Invalid response from upstream")
                
    except HTTPException:
        raise
    except Exception as e:
        error_response = ErrorResponse(
            error=ErrorDetail(
                message=f"Internal server error: {str(e)}",
                type="server_error"
            )
        )
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )


@router.post("/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    """Create embeddings, matching OpenAI API format exactly."""
    try:
        # Validate model availability
        if not model_manager.is_model_available():
            raise HTTPException(
                status_code=503,
                detail="Model is not available or not configured"
            )
        
        # Process model request
        request_dict = request.model_dump()
        try:
            processed_request, actual_model = model_manager.process_model_request(request_dict)
        except ValueError as e:
            error_response = ErrorResponse(
                error=ErrorDetail(
                    message=str(e),
                    type="invalid_request_error",
                    param="model"
                )
            )
            return JSONResponse(
                status_code=400,
                content=error_response.model_dump()
            )
        
        # Get model configuration
        model_config = model_manager.get_model_config()
        
        # Create platform-specific client
        client = PlatformClientFactory.create_client(
            model_config.get("type", "openai"),
            model_config
        )
        
        # Prepare request data
        request_data = request.model_dump(exclude_none=True)
        request_data["model"] = actual_model
        
        # Make request to platform
        response_data = await client.make_request(
            method="POST",
            path="/embeddings",
            headers={"Content-Type": "application/json"},
            json_data=request_data
        )
        
        # Return response
        if response_data["json"]:
            return JSONResponse(
                content=response_data["json"],
                status_code=response_data["status_code"]
            )
        else:
            raise HTTPException(status_code=500, detail="Invalid response from upstream")
            
    except HTTPException:
        raise
    except Exception as e:
        error_response = ErrorResponse(
            error=ErrorDetail(
                message=f"Internal server error: {str(e)}",
                type="server_error"
            )
        )
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )