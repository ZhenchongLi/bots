from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
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
from src.auth.client_auth import (
    verify_api_key, 
    require_chat_permission, 
    require_completion_permission, 
    require_embedding_permission
)
from src.config.settings import settings
from src.database.connection import get_db_session
from src.database.conversation_repository import ConversationRepository

router = APIRouter(prefix="/v1")


async def log_conversation_if_enabled(
    request: Request,
    messages: list,
    response_content: Optional[str] = None,
    actual_model: Optional[str] = None,
    db: Optional[AsyncSession] = None
):
    """Log conversation if session tracking is enabled via headers"""
    session_id = request.headers.get("X-Session-ID")
    user_identifier = request.headers.get("X-User-ID") or request.client.host
    
    if not session_id or not db:
        return
    
    try:
        repo = ConversationRepository(db)
        
        # Get or create conversation
        conversation = await repo.get_conversation_by_session_id(session_id)
        if not conversation:
            conversation = await repo.create_conversation(
                user_identifier=user_identifier,
                session_id=session_id
            )
        
        # Log user messages
        for message in messages:
            if message.get("role") == "user":
                await repo.add_message(
                    conversation_id=conversation.id,
                    role=message["role"],
                    content=message["content"]
                )
        
        # Log assistant response if available
        if response_content:
            await repo.add_message(
                conversation_id=conversation.id,
                role="assistant",
                content=response_content,
                model_name=actual_model
            )
    except Exception as e:
        # Don't fail the main request if conversation logging fails
        print(f"Failed to log conversation: {e}")
        pass


@router.get("/models", response_model=ModelListResponse)
async def list_models(key_data: Dict[str, Any] = Depends(verify_api_key)):
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
async def create_chat_completion(
    request_obj: ChatCompletionRequest,
    request: Request,
    key_data: Dict[str, Any] = Depends(require_chat_permission),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a chat completion, matching OpenAI API format exactly."""
    try:
        # Validate model availability
        if not model_manager.is_model_available():
            raise HTTPException(
                status_code=503,
                detail="Model is not available or not configured"
            )
        
        # Process model request
        request_dict = request_obj.model_dump()
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
        for msg in request_obj.messages:
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
            "temperature": request_obj.temperature,
            "max_tokens": request_obj.max_tokens,
            "top_p": request_obj.top_p,
            "n": request_obj.n,
            "stream": request_obj.stream,
            "stop": request_obj.stop,
            "presence_penalty": request_obj.presence_penalty,
            "frequency_penalty": request_obj.frequency_penalty,
            "logit_bias": request_obj.logit_bias,
            "user": request_obj.user,
            "tools": request_obj.tools,
            "tool_choice": request_obj.tool_choice
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
        
        if request_obj.stream:
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
                # Log conversation if enabled
                response_content = None
                if response_data["json"].get("choices") and len(response_data["json"]["choices"]) > 0:
                    first_choice = response_data["json"]["choices"][0]
                    if first_choice.get("message") and first_choice["message"].get("content"):
                        response_content = first_choice["message"]["content"]
                
                await log_conversation_if_enabled(
                    request=request,
                    messages=messages,
                    response_content=response_content,
                    actual_model=actual_model,
                    db=db
                )
                
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
async def create_completion(
    request: CompletionRequest,
    key_data: Dict[str, Any] = Depends(require_completion_permission)
):
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
async def create_embeddings(
    request: EmbeddingRequest,
    key_data: Dict[str, Any] = Depends(require_embedding_permission)
):
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