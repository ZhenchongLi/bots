from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import orjson as json
import time
import uuid
from datetime import datetime
import structlog

logger = structlog.get_logger()

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


async def log_conversation_background(
    session_id: str,
    user_identifier: str,
    messages: list,
    response_content: Optional[str] = None,
    actual_model: Optional[str] = None
):
    """Background task to log conversation to database"""
    try:
        # Create new database session for background task
        from src.database.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            repo = ConversationRepository(db)
            
            logger.info("Starting background conversation logging", 
                       session_id=session_id, 
                       user_identifier=user_identifier,
                       has_response=bool(response_content))
            
            # Get or create conversation
            conversation = await repo.get_conversation_by_session_id(session_id)
            if not conversation:
                logger.info("Creating new conversation", session_id=session_id)
                conversation = await repo.create_conversation(
                    user_identifier=user_identifier,
                    session_id=session_id
                )
            else:
                logger.info("Using existing conversation", 
                           conversation_id=conversation.id, 
                           session_id=session_id)
            
            # Log user messages
            user_message_count = 0
            for message in messages:
                if message.get("role") == "user":
                    await repo.add_message(
                        conversation_id=conversation.id,
                        role=message["role"],
                        content=message["content"]
                    )
                    user_message_count += 1
            
            logger.info("Logged user messages", 
                       conversation_id=conversation.id, 
                       count=user_message_count)
            
            # Log assistant response if available
            if response_content:
                await repo.add_message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=response_content,
                    model_name=actual_model
                )
                logger.info("Logged assistant response", 
                           conversation_id=conversation.id,
                           content_length=len(response_content))
            
            logger.info("Background conversation logging completed successfully", 
                       conversation_id=conversation.id)
                       
    except Exception as e:
        logger.error("Failed to log conversation in background", error=str(e))


async def log_conversation_always(
    request: Request,
    messages: list,
    response_content: Optional[str] = None,
    actual_model: Optional[str] = None,
    db: Optional[AsyncSession] = None
):
    """Log conversation automatically for all requests"""
    # Generate session ID if not provided
    session_id = request.headers.get("X-Session-ID") or f"auto_{request.client.host}_{int(time.time())}"
    user_identifier = request.headers.get("X-User-ID") or request.client.host
    
    if not db:
        return
    
    try:
        repo = ConversationRepository(db)
        
        logger.info("Starting conversation logging", 
                   session_id=session_id, 
                   user_identifier=user_identifier,
                   has_response=bool(response_content))
        
        # Get or create conversation
        conversation = await repo.get_conversation_by_session_id(session_id)
        if not conversation:
            logger.info("Creating new conversation", session_id=session_id)
            conversation = await repo.create_conversation(
                user_identifier=user_identifier,
                session_id=session_id
            )
        else:
            logger.info("Using existing conversation", 
                       conversation_id=conversation.id, 
                       session_id=session_id)
        
        # Log user messages
        user_message_count = 0
        for message in messages:
            if message.get("role") == "user":
                await repo.add_message(
                    conversation_id=conversation.id,
                    role=message["role"],
                    content=message["content"]
                )
                user_message_count += 1
        
        logger.info("Logged user messages", 
                   conversation_id=conversation.id, 
                   count=user_message_count)
        
        # Log assistant response if available
        if response_content:
            await repo.add_message(
                conversation_id=conversation.id,
                role="assistant",
                content=response_content,
                model_name=actual_model
            )
            logger.info("Logged assistant response", 
                       conversation_id=conversation.id,
                       content_length=len(response_content))
        
        logger.info("Conversation logging completed successfully", 
                   conversation_id=conversation.id)
                   
    except Exception as e:
        # Don't fail the main request if conversation logging fails
        logger.error("Failed to log conversation", error=str(e))
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


@router.get("/debug/conversations")
async def debug_conversations(
    db: AsyncSession = Depends(get_db_session),
    key_data: Dict[str, Any] = Depends(verify_api_key)
):
    """Debug endpoint to check conversations in database."""
    from src.database.conversation_repository import ConversationRepository
    
    repo = ConversationRepository(db)
    
    # Get all conversations (limit to 10 for debug)
    from sqlalchemy import select
    from src.models.conversation import Conversation, ConversationMessage
    
    conversations_result = await db.execute(
        select(Conversation).order_by(Conversation.created_at.desc()).limit(10)
    )
    conversations = conversations_result.scalars().all()
    
    result = []
    for conv in conversations:
        messages_result = await db.execute(
            select(ConversationMessage).where(
                ConversationMessage.conversation_id == conv.id
            ).order_by(ConversationMessage.timestamp)
        )
        messages = messages_result.scalars().all()
        
        result.append({
            "id": conv.id,
            "session_id": conv.session_id,
            "title": conv.title,
            "user_identifier": conv.user_identifier,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat(),
            "message_count": len(messages),
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                    "model_name": msg.model_name,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ]
        })
    
    return {"conversations": result, "total_count": len(result)}


@router.post("/chat/completions")
async def create_chat_completion(
    request_obj: ChatCompletionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
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
        
        if request_obj.stream:
            # Handle streaming response
            # Generate session info for background logging
            session_id = request.headers.get("X-Session-ID") or f"auto_{request.client.host}_{int(time.time())}"
            user_identifier = request.headers.get("X-User-ID") or request.client.host
            
            # Store collected content in a container that can be accessed outside the generator
            collected_content_container = {"content": ""}
            
            async def generate_stream():
                try:
                    async for chunk in client.make_stream_request(
                        method="POST",
                        path="/chat/completions",
                        headers={"Content-Type": "application/json"},
                        json_data=request_data
                    ):
                        if chunk.strip():
                            # Try to extract content from chunk for logging
                            try:
                                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                                    chunk_data = json.loads(chunk[6:])  # Remove "data: " prefix
                                    if isinstance(chunk_data, dict) and "choices" in chunk_data:
                                        for choice in chunk_data["choices"]:
                                            if "delta" in choice and "content" in choice["delta"]:
                                                collected_content_container["content"] += choice["delta"]["content"]
                            except:
                                pass  # Ignore parsing errors for content collection
                            
                            yield f"{chunk}\n\n"
                    
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    logger.error("Error in streaming response", error=str(e))
                    error_data = {
                        "error": {
                            "message": f"Streaming error: {str(e)}",
                            "type": "internal_error"
                        }
                    }
                    yield f"data: {json.dumps(error_data).decode()}\n\n"
                    yield "data: [DONE]\n\n"
            
            # Schedule background task immediately (before streaming starts)
            logger.info("Scheduling stream conversation logging", session_id=session_id)
            background_tasks.add_task(
                log_conversation_background,
                session_id=session_id,
                user_identifier=user_identifier,
                messages=messages,
                response_content=None,  # We'll log user messages first
                actual_model=actual_model
            )
            
            # Also schedule a delayed task to log the complete response
            # This is a workaround since we can't easily wait for the generator to complete
            import asyncio
            async def delayed_response_logging():
                await asyncio.sleep(5)  # Wait for stream to likely complete
                if collected_content_container["content"].strip():
                    logger.info("Logging delayed stream response", 
                               session_id=session_id,
                               content_length=len(collected_content_container["content"]))
                    await log_conversation_background(
                        session_id=session_id,
                        user_identifier=user_identifier,
                        messages=[],  # Don't log user messages again
                        response_content=collected_content_container["content"],
                        actual_model=actual_model
                    )
            
            background_tasks.add_task(delayed_response_logging)
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # Make request to platform for non-streaming
            response_data = await client.make_request(
                method="POST",
                path="/chat/completions",
                headers={"Content-Type": "application/json"},
                json_data=request_data
            )
            
            # Return standard response
            if response_data["json"]:
                # Log conversation if enabled
                response_content = None
                if response_data["json"].get("choices") and len(response_data["json"]["choices"]) > 0:
                    first_choice = response_data["json"]["choices"][0]
                    if first_choice.get("message") and first_choice["message"].get("content"):
                        response_content = first_choice["message"]["content"]
                
                await log_conversation_always(
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